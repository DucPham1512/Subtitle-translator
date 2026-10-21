"""Who is on screen and who is talking, and the sprite bank learned from reviewed speakers (5.8b).

The detector, image model, frames and motion are fakes: a "frame" encodes which characters are on screen,
and each character's look is a fixed unit vector.
"""

from __future__ import annotations

import numpy as np

from subagent.kernel.models import (
    CastDetection,
    CastLine,
    EpisodeState,
    ReviewedLine,
    SpeakerCandidates,
    VideoInfo,
)
from subagent.kernel.util import read_jsonl, write_jsonl
from subagent.memory.manager import MemoryManager
from subagent.memory.sprite_learning import learn_sprites, plan
from subagent.stages import cast
from subagent.workspace.context import EpisodeContext
from subagent.workspace.state import save_state
from tests.conftest import make_episode, register_episode, sample_events, seed_memory, write_events

DIM = 8
LOOK = {"lin_yuan": 0, "shi_zun": 1, "stranger": 2}


def _vec(k: int, wobble: float = 0.0) -> np.ndarray:
    v = np.zeros(DIM, np.float32)
    v[k] = 1.0
    v[(k + 3) % DIM] = wobble
    return v / np.linalg.norm(v)


class FakeEngine:
    """Frame = (H, W, 3) array whose first row lists who is on screen (look index + 1, 0 = nobody)."""

    def detect(self, frame, threshold):
        who = [int(v) - 1 for v in frame[0, :, 0] if v > 0]
        return [([100.0 + 200 * n, 50.0, 250.0 + 200 * n, 450.0], 0.5, "a cartoon character")
                for n, _ in enumerate(who)]

    def embed(self, crops):
        return np.stack([_vec(int(c[0, 0, 1]) - 1, 0.1) for c in crops])


def _frame(*names: str) -> np.ndarray:
    f = np.zeros((540, 960, 3), np.uint8)
    for n, name in enumerate(names):
        f[0, n, 0] = LOOK[name] + 1
        f[50:450, 100 + 200 * n:250 + 200 * n, 1] = LOOK[name] + 1   # the crop carries the look
    return f


# -- pure helpers ----------------------------------------------------------------------------------

def test_box_filter_and_talking(project):
    config, _ = project
    cfg = config.cast
    dets = [([0, 0, 100, 300], 0.9, "c"), ([10, 10, 90, 290], 0.8, "c"),     # overlapping: one kept
            ([0, 0, 100, 20], 0.9, "c"),                                     # too short
            ([500, 0, 650, 300], 0.1, "c"),                                  # too unsure
            ([700, 0, 800, 300], 0.5, "c")]
    assert cast.keep_boxes(dets, cfg, 960, 540) == [0, 4]
    assert cast.talking_index([5.0, 2.0, 1.0], 1.6) == 0
    assert cast.talking_index([5.0, 4.0], 1.6) is None                       # nobody clearly talks
    assert cast.talking_index([5.0, None], 1.6) is None                      # one measurable sprite: no claim


def test_match_needs_a_clear_winner(project):
    config, _ = project
    bank = {"lin_yuan": (np.stack([_vec(0)]), [1]), "shi_zun": (np.stack([_vec(1)]), [2])}
    assert cast.match(_vec(0, 0.2), bank, config.cast)[:1] == ("lin_yuan",)
    assert cast.match(_vec(2), bank, config.cast)[0] is None                 # nobody close: unknown
    blend = (_vec(0) + _vec(1)) / np.linalg.norm(_vec(0) + _vec(1))
    assert cast.match(blend, bank, config.cast)[0] is None                   # two equally close: unknown


# -- stage -----------------------------------------------------------------------------------------

def test_stage_records_cast_and_talker(project):
    config, paths = project
    config.cast.enabled = True
    seed_memory(config, paths)
    MemoryManager(paths, config).write_sprites([("lin_yuan", _vec(0), "ep000", "x")], {}, [], max_per_character=60)
    ctx = EpisodeContext(config, paths, make_episode(paths, 1))
    events = sample_events()[:2]
    write_events(ctx.work, events)
    (ctx.work / "video.json").write_text(VideoInfo(width=1280, height=720, duration_ms=10000, fps=30,
                                                   has_audio=True).model_dump_json(), encoding="utf-8")
    frames = {0: _frame("lin_yuan", "stranger"), 1: _frame("stranger")}

    def frames_fn(times, w, h):
        return {t: frames[i] for i, t in enumerate(sorted(times))}

    counts = cast.run(ctx, engine=FakeEngine(), motion_fn=lambda e, boxes: [1.0, 4.0][: len(boxes)],
                      frames_fn=frames_fn)
    lines = {c.event_id: c for c in read_jsonl(ctx.artifact("cast.jsonl"), CastLine)}
    first = lines["ep001:0000"]
    assert first.on_screen() == ["lin_yuan"] and first.talker().character is None   # the stranger talks
    assert first.detections[1].unknown == lines["ep001:0001"].detections[0].unknown == "u001"
    assert counts == {"lines": 2, "characters": 3, "recognised": 1, "unknown_sprites": 1, "talking": 1,
                      "talking_recognised": 0}
    assert np.load(ctx.artifact("cast_embeddings.npy")).shape == (3, DIM)
    assert cast.load_frame(ctx.work, "ep001:0000").shape == (540, 960, 3)      # the analysed frame is kept


def test_translator_sees_the_cast(project):
    from subagent.stages.translate import line_input

    config, paths = project
    ctx = EpisodeContext(config, paths, make_episode(paths, 1))
    line = CastLine(event_id="ep001:0000", talking=1, detections=[
        CastDetection(index=0, box=[0, 0, 1, 1], score=0.5, label="c", character="lin_yuan"),
        CastDetection(index=1, box=[0, 0, 1, 1], score=0.5, label="c", unknown="u001")])
    row = line_input(sample_events()[0], None, ctx, line)
    assert row["on_screen"] == ["lin_yuan"] and row["unrecognised_on_screen"] == 1 and row["talking"] == "unrecognised"
    assert "on_screen" not in line_input(sample_events()[0], None, ctx, None)
    # a sure voice is never changed by the picture: by default the translator does not see it there
    sure = SpeakerCandidates(event_id="ep001:0000", status="new_voice", candidates=[("npc_001_01", 0.8)])
    assert "talking" not in line_input(sample_events()[0], sure, ctx, line)
    unsure = sure.model_copy(update={"status": "confusable"})
    assert line_input(sample_events()[0], unsure, ctx, line)["talking"] == "unrecognised"
    config.translate.picture_evidence = "all"
    assert "talking" in line_input(sample_events()[0], sure, ctx, line)
    config.translate.picture_evidence = "off"
    assert "on_screen" not in line_input(sample_events()[0], unsure, ctx, line)


# -- learning --------------------------------------------------------------------------------------

def _lines(spec: list[tuple[list[str], int | None]], start: int = 0) -> tuple[list[CastLine], np.ndarray]:
    """spec: (who is on screen, position of the talker)."""
    lines, embs = [], []
    for n, (who, talking) in enumerate(spec):
        dets = []
        for name in who:
            dets.append(CastDetection(index=len(embs), box=[0, 0, 1, 1], score=0.5, label="c"))
            embs.append(_vec(LOOK[name], 0.1 * (n % 3)))
        lines.append(CastLine(event_id=f"ep001:{start + n:04d}", detections=dets, talking=talking))
    return lines, np.stack(embs)


def test_votes_name_an_unknown_sprite_and_corrections_remove_wrong_exemplars(project):
    config, _ = project
    # shi_zun's look was wrongly learned as lin_yuan's; lin_yuan himself is not in the bank yet
    bank = {"lin_yuan": (np.stack([_vec(1)]), [7])}
    lines, embs = _lines([(["lin_yuan", "shi_zun"], 1)] * 2 + [(["lin_yuan", "shi_zun"], 0)] * 3)
    speakers = {ln.event_id: ("shi_zun" if ln.talking == 1 else "lin_yuan") for ln in lines}
    additions, stats, removals, result = plan(lines, embs, speakers, bank, {7: (0, 0)}, config, "ep001")
    assert result.corrected == 2 and removals == [7]                        # the wrong exemplar goes
    assert set(result.named.values()) == {"lin_yuan"}                       # 3 talking votes: named
    assert {c for c, *_ in additions} == {"lin_yuan"}
    assert "shi_zun" not in {c for c, *_ in additions}                      # 2 votes are not enough


def test_learn_sprites_end_to_end(project):
    config, paths = project
    seed_memory(config, paths)
    ep = register_episode(paths, 1)
    work = paths.episode_dir(ep.id)
    lines, embs = _lines([(["lin_yuan", "shi_zun"], 0)] * 3 + [(["lin_yuan", "shi_zun"], 1)] * 3)
    write_jsonl(work / "cast.jsonl", lines)
    np.save(work / "cast_embeddings.npy", embs)
    write_jsonl(work / "approved.jsonl", [
        ReviewedLine(event_id=ln.event_id, start_ms=0, end_ms=1000, speaker="lin_yuan" if ln.talking == 0 else "shi_zun",
                     listener=None, zh="字", pinyin="", vi="x", approved=True) for ln in lines])
    save_state(work, EpisodeState(episode_id=ep.id, mode="human"))
    result = learn_sprites(config, paths, ep.id)
    assert result.named and set(result.named.values()) == {"lin_yuan", "shi_zun"}
    m = MemoryManager(paths, config)
    bank = cast.build_bank(m.store)
    assert cast.match(_vec(LOOK["shi_zun"], 0.05), bank, config.cast)[0] == "shi_zun"
    assert m.history(1)[0].message.startswith("sprites from ep001")
    # deleting a character deletes its sprites
    from subagent.kernel.models import MemoryProposal
    m.manual_edit([MemoryProposal(kind="character", source="human", payload={"id": "shi_zun", "_delete": True})])
    assert "shi_zun" not in cast.build_bank(m.store)


def test_auto_mode_learns_only_from_trusted_lines(project):
    config, paths = project
    seed_memory(config, paths)
    ep = register_episode(paths, 1)
    work = paths.episode_dir(ep.id)
    lines, embs = _lines([(["lin_yuan", "shi_zun"], 0)] * 3)
    write_jsonl(work / "cast.jsonl", lines)
    np.save(work / "cast_embeddings.npy", embs)
    write_jsonl(work / "approved.jsonl", [ReviewedLine(event_id=ln.event_id, start_ms=0, end_ms=1000, speaker="lin_yuan",
                                                       listener=None, zh="字", pinyin="", vi="x", approved=True)
                                          for ln in lines])
    save_state(work, EpisodeState(episode_id=ep.id, mode="auto"))   # no speakers.jsonl: nothing is trusted
    assert learn_sprites(config, paths, ep.id).named == {}


def test_backfill_runs_cast_where_missing_then_learns(project, monkeypatch):
    from subagent.pipeline import Pipeline
    from subagent.workspace.episodes import Registry
    from subagent.workspace.state import load_state

    config, paths = project
    config.cast.enabled = True
    seed_memory(config, paths)
    ep = register_episode(paths, 1)
    Registry(paths).set_status(ep.id, "done")
    work = paths.episode_dir(ep.id)
    lines, embs = _lines([(["lin_yuan", "shi_zun"], 0)] * 3)
    write_jsonl(work / "approved.jsonl", [ReviewedLine(event_id=ln.event_id, start_ms=0, end_ms=1000, speaker="lin_yuan",
                                                       listener=None, zh="字", pinyin="", vi="x", approved=True)
                                          for ln in lines])
    save_state(work, EpisodeState(episode_id=ep.id, mode="human"))
    ran = []

    def fake_cast(ctx):
        ran.append(ctx.episode.id)
        write_jsonl(ctx.artifact("cast.jsonl"), lines)
        np.save(ctx.artifact("cast_embeddings.npy"), embs)
        return {"lines": len(lines)}

    monkeypatch.setattr("subagent.stages.cast.run", fake_cast)
    out = Pipeline(config, paths).learn_sprites_backfill()
    assert ran == ["ep001"] and out[0][0] == "ep001" and out[0][1]["named"] == 1
    assert Pipeline(config, paths).learn_sprites_backfill()[0][1] == out[0][1]     # second run: nothing relearned
    assert load_state(work, ep.id).stages["cast"].status == "done"


def test_reviewer_box_labels_teach_first(project):
    from subagent.stages.cast import NOT_A_CHARACTER
    from subagent.stages.review import compute_edits

    config, _ = project
    bank = {"lin_yuan": (np.stack([_vec(1)]), [7])}                 # shi_zun's look wrongly filed as lin_yuan
    lines, embs = _lines([(["shi_zun", "stranger"], None)])
    labels = {"ep001:0000": {"0": "shi_zun", "1": NOT_A_CHARACTER}}
    additions, stats, removals, result = plan(lines, embs, {}, bank, {7: (0, 0)}, config, "ep001", labels)
    assert result.labelled == 1 and removals == [7]                  # the exemplar that misnamed it goes
    assert [(c, ev) for c, _, _, ev in additions] == [("shi_zun", "ep001:0000")]   # the stranger is never learned
    before = ReviewedLine(event_id="ep001:0000", start_ms=0, end_ms=1, speaker=None, listener=None, zh="字",
                          pinyin="", vi="x")
    after = before.model_copy(update={"cast_labels": labels["ep001:0000"]})
    edit = compute_edits([before], [after])[0]
    assert edit.field == "cast_labels" and edit.before is None and '"0": "shi_zun"' in edit.after


def test_reviewer_box_edits_and_talking_mark_teach(project):
    from subagent.kernel.models import CastBoxEdit
    from subagent.memory.sprite_learning import apply_review_edits

    config, _ = project
    lines, embs = _lines([(["stranger", "lin_yuan"], 1)])            # detector: lin_yuan talks; shi_zun was missed
    reviewed = {"ep001:0000": ReviewedLine(
        event_id="ep001:0000", start_ms=0, end_ms=1, speaker="shi_zun", listener=None, zh="字", pinyin="", vi="x",
        cast_boxes={"0": [0, 0, 5, 5]}, cast_added=[CastBoxEdit(box=[10, 10, 20, 20], character="shi_zun")],
        cast_talking="a0")}
    seen = []

    def embed(event_id, boxes):
        seen.append(boxes)
        return np.stack([_vec(LOOK["stranger"], 0.3), _vec(LOOK["shi_zun"])])

    new_lines, new_embs, labels = apply_review_edits(lines, embs, reviewed, {"ep001:0000": "shi_zun"}, embed)
    ln = new_lines[0]
    assert seen == [[[0, 0, 5, 5], [10, 10, 20, 20]]]                # moved box and drawn box described again
    assert ln.detections[0].box == [0, 0, 5, 5] and ln.detections[0].index == 2
    assert len(ln.detections) == 3 and ln.talking == 2 and labels == {"ep001:0000": {"2": "shi_zun"}}
    additions, *_ = plan(new_lines, new_embs, {"ep001:0000": "shi_zun"}, {}, {}, config, "ep001", labels)
    assert [(c, ev) for c, _, _, ev in additions] == [("shi_zun", "ep001:0000")]

    # "none": the reviewer says nobody on screen talks, so the detector's talker teaches nothing
    reviewed["ep001:0000"] = reviewed["ep001:0000"].model_copy(update={"cast_added": [], "cast_boxes": {},
                                                                       "cast_talking": "none"})
    new_lines, _, labels = apply_review_edits(lines, embs, reviewed, {"ep001:0000": "shi_zun"}, embed)
    assert new_lines[0].talking is None and labels == {}


def test_picture_veto_disputes_the_voice(project):
    from subagent.stages.evaluate import RuleContext, rule_checks
    from subagent.stages.translate import picture_veto

    config, paths = project
    seed_memory(config, paths)

    def line(eid, talker_char=None, unknown=False, talking=True):
        dets = [CastDetection(index=0, box=[0, 0, 1, 1], score=0.5, label="c", character="lin_yuan"),
                CastDetection(index=1, box=[0, 0, 1, 1], score=0.5, label="c", similarity=0.8,
                              character=talker_char, unknown="u001" if unknown else None)]
        return CastLine(event_id=eid, detections=dets, talking=1 if talking else None)

    voice = lambda eid, status, *c: SpeakerCandidates(event_id=eid, status=status,  # noqa: E731
                                                      candidates=[(x, 0.7) for x in c])
    speakers = {"a": voice("a", "fixed", "lin_yuan"), "b": voice("b", "fixed", "lin_yuan"),
                "c": voice("c", "fixed", "lin_yuan"), "d": voice("d", "confusable", "lin_yuan", "shi_zun"),
                "e": voice("e", "fixed", "lin_yuan")}
    cast_lines = {"a": line("a", "shi_zun"), "b": line("b", unknown=True), "c": line("c", "lin_yuan"),
                  "d": line("d", "shi_zun"), "e": line("e", "shi_zun", talking=False)}
    assert picture_veto(speakers, cast_lines, "off") is speakers
    rec = picture_veto(speakers, cast_lines, "recognised")
    assert rec["a"].status == "disputed" and [c for c, _ in rec["a"].candidates] == ["lin_yuan", "shi_zun"]
    assert rec["b"].status == "fixed"                       # unrecognised talker: only in "any"
    assert rec["c"].status == "fixed" and rec["d"].status == "confusable" and rec["e"].status == "fixed"
    assert picture_veto(speakers, cast_lines, "any")["b"].status == "disputed"

    from subagent.kernel.models import LineTranslation
    from subagent.memory.store import MemoryStore
    event = sample_events()[0]
    rc = RuleContext(config, MemoryStore(paths.memory_db))
    blank = LineTranslation(event_id=event.id, speaker=None, listener=None, speaker_conf=0.3, vi="Đi thôi.", attempts=1)
    fails, _ = rule_checks(blank, event, rec["a"], rc)
    assert not [f for f in fails if f.code == "speaker_not_candidate"]     # disputed: blank is allowed
    fails, _ = rule_checks(blank, event, speakers["d"], rc)
    assert [f for f in fails if f.code == "speaker_not_candidate"]         # confusable: still must choose


def test_learning_an_episode_again_replaces_what_it_learned(project):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    m.write_sprites([("lin_yuan", _vec(LOOK["lin_yuan"]), "ep000", "x")], {}, [], max_per_character=60)
    ep = register_episode(paths, 1)
    work = paths.episode_dir(ep.id)
    lines, embs = _lines([(["lin_yuan", "shi_zun"], 0)] * 3 + [(["lin_yuan", "shi_zun"], 1)] * 3)
    write_jsonl(work / "cast.jsonl", lines)
    np.save(work / "cast_embeddings.npy", embs)
    write_jsonl(work / "approved.jsonl", [
        ReviewedLine(event_id=ln.event_id, start_ms=0, end_ms=1000, speaker="lin_yuan" if ln.talking == 0 else "shi_zun",
                     listener=None, zh="字", pinyin="", vi="x", approved=True) for ln in lines])
    save_state(work, EpisodeState(episode_id=ep.id, mode="human"))

    def bank() -> list:
        return sorted((e.character_id, e.right, e.wrong, e.embedding.tobytes()) for e in m.store.sprite_exemplars())

    learn_sprites(config, paths, ep.id)
    once = bank()
    assert any(right for _, right, _, _ in once)              # the old exemplar earned votes
    learn_sprites(config, paths, ep.id)                        # the review finished again
    assert bank() == once
