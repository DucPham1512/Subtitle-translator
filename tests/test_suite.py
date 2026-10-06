"""Benchmark suite (6.11e): scoring against a frozen baseline, and the sandbox re-run harness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from subagent import bench_run, suite
from subagent.models import (
    CastBoxEdit,
    CastDetection,
    CastLine,
    EditRecord,
    Evaluation,
    LineTranslation,
    ReviewedLine,
    ScriptDecision,
    SpeakerCandidates,
)
from subagent.util import write_jsonl
from tests.conftest import register_episode, sample_events, write_events


def _line(eid: str, i: int, speaker: str | None, vi: str, **kw) -> ReviewedLine:
    return ReviewedLine(event_id=eid, start_ms=i * 2500, end_ms=i * 2500 + 2200, speaker=speaker,
                        listener=kw.pop("listener", None), zh=kw.pop("zh", sample_events()[i].zh), pinyin="",
                        vi=vi, approved=True, **kw)


def make_baseline(folder: Path, ep: str = "ep001", *, aliases: dict[str, str] | None = None) -> Path:
    """One frozen episode: four events; the reviewer fixed a speaker and a translation and deleted line 3."""
    work = folder / ep
    events = sample_events(ep)
    raw = [e.model_copy(update={"zh_raw": e.zh.replace("了", "7")}) for e in events]
    write_events(work, events)
    write_events(work, raw, "events_raw.jsonl")
    ids = [e.id for e in events]
    write_jsonl(work / "approved.jsonl", [
        _line(ids[0], 0, "co_tu", "Đệ tử đã Trúc Cơ.", listener="npc_001_01"),
        _line(ids[1], 1, "npc_001_01", "Rất tốt.", listener="co_tu"),
        _line(ids[2], 2, "npc_001_01", "Đệ tử muốn xuống núi."),
        _line(ids[3], 3, None, "Xuống núi?", deleted=True)])
    write_jsonl(work / "edits.jsonl", [
        EditRecord(edit_id=f"{ids[2]}:speaker", event_id=ids[2], field="speaker", before="co_tu", after="npc_001_01"),
        EditRecord(edit_id=f"{ids[2]}:vi", event_id=ids[2], field="vi", before="Ta muốn đi.",
                   after="Đệ tử muốn xuống núi."),
        EditRecord(edit_id=f"{ids[3]}:deleted", event_id=ids[3], field="deleted", before="false", after="true")])
    write_jsonl(work / "translations.jsonl", [
        LineTranslation(event_id=ids[0], speaker="co_tu", listener="npc_001_07", speaker_conf=0.9,
                        vi="Đệ tử đã Trúc Cơ.", attempts=1),
        LineTranslation(event_id=ids[1], speaker="npc_001_07", listener="co_tu", speaker_conf=0.6, vi="Rất tốt.",
                        attempts=1),
        LineTranslation(event_id=ids[2], speaker="co_tu", listener=None, speaker_conf=0.5, vi="Ta muốn đi.",
                        attempts=2),
        LineTranslation(event_id=ids[3], speaker=None, listener=None, speaker_conf=0.0, vi="Xuống núi?", attempts=1)])
    write_jsonl(work / "evaluations.jsonl", [
        Evaluation(event_id=ids[0], attempt=1, passed=True, scores={"meaning": 5, "speaker": 5}),
        Evaluation(event_id=ids[1], attempt=1, passed=True, scores={"meaning": 4, "speaker": 3}),
        Evaluation(event_id=ids[2], attempt=1, passed=False, scores={"meaning": 2, "speaker": 2}),
        Evaluation(event_id=ids[2], attempt=2, passed=False, scores={"meaning": 2, "speaker": 4}),
        Evaluation(event_id=ids[3], attempt=1, passed=True, scores={"meaning": 5})])
    write_jsonl(work / "speakers.jsonl", [
        SpeakerCandidates(event_id=ids[0], candidates=[("co_tu", 0.8)], status="fixed"),
        SpeakerCandidates(event_id=ids[1], candidates=[("npc_001_07", 0.7)], status="new_voice"),
        SpeakerCandidates(event_id=ids[2], candidates=[("co_tu", 0.5), ("npc_001_07", 0.45)], status="confusable"),
        SpeakerCandidates(event_id=ids[3], status="too_short")])
    write_jsonl(work / "cast.jsonl", [CastLine(event_id=e) for e in ids])
    write_jsonl(work / "script_review.jsonl", [
        ScriptDecision(event_id=ids[3], action="remove", reason="noise", source="llm"),
        ScriptDecision(event_id=ids[0], action="fix", reason="ocr", source="llm", zh_fix="师尊，弟子已经筑基7。",
                       evidence="x")])
    write_jsonl(work / "pinyin.jsonl", [])
    manifest = folder / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {"name": "b", "episodes": {}}
    data["episodes"][ep] = {"memory_at_run": f"sha-{ep}"}
    manifest.write_text(json.dumps(data), encoding="utf-8")
    if aliases:
        (folder / "aliases.json").write_text(json.dumps(
            {"aliases": [{"id": k, "same_as": v} for k, v in aliases.items()]}), encoding="utf-8")
    return work


def test_group_map_is_one_to_one_by_shared_lines():
    pairs = [("a", "x"), ("a", "x"), ("b", "x"), ("b", "y"), ("c", "known")]
    assert suite.group_map(pairs, {"a", "b", "c"}, {"x", "y"}) == {"a": "x", "b": "y"}


def test_speakers_group_automatic_ids_onto_new_characters_only(project, monkeypatch):
    config, paths = project
    folder = paths.work / "_baseline" / "b"
    make_baseline(folder)
    monkeypatch.setattr(suite, "characters_at", lambda memory, sha, cache=None: {"co_tu"})
    s = suite.score_speakers(config, paths, suite.load_gold(folder), folder)
    # npc_001_07 groups the lines of the reviewer's npc_001_01, so its numbering does not count
    assert s["grouped"]["translator"] == {"npc_001_07": "npc_001_01"}
    assert (s["speaker_known"]["right"], s["speaker_known"]["of"]) == (1, 1)
    assert (s["speaker_new"]["right"], s["speaker_new"]["of"]) == (1, 2)       # line 2: co_tu, not the NPC
    assert (s["listener"]["right"], s["listener"]["of"]) == (3, 3)
    assert s["voice_by_status"]["confusable"]["voice"]["right"] == 0
    assert [w["event_id"] for w in s["wrong"]] == ["ep001:0002"]


def test_aliases_count_as_one_character(project, monkeypatch):
    config, paths = project
    folder = paths.work / "_baseline" / "b"
    make_baseline(folder, aliases={"npc_001_07": "npc_001_01"})
    monkeypatch.setattr(suite, "characters_at", lambda memory, sha, cache=None: {"co_tu"})
    s = suite.score_speakers(config, paths, suite.load_gold(folder), folder)
    assert s["grouped"]["translator"] == {"npc_001_01": "npc_001_01"} and s["speaker_new"]["right"] == 1


def test_cast_gold_follows_the_review_edits():
    det = [CastDetection(index=0, box=[0, 0, 10, 10], score=0.9, label="a", character="co_tu"),
           CastDetection(index=1, box=[20, 0, 30, 10], score=0.9, label="a", unknown="u001"),
           CastDetection(index=2, box=[40, 0, 50, 10], score=0.9, label="a", character="bac_ty")]
    cast = CastLine(event_id="ep001:0000", detections=det, talking=1)
    line = _line("ep001:0000", 0, "tieu_luong", "x", cast_checked=True, cast_labels={"1": "npc_001_01", "2": "_none"},
                 cast_added=[CastBoxEdit(box=[60, 0, 70, 10])], cast_talking="a0")
    boxes, talking = suite.gold_boxes(line, cast)
    # the drawn box the reviewer marked talking, with no name of its own, is the speaker
    assert [lab for _, lab in boxes] == ["co_tu", "npc_001_01", "_none", "tieu_luong"]
    assert talking == [60, 0, 70, 10]


def test_cast_scores_boxes_names_and_talker(project):
    config, paths = project
    folder = paths.work / "_baseline" / "b"
    work = make_baseline(folder)
    det = [CastDetection(index=0, box=[0, 0, 10, 10], score=0.9, label="a", character="co_tu"),
           CastDetection(index=1, box=[20, 0, 30, 10], score=0.9, label="a", unknown="u001"),
           CastDetection(index=2, box=[40, 0, 50, 10], score=0.9, label="a", character="bac_ty")]
    write_jsonl(work / "cast.jsonl", [CastLine(event_id="ep001:0000", detections=det, talking=1)])
    lines = [x.model_copy(update={"cast_checked": True, "cast_labels": {"1": "npc_001_01", "2": "_none"},
                                  "cast_added": [CastBoxEdit(box=[60, 0, 70, 10], character="tieu_luong")],
                                  "cast_talking": "0"}) if x.event_id == "ep001:0000" else x
             for x in suite._approved(work)]
    write_jsonl(work / "approved.jsonl", lines)
    c = suite.score_cast(suite.load_gold(folder), folder)
    assert c["lines"] == 1
    assert (c["box_recall"]["right"], c["box_recall"]["of"]) == (2, 3)        # the drawn box was missed
    assert (c["box_precision"]["right"], c["box_precision"]["of"]) == (2, 3)  # one box is not a character
    assert (c["names"]["right"], c["names"]["of"], c["names_unrecognised"]) == (1, 2, 1)
    assert (c["talker"]["right"], c["talker"]["of"]) == (0, 1)               # the reviewer moved the talker


def test_translation_and_evaluator_scores(project, monkeypatch):
    config, paths = project
    folder = paths.work / "_baseline" / "b"
    make_baseline(folder)
    gold = suite.load_gold(folder)
    t = suite.score_translation(config, gold, folder, {"ep001:0000": True, "ep001:0001": True, "ep001:0002": False})
    assert (t["exact"]["right"], t["exact"]["of"]) == (2, 3)
    assert t["similarity"]["rewritten"]["lines"] == 1 and t["similarity"]["speaker"]["lines"] == 1
    ev = t["evaluator"]
    assert (ev["catch_failed"]["right"], ev["catch_failed"]["of"]) == (1, 1)      # kept attempt 2 still failed
    assert (ev["false_alarm_failed"]["right"], ev["false_alarm_failed"]["of"]) == (0, 2)
    assert (ev["false_alarm_doubt"]["right"], ev["false_alarm_doubt"]["of"]) == (1, 2)   # a 3 is a doubt
    # the kept attempt (best rank: same verdict, higher total) scored the speaker 4: the wrong speaker slipped by
    assert (ev["speaker_catch_failed"]["right"], ev["speaker_catch_failed"]["of"]) == (0, 1)


def test_script_review_and_ocr_levels(project):
    config, paths = project
    folder = paths.work / "_baseline" / "b"
    make_baseline(folder)
    gold = suite.load_gold(folder)
    sr = suite.score_script_review(config, gold, folder)
    assert (sr["predelete_precision"]["right"], sr["predelete_precision"]["of"]) == (1, 1)
    assert sr["predeleted_by_source"] == {"script_noise": {"lines": 1, "deleted_by_reviewer": 1}}
    assert sr["fixes"] == {"suggested": 1, "right": 0, "harmful": 1}      # it broke a right line
    o = suite.score_ocr(gold, folder)
    assert o["raw"]["exact"] == 2 and o["ocr_fix"]["exact"] == 3 and o["fixes_accepted"]["exact"] == 2


def test_stage_plan():
    assert bench_run.stage_plan("translate", "snapshot") == ["translate", "sprite", "script_review"]
    assert bench_run.stage_plan("translate", "chain")[0] == "audio"
    assert "audio" in bench_run.stage_plan("ocr_fix", "snapshot")
    from subagent.errors import SubagentError

    with pytest.raises(SubagentError):
        bench_run.stage_plan("ocr", "snapshot")                # the bands are not frozen


@pytest.mark.parametrize("mode", ["snapshot", "chain"])
def test_run_works_in_a_sandbox_and_learns_from_the_gold_in_chain_mode(project, monkeypatch, mode):
    config, paths = project
    folder = paths.work / "_baseline" / "b"
    for n in (1, 2):
        register_episode(paths, n)
        make_baseline(folder, f"ep00{n}")
    checkouts, ran, learned = [], [], []
    monkeypatch.setattr(bench_run, "checkout_memory", lambda real, sp, sha: checkouts.append(sha))
    monkeypatch.setattr(suite, "characters_at", lambda memory, sha, cache=None: {"co_tu"})

    def stage(name, ctx):
        ran.append((ctx.episode.id, name))
        assert ctx.paths.memory.is_relative_to(paths.work / "_suite")
        if name == "translate":       # the frozen inputs are there; the earlier episode holds its frozen review
            assert (ctx.work / "speakers.jsonl").is_file() and (ctx.work / "pinyin.jsonl").is_file()
            if ctx.episode.id == "ep002":
                assert (ctx.paths.episode_dir("ep001") / "approved.jsonl").is_file()
            write_jsonl(ctx.work / "translations.jsonl", [
                LineTranslation(event_id=e.id, speaker="co_tu", listener=None, speaker_conf=1, vi="khác", attempts=1)
                for e in sample_events(ctx.episode.id)])

    def learner(cfg, sp, ctx):
        learned.append(ctx.episode.id)
        assert (ctx.work / "approved.jsonl").is_file()          # learning reads the frozen review
        return 0.0

    r = bench_run.run(config, paths, folder, mode=mode, from_stage="translate", episodes=["ep002"], label="t",
                      stage_runner=stage, learner=learner)
    assert [e for e, n in ran if n == "translate"] == ["ep002"]      # ep001 is not scored, only learned from
    assert checkouts == (["sha-ep002"] if mode == "snapshot" else ["sha-ep001"])
    assert learned == ([] if mode == "snapshot" else ["ep001"])
    out = Path(r.system)
    assert sorted(p.name for p in out.iterdir()) == ["ep002"] and r.translation["exact"]["right"] == 0
    assert not paths.episode_dir("ep002").exists()                 # nothing real was written
    assert (out.parent / "report.md").is_file() and (paths.work / "_suite" / "history.jsonl").is_file()
