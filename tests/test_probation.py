"""Probation for new characters (5.15b): a candidate first, a character once it comes back."""

from __future__ import annotations

import numpy as np

from subagent.kernel.models import (
    CastDetection,
    CastLine,
    LineTranslation,
    MemoryProposal,
    NewVoice,
    ReviewedLine,
    SpeakerCandidates,
)
from subagent.kernel.util import write_jsonl
from subagent.memory.manager import MemoryManager
from subagent.memory.probation import check_return
from subagent.memory.store import Candidate
from subagent.stages.voice import find_new_voices, save_line_voices
from tests.conftest import register_episode, seed_memory


def _unit(k: int, wobble: int = 0) -> np.ndarray:
    v = np.zeros(8, np.float32)
    v[k] = 1.0
    v[(k + 1 + wobble) % 8] += 0.15
    return v / np.linalg.norm(v)


def _lines(ep: str, ids: list[int], speaker: str, listener: str = "lin_yuan") -> list[ReviewedLine]:
    return [ReviewedLine(event_id=f"{ep}:{i:04d}", start_ms=i * 1000, end_ms=i * 1000 + 900, speaker=speaker,
                         listener=listener, zh="掌柜的", pinyin="", vi="x", approved=True) for i in ids]


def _finish(m: MemoryManager, paths, ep: str, lines: list[ReviewedLine], voices: list[NewVoice],
            translations: list[LineTranslation] | None = None, mode: str = "human"):
    work = paths.episode_dir(ep)
    work.mkdir(parents=True, exist_ok=True)
    save_line_voices(work / "voice_embeddings.npz", {x.event_id: _unit(5) for x in lines})
    write_jsonl(work / "approved.jsonl", lines)
    return m.episode_update(ep, lines, translations or [], [], None, new_voices=voices, mode=mode)


def test_returning_candidate_keeps_its_id_in_the_voice_stage(project):
    config, _ = project
    bank = {"lin_yuan": _unit(0), "shi_zun": _unit(1)}
    results = [SpeakerCandidates(event_id=f"ep006:{i:04d}", status="unknown",
                                 candidates=[("lin_yuan", 0.1), ("shi_zun", 0.05)]) for i in range(5)]
    embs = {"ep006:0000": _unit(5), "ep006:0001": _unit(6), "ep006:0002": _unit(6, 1), "ep006:0003": _unit(6, 2),
            "ep006:0004": _unit(3)}
    cand = Candidate(id="npc_005_01", first_episode="ep005", n_lines=3, name_vi="Vương chưởng quỹ",
                     embedding=_unit(5, 1))
    updated, voices = find_new_voices(results, embs, bank, config.voice, 6, [cand])
    by_id = {v.id: v for v in voices}
    assert by_id["npc_005_01"].event_ids == ["ep006:0000"]
    assert by_id["npc_005_01"].returning_from == "ep005" and by_id["npc_005_01"].name_vi == "Vương chưởng quỹ"
    assert by_id["npc_006_01"].event_ids == ["ep006:0001", "ep006:0002", "ep006:0003"]   # a brand-new voice
    line = {r.event_id: r for r in updated}["ep006:0000"]
    assert line.status == "new_voice" and line.candidates[0][0] == "npc_005_01"


def test_a_new_voice_waits_on_probation_and_is_promoted_when_it_comes_back(project):
    config, paths = project
    seed_memory(config, paths)
    for n in (5, 6):
        register_episode(paths, n)
    m = MemoryManager(paths, config)
    naming = MemoryProposal(kind="character", source="translator", evidence=["ep005:0002"], payload={
        "id": "npc_005_01", "name_zh": "王掌柜", "name_vi": "Vương chưởng quỹ", "description": "chủ quán"})
    pair = MemoryProposal(kind="pronoun_pair", source="translator", evidence=["ep005:0001"], payload={
        "speaker_id": "npc_005_01", "listener_id": "lin_yuan", "self_term": "lão phu", "address_term": "tiểu tử"})
    tr = [LineTranslation(event_id="ep005:0002", speaker="npc_005_01", listener="lin_yuan", speaker_conf=0.8,
                          vi="x", attempts=1, proposals=[naming]),
          LineTranslation(event_id="ep005:0001", speaker="npc_005_01", listener="lin_yuan", speaker_conf=0.8,
                          vi="x", attempts=1, proposals=[pair])]
    voices = [NewVoice(id="npc_005_01", event_ids=["ep005:0001"], cohesion=0.8),
              NewVoice(id="npc_005_02", event_ids=["ep005:0009"], cohesion=0.8)]
    r5 = _finish(m, paths, "ep005", _lines("ep005", [1, 2, 3], "npc_005_01") + _lines("ep005", [8, 9], "npc_005_02"),
                 voices, tr)
    assert r5.probation["candidates"] == 1
    assert m.store.get_row("characters", "npc_005_01") is None                 # not a character yet
    (cand,) = m.store.candidates()
    assert (cand.id, cand.name_vi, cand.n_lines) == ("npc_005_01", "Vương chưởng quỹ", 3)
    assert cand.embedding is not None and len(cand.pending) == 1               # the pronoun pair waits
    assert not [c for c in m.store.candidates(None) if c.id == "npc_005_02"]   # 2 lines: forgotten
    assert [c.id for c in m.store.returning_candidates(6, 2)] == ["npc_005_01"]  # what the voice stage asks
    assert m.store.returning_candidates(5, 2) == [] and m.store.returning_candidates(8, 2) == []

    back = [NewVoice(id="npc_005_01", event_ids=["ep006:0004"], cohesion=0.8, returning_from="ep005")]
    r6 = _finish(m, paths, "ep006", _lines("ep006", [4], "npc_005_01"), back)
    assert r6.probation["promoted"] == 1
    row = m.store.get_row("characters", "npc_005_01")
    assert row["name_vi"] == "Vương chưởng quỹ" and not row["locked"]
    assert "npc_005_01" in m.store.voice_bank()
    assert {(a["character_id"], a["episode_id"]) for a in m.store.appearances()} >= {
        ("npc_005_01", "ep005"), ("npc_005_01", "ep006")}
    assert [p.self_term for p in m.store.pronoun_variants("npc_005_01", "lin_yuan")] == ["lão phu"]
    assert m.store.candidates() == [] and m.store.candidates("promoted")[0].id == "npc_005_01"


def test_a_candidate_not_back_in_time_is_dropped(project):
    config, paths = project
    seed_memory(config, paths)
    for n in (5, 8):
        register_episode(paths, n)
    m = MemoryManager(paths, config)
    _finish(m, paths, "ep005", _lines("ep005", [1, 2, 3], "npc_005_01"),
            [NewVoice(id="npc_005_01", event_ids=["ep005:0001"], cohesion=0.8)])
    r8 = _finish(m, paths, "ep008", _lines("ep008", [1], "lin_yuan", "shi_zun"), [])
    assert r8.probation["dropped"] == 1 and m.store.candidates("dropped")[0].id == "npc_005_01"


def test_auto_mode_needs_a_trusted_line_to_promote(project):
    config, paths = project
    seed_memory(config, paths)
    for n in (5, 6):
        register_episode(paths, n)
    m = MemoryManager(paths, config)
    _finish(m, paths, "ep005", _lines("ep005", [1, 2, 3], "npc_005_01"),
            [NewVoice(id="npc_005_01", event_ids=["ep005:0001"], cohesion=0.8)])
    back = [NewVoice(id="npc_005_01", event_ids=["ep006:0004"], cohesion=0.8, returning_from="ep005")]
    r6 = _finish(m, paths, "ep006", _lines("ep006", [4], "npc_005_01"), back, mode="auto")  # no voice evidence
    assert r6.probation["promoted"] == 0 and m.store.candidates()[0].id == "npc_005_01"


def _talks(character: str | None, idx: int = 0) -> dict[str, CastLine]:
    return {"ep006:0004": CastLine(event_id="ep006:0004", talking=0, detections=[
        CastDetection(index=idx, box=[0, 0, 1, 1], score=0.5, label="c", character=character)])}


def test_the_look_can_stop_a_promotion():
    line = _lines("ep006", [4], "npc_005_01")
    embs = np.stack([_unit(2), _unit(4)])
    assert check_return(line, _talks("shi_zun"), embs, [_unit(2)], 0.7).promote is False   # someone known talks
    assert check_return(line, _talks(None, 0), embs, [_unit(2)], 0.7).promote is True      # looks like it
    assert check_return(line, _talks(None, 1), embs, [_unit(2)], 0.7).promote is False     # looks different
    assert check_return(line, {}, embs, [_unit(2)], 0.7).promote is True                   # no picture: voice alone


def test_npcs_created_in_review_are_ids_of_their_episode(project):
    from subagent.memory.characters import episode_character_ids, review_voice_ids

    config, paths = project
    lines = _lines("ep006", [1, 2], "npc_006_03") + _lines("ep006", [3], "npc_005_02")   # another episode's id
    assert review_voice_ids(lines, "npc") == {"npc_006_03"}
    work = paths.episode_dir("ep006")
    work.mkdir(parents=True)
    write_jsonl(work / "review_draft.jsonl", lines)
    ids = episode_character_ids(work, {"lin_yuan"}, "npc", {"npc_005_02"})       # a candidate that may come back
    assert ids == {"lin_yuan", "npc_006_03", "npc_005_02"}


def test_a_review_npc_goes_on_probation_at_finish(project, monkeypatch):
    from subagent.kernel.models import EpisodeState
    from subagent.pipeline import Pipeline
    from subagent.workspace.state import save_state

    config, paths = project
    seed_memory(config, paths)
    ep = register_episode(paths, 6)
    work = paths.episode_dir(ep.id)
    work.mkdir(parents=True)
    lines = _lines("ep006", [1, 2, 3], "npc_006_01")
    write_jsonl(work / "approved.jsonl", lines)
    save_line_voices(work / "voice_embeddings.npz", {x.event_id: _unit(5) for x in lines})
    save_state(work, EpisodeState(episode_id=ep.id, mode="human"))
    pipe = Pipeline(config, paths)
    monkeypatch.setattr(pipe, "_line_decisions", lambda ctx, approved: None)
    ctx = pipe.context(ep)
    ctx.llm_override = None
    monkeypatch.setattr(type(ctx), "llm", property(lambda self: None))
    pipe._memory_update(ctx)
    (cand,) = MemoryManager(paths, config).store.candidates()
    assert (cand.id, cand.n_lines, cand.first_episode) == ("npc_006_01", 3, "ep006")


def test_in_human_mode_the_picture_cannot_veto_a_return_the_reviewer_assigned(project):
    config, paths = project
    seed_memory(config, paths)
    for n in (5, 6):
        register_episode(paths, n)
    m = MemoryManager(paths, config)
    w5 = paths.episode_dir("ep005")
    w5.mkdir(parents=True, exist_ok=True)
    write_jsonl(w5 / "cast.jsonl", [CastLine(event_id=f"ep005:{i:04d}", talking=0, detections=[
        CastDetection(index=0, box=[0, 0, 1, 1], score=0.5, label="c")]) for i in (1, 2, 3)])
    np.save(w5 / "cast_embeddings.npy", np.stack([_unit(2)]))
    _finish(m, paths, "ep005", _lines("ep005", [1, 2, 3], "npc_005_01"),
            [NewVoice(id="npc_005_01", event_ids=["ep005:0001"], cohesion=0.8)])
    assert m.store.get_row("characters", "npc_005_01") is None
    assert m.store.candidate_sprites("npc_005_01")                      # a look was remembered in ep005
    w6 = paths.episode_dir("ep006")
    w6.mkdir(parents=True, exist_ok=True)
    write_jsonl(w6 / "cast.jsonl", list(_talks("shi_zun").values()))    # the picture says shi_zun is talking
    np.save(w6 / "cast_embeddings.npy", np.stack([_unit(4)]))
    back = [NewVoice(id="npc_005_01", event_ids=["ep006:0004"], cohesion=0.8, returning_from="ep005")]
    r6 = _finish(m, paths, "ep006", _lines("ep006", [4], "npc_005_01"), back)          # human mode
    assert r6.probation["promoted"] == 1
    assert "assigned by the reviewer" in m.store.get_row("characters", "npc_005_01")["description"] or \
        "assigned by the reviewer" in (m.store.candidates("promoted")[0].status_note or "")
    assert not [e for e in m.store.sprite_exemplars() if e.character_id == "npc_005_01"]   # disputed look not kept
