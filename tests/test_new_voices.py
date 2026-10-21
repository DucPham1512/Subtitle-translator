"""Voices that match no known character become automatic characters (npc_005_01), named when the dialogue says who."""

from __future__ import annotations

import numpy as np

from subagent.kernel.models import LineTranslation, MemoryProposal, NewVoice, ReviewedLine, SpeakerCandidates
from subagent.memory.characters import (
    episode_character_ids,
    is_auto_id,
    is_unnamed,
    load_new_voices,
    save_new_voices,
)
from subagent.memory.manager import MemoryManager
from subagent.memory.prefix import new_voices_block
from subagent.stages.evaluate import RuleContext, rule_checks
from subagent.voice.voice import find_new_voices, group_voices
from tests.conftest import sample_events, seed_memory


def _e(*dims: float) -> np.ndarray:
    v = np.zeros(8, np.float32)
    v[: len(dims)] = dims
    return v


def _unit(k: int, wobble: int = 0) -> np.ndarray:
    v = np.zeros(8, np.float32)
    v[k] = 1.0
    v[(k + 1 + wobble) % 8] += 0.15             # a little variation between lines of the same voice
    return v


BANK = {"lin_yuan": _unit(0), "shi_zun": _unit(1)}


def _results(spec: list[tuple[str, float]]) -> list[SpeakerCandidates]:
    return [SpeakerCandidates(event_id=f"ep005:{i:04d}", status=status,  # type: ignore[arg-type]
                              candidates=[("lin_yuan", score), ("shi_zun", score - 0.05)])
            for i, (status, score) in enumerate(spec)]


def test_group_voices_keeps_alike_voices_together():
    embs = [_unit(5), _unit(5, 1), _unit(6), _unit(5, 2), _unit(6, 1)]
    groups = sorted(group_voices(embs, 0.6), key=min)
    assert groups == [[0, 1, 3], [2, 4]]


def test_new_voice_needs_enough_lines_and_an_unfamiliar_voice(project):
    config, _ = project
    cfg = config.voice
    results = _results([("fixed", 0.9)] + [("unknown", 0.2)] * 4 + [("confusable", 0.4)] * 2 + [("unknown", 0.2)] * 2)
    embs = {r.event_id: e for r, e in zip(results, [_unit(0), _unit(5), _unit(5, 1), _unit(5, 2), _unit(5, 3),
                                                    _unit(6), _unit(6, 1), _unit(7), _unit(3)], strict=True)}
    updated, voices = find_new_voices(results, embs, BANK, cfg, 5)
    assert [v.id for v in voices] == ["npc_005_01"]                       # 5 + 6 groups are too small (2 lines)
    assert voices[0].event_ids == ["ep005:0001", "ep005:0002", "ep005:0003", "ep005:0004"]
    line = {r.event_id: r for r in updated}["ep005:0002"]
    assert line.status == "new_voice" and line.candidates[0][0] == "npc_005_01" and len(line.candidates) == cfg.top_k
    assert {r.event_id: r for r in updated}["ep005:0000"].status == "fixed"   # confident lines are never touched

    cfg.new_voice_known_max = 0.0                                          # every group sounds like someone known
    assert find_new_voices(results, embs, BANK, cfg, 5)[1] == []


def test_lines_may_use_the_episode_new_voices(project):
    config, paths = project
    seed_memory(config, paths)
    work = paths.episode_dir("ep005")
    work.mkdir(parents=True)
    save_new_voices(work, [NewVoice(id="npc_005_01", event_ids=["ep005:0000"], cohesion=0.8)])
    store = MemoryManager(paths, config).store
    ids = episode_character_ids(work, store.character_ids())
    assert {"lin_yuan", "npc_005_01"} <= ids
    rc = RuleContext(config, store, ids)
    event = sample_events()[0]
    line = LineTranslation(event_id=event.id, speaker="npc_005_01", listener="lin_yuan", speaker_conf=0.8,
                           vi="Ngươi đi đi.", attempts=1)
    failures, _ = rule_checks(line, event, None, rc)
    assert not [f for f in failures if f.code.startswith(("speaker", "listener"))]
    block = new_voices_block(load_new_voices(work), store, {"ep005:0000": 83_000})
    assert "npc_005_01: 1 lines, first at 01:23" in block
    assert "lin_yuan (Lâm Uyên)" in block                                   # no voice sample yet: may be them


def _approved(ids: list[int], speaker: str) -> list[ReviewedLine]:
    return [ReviewedLine(event_id=f"ep005:{i:04d}", start_ms=i * 1000, end_ms=i * 1000 + 900, speaker=speaker,
                         listener="lin_yuan", zh="掌柜的", pinyin="", vi="x", approved=True) for i in ids]


def test_new_voice_becomes_a_character_and_takes_the_first_name_everywhere(project):
    config, paths = project
    config.memory.probation = False             # the old path: a new voice is a character at once
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    (paths.memory / "briefings").mkdir(exist_ok=True)
    (paths.memory / "briefings" / "ep004.md").write_text("npc_005_01 bán cá cho Lâm Uyên.\n", encoding="utf-8")
    (paths.memory / "briefings" / "story_so_far.md").write_text("Lâm Uyên gặp npc_005_01x và npc_005_01.\n",
                                                                encoding="utf-8")
    voices = [NewVoice(id="npc_005_01", event_ids=["ep005:0001"], cohesion=0.8),
              NewVoice(id="npc_005_02", event_ids=["ep005:0009"], cohesion=0.8)]      # reviewer moved its lines away
    naming = MemoryProposal(kind="character", source="translator", evidence=["ep005:0002"], payload={
        "id": "npc_005_01", "name_zh": "王掌柜", "name_vi": "Vương chưởng quỹ", "description": "chủ quán"})
    translations = [LineTranslation(event_id="ep005:0002", speaker="npc_005_01", listener="lin_yuan",
                                    speaker_conf=0.8, vi="x", attempts=1, proposals=[naming])]
    result = m.episode_update("ep005", _approved([1, 2, 3], "npc_005_01") + _approved([9], "lin_yuan"),
                              translations, [], None, new_voices=voices)

    row = m.store.get_row("characters", "npc_005_01")
    assert row["name_vi"] == "Vương chưởng quỹ" and row["description"] == "chủ quán" and not row["locked"]
    assert m.store.get_row("characters", "npc_005_02") is None
    assert result.renamed == [("npc_005_01", "Vương chưởng quỹ")]
    assert (paths.memory / "briefings" / "ep004.md").read_text(encoding="utf-8") == "Vương chưởng quỹ bán cá cho Lâm Uyên.\n"
    assert "npc_005_01x và Vương chưởng quỹ" in (paths.memory / "briefings" / "story_so_far.md").read_text(encoding="utf-8")

    # once named, a later rename with less evidence is a conflict for the reviewer, not an overwrite
    later = MemoryProposal(kind="character", source="translator", evidence=["ep006:0001"],
                           payload={"id": "npc_005_01", "name_vi": "Lão Vương"})
    again = m.apply([later], approved_ids={"ep006:0001"}, episode_id="ep006")
    assert again.conflicts == ["characters:npc_005_01"] and again.renamed == []
    assert m.store.get_row("characters", "npc_005_01")["name_vi"] == "Vương chưởng quỹ"


def test_a_name_you_give_is_locked(project):
    config, paths = project
    config.memory.probation = False             # the old path: a new voice is a character at once
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    m.episode_update("ep005", _approved([1, 2, 3], "npc_005_01"), [], [], None,
                     new_voices=[NewVoice(id="npc_005_01", event_ids=["ep005:0001"], cohesion=0.8)])
    assert is_unnamed(m.store.get_row("characters", "npc_005_01"), "npc")
    m.manual_edit([MemoryProposal(kind="character", source="human",
                                  payload={"id": "npc_005_01", "name_zh": "老板", "name_vi": "Lão bản"})])
    guess = MemoryProposal(kind="character", source="translator", evidence=["ep006:0001"],
                           payload={"id": "npc_005_01", "name_vi": "Chưởng quỹ"})
    assert m.apply([guess], approved_ids={"ep006:0001"}).rejected[0][1] == "entry is locked"
    assert m.store.get_row("characters", "npc_005_01")["name_vi"] == "Lão bản"


def test_auto_ids():
    assert is_auto_id("npc_005_01", "npc") and not is_auto_id("npc_5_1", "npc") and not is_auto_id("lin_yuan", "npc")
    assert not is_unnamed({"id": "npc_005_01", "name_vi": "Vương chưởng quỹ"}, "npc")
    assert not is_unnamed({"id": "lin_yuan", "name_vi": "lin_yuan"}, "npc")
