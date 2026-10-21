"""Unlocked characters are kept, archived or brought back by their appearances and stated fates (5.15a)."""

from __future__ import annotations

import sqlite3

import numpy as np

from subagent.kernel.models import MemoryProposal, ReviewedLine
from subagent.kernel.util import write_jsonl
from subagent.memory.briefing_gen import CharacterFate
from subagent.memory.manager import MemoryManager
from subagent.memory.prefix import characters_block, pronoun_block
from tests.conftest import register_episode, seed_memory


def _lines(ep: int, *speakers: str) -> list[ReviewedLine]:
    return [ReviewedLine(event_id=f"ep{ep:03d}:{i:04d}", start_ms=i * 1000, end_ms=i * 1000 + 900, speaker=s,
                         listener="lin_yuan", zh="字", pinyin="", vi="x", approved=True) for i, s in enumerate(speakers)]


def _setup(project, *npcs: str) -> MemoryManager:
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    m.apply([MemoryProposal(kind="character", source="translator", evidence=["e"],
                            payload={"id": n, "name_zh": n, "name_vi": n}) for n in npcs], approved_ids={"e"})
    m.apply([MemoryProposal(kind="pronoun_pair", source="bootstrap", payload={
        "speaker_id": npcs[0], "listener_id": "lin_yuan", "self_term": "ta", "address_term": "ngươi"})])
    return m


def _status(m: MemoryManager, cid: str) -> str:
    return m.store.get_row("characters", cid)["status"]


def test_one_off_is_archived_after_two_absent_episodes_and_comes_back(project):
    m = _setup(project, "npc_005_01")
    m.update_lifecycle("ep005", _lines(5, "npc_005_01", "lin_yuan"))
    assert m.update_lifecycle("ep006", _lines(6, "lin_yuan")) == {}               # one episode away: still active
    assert m.update_lifecycle("ep007", _lines(7, "lin_yuan")) == {"archived": 1}
    row = m.store.get_row("characters", "npc_005_01")
    assert row["status"] == "archived" and row["status_note"] == "not seen since ep005"
    assert _status(m, "lin_yuan") == "active"                                      # locked cast is never touched
    assert "npc_005_01" not in characters_block(m.store) and "npc_005_01" not in pronoun_block(m.store)

    m.update_lifecycle("ep009", _lines(9, "npc_005_01"))                           # a reviewer used it again
    assert _status(m, "npc_005_01") == "active"
    assert "npc_005_01" in characters_block(m.store)


def test_consecutive_episodes_keep_a_character(project):
    m = _setup(project, "npc_005_01")
    m.update_lifecycle("ep005", _lines(5, "npc_005_01"))
    assert m.update_lifecycle("ep006", _lines(6, "npc_005_01")) == {"kept": 1}
    for ep in (7, 8, 9):
        m.update_lifecycle(f"ep{ep:03d}", _lines(ep, "lin_yuan"))
    assert _status(m, "npc_005_01") == "kept"                                      # absence never archives it


def test_stated_fates(project):
    m = _setup(project, "npc_005_01", "npc_005_02")
    m.update_lifecycle("ep005", _lines(5, "npc_005_01", "npc_005_02"))
    m.update_lifecycle("ep006", _lines(6, "npc_005_01"))                           # npc_005_01 now kept
    fates = [CharacterFate(id="npc_005_01", fate="dies", evidence="ep007:0003 他死了"),
             CharacterFate(id="npc_005_02", fate="returns", evidence="ep007:0004 后会有期")]
    assert m.update_lifecycle("ep007", _lines(7, "npc_005_01", "npc_005_02"), fates) == {"archived": 1, "kept": 1}
    assert m.store.get_row("characters", "npc_005_01")["status_note"] == "dies in ep007: ep007:0003 他死了"
    assert _status(m, "npc_005_02") == "kept"


def test_archived_voices_are_not_matched(project):
    from subagent.voice import voice
    from subagent.workspace.context import EpisodeContext
    from tests.conftest import make_episode, sample_events, write_events
    from tests.test_pinyin_voice_windows import _write_wav

    config, paths = project
    m = _setup(project, "npc_001_01")
    m.write_voices({"npc_001_01": (np.array([1, 0, 0], np.float32), 3),
                    "shi_zun": (np.array([0, 1, 0], np.float32), 3)})
    m.update_lifecycle("ep001", _lines(1, "npc_001_01"))
    m.update_lifecycle("ep002", _lines(2, "lin_yuan"))
    m.update_lifecycle("ep003", _lines(3, "lin_yuan"))
    assert _status(m, "npc_001_01") == "archived"
    ctx = EpisodeContext(config, paths, make_episode(paths, 4))
    write_events(ctx.work, sample_events("ep004")[:1])
    _write_wav(ctx.artifact("audio.wav"), 4)
    voice.run(ctx, embed=lambda clip: voice.l2_normalize(np.array([1, 0, 0], np.float32)))   # sounds like the npc
    from subagent.kernel.models import SpeakerCandidates
    from subagent.kernel.util import read_jsonl
    out = read_jsonl(ctx.artifact("speakers.jsonl"), SpeakerCandidates)[0]
    assert "npc_001_01" not in [c for c, _ in out.candidates]


def test_status_is_set_by_people_not_by_models(project):
    m = _setup(project, "npc_005_01")
    guess = MemoryProposal(kind="character", source="translator", evidence=["e"],
                           payload={"id": "npc_005_01", "status": "archived"})
    m.apply([guess], approved_ids={"e"})
    assert _status(m, "npc_005_01") == "active"
    m.manual_edit([MemoryProposal(kind="character", source="human",
                                  payload={"id": "npc_005_01", "status": "archived", "status_note": "one-off"})])
    row = m.store.get_row("characters", "npc_005_01")
    assert row["status"] == "archived" and row["locked"]                          # locked: the lifecycle leaves it
    bad = m.manual_edit([MemoryProposal(kind="character", source="human", payload={"id": "npc_005_01",
                                                                                     "status": "gone"})])
    assert bad.rejected and "status must be one of" in bad.rejected[0][1]


def test_first_run_counts_earlier_episodes(project):
    config, paths = project
    m = _setup(project, "npc_001_01")
    for n, who in ((1, "npc_001_01"), (2, "lin_yuan")):
        ep = register_episode(paths, n)
        write_jsonl(paths.episode_dir(ep.id) / "approved.jsonl", _lines(n, who))
    assert m.update_lifecycle("ep003", _lines(3, "lin_yuan")) == {"archived": 1}  # ep001 counted from its script
    assert {(r["character_id"], r["episode_id"]) for r in m.store.appearances()} >= {
        ("npc_001_01", "ep001"), ("lin_yuan", "ep002"), ("lin_yuan", "ep003")}


def test_old_memory_gets_the_new_columns(project):
    config, paths = project
    seed_memory(config, paths)
    with sqlite3.connect(paths.memory_db) as conn:          # an older memory.db: no status columns
        conn.executescript("ALTER TABLE characters DROP COLUMN status_note; ALTER TABLE characters DROP COLUMN status;")
        conn.execute("UPDATE characters SET locked=0 WHERE id='shi_zun'")
    m = MemoryManager(paths, config)
    for n in (1, 2, 3):                                      # shi_zun: one-off, then away for two episodes
        m.update_lifecycle(f"ep{n:03d}", _lines(n, "shi_zun" if n == 1 else "lin_yuan"))
    assert _status(m, "lin_yuan") == "active" and _status(m, "shi_zun") == "archived"


def test_generic_characters_are_never_matched_or_learned(project):
    from subagent.kernel.models import NewVoice
    from subagent.memory.prefix import new_voices_block
    from subagent.stages.cast import build_bank

    m = _setup(project, "npc_005_01")
    m.write_voices({"lin_yuan": (np.array([1, 0, 0], np.float32), 3), "shi_zun": (np.array([0, 1, 0], np.float32), 3)})
    m.write_sprites([("shi_zun", np.array([0, 1, 0], np.float32), "ep001", "x")], {}, [], max_per_character=60)
    guess = MemoryProposal(kind="character", source="translator", evidence=["e"], payload={"id": "shi_zun", "generic": 1})
    m.apply([guess], approved_ids={"e"})
    assert not m.store.get_row("characters", "shi_zun")["generic"]          # models cannot set it
    m.manual_edit([MemoryProposal(kind="character", source="human", payload={"id": "shi_zun", "generic": "1"})])
    assert m.store.unmatchable_ids() == {"shi_zun"}
    assert "shi_zun" not in build_bank(m.store)                              # picture
    assert "(generic:" in characters_block(m.store)
    assert "shi_zun" not in new_voices_block([NewVoice(id="npc_005_01", event_ids=["e"], cohesion=1.0)], m.store, {})
    for ep in (5, 6, 7):                                                     # never archived for absence
        m.update_lifecycle(f"ep{ep:03d}", _lines(ep, "lin_yuan"))
    assert _status(m, "shi_zun") == "active"
