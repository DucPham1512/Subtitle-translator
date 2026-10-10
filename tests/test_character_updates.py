"""Character updates from an episode (5.15c): checked in code, applied to unlocked entries, held for locked ones."""

from __future__ import annotations

import json

import numpy as np

from subagent.memory import character_updates as cu
from subagent.memory.manager import UPDATE_REJECTIONS_FILE, UPDATES_FILE, MemoryManager
from subagent.memory.prefix import characters_block
from subagent.models import MemoryProposal, NewVoice, ReviewedLine
from subagent.stages.voice import save_line_voices
from subagent.util import write_jsonl
from tests.conftest import make_llm, register_episode, seed_memory

BRIEF = {"summary_sentence": "x", "characters_introduced": [], "episode_markdown": "# ep\nx", "story_so_far": "x"}


def _line(event_id: str, speaker: str, listener: str, zh: str, vi: str) -> ReviewedLine:
    return ReviewedLine(event_id=event_id, start_ms=0, end_ms=900, speaker=speaker, listener=listener, zh=zh,
                        pinyin="", vi=vi, approved=True)


def _llm(config, paths, updates: dict):
    def utility(msgs):
        return updates if "character memory" in msgs[0]["content"] else BRIEF

    llm, clients = make_llm(config, paths, {"utility": utility})
    return llm, clients


def _npc(m: MemoryManager, cid: str, desc: str) -> None:
    m.apply([MemoryProposal(kind="character", source="dreaming", payload={
        "id": cid, "name_zh": cid, "name_vi": cid, "description": desc})])


def test_check_keeps_only_what_the_lines_show(project):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    config.memory.description_max_chars = 30
    lines = [_line("ep007:0001", "lin_yuan", "npc_007_01", "王会长好", "Vương hội trưởng, đệ tử chào ngài."),
             _line("ep007:0002", "npc_007_01", "lin_yuan", "老夫王五", "Lão phu là Vương Ngũ.")]
    resp = cu.CharacterUpdateResponse.model_validate({
        "characters": [
            {"id": "npc_007_01", "name_zh": "王五", "name_vi": "Vương Ngũ",
             "description": "Hội trưởng của thương hội ở thành Đông, quen biết sư tôn từ lâu",
             "aliases": ["会长 (Hội trưởng)", "掌门 (Chưởng môn)"], "evidence": ["ep007:0001", "ep007:0002"]},
            {"id": "ghost", "description": "x", "evidence": ["ep007:0001"]},                  # not in the episode
            {"id": "lin_yuan", "name_zh": "李四", "name_vi": "Lý Tứ", "evidence": ["ep007:0001"]},  # name not quoted
            {"id": "lin_yuan", "description": "y", "evidence": ["ep009:0001"]},             # evidence elsewhere
            {"id": "lin_yuan", "aliases": ["会长 (Hội trưởng)"], "evidence": ["ep007:0001"]},  # it says 会长 to npc
        ],
        "pronouns": [
            {"speaker_id": "npc_007_01", "listener_id": "lin_yuan", "self_term": "lão phu", "address_term": "ngươi",
             "evidence": ["ep007:0002"]},
            {"speaker_id": "npc_007_01", "listener_id": "lin_yuan", "self_term": "bổn tọa", "address_term": "con",
             "context": "khi vui", "evidence": ["ep007:0002"]},                             # terms not used
            {"speaker_id": "lin_yuan", "listener_id": "shi_zun", "self_term": "đồ nhi", "address_term": "sư phụ",
             "evidence": ["ep007:0001"]},                                                  # shi_zun absent
            {"speaker_id": "lin_yuan", "listener_id": "npc_007_01", "self_term": "đệ tử", "address_term": "ngài",
             "evidence": ["ep007:0001"]},
        ]})
    out = cu.check(resp, m.store, lines, cu.present_ids(lines), None, config)
    chars = [p for p in out if p.kind == "character"]
    assert len(chars) == 1
    pl = chars[0].payload
    assert (pl["name_zh"], pl["name_vi"]) == ("王五", "Vương Ngũ")
    assert pl["aliases"] == ["会长 (Hội trưởng)"]                 # 掌门 is in no line
    assert pl["description"].endswith("…") and len(pl["description"]) <= 31
    pairs = sorted((p.payload["speaker_id"], p.payload["self_term"]) for p in out if p.kind == "pronoun_pair")
    assert pairs == [("lin_yuan", "đệ tử"), ("npc_007_01", "lão phu")]
    # auto mode: evidence only from trusted lines
    trusted = cu.check(resp, m.store, lines, cu.present_ids(lines), {"ep007:0002"}, config)
    assert [(p.kind, p.evidence) for p in trusted] == [("character", ["ep007:0002"]), ("pronoun_pair", ["ep007:0002"])]
    assert "aliases" not in trusted[0].payload                     # 会长 is only on the untrusted line


def test_unlocked_characters_are_updated_and_locked_ones_wait_for_the_reviewer(project):
    config, paths = project
    config.memory.character_updates = True
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    _npc(m, "npc_003_01", "Voice found automatically in ep003; back in ep004")
    lines = [_line("ep004:0001", "lin_yuan", "npc_003_01", "会长，师尊让我来", "Hội trưởng, sư tôn bảo đồ nhi đến."),
             _line("ep004:0002", "npc_003_01", "lin_yuan", "老夫王五", "Lão phu là Vương Ngũ."),
             _line("ep004:0003", "lin_yuan", "shi_zun", "师尊，我走了", "Thưa thầy, con đi đây.")]
    updates = {"characters": [
        {"id": "npc_003_01", "name_zh": "王五", "name_vi": "Vương Ngũ", "description": "Hội trưởng, quen sư tôn",
         "aliases": ["会长 (Hội trưởng)"], "evidence": ["ep004:0001", "ep004:0002"]},
        {"id": "lin_yuan", "description": "Đệ tử của Sư tôn (shi_zun)", "evidence": ["ep004:0001"]}],
        "pronouns": [
        {"speaker_id": "lin_yuan", "listener_id": "shi_zun", "self_term": "con", "address_term": "thầy",
         "evidence": ["ep004:0003"]},
        {"speaker_id": "npc_003_01", "listener_id": "lin_yuan", "self_term": "lão phu", "address_term": "ngươi",
         "evidence": ["ep004:0002"]}]}
    llm, _ = _llm(config, paths, updates)
    result = m.episode_update("ep004", lines, [], [], llm)

    npc = m.store.get_row("characters", "npc_003_01")
    assert (npc["name_vi"], npc["description"], npc["locked"]) == ("Vương Ngũ", "Hội trưởng, quen sư tôn", 0)
    assert json.loads(npc["aliases"]) == ["会长 (Hội trưởng)"]
    assert [p.self_term for p in m.store.pronoun_variants("npc_003_01", "lin_yuan")] == ["lão phu"]
    assert m.store.get_row("characters", "lin_yuan")["description"] == "đệ tử"          # locked: unchanged
    assert [p.self_term for p in m.store.pronoun_variants("lin_yuan", "shi_zun")] == ["đồ nhi"]
    pending = {u.id: u for u in m.pending_updates()}
    assert set(pending) == {"characters:lin_yuan:description", "pronoun_pairs:lin_yuan|shi_zun|:pair"}
    assert pending["characters:lin_yuan:description"].lines == ["ep004:0001: 会长，师尊让我来 | Hội trưởng, sư tôn bảo đồ nhi đến."]
    assert len(result.held) == 2 and "2 held for review" in m.history()[0].message

    m.resolve_update("characters:lin_yuan:description", accept=True)
    row = m.store.get_row("characters", "lin_yuan")
    assert (row["description"], row["locked"]) == ("Đệ tử của Sư tôn (shi_zun)", 1)
    m.resolve_update("pronoun_pairs:lin_yuan|shi_zun|:pair", accept=False)
    assert m.pending_updates() == []
    assert len(json.loads((paths.memory / UPDATE_REJECTIONS_FILE).read_text(encoding="utf-8"))) == 1

    m.episode_update("ep004", lines, [], [], llm)        # finishing again: nothing comes back
    assert m.pending_updates() == []
    assert json.loads((paths.memory / UPDATES_FILE).read_text(encoding="utf-8")) == []


def test_auto_mode_holds_updates_from_unchecked_lines(project):
    config, paths = project
    config.memory.character_updates = True
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    _npc(m, "npc_003_01", "Voice found automatically in ep003")
    lines = [_line("ep004:0001", "npc_003_01", "lin_yuan", "老夫王五", "Lão phu là Vương Ngũ."),
             _line("ep004:0002", "npc_004_01", "lin_yuan", "掌柜的来了", "Chưởng quỹ đến rồi.")]
    updates = {"characters": [
        {"id": "npc_003_01", "description": "Hội trưởng", "evidence": ["ep004:0001"]},
        {"id": "npc_004_01", "description": "Chủ quán", "evidence": ["ep004:0002"]}]}
    llm, _ = _llm(config, paths, updates)
    m.episode_update("ep004", lines, [], [], llm, mode="auto")      # no voice match on disk: nothing is trusted
    assert m.store.get_row("characters", "npc_003_01")["description"] == "Voice found automatically in ep003"
    (held,) = m.pending_updates()
    assert (held.id, held.reason) == ("characters:npc_003_01:description", "untrusted")


def test_a_candidate_keeps_its_updates_when_promoted(project):
    config, paths = project
    config.memory.character_updates = True
    seed_memory(config, paths)
    for n in (5, 6):
        register_episode(paths, n)
    m = MemoryManager(paths, config)

    def finish(ep, lines, voices, updates):
        work = paths.episode_dir(ep)
        work.mkdir(parents=True, exist_ok=True)
        v = np.zeros(8, np.float32)
        v[5] = 1.0
        save_line_voices(work / "voice_embeddings.npz", {x.event_id: v for x in lines})
        write_jsonl(work / "approved.jsonl", lines)
        llm, _ = _llm(config, paths, updates)
        return m.episode_update(ep, lines, [], [], llm, new_voices=voices)

    lines5 = [_line(f"ep005:{i:04d}", "npc_005_01", "lin_yuan", "客官里边请", "Khách quan mời vào.") for i in (1, 2, 3)]
    lines5.append(_line("ep005:0004", "lin_yuan", "npc_005_01", "掌柜的，来壶酒", "Chưởng quỹ, cho một bình rượu."))
    voice = NewVoice(id="npc_005_01", event_ids=[x.event_id for x in lines5[:3]], cohesion=0.8)
    r5 = finish("ep005", lines5, [voice],
                {"characters": [{"id": "npc_005_01", "description": "Chủ quán trọ",
                                 "aliases": ["掌柜 (Chưởng quỹ)", "客官 (Khách quan)"],     # 客官: what it says
                                 "evidence": ["ep005:0001", "ep005:0004"]}]})
    assert r5.probation["candidates"] == 1
    (cand,) = m.store.candidates()
    assert (cand.description, cand.aliases) == ("Chủ quán trọ", ["掌柜 (Chưởng quỹ)"])

    lines6 = [_line("ep006:0004", "npc_005_01", "lin_yuan", "又见面了", "Lại gặp nhau rồi.")]
    r6 = finish("ep006", lines6, [NewVoice(id="npc_005_01", event_ids=["ep006:0004"], cohesion=0.8,
                                           returning_from="ep005")], {})
    assert r6.probation["promoted"] == 1
    row = m.store.get_row("characters", "npc_005_01")
    assert row["description"] == "Chủ quán trọ" and json.loads(row["aliases"]) == ["掌柜 (Chưởng quỹ)"]
    assert "(called: 掌柜 (Chưởng quỹ))" in characters_block(m.store)


def test_updates_are_off_when_disabled(project):
    config, paths = project
    config.memory.character_updates = False
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    llm, clients = _llm(config, paths, {"characters": []})
    m.episode_update("ep004", [_line("ep004:0001", "lin_yuan", "shi_zun", "师尊", "Sư phụ.")], [], [], llm)
    assert len(clients["utility"].calls) == 1                         # the briefing only
    assert not (paths.memory / UPDATES_FILE).exists()
