from __future__ import annotations

import pytest

from subagent.errors import JobRunningError
from subagent.memory import briefings as bf
from subagent.memory.manager import MemoryManager, merge_proposals, replaced_term
from subagent.memory.store import MemoryStore
from subagent.models import EditRecord, LineTranslation, MemoryProposal, ReviewedLine
from tests.conftest import make_llm, seed_memory


def P(kind, payload, source="translator", evidence=None):
    return MemoryProposal(kind=kind, payload=payload, source=source, evidence=evidence or [])


def test_store_is_read_only(project):
    config, paths = project
    seed_memory(config, paths)
    import sqlite3

    store = MemoryStore(paths.memory_db)
    with store._ro() as conn, pytest.raises(sqlite3.OperationalError):
        conn.execute("DELETE FROM glossary")
    assert {c.id for c in store.characters()} == {"lin_yuan", "shi_zun"}
    assert [g.zh for g in store.glossary_in("林渊已经筑基")] == ["林渊", "筑基"]


def test_locked_entries_change_only_by_human(project):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    r = m.apply([P("glossary", {"zh": "筑基", "vi": "Xây Nền"}, "dreaming", ["x"])])
    assert r.rejected and "locked" in r.rejected[0][1]
    r = m.apply([P("glossary", {"zh": "筑基", "vi": "Trúc cơ kỳ"}, "human", ["edit"])])
    assert r.applied == ["glossary:筑基"]
    assert m.store.get_row("glossary", "筑基")["vi"] == "Trúc cơ kỳ"


def test_translator_proposals_need_approved_evidence(project):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    p = P("glossary", {"zh": "金丹", "vi": "Kim Đan", "type": "realm"}, evidence=["ep001:0001"])
    assert m.apply([p], approved_ids=set()).rejected
    r = m.apply([p], approved_ids={"ep001:0001"}, episode_id="ep001")
    assert r.applied == ["glossary:金丹"]
    row = m.store.get_row("glossary", "金丹")
    assert row["locked"] == 0 and row["first_episode"] == "ep001" and row["source"] == "translator"
    log = m.store.log(table="glossary", key="金丹")
    assert [e.op for e in log] == ["insert", "rejected"]


def test_conflicts_need_more_evidence(project):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    ids = {f"ep001:{i:04d}" for i in range(5)}
    m.apply([P("glossary", {"zh": "宗门", "vi": "tông môn"}, evidence=["ep001:0000", "ep001:0001"])], approved_ids=ids)
    r = m.apply([P("glossary", {"zh": "宗门", "vi": "môn phái"}, evidence=["ep001:0002"])], approved_ids=ids)
    assert r.conflicts == ["glossary:宗门"]
    assert m.store.get_row("glossary", "宗门")["vi"] == "tông môn"
    assert "môn phái" in (paths.memory / "conflicts.md").read_text(encoding="utf-8")
    r = m.apply([P("glossary", {"zh": "宗门", "vi": "môn phái"}, evidence=["ep001:0002", "ep001:0003", "ep001:0004"])],
                approved_ids=ids)
    assert r.applied == ["glossary:宗门"]

    conflict = m.conflicts()[0]
    m.resolve_conflict(conflict.id, accept=False)
    assert m.conflicts() == []


def test_identical_translator_proposals_pool_evidence():
    merged = merge_proposals([P("glossary", {"zh": "a", "vi": "b"}, evidence=["1"]),
                              P("glossary", {"zh": "a", "vi": "b"}, evidence=["2", "1"])])
    assert len(merged) == 1 and merged[0].evidence == ["1", "2"]


def test_pronoun_pair_needs_known_characters(project):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    r = m.apply([P("pronoun_pair", {"speaker_id": "ghost", "listener_id": "lin_yuan", "self_term": "ta",
                                    "address_term": "ngươi"}, "human")])
    assert "unknown character" in r.rejected[0][1]
    r = m.apply([P("pronoun_pair", {"speaker_id": "shi_zun", "listener_id": "lin_yuan", "self_term": "ta",
                                    "address_term": "ngươi", "context": "khi tức giận"}, "human")])
    assert r.applied
    assert len(m.store.pronoun_variants("shi_zun", "lin_yuan")) == 2


def test_history_diff_and_rollback(project):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    before = m.history()[0].sha
    m.manual_edit([P("glossary", {"zh": "元婴", "vi": "Nguyên Anh"}, "human")])
    head = m.history()[0]
    assert head.message == "manual edit: 1 changes"
    d = m.diff(head.sha)
    assert [r["zh"] for r in d.tables["glossary"].added] == ["元婴"]

    m.rollback(before)
    assert m.store.get_row("glossary", "元婴") is None
    assert m.history()[0].message.startswith("rollback to")
    assert len(m.history()) == 4   # init, seed, manual edit, rollback: nothing rewritten
    assert m.entry_history("glossary", "筑基")


def test_rollback_refused_while_a_job_runs(project, monkeypatch):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    monkeypatch.setattr("subagent.memory.manager.running_jobs", lambda p: ["ep002"])
    with pytest.raises(JobRunningError):
        m.rollback(m.history()[0].sha)


def test_style_rules_capped_by_usage(project):
    config, paths = project
    config.memory.style_rules_max = 2
    m = MemoryManager(paths, config)
    m.ensure_repo()
    m.apply([P("style_rule", {"rule": "A"}, "dreaming"), P("style_rule", {"rule": "B"}, "dreaming"),
             P("style_rule", {"rule": "C", "uses": 3}, "dreaming")])
    m.apply([P("style_rule", {"rule": "A", "action": "use"}, "dreaming")])
    rules = bf.read_style_rules(paths.memory)
    assert [(r.rule, r.uses) for r in rules] == [("C", 3), ("A", 2)]


def test_replaced_term_finds_human_replacement():
    assert replaced_term("Đồ nhi đã Trúc Cơ rồi.", "Đồ nhi đã Xây Nền rồi.", "Trúc Cơ") == "Xây Nền"
    assert replaced_term("Đồ nhi đã Trúc Cơ rồi.", "Đồ nhi đã Trúc Cơ.", "Trúc Cơ") is None
    assert replaced_term("Không có gì.", "Khác hẳn.", "Trúc Cơ") is None


def test_episode_update_applies_mines_briefs_and_commits(project):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    approved = [ReviewedLine(event_id="ep001:0000", start_ms=0, end_ms=1000, speaker="shi_zun", listener="lin_yuan",
                             zh="你已经筑基了", pinyin="", vi="Con đã Xây Nền rồi.", approved=True, edited=True)]
    translations = [LineTranslation(event_id="ep001:0000", speaker="lin_yuan", listener="shi_zun", speaker_conf=0.9,
                                    vi="Con đã Trúc Cơ rồi.", attempts=1,
                                    proposals=[P("glossary", {"zh": "为师", "vi": "vi sư"}, evidence=["ep001:0000"])])]
    edits = [EditRecord(edit_id="ep001:0000:vi", event_id="ep001:0000", field="vi", before="Con đã Trúc Cơ rồi.",
                        after="Con đã Xây Nền rồi."),
             EditRecord(edit_id="ep001:0000:speaker", event_id="ep001:0000", field="speaker", before="lin_yuan",
                        after="shi_zun")]
    brief = {"summary_sentence": "Lâm Uyên Trúc Cơ.", "characters_introduced": ["lin_yuan"],
             "episode_markdown": "# ep001\n## Tóm tắt\nx", "story_so_far": "Lâm Uyên Trúc Cơ."}
    llm, _ = make_llm(config, paths, {"utility": lambda msgs: brief})
    result = m.episode_update("ep001", approved, translations, edits, llm)
    assert "glossary:为师" in result.applied
    assert m.store.get_row("glossary", "筑基")["vi"] == "Xây Nền"          # human edit mined, locked entry updated
    assert (paths.memory / "speaker_corrections.jsonl").is_file()
    assert bf.read_index(paths.memory)[0].episode_id == "ep001"
    assert "ep001" in (paths.memory / "briefings" / "ep001.md").read_text(encoding="utf-8")
    assert m.history()[0].message.startswith("episode ep001:")


def test_episode_update_failure_restores_memory(project):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    translations = [LineTranslation(event_id="ep001:0000", speaker=None, listener=None, speaker_conf=1, vi="x",
                                    attempts=1, proposals=[P("glossary", {"zh": "新词", "vi": "từ mới"},
                                                             evidence=["ep001:0000"])])]
    approved = [ReviewedLine(event_id="ep001:0000", start_ms=0, end_ms=1, speaker=None, listener=None, zh="新词",
                             pinyin="", vi="x", approved=True)]

    def boom(msgs):
        raise RuntimeError("network down")

    llm, _ = make_llm(config, paths, {"utility": boom})
    with pytest.raises(Exception):  # noqa: B017
        m.episode_update("ep001", approved, translations, [], llm)
    assert m.store.get_row("glossary", "新词") is None


def test_human_lock_toggle(project):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    m.manual_edit([P("glossary", {"zh": "筑基", "vi": "Trúc Cơ", "_locked": False}, "human")])
    assert m.store.get_row("glossary", "筑基")["locked"] == 0
    m.manual_edit([P("glossary", {"zh": "新", "vi": "mới", "_locked": False}, "human")])
    assert m.store.get_row("glossary", "新")["locked"] == 0
    # only a human may set the lock explicitly
    m.apply([P("glossary", {"zh": "新", "vi": "mới", "_locked": True}, "dreaming", ["x", "y"])])
    assert m.store.get_row("glossary", "新")["locked"] == 0


def test_deleted_lines_are_not_memory_evidence(project):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    kept = ReviewedLine(event_id="ep001:0000", start_ms=0, end_ms=1, speaker=None, listener=None, zh="甲", pinyin="",
                        vi="a", approved=True)
    gone = kept.model_copy(update={"event_id": "ep001:0001", "deleted": True})
    translations = [LineTranslation(event_id=x.event_id, speaker=None, listener=None, speaker_conf=1, vi="a",
                                    attempts=1, proposals=[P("glossary", {"zh": f"词{i}", "vi": f"từ {i}"},
                                                             evidence=[x.event_id])])
                    for i, x in enumerate((kept, gone))]
    m.episode_update("ep001", [kept, gone], translations, [], llm=None)
    assert m.store.get_row("glossary", "词0") is not None
    assert m.store.get_row("glossary", "词1") is None


def test_mining_an_episode_again_replaces_its_speaker_corrections(project):
    import json

    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)

    def mine(ep: str) -> None:
        line = ReviewedLine(event_id=f"{ep}:0000", start_ms=0, end_ms=1000, speaker="shi_zun", listener=None,
                            zh="字", pinyin="", vi="x", approved=True)
        edit = EditRecord(edit_id=f"{ep}:0000:speaker", event_id=f"{ep}:0000", field="speaker", before="lin_yuan",
                          after="shi_zun")
        m.mine_edits(ep, [line], [], [edit])

    mine("ep002")
    mine("ep001")
    mine("ep001")                                   # the review of ep001 finished again
    rows = [json.loads(ln) for ln in (paths.memory / "speaker_corrections.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [r["episode"] for r in rows] == ["ep002", "ep001"]
