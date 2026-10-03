"""Whole-script review: lossless repeat merges, flags, memory of reviewer decisions, confident model removals."""

from __future__ import annotations

from subagent.context import EpisodeContext
from subagent.memory.manager import MemoryManager
from subagent.memory.store import LineDecision, MemoryStore
from subagent.models import LineTranslation, ReviewedLine, ScriptDecision, SubtitleEvent
from subagent.stages import review, script_review
from subagent.util import read_jsonl, write_jsonl
from tests.conftest import make_episode, make_llm, seed_memory, user_json


def _ev(i: int, zh: str, start: int, end: int) -> SubtitleEvent:
    return SubtitleEvent(id=f"ep001:{i:04d}", start_ms=start, end_ms=end, zh_raw=zh, zh=zh, ocr_conf=0.9)


EVENTS = [
    _ev(0, "他们都留下了后代", 0, 1000),
    _ev(1, "他们都留下了后代", 1000, 2000),        # same text back to back: one subtitle split in two
    _ev(2, "出来单挑啊", 5000, 6000),
    _ev(3, "单挑啊", 6200, 7000),                  # echo within 4 s: maybe real, only flagged
    _ev(4, "楚", 9000, 9500),
    _ev(5, "哼", 10000, 10500),
    _ev(6, "你以为我吊你啊", 11000, 12500),
    _ev(7, "频道水印", 13000, 15000),
]


def test_repeats_merge_losslessly_and_echoes_are_only_flagged(project):
    config, _ = project
    d = {x.event_id: x for x in script_review.find_repeats(EVENTS, config.script_review)}
    assert d["ep001:0001"].action == "remove" and d["ep001:0001"].keep_id == "ep001:0000"
    assert d["ep001:0003"].action == "flag" and d["ep001:0003"].reason == "repeat"
    assert set(d) == {"ep001:0001", "ep001:0003"}

    lines = review.build_draft(EVENTS, [], [], decisions=list(d.values()))
    by = {x.event_id: x for x in lines}
    assert by["ep001:0001"].deleted and "script_repeat" in by["ep001:0001"].flags
    assert (by["ep001:0000"].start_ms, by["ep001:0000"].end_ms) == (0, 2000)    # takes over the removed time
    assert not by["ep001:0003"].deleted and "script_suspect" in by["ep001:0003"].flags


def test_memory_removes_only_short_texts_never_kept(project):
    config, _ = project
    memory = {"楚": LineDecision(zh="楚", remove_count=3), "哼": LineDecision(zh="哼", remove_count=2, keep_count=1),
              "你以为我吊你啊": LineDecision(zh="你以为我吊你啊", remove_count=5)}
    out = script_review.memory_removals(EVENTS, memory, config.script_review)
    assert [(x.event_id, x.source) for x in out] == [("ep001:0004", "memory")]   # 哼 was kept once; long text never


def _ctx(project):
    config, paths = project
    seed_memory(config, paths)
    ctx = EpisodeContext(config, paths, make_episode(paths))
    ctx.work.mkdir(parents=True, exist_ok=True)
    write_jsonl(ctx.artifact("events.jsonl"), EVENTS)
    write_jsonl(ctx.artifact("translations.jsonl"), [
        LineTranslation(event_id=e.id, speaker=None, listener=None, speaker_conf=1, vi="x", attempts=1) for e in EVENTS])
    return ctx


def test_model_removes_only_when_confident(project):
    ctx = _ctx(project)
    seen = {}

    def utility(messages):
        rows = user_json(messages, "The whole episode script, in time order")
        seen["already"] = {r["event_id"] for r in rows if r.get("already_removed")}
        return {"lines": [
            {"event_id": "ep001:0007", "action": "remove", "reason": "unrelated", "confidence": 0.95, "note": "watermark"},
            {"event_id": "ep001:0005", "action": "remove", "reason": "noise", "confidence": 0.6, "note": "maybe noise"},
            {"event_id": "ep001:0001", "action": "remove", "reason": "repeat", "confidence": 0.99},   # already merged
        ]}

    ctx.llm_override, _ = make_llm(ctx.config, ctx.paths, {"utility": utility})
    counts = script_review.run(ctx)
    d = {x.event_id: x for x in read_jsonl(ctx.artifact("script_review.jsonl"), ScriptDecision)}
    assert seen["already"] == {"ep001:0001"}
    assert d["ep001:0007"].action == "remove" and d["ep001:0007"].source == "llm"
    assert d["ep001:0005"].action == "flag"                                       # 0.6 < 0.8: the reviewer decides
    assert d["ep001:0001"].source == "rule"
    assert counts["removed"] == 2 and counts["removed_by_llm"] == 1


def test_safety_cap_turns_mass_removals_into_flags(project):
    ctx = _ctx(project)

    def utility(messages):
        return {"lines": [{"event_id": f"ep001:{i:04d}", "action": "remove", "reason": "noise", "confidence": c}
                          for i, c in ((2, 0.91), (4, 0.99), (5, 0.93), (6, 0.95), (7, 0.92))]}

    ctx.llm_override, _ = make_llm(ctx.config, ctx.paths, {"utility": utility})
    script_review.run(ctx)
    d = {x.event_id: x for x in read_jsonl(ctx.artifact("script_review.jsonl"), ScriptDecision) if x.source == "llm"}
    # 8 lines x 10% allows 1 removal: only the most confident is removed, the rest are flagged
    assert [k for k, x in d.items() if x.action == "remove"] == ["ep001:0004"]
    assert all(x.action == "flag" and "safety cap" in x.note for k, x in d.items() if k != "ep001:0004")


def test_reviewer_decisions_become_script_memory(project):
    config, paths = project
    seed_memory(config, paths)
    m = MemoryManager(paths, config)
    m.record_line_decisions("ep001", removed=["楚", "楚", "90"], kept=["哼"])
    m.record_line_decisions("ep002", removed=["楚。"], kept=["哼", "楚"])
    rows = {d.zh: d for d in MemoryStore(paths.memory_db).line_decisions()}
    assert (rows["楚"].remove_count, rows["楚"].keep_count, rows["楚"].last_episode) == (3, 1, "ep002")
    assert rows["哼"].keep_count == 2 and rows["90"].remove_count == 1
    block = script_review.examples_block(list(rows.values()), 30)
    assert "楚 (×3)" in block and "哼 (×2)" in block

    m.manual_edit([__import__("subagent.models", fromlist=["MemoryProposal"]).MemoryProposal(
        kind="line_decision", source="human", payload={"zh": "90", "keep_count": 5})])
    m.record_line_decisions("ep003", removed=["90"], kept=[])                    # locked by the human edit
    assert {d.zh: d for d in MemoryStore(paths.memory_db).line_decisions()}["90"].remove_count == 1


def test_pipeline_records_what_the_reviewer_removed_and_kept(project):
    from subagent.pipeline import Pipeline

    ctx = _ctx(project)
    write_jsonl(ctx.artifact("script_review.jsonl"), [
        ScriptDecision(event_id="ep001:0001", action="remove", reason="repeat", source="rule", keep_id="ep001:0000"),
        ScriptDecision(event_id="ep001:0004", action="remove", reason="noise", source="memory")])
    final = review.original_draft(ctx.work)
    by = {x.event_id: x for x in final}
    by["ep001:0004"].deleted = False      # reviewer restores 楚
    by["ep001:0006"].deleted = True       # and deletes a long line
    removed, kept = Pipeline(ctx.config, ctx.paths)._line_decisions(ctx, list(by.values()))
    assert removed == ["你以为我吊你啊"]                                            # the merged repeat is not counted
    assert sorted(kept) == ["哼", "楚"]
    assert isinstance(final[0], ReviewedLine)


def test_ocr_fixes_are_checked_before_they_are_suggested(project):
    ctx = _ctx(project)
    events = [_ev(0, "怎么可能姬", 0, 1000), _ev(1, "太多7", 2000, 3000), _ev(2, "第7个", 4000, 5000),
              _ev(3, "来7", 6000, 7000), _ev(4, "我知道7", 8000, 9000), _ev(5, "你以为我吊你啊", 10000, 11000)]
    write_jsonl(ctx.artifact("events.jsonl"), events)
    fix = lambda i, zh, ev="context checked": {  # noqa: E731
        "event_id": f"ep001:{i:04d}", "action": "fix", "reason": "ocr", "confidence": 0.9, "zh_fix": zh,
        "evidence": ev, "note": "OCR"}

    def utility(messages):
        return {"lines": [
            fix(0, "怎么可能"),                    # stray character at the edge: suggested
            fix(1, "太多了"),                      # 7 as the particle: suggested
            fix(2, "第了个"),                      # 7 after 第 is a number: refused, flagged
            fix(3, "来"),                          # a 7 is never just dropped: refused
            fix(4, "我知道7了"),                    # 了 added next to the 7: refused
            fix(5, "你以为我钓你啊", ev=""),         # no context check given: refused
        ]}

    ctx.llm_override, _ = make_llm(ctx.config, ctx.paths, {"utility": utility})
    counts = script_review.run(ctx)
    d = {x.event_id: x for x in read_jsonl(ctx.artifact("script_review.jsonl"), ScriptDecision)}
    assert d["ep001:0000"].action == "fix" and d["ep001:0000"].zh_fix == "怎么可能"
    assert d["ep001:0001"].zh_fix == "太多了" and d["ep001:0001"].evidence == "context checked"
    assert all(d[f"ep001:{i:04d}"].action == "flag" and d[f"ep001:{i:04d}"].reason == "ocr" for i in (2, 3, 4, 5))
    assert counts["ocr_fixes"] == 2
    lines = [ReviewedLine(event_id=e.id, start_ms=e.start_ms, end_ms=e.end_ms, speaker=None, listener=None,
                          zh=e.zh, pinyin="", vi="x") for e in events]
    flagged = {x.event_id: x for x in review.apply_script_review(lines, list(d.values()))}
    assert "script_ocr" in flagged["ep001:0000"].flags and flagged["ep001:0000"].zh == "怎么可能姬"   # never applied
