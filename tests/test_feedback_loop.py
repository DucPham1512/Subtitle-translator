"""Evaluator feedback loop: OCR fragments, soft reading-speed rule, retry history, reviewer corrections."""

from __future__ import annotations

from subagent.kernel.models import (
    EditRecord,
    Evaluation,
    LineTranslation,
    OcrReading,
    ReviewedLine,
    SubtitleEvent,
)
from subagent.kernel.util import read_jsonl, write_jsonl
from subagent.memory.store import MemoryStore
from subagent.ocr.events import build_events
from subagent.stages import review, translate
from tests.conftest import make_llm, register_episode, seed_memory, user_json
from tests.test_translate_review import GOOD, _review_ctx, _translate_ctx


def _reading(t: int, text: str, kind: str = "text") -> OcrReading:
    return OcrReading(t_ms=t, kind=kind, text=text, confidence=0.9, box_height=0.4, box_vcenter=0.5, box_hcenter=0.5)


def test_fragments_merge_by_time_on_screen_and_noise_is_predeleted(project):
    config, _ = project
    readings = [
        _reading(0, "他们都留"),              # caught mid-change for one frame: part of the next line
        _reading(250, "他们都留下了后代"),     # one reading but on screen 3 s: a real line, not a fragment
        _reading(3250, "史"),                 # one frame of noise
        _reading(3500, "信不信我把你打出来"),  # one frame, but a real-looking sentence
        _reading(3750, "", kind="empty"),
    ]
    events = build_events(readings, "ep001", 5000, config)
    assert [(e.zh, e.start_ms, e.end_ms) for e in events] == [
        ("他们都留下了后代", 0, 3250), ("史", 3250, 3500), ("信不信我把你打出来", 3500, 3750)]
    assert [("ocr_fragment" in e.flags) for e in events] == [False, True, True]

    draft = review.build_draft(events, [], [])
    assert [line.deleted for line in draft] == [False, True, False]     # only the noisy one is pre-deleted
    assert not review.build_draft(events, [], [], predelete_fragments=False)[1].deleted
    assert review.looks_like_noise("姬7", 2) and review.looks_like_noise("表哥", 2)
    assert not review.looks_like_noise("信不信我把你打出来", 2)


def test_predeleted_lines_are_not_reviewer_edits(project):
    ctx = _review_ctx(project)
    events = read_jsonl(ctx.artifact("events.jsonl"), SubtitleEvent)
    events[2].flags.append("ocr_fragment")
    events[2].zh = "史"
    write_jsonl(ctx.artifact("events.jsonl"), events)
    review.gate(ctx.work, "human")
    lines = review.load_draft(ctx.work)
    assert lines[2].deleted
    for x in lines:
        x.approved = True
    review.save_draft(ctx.work, lines)
    known = MemoryStore(ctx.paths.memory_db).character_ids()
    _, edits = review.finish_review(ctx.work, known)
    assert edits == []                                   # the pipeline pre-deleted it, not the reviewer
    lines[2].deleted = False                             # restoring it is a reviewer edit
    lines[2].vi = "Sử"
    review.save_draft(ctx.work, lines)
    _, edits = review.finish_review(ctx.work, known)
    assert ("deleted", "true", "false") in {(e.field, e.before, e.after) for e in edits}


def _rubric(score_for):
    def evaluator(messages):
        out = []
        for x in user_json(messages, "Lines to evaluate"):
            s = score_for(x)
            out.append({"event_id": x["event_id"],
                        "scores": dict.fromkeys(["meaning", "pronouns", "register", "naturalness", "speaker"], s),
                        "feedback": "" if s >= 4 else "dịch thiếu ý",
                        "suggestion": "" if s >= 4 else "Bản sửa của evaluator"})
        return {"lines": out}
    return evaluator


def _translator(vi_for):
    def translator(messages):
        return {"lines": [{"event_id": x["event_id"], "speaker": GOOD[x["event_id"]][0],
                           "listener": GOOD[x["event_id"]][1], "speaker_conf": 0.9, "vi": vi_for(x, messages)}
                          for x in user_json(messages, "Lines to translate")]}
    return translator


def test_reading_speed_is_flagged_not_retried(project):
    ctx = _translate_ctx(project)
    long_vi = "Sư phụ ơi, đồ nhi cuối cùng đã Trúc Cơ thành công rồi đó"   # > 17 chars/s for a 2.2 s line
    vi = _translator(lambda x, m: long_vi if x["event_id"] == "ep001:0000" else GOOD[x["event_id"]][2])
    ctx.llm_override, clients = make_llm(ctx.config, ctx.paths, {"translator": vi, "evaluator": _rubric(lambda x: 5)})
    translate.run(ctx)
    out = {t.event_id: t for t in read_jsonl(ctx.artifact("translations.jsonl"), LineTranslation)}
    assert len(clients["translator"].calls) == 1         # no retry spent on reading speed
    assert out["ep001:0000"].vi == long_vi and "cps_exceeded" in out["ep001:0000"].flags
    assert "retry_cap" not in out["ep001:0000"].flags
    first = next(e for e in read_jsonl(ctx.artifact("evaluations.jsonl"), Evaluation) if e.event_id == "ep001:0000")
    assert first.passed and first.soft_failures == ["cps"]


def test_retry_sends_history_and_suggestion(project):
    ctx = _translate_ctx(project)
    calls: list[str] = []

    def vi_for(x, messages):
        if messages[1]["content"] not in calls:
            calls.append(messages[1]["content"])
        return f"{GOOD[x['event_id']][2]} (v{len(calls)})"

    def score(x):   # line 0001 fails its first two versions, then passes
        return 2 if x["event_id"] == "ep001:0001" and "(v3)" not in x["vi"] else 5

    ctx.llm_override, _ = make_llm(ctx.config, ctx.paths, {"translator": _translator(vi_for),
                                                           "evaluator": _rubric(score)})
    translate.run(ctx)
    feedback = user_json([{"role": "user", "content": calls[2]}],
                         "These lines failed evaluation. Fix them using the feedback")
    assert [a["vi"][-4:] for a in feedback[0]["earlier_attempts"]] == ["(v1)", "(v2)"]
    assert feedback[0]["evaluator_suggestion"] == "Bản sửa của evaluator"
    out = {t.event_id: t for t in read_jsonl(ctx.artifact("translations.jsonl"), LineTranslation)}
    assert out["ep001:0001"].vi.endswith("(v3)") and "retry_cap" not in out["ep001:0001"].flags


def test_reviewer_corrections_reach_both_prompts(project):
    config, paths = project
    seed_memory(config, paths)
    ctx = _translate_ctx(project)                        # episode 1 is the one being translated
    done = register_episode(paths, 2)                    # a finished episode with a reviewer correction
    work = paths.episode_dir(done.id)
    write_jsonl(work / "approved.jsonl", [ReviewedLine(event_id="ep002:0000", start_ms=0, end_ms=1, speaker=None,
                                                       listener=None, zh="青龙钓帝", pinyin="",
                                                       vi="Thanh Long Điếu Đế", approved=True)])
    write_jsonl(work / "edits.jsonl", [EditRecord(edit_id="ep002:0000:vi", event_id="ep002:0000", field="vi",
                                                  before="Thanh Long Câu Đế", after="Thanh Long Điếu Đế")])
    vi = _translator(lambda x, m: GOOD[x["event_id"]][2])
    ctx.llm_override, clients = make_llm(ctx.config, ctx.paths, {"translator": vi, "evaluator": _rubric(lambda x: 5)})
    translate.run(ctx)
    expected = "- 青龙钓帝: “Thanh Long Câu Đế” → “Thanh Long Điếu Đế”"
    assert expected in clients["translator"].calls[0]["messages"][0]["content"]
    assert expected in clients["evaluator"].calls[0]["messages"][0]["content"]


def test_a_passing_line_keeps_the_evaluators_suggestion_for_the_reviewer(project):
    ctx = _translate_ctx(project)
    vi = _translator(lambda x, m: GOOD[x["event_id"]][2])
    ctx.llm_override, clients = make_llm(ctx.config, ctx.paths, {
        "translator": vi, "evaluator": _rubric(lambda x: 3 if x["event_id"] == "ep001:0001" else 5)})
    translate.run(ctx)
    assert len(clients["translator"].calls) == 1          # a 3 passes (min_score 3): no retry
    ev = next(e for e in read_jsonl(ctx.artifact("evaluations.jsonl"), Evaluation) if e.event_id == "ep001:0001")
    assert ev.passed and ev.suggestion == "Bản sửa của evaluator"
    assert "suggested: Bản sửa của evaluator" in ev.feedback
