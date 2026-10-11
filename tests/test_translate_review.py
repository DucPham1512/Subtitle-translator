from __future__ import annotations

import numpy as np
import pytest

from subagent.context import EpisodeContext
from subagent.errors import ReviewIncompleteError, SubagentError
from subagent.memory.store import MemoryStore
from subagent.models import (
    Evaluation,
    LineTranslation,
    PinyinLine,
    ReviewedLine,
    SpeakerCandidates,
    SubtitleEvent,
)
from subagent.stages import review, sprite, translate
from subagent.stages.evaluate import RuleContext, rule_checks
from subagent.stages.windows import build_windows
from subagent.util import atomic_write_json, read_jsonl, write_jsonl
from tests.conftest import make_episode, make_llm, sample_events, seed_memory, user_json, write_events


def _line(vi, speaker="lin_yuan", listener="shi_zun", **kw):
    return LineTranslation(event_id="ep001:0000", speaker=speaker, listener=listener, speaker_conf=0.9, vi=vi,
                           attempts=1, **kw)


# -- rule checks -----------------------------------------------------------------------------------

@pytest.fixture
def rules(project):
    config, paths = project
    seed_memory(config, paths)
    return RuleContext(config, MemoryStore(paths.memory_db))


def test_rules_pass_for_a_good_line(rules):
    ev = sample_events()[0]
    failures, warnings = rule_checks(_line("Sư phụ, đồ nhi đã Trúc Cơ rồi."), ev, None, rules)
    assert failures == [] and warnings == []


def test_rules_catch_glossary_length_cps_and_speaker(rules):
    ev = sample_events()[0]
    codes = {f.code for f in rule_checks(_line("Sư phụ, đồ nhi đã xây nền rồi."), ev, None, rules)[0]}
    assert codes == {"glossary"}
    long = "Sư phụ ơi, đồ nhi cuối cùng đã Trúc Cơ thành công rồi, sau bao nhiêu năm tháng khổ luyện gian nan vất vả"
    codes = {f.code for f in rule_checks(_line(long), ev, None, rules)[0]}
    assert {"cps", "line_count"} <= codes
    codes = {f.code for f in rule_checks(_line("Đồ nhi đã Trúc Cơ.", speaker="nobody"), ev, None, rules)[0]}
    assert codes == {"speaker_unknown"}
    cands = SpeakerCandidates(event_id=ev.id, candidates=[("shi_zun", 0.6), ("lin_yuan", 0.58)], status="confusable")
    ok = rule_checks(_line("Đồ nhi đã Trúc Cơ."), ev, cands, rules)[0]
    assert ok == []
    cands.candidates = [("shi_zun", 0.6)]
    bad = rule_checks(_line("Đồ nhi đã Trúc Cơ."), ev, cands, rules)[0]
    assert [f.code for f in bad] == ["speaker_not_candidate"]


def test_pronoun_rule(rules):
    ev = sample_events()[0]
    bad = rule_checks(_line("Ta đã Trúc Cơ rồi, ngươi xem."), ev, None, rules)[0]
    assert [f.code for f in bad] == ["pronoun"]
    failures, warnings = rule_checks(_line("Sư phụ, ta đã Trúc Cơ."), ev, None, rules)
    assert failures == [] and warnings   # matrix term present: warning only


# -- translate loop --------------------------------------------------------------------------------

def _translate_ctx(project):
    config, paths = project
    seed_memory(config, paths)
    ctx = EpisodeContext(config, paths, make_episode(paths))
    events = sample_events()
    write_events(ctx.work, events)
    write_jsonl(ctx.artifact("speakers.jsonl"), [SpeakerCandidates(event_id=e.id, status="unknown") for e in events])
    atomic_write_json(ctx.artifact("windows.json"), [w.model_dump() for w in build_windows(events, config.windows)])
    return ctx


GOOD = {
    "ep001:0000": ("lin_yuan", "shi_zun", "Sư phụ, đồ nhi đã Trúc Cơ rồi."),
    "ep001:0001": ("shi_zun", "lin_yuan", "Tốt. Con không làm vi sư thất vọng."),
    "ep001:0002": ("lin_yuan", "shi_zun", "Đồ nhi muốn xuống núi lịch luyện."),
    "ep001:0003": ("shi_zun", "lin_yuan", "Xuống núi? Bên ngoài rất nguy hiểm."),
}


def test_translate_retries_only_failed_lines(project):
    ctx = _translate_ctx(project)
    requests = []

    def translator(messages):
        lines = user_json(messages, "Lines to translate")
        requests.append([x["event_id"] for x in lines])
        out = []
        for x in lines:
            s, listener, vi = GOOD[x["event_id"]]
            if x["event_id"] == "ep001:0000" and len(requests) == 1:
                vi = "Sư phụ, đồ nhi đã xây nền rồi."      # glossary miss on the first attempt
            out.append({"event_id": x["event_id"], "speaker": s, "listener": listener, "speaker_conf": 0.9, "vi": vi,
                        "proposals": [{"kind": "glossary", "payload": {"zh": "下山", "vi": "xuống núi"},
                                       "evidence": [x["event_id"]]}] if x["event_id"] == "ep001:0002" else []})
        return {"lines": out}

    def evaluator(messages):
        lines = user_json(messages, "Lines to evaluate")
        return {"lines": [{"event_id": x["event_id"], "scores": dict.fromkeys(
            ["meaning", "pronouns", "register", "naturalness", "speaker"], 4), "feedback": ""} for x in lines]}

    ctx.llm_override, clients = make_llm(ctx.config, ctx.paths, {"translator": translator, "evaluator": evaluator})
    counts = translate.run(ctx)
    assert requests == [list(GOOD), ["ep001:0000"]]
    retry_msg = clients["translator"].calls[1]["messages"][1]["content"]
    assert "failed evaluation" in retry_msg and "Trúc Cơ" in retry_msg
    assert clients["translator"].calls[0]["messages"][0] == clients["translator"].calls[1]["messages"][0]
    out = {t.event_id: t for t in read_jsonl(ctx.artifact("translations.jsonl"), LineTranslation)}
    assert out["ep001:0000"].vi == GOOD["ep001:0000"][2] and out["ep001:0000"].attempts == 2
    assert out["ep001:0002"].proposals[0].source == "translator"
    assert counts["first_pass"] == 3 and counts["retry_cap"] == 0
    evals = read_jsonl(ctx.artifact("evaluations.jsonl"), Evaluation)
    assert len(evals) == 5


def test_translate_retry_cap_keeps_best_and_flags(project):
    ctx = _translate_ctx(project)

    def translator(messages):
        lines = user_json(messages, "Lines to translate")
        return {"lines": [{"event_id": x["event_id"], "speaker": GOOD[x["event_id"]][0],
                           "listener": GOOD[x["event_id"]][1], "speaker_conf": 0.3,
                           "vi": GOOD[x["event_id"]][2]} for x in lines]}

    def evaluator(messages):
        lines = user_json(messages, "Lines to evaluate")
        return {"lines": [{"event_id": x["event_id"], "scores": {"meaning": 2, "pronouns": 4, "register": 4,
                                                                 "naturalness": 4, "speaker": 4},
                           "feedback": "meaning is off"} for x in lines]}

    ctx.llm_override, clients = make_llm(ctx.config, ctx.paths, {"translator": translator, "evaluator": evaluator})
    translate.run(ctx)
    out = read_jsonl(ctx.artifact("translations.jsonl"), LineTranslation)
    assert all("retry_cap" in t.flags and "low_speaker_conf" in t.flags for t in out)
    # attempt 2 returned the same translation as attempt 1: no point judging or retrying it again
    assert all(t.attempts == 2 for t in out)
    assert len(clients["translator"].calls) == 2
    assert len(clients["evaluator"].calls) == 1


def test_register_block_selection(project):
    config, paths = project
    from subagent.registers import load_register

    prompt = (paths.prompts / "translator_system.md").read_text(encoding="utf-8")
    style = load_register(paths.root, "co_trang_tien_hiep")
    text = translate.translator_static(prompt, "co_trang_tien_hiep", config, style.body)
    assert "Register: cổ trang" in text and "<!--" not in text and "{{" not in text
    with pytest.raises(SubagentError):                       # a style without its file
        translate.translator_static(prompt, "no_such_style", config, None)


# -- sprite ----------------------------------------------------------------------------------------

def test_sprite_resolves_single_match(project):
    config, paths = project
    config.sprite.enabled = True
    seed_memory(config, paths)
    rng = np.random.default_rng(0)
    frame = rng.integers(0, 255, (360, 640), dtype=np.uint8)
    face = frame[100:180, 200:260].copy()
    other = rng.integers(0, 255, (80, 60), dtype=np.uint8)
    sprite.save_template(paths, "lin_yuan", face, "a")
    sprite.save_template(paths, "shi_zun", other, "a")

    ctx = EpisodeContext(config, paths, make_episode(paths))
    events = sample_events()
    write_events(ctx.work, events)
    write_jsonl(ctx.artifact("speakers.jsonl"), [SpeakerCandidates(
        event_id=e.id, candidates=[("shi_zun", 0.5), ("lin_yuan", 0.49)], status="confusable") for e in events])
    lines = [LineTranslation(event_id=e.id, speaker="shi_zun", listener=None, speaker_conf=0.3, vi="x", attempts=1,
                             flags=["low_speaker_conf"] if i < 2 else []) for i, e in enumerate(events)]
    write_jsonl(ctx.artifact("translations.jsonl"), lines)
    counts = sprite.run(ctx, frame_reader=lambda t: frame)
    assert counts == {"triggered": 2, "resolved": 2, "unresolved": 0}
    out = read_jsonl(ctx.artifact("translations.jsonl"), LineTranslation)
    assert out[0].speaker == "lin_yuan" and "low_speaker_conf" not in out[0].flags


# -- review ----------------------------------------------------------------------------------------

def _review_ctx(project):
    config, paths = project
    seed_memory(config, paths)
    ctx = EpisodeContext(config, paths, make_episode(paths))
    events = sample_events()
    events[3].flags = ["non_dialogue_suspect"]
    write_events(ctx.work, events)
    write_jsonl(ctx.artifact("pinyin.jsonl"), [PinyinLine(event_id=e.id, pinyin="py") for e in events])
    trs = [LineTranslation(event_id=e.id, speaker=GOOD[e.id][0], listener=GOOD[e.id][1], speaker_conf=0.9,
                           vi=GOOD[e.id][2], attempts=1) for e in events]
    trs[1].flags = ["retry_cap"]
    write_jsonl(ctx.artifact("translations.jsonl"), trs)
    return ctx


def test_review_order_is_chronological(project):
    ctx = _review_ctx(project)                       # lines 1 and 3 are flagged: they stay in time order
    draft = list(reversed(review.original_draft(ctx.work)))
    lines = review.review_order(draft)
    assert [x.event_id for x in lines] == ["ep001:0000", "ep001:0001", "ep001:0002", "ep001:0003"]


def test_gate_auto_and_human(project):
    ctx = _review_ctx(project)
    assert review.gate(ctx.work, "human") == "awaiting_review"
    assert not ctx.artifact("approved.jsonl").exists() and review.load_draft(ctx.work)
    assert review.gate(ctx.work, "auto") == "approved"
    assert all(x.approved for x in read_jsonl(ctx.artifact("approved.jsonl"), ReviewedLine))


def test_finish_review_validates_and_records_edits(project):
    ctx = _review_ctx(project)
    review.gate(ctx.work, "human")
    known = MemoryStore(ctx.paths.memory_db).character_ids()
    with pytest.raises(ReviewIncompleteError):
        review.finish_review(ctx.work, known)
    lines = review.load_draft(ctx.work)
    for x in lines:
        x.approved = True
    lines[0].vi = "Sư phụ, con đã Trúc Cơ."
    lines[0].speaker = "ghost"
    review.save_draft(ctx.work, lines)
    with pytest.raises(ReviewIncompleteError, match="unknown speaker"):
        review.finish_review(ctx.work, known)
    lines[0].speaker = "shi_zun"
    review.save_draft(ctx.work, lines)
    approved, edits = review.finish_review(ctx.work, known)
    assert {e.field for e in edits} == {"vi", "speaker"}
    assert approved[0].edited and not approved[1].edited


def test_regenerate_pinyin_flags_polyphones(project):
    from tests.test_pinyin_voice_windows import _engine

    engine = _engine()
    line = ReviewedLine(event_id="e", start_ms=0, end_ms=1, speaker=None, listener=None, zh="好了", pinyin="",
                        vi="x")
    out = review.regenerate_pinyin(line, engine)
    assert out.pinyin and "check_pinyin" in out.flags
    kept = review.regenerate_pinyin(line.model_copy(update={"pinyin": "mine", "pinyin_overridden": True}), engine)
    assert kept.pinyin == "mine"


def test_events_without_translation_are_flagged(project):
    ctx = _review_ctx(project)
    draft = review.build_draft(read_jsonl(ctx.artifact("events.jsonl"), SubtitleEvent), [], [])
    assert all("missing_translation" in x.flags for x in draft)


def test_deleted_lines_need_no_approval_and_are_recorded(project):
    ctx = _review_ctx(project)
    review.gate(ctx.work, "human")
    known = MemoryStore(ctx.paths.memory_db).character_ids()
    lines = review.load_draft(ctx.work)
    for x in lines[1:]:
        x.approved = True
    lines[0].deleted = True          # not approved, empty-able, still valid
    lines[0].vi = ""
    review.save_draft(ctx.work, lines)
    approved, edits = review.finish_review(ctx.work, known)
    assert {(e.field, e.before, e.after) for e in edits if e.event_id == "ep001:0000"} >= {("deleted", "false", "true")}
    assert approved[0].deleted
    assert not review.needs_attention(approved[0].model_copy(update={"flags": ["retry_cap"]}))


def test_glossary_rule_matches_whole_words_only(project):
    config, paths = project
    seed_memory(config, paths)
    from subagent.memory.manager import MemoryManager
    from subagent.models import MemoryProposal

    MemoryManager(paths, config).apply([MemoryProposal(kind="glossary", source="bootstrap",
                                                       payload={"zh": "鱼", "vi": "cá"})])
    rc = RuleContext(config, MemoryStore(paths.memory_db))
    ev = sample_events()[0]
    fishing = ev.model_copy(update={"zh": "你们三个先去钓鱼吧"})       # 钓鱼 "to fish": 鱼 is not a word here
    assert rule_checks(_line("Ba người các con đi câu trước đi"), fishing, None, rc)[0] == []
    hook = ev.model_copy(update={"zh": "挂上鱼钩"})                     # 鱼钩 "fish hook"
    assert [e.zh for e in rc.glossary_in(hook.zh)] == []
    fish = ev.model_copy(update={"zh": "这条鱼卖给我"})                 # 鱼 on its own: the rule applies
    assert [f.code for f in rule_checks(_line("Bán con này đi", speaker=None), fish, None, rc)[0]] == ["glossary"]
    assert [e.zh for e in rc.glossary_in("林渊已经筑基")] == ["林渊", "筑基"]   # multi-character terms still found
    for coinage in ("我就教你们降鱼钓法", "这条何罗鱼钓上来"):     # the show's own words, not in the glossary yet
        assert [e.zh for e in rc.glossary_in(coinage)] == []
