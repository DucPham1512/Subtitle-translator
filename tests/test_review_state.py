"""Review screen state without widgets: undo / redo steps, the line filter and counts, audit marking, new NPC ids."""

from __future__ import annotations

from app.views.review_state import (
    MERGE_S,
    LineFilter,
    LineHistory,
    all_correct_mark,
    line_matches,
    marked_count,
    next_npc_number,
    next_pending,
    next_unmarked,
    review_counts,
    row_state,
)
from subagent.kernel import AuditMark, ReviewedLine


def _line(eid: str = "ep001:0000", **kw) -> ReviewedLine:
    base = {"event_id": eid, "start_ms": 0, "end_ms": 1000, "speaker": "lin_yuan", "listener": None, "zh": "你好",
            "pinyin": "nǐ hǎo", "vi": "Chào ngươi"}
    return ReviewedLine(**(base | kw))


class _Clock:
    def __init__(self) -> None:
        self.t = 100.0

    def __call__(self) -> float:
        return self.t


def test_typing_in_one_field_is_one_undo_step():
    clock = _Clock()
    h = LineHistory(clock)
    line = _line()
    h.push(line, "vi")
    clock.t += MERGE_S / 2
    h.push(line.model_copy(update={"vi": "Chào"}), "vi")       # same field soon after: merged
    assert len(h.undo[line.event_id]) == 1
    h.push(line, "pinyin")                                       # another field: a new step
    clock.t += MERGE_S * 2
    h.push(line, "pinyin")                                       # same field, later: a new step
    assert len(h.undo[line.event_id]) == 3


def test_undo_and_redo_restore_the_line_and_break_the_merge():
    clock = _Clock()
    h = LineHistory(clock)
    before = _line()
    after = before.model_copy(update={"vi": "Chào huynh", "edited": True})
    h.push(before, "vi")
    assert h.undo_step(after) == before
    assert h.undo_step(before) is None                           # nothing left to undo
    assert h.redo_step(before) == after
    h.push(after, "vi")                                          # right after undo, still a new step
    assert len(h.undo[before.event_id]) == 2
    assert h.redo[before.event_id] == []                         # a new edit clears redo


def test_steps_are_per_line_and_copies():
    h = LineHistory(_Clock())
    a, b = _line("ep001:0000"), _line("ep001:0001")
    h.push(a, "vi")
    a.vi = "changed later"
    assert h.undo_step(b) is None
    assert h.undo_step(a).vi == "Chào ngươi"
    h.clear()
    assert h.undo == {} and h.redo == {}


def test_line_filter():
    flagged = _line(flags=["cps_exceeded"])
    plain = _line("ep001:0001", speaker="shi_zun", approved=True, zh="师尊", vi="Sư tôn")
    assert line_matches(flagged, LineFilter()) and line_matches(plain, LineFilter())
    assert line_matches(flagged, LineFilter(flag="cps_exceeded"))
    assert not line_matches(plain, LineFilter(flag="cps_exceeded"))
    assert line_matches(flagged, LineFilter(flag="rule_warnings"))
    assert not line_matches(plain, LineFilter(flag="rule_warnings"))
    assert line_matches(plain, LineFilter(speaker="shi_zun"))
    assert not line_matches(flagged, LineFilter(speaker="shi_zun"))
    assert not line_matches(plain, LineFilter(unapproved_only=True))
    assert line_matches(plain, LineFilter(text="  SƯ "))           # trimmed, case-insensitive, Vietnamese
    assert line_matches(plain, LineFilter(text="师"))              # Chinese
    assert not line_matches(plain, LineFilter(text="chào"))
    assert line_matches(plain, LineFilter(sample={"ep001:0001": None}))
    assert not line_matches(flagged, LineFilter(sample={"ep001:0001": None}))
    assert not line_matches(flagged, LineFilter(sample={}))       # audit mode with an empty sample shows nothing


def test_audit_marking():
    sample = {"a": None, "b": None, "c": None}
    marks = {"a": AuditMark(event_id="a", speaker=True), "b": AuditMark(event_id="b")}   # b: opened, not marked
    assert marked_count(sample, marks) == 1
    old = AuditMark(event_id="c", pronouns=False, na=["pronouns"], note="no pronoun")
    mark = all_correct_mark("c", old, "lin_yuan", "2026-11-03T10:00:00")
    assert (mark.speaker, mark.ocr, mark.translation, mark.pronouns) == (True, True, True, None)   # n/a kept
    assert mark.note == "no pronoun" and mark.speaker_value == "lin_yuan" and mark.marked_at.startswith("2026")
    assert all_correct_mark("a", None, None, "t").na == []


def test_next_unmarked_wraps_and_waits_for_who_really_speaks():
    order = ["a", "b", "c"]
    done = AuditMark(event_id="", speaker=True)
    assert next_unmarked(order, "a", {"a": done}) == "b"
    assert next_unmarked(order, "c", {"c": done, "b": done}) == "a"              # wraps round
    assert next_unmarked(order, None, {}) == "a"                               # nothing selected: the first
    wrong = AuditMark(event_id="b", speaker=False)
    assert next_unmarked(order, "a", {"a": done, "b": wrong, "c": done}) == "b"  # wrong but no answer yet
    answered = wrong.model_copy(update={"correct_speaker": "shi_zun"})
    assert next_unmarked(order, "a", {"a": done, "b": answered, "c": done}) is None


def test_next_npc_number_counts_this_episode_only():
    ids = ["lin_yuan", "npc_007_01", "npc_007_03", "npc_006_09", "npc_7_02"]   # the last is not an automatic id
    assert next_npc_number(ids, "npc", 7) == 4
    assert next_npc_number(ids, "npc", 8) == 1
    assert next_npc_number([], "npc", 7) == 1


def test_review_counts_leave_deleted_lines_out():
    lines = [_line("a", flags=["cps_exceeded"]), _line("b", approved=True), _line("c", deleted=True, flags=["x"]),
             _line("d", approved=True, flags=["cps_exceeded"])]
    c = review_counts(lines)
    assert (c.total, c.approved, c.flagged_left, c.deleted) == (3, 2, 1, 1)


def test_next_pending_goes_forward_then_wraps():
    lines = {e: _line(e) for e in "abcd"}
    lines["b"] = _line("b", approved=True)
    lines["d"] = _line("d", deleted=True)
    visible = list("abcd")
    assert next_pending(visible, lines, "a") == "c"         # b approved, skipped
    assert next_pending(visible, lines, "c") == "a"         # d deleted: wraps to the first pending
    for e in "ac":
        lines[e] = _line(e, approved=True)
    assert next_pending(visible, lines, "c") == "c"         # nothing left: stays


def test_row_state():
    assert row_state(_line()) == "·"
    assert row_state(_line(flags=["cps_exceeded"])) == "⚑"
    assert row_state(_line(approved=True, flags=["cps_exceeded"])) == "✓"
    assert row_state(_line(deleted=True, approved=True)) == "✕"
    assert row_state(_line(approved=True), None, audit=True) == "·"           # audit mode shows the mark only
    assert row_state(_line(), AuditMark(event_id="a", speaker=True), audit=True) == "✓"
    assert row_state(_line(), AuditMark(event_id="a", speaker=False), audit=True) == "✗"
