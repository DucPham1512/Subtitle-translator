"""Review screen state without widgets: undo / redo steps and the line filter."""

from __future__ import annotations

from app.views.review_state import MERGE_S, LineFilter, LineHistory, line_matches
from subagent.kernel import ReviewedLine


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
