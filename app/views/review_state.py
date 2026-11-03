"""Review screen state without widgets: per-line undo / redo and the line filter (6.4). Qt-free, so it is tested
without the app."""

from __future__ import annotations

import time
from collections.abc import Callable, Collection
from dataclasses import dataclass

from app.services.review import RULE_WARNING_FLAGS
from subagent.kernel import ReviewedLine

MERGE_S = 1.5       # edits of one field of one line closer together than this are one undo step


class LineHistory:
    """Undo and redo stacks per line: each step is a copy of the line before the change."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self.undo: dict[str, list[ReviewedLine]] = {}
        self.redo: dict[str, list[ReviewedLine]] = {}
        self._clock = clock
        self._last: tuple[str, str, float] = ("", "", 0.0)

    def push(self, line: ReviewedLine, field: str) -> None:
        """Remember the line as it is before an edit of `field`; typing in one field makes one step."""
        now = self._clock()
        last_id, last_field, last_t = self._last
        self._last = (line.event_id, field, now)
        if last_id == line.event_id and last_field == field and now - last_t < MERGE_S:
            return
        self.undo.setdefault(line.event_id, []).append(line.model_copy(deep=True))
        self.redo[line.event_id] = []

    def undo_step(self, line: ReviewedLine) -> ReviewedLine | None:
        """The line before its last change (None: nothing to undo); `line` goes on the redo stack."""
        return self._step(self.undo, self.redo, line)

    def redo_step(self, line: ReviewedLine) -> ReviewedLine | None:
        return self._step(self.redo, self.undo, line)

    def _step(self, source: dict[str, list[ReviewedLine]], target: dict[str, list[ReviewedLine]],
              line: ReviewedLine) -> ReviewedLine | None:
        if not source.get(line.event_id):
            return None
        target.setdefault(line.event_id, []).append(line.model_copy(deep=True))
        self.break_merge()
        return source[line.event_id].pop()

    def break_merge(self) -> None:
        """The next edit starts a new step even in the same field (after undo, reset, discard)."""
        self._last = ("", "", 0.0)

    def clear(self) -> None:
        self.undo, self.redo = {}, {}


@dataclass(frozen=True)
class LineFilter:
    """What the line list shows: the toolbar's flag, speaker, unapproved and search filters, and in audit mode
    the sampled lines only."""

    flag: str | None = None          # a flag, "rule_warnings" (any rule-check flag) or None (all)
    speaker: str | None = None
    unapproved_only: bool = False
    text: str = ""                   # found in the Chinese or the Vietnamese, case-insensitive
    sample: Collection[str] | None = None


def line_matches(line: ReviewedLine, f: LineFilter) -> bool:
    if f.sample is not None and line.event_id not in f.sample:
        return False
    if f.flag == "rule_warnings":
        if not any(flag in RULE_WARNING_FLAGS for flag in line.flags):
            return False
    elif f.flag and f.flag not in line.flags:
        return False
    if f.speaker and line.speaker != f.speaker:
        return False
    if f.unapproved_only and line.approved:
        return False
    q = f.text.strip().lower()
    return not q or q in line.zh.lower() or q in line.vi.lower()
