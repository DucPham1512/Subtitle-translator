"""Review screen state without widgets: per-line undo / redo, the line filter and counts (6.4), audit marking
(6.11) and new NPC ids. Qt-free, so it is tested without the app."""

from __future__ import annotations

import time
from collections.abc import Callable, Collection, Iterable, Mapping
from dataclasses import dataclass

from app.services.review import RULE_WARNING_FLAGS, is_auto_id, needs_attention
from subagent.kernel import AUDIT_ASPECTS, AuditMark, ReviewedLine

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


@dataclass(frozen=True)
class ReviewCounts:
    """The header counter (deleted lines are left out of the others)."""

    total: int
    approved: int
    flagged_left: int      # flagged and not approved yet
    deleted: int


def review_counts(lines: Collection[ReviewedLine]) -> ReviewCounts:
    kept = [x for x in lines if not x.deleted]
    return ReviewCounts(total=len(kept), approved=sum(1 for x in kept if x.approved),
                        flagged_left=sum(1 for x in kept if needs_attention(x) and not x.approved),
                        deleted=len(lines) - len(kept))


def next_pending(visible: list[str], lines: Mapping[str, ReviewedLine], current: str) -> str:
    """The first line after `current` still to approve, else the first one before it, else `current`."""
    pending = [x for x in visible if not lines[x].approved and not lines[x].deleted]
    after = [x for x in pending if visible.index(x) > visible.index(current)]
    return (after or pending or [current])[0]


def row_state(line: ReviewedLine, audit_mark: AuditMark | None = None, *, audit: bool = False) -> str:
    """The line list's state column: deleted, approved, flagged or pending; in audit mode the line's mark."""
    if audit:
        return "·" if audit_mark is None or not audit_mark.marked() else "✗" if audit_mark.any_wrong() else "✓"
    return "✕" if line.deleted else "✓" if line.approved else ("⚑" if needs_attention(line) else "·")

def marked_count(sample: Collection[str], marks: Mapping[str, AuditMark]) -> int:
    return sum(1 for e in sample if e in marks and marks[e].marked())


def all_correct_mark(event_id: str, old: AuditMark | None, speaker: str | None, marked_at: str) -> AuditMark:
    """Every aspect correct, except the ones already marked not applicable; the note is kept."""
    na = old.na if old else []
    return AuditMark(event_id=event_id, na=na, note=old.note if old else "", marked_at=marked_at,
                     speaker_value=speaker, **{a: (None if a in na else True) for a in AUDIT_ASPECTS})


def next_unmarked(order: list[str], current: str | None, marks: Mapping[str, AuditMark]) -> str | None:
    """The first sampled line after `current` (wrapping round) still to mark: unmarked, or speaker marked wrong
    without who really speaks. None when every line is done."""
    start = order.index(current) + 1 if current in order else 0
    for e in order[start:] + order[:start]:
        m = marks.get(e)
        if m is None or (m.speaker is False and not m.correct_speaker):
            return e
    return None


def next_npc_number(ids: Iterable[str], prefix: str, episode_number: int) -> int:
    """The next free <n> of this episode's automatic ids (<prefix>_<ep>_<n>), after the voice stage's and the ones
    made in review."""
    used = [int(c.rsplit("_", 1)[-1]) for c in ids
            if is_auto_id(c, prefix) and int(c.rsplit("_", 2)[-2]) == episode_number]
    return max(used, default=0) + 1
