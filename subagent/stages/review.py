"""Stages 11-12: review gate, review draft and finish-review (5.14). Review never calls an LLM."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from subagent.errors import ReviewIncompleteError
from subagent.models import (
    EditRecord,
    LineTranslation,
    PinyinLine,
    ReviewedLine,
    ScriptDecision,
    SubtitleEvent,
)
from subagent.textutil import is_han
from subagent.util import read_jsonl, write_jsonl

log = logging.getLogger(__name__)

# Flag groups for the review filter and the flagged counter; anything else is a "rule warning".
FLAG_ORDER = ["retry_cap", "sprite_unresolved", "low_speaker_conf", "non_dialogue_suspect", "script_suspect",
              "ocr_uncertain",
              "check_pinyin"]
RULE_WARNING_FLAGS = ["partial_speaker", "partial_suggestion", "check_pronouns", "script_repeat", "script_noise", "script_unrelated", "script_other", "ocr_fragment", "missing_translation", "line_too_long", "cps_exceeded", "glossary_mismatch",
                      "pronoun_mismatch", "speaker_invalid", "speaker_override", "ocr_low_conf", "not_evaluated"]
EDITABLE_FIELDS = ("zh", "pinyin", "vi", "speaker", "listener", "line_type", "deleted", "cast_labels", "cast_boxes",
                   "cast_added", "cast_talking")


def flag_group(flags: list[str]) -> int | None:
    """Index of the review group a line belongs to, or None for unflagged lines."""
    for i, f in enumerate(FLAG_ORDER):
        if f in flags:
            return i
    if any(f in RULE_WARNING_FLAGS for f in flags) or flags:
        return len(FLAG_ORDER)
    return None


def needs_attention(line: ReviewedLine) -> bool:
    """Flagged and still in the script (a deleted line needs no more review)."""
    return not line.deleted and flag_group(line.flags) is not None


def review_order(lines: list[ReviewedLine]) -> list[ReviewedLine]:
    """Always chronological (user decision, replacing the flagged-first order of 6.4).

    Flagged lines are found with the Flag filter instead.
    """
    return sorted(lines, key=lambda line: (line.start_ms, line.end_ms, line.event_id))


def looks_like_noise(zh: str, max_han: int) -> bool:
    """OCR noise from the background: very few Chinese characters, or stray digits (e.g. '1', '史', '姬7')."""
    han = sum(is_han(ch) for ch in zh)
    return han <= max_han or any(ch.isdigit() for ch in zh)


def build_draft(events: list[SubtitleEvent], pinyin: list[PinyinLine], translations: list[LineTranslation],
                predelete_fragments: bool = True, noise_max_han: int = 2,
                decisions: list[ScriptDecision] | None = None) -> list[ReviewedLine]:
    py = {p.event_id: p for p in pinyin}
    tr = {t.event_id: t for t in translations}
    lines = []
    for e in events:
        t = tr.get(e.id)
        p = py.get(e.id)
        flags = list(dict.fromkeys(e.flags + (t.flags if t else ["missing_translation"]) + (p.flags if p else [])))
        lines.append(ReviewedLine(
            event_id=e.id, start_ms=e.start_ms, end_ms=e.end_ms, speaker=t.speaker if t else None,
            listener=t.listener if t else None, zh=e.zh, pinyin=p.pinyin if p else "", vi=t.vi if t else "",
            line_type=t.line_type if t else "dialogue", approved=False, edited=False, flags=flags,
            deleted=predelete_fragments and "ocr_fragment" in e.flags and looks_like_noise(e.zh, noise_max_han),
        ))
    return apply_script_review(lines, decisions or [])


def apply_script_review(lines: list[ReviewedLine], decisions: list[ScriptDecision]) -> list[ReviewedLine]:
    """Removed lines are pre-deleted (restorable) with the reason as a flag; doubtful ones are flagged. A merged
    repeat hands its time to the line it repeats, so the subtitle stays on screen as before."""
    by_id = {line.event_id: line for line in lines}
    for d in decisions:
        line = by_id.get(d.event_id)
        if line is None:
            continue
        if d.action == "remove":
            line.deleted = True
            line.flags = list(dict.fromkeys(line.flags + [f"script_{d.reason}"]))
            kept = by_id.get(d.keep_id or "")
            if d.reason == "repeat" and kept is not None and not kept.deleted:
                kept.start_ms = min(kept.start_ms, line.start_ms)
                kept.end_ms = max(kept.end_ms, line.end_ms)
        else:
            line.flags = list(dict.fromkeys(line.flags + ["script_suspect"]))
    return lines


def original_draft(work: Path, predelete_fragments: bool = True, noise_max_han: int = 2) -> list[ReviewedLine]:
    """The pipeline's version of the review script (noisy fragments pre-deleted when configured)."""
    return build_draft(
        read_jsonl(work / "events.jsonl", SubtitleEvent),
        read_jsonl(work / "pinyin.jsonl", PinyinLine),
        read_jsonl(work / "translations.jsonl", LineTranslation),
        predelete_fragments, noise_max_han,
        read_jsonl(work / "script_review.jsonl", ScriptDecision),
    )


def draft_path(work: Path) -> Path:
    return work / "review_draft.jsonl"


def load_draft(work: Path) -> list[ReviewedLine]:
    return read_jsonl(draft_path(work), ReviewedLine)


def save_draft(work: Path, lines: list[ReviewedLine]) -> None:
    """Atomic write; the app autosaves through this (debounced)."""
    write_jsonl(draft_path(work), sorted(lines, key=lambda line: line.start_ms))


def gate(work: Path, mode: str, predelete_fragments: bool = True, noise_max_han: int = 2) -> str:
    """Auto: everything approved. Human: write the draft and stop at awaiting_review."""
    lines = original_draft(work, predelete_fragments, noise_max_han)
    if mode == "auto":
        for line in lines:
            line.approved = True
        write_jsonl(work / "approved.jsonl", lines)
        write_jsonl(work / "edits.jsonl", [])
        return "approved"
    # The pipeline reruns the gate only when its inputs changed or it was forced (the app confirms that
    # the draft will be discarded), so an unchanged episode keeps the user's work in progress.
    save_draft(work, lines)
    return "awaiting_review"


def validate(lines: list[ReviewedLine], character_ids: set[str]) -> list[str]:
    errors = []
    for line in lines:
        if line.deleted:
            continue   # a deletion is itself the reviewer's decision
        if not line.approved:
            errors.append(f"{line.event_id}: not approved")
        if not line.vi.strip():
            errors.append(f"{line.event_id}: Vietnamese text is empty")
        for role in ("speaker", "listener"):
            value = getattr(line, role)
            if value and value not in character_ids:
                errors.append(f"{line.event_id}: unknown {role} '{value}'")
    return errors


def compute_edits(original: list[ReviewedLine], final: list[ReviewedLine]) -> list[EditRecord]:
    before = {line.event_id: line for line in original}
    edits = []
    for line in final:
        old = before.get(line.event_id)
        if old is None:
            continue
        for field in EDITABLE_FIELDS:
            a, b = getattr(old, field), getattr(line, field)
            if (a or None) != (b or None):
                edits.append(EditRecord(edit_id=f"{line.event_id}:{field}", event_id=line.event_id, field=field,
                                        before=_text(a), after=_text(b)))
    return edits


def _text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict | list):
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          default=lambda o: o.model_dump() if hasattr(o, "model_dump") else str(o)) if value else None
    return str(value)


def finish_review(work: Path, character_ids: set[str], predelete_fragments: bool = True,
                  noise_max_han: int = 2) -> tuple[list[ReviewedLine], list[EditRecord]]:
    lines = load_draft(work)
    if not lines:
        raise ReviewIncompleteError("No review draft found; run the episode in human mode first")
    errors = validate(lines, character_ids)
    if errors:
        shown = "\n".join(errors[:20]) + (f"\n… and {len(errors) - 20} more" if len(errors) > 20 else "")
        raise ReviewIncompleteError(f"Review is not complete:\n{shown}")
    edits = compute_edits(original_draft(work, predelete_fragments, noise_max_han), lines)
    edited_ids = {e.event_id for e in edits}
    for line in lines:
        line.edited = line.event_id in edited_ids
    write_jsonl(work / "approved.jsonl", lines)
    write_jsonl(work / "edits.jsonl", edits)
    return lines, edits


def regenerate_pinyin(line: ReviewedLine, engine) -> ReviewedLine:
    """After a zh edit: local pypinyin; polyphones outside known phrases get `check_pinyin` (no LLM)."""
    if line.pinyin_overridden:
        return line
    pinyin, polyphones = engine.line(line.zh)
    flags = [f for f in line.flags if f != "check_pinyin"]
    if polyphones:
        flags.append("check_pinyin")
    return line.model_copy(update={"pinyin": pinyin, "flags": flags})
