"""Whole-script review: catch low-value lines the per-line evaluator cannot see (repeats, noise, unrelated text).

Precision first: only lossless merges, lines the reviewer has repeatedly removed, and confident model
decisions remove a line; everything else is flagged for the reviewer. Removed lines arrive pre-deleted in
review (restorable) and are left out of the video in auto mode.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from subagent.kernel.models import LineTranslation, ScriptDecision, SubtitleEvent
from subagent.kernel.textutil import is_han, normalize_zh, relatedness
from subagent.kernel.util import read_jsonl, write_jsonl
from subagent.llm.client import build_messages, load_prompt
from subagent.memory.store import LineDecision, MemoryStore
from subagent.settings.config import ScriptReviewConfig
from subagent.workspace.context import EpisodeContext

log = logging.getLogger(__name__)


def han_count(text: str) -> int:
    return sum(is_han(ch) for ch in text)


# -- rules (free) ----------------------------------------------------------------------------------

def find_repeats(events: list[SubtitleEvent], cfg: ScriptReviewConfig) -> list[ScriptDecision]:
    """Identical text back to back is one subtitle split in two: merge it (the display is unchanged).
    A similar line shortly after is only flagged: reviewers often keep real repetitions."""
    evs = sorted((e for e in events if normalize_zh(e.zh)), key=lambda e: (e.start_ms, e.id))
    out: list[ScriptDecision] = []
    merged: set[str] = set()
    flagged: set[str] = set()
    for i, a in enumerate(evs):
        if a.id in merged:
            continue
        for b in evs[i + 1:]:
            gap = b.start_ms - a.end_ms
            if gap > cfg.repeat_window_ms:
                break
            if b.id in merged:
                continue
            if gap <= cfg.repeat_merge_gap_ms and normalize_zh(a.zh) == normalize_zh(b.zh):
                merged.add(b.id)
                out.append(ScriptDecision(event_id=b.id, action="remove", reason="repeat", source="rule", keep_id=a.id,
                                          note=f"same text as the line before it ({a.id}); merged into it"))
            elif b.id not in flagged and relatedness(a.zh, b.zh) >= cfg.repeat_similarity:
                weaker = b if len(normalize_zh(b.zh)) <= len(normalize_zh(a.zh)) else a
                other = a if weaker is b else b
                if weaker.id not in merged and weaker.id not in flagged:
                    flagged.add(weaker.id)
                    out.append(ScriptDecision(event_id=weaker.id, action="flag", reason="repeat", source="rule",
                                              keep_id=other.id, confidence=0.5,
                                              note=f"possible repeat of “{other.zh}” ({other.id})"))
    return out


def memory_removals(events: Iterable[SubtitleEvent], decisions: dict[str, LineDecision],
                    cfg: ScriptReviewConfig) -> list[ScriptDecision]:
    """Short texts the reviewer removed several times and never kept."""
    out = []
    for e in events:
        key = normalize_zh(e.zh)
        d = decisions.get(key)
        if (d and d.keep_count == 0 and d.remove_count >= cfg.memory_auto_remove_min
                and han_count(e.zh) <= cfg.memory_max_han):
            out.append(ScriptDecision(event_id=e.id, action="remove", reason="noise", source="memory",
                                      note=f"you removed “{e.zh}” {d.remove_count} times and never kept it"))
    return out


# -- model pass ------------------------------------------------------------------------------------

class ReviewedVerdict(BaseModel):
    event_id: str
    action: Literal["remove", "check", "fix"] = Field(
        description="remove: low value; check: the reviewer should look; fix: real dialogue with an OCR error")
    reason: Literal["repeat", "noise", "unrelated", "other", "ocr"]
    confidence: float = Field(description="0..1, how sure you are that your verdict (removal or fix) is right")
    note: str = Field(default="", description="one short sentence for the reviewer")
    zh_fix: str = Field(default="", description="fix only: the line's Chinese with the OCR error corrected")
    evidence: str = Field(default="", description="fix only: the context check that supports the fix")

    @field_validator("confidence")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class ScriptReviewResponse(BaseModel):
    lines: list[ReviewedVerdict] = Field(default_factory=list, description="only lines to remove or check")


def examples_block(decisions: list[LineDecision], limit: int) -> str:
    removed = sorted((d for d in decisions if d.remove_count > d.keep_count), key=lambda d: -d.remove_count)[:limit]
    kept = sorted((d for d in decisions if d.keep_count >= d.remove_count), key=lambda d: -d.keep_count)[:limit]
    if not removed and not kept:
        return ""
    lines = ["## Reviewer decisions on earlier episodes"]
    if removed:
        lines.append("Removed (low value): " + "、".join(f"{d.zh} (×{d.remove_count})" for d in removed))
    if kept:
        lines.append("Kept even though short or suspicious: " + "、".join(f"{d.zh} (×{d.keep_count})" for d in kept))
    return "\n".join(lines) + "\n"


def script_payload(events: list[SubtitleEvent], translations: dict[str, LineTranslation],
                   decided: dict[str, ScriptDecision]) -> str:
    rows = []
    for e in sorted(events, key=lambda e: e.start_ms):
        t = translations.get(e.id)
        row = {"event_id": e.id, "t": round(e.start_ms / 1000, 2), "dur": round((e.end_ms - e.start_ms) / 1000, 2),
               "zh": e.zh, "vi": t.vi if t else "", "speaker": t.speaker if t else None}
        if t and t.line_type != "dialogue":
            row["line_type"] = t.line_type
        if e.id in decided and decided[e.id].action == "remove":
            row["already_removed"] = decided[e.id].reason
        rows.append(row)
    return "The whole episode script, in time order:\n" + json.dumps(rows, ensure_ascii=False, indent=0)


def model_pass(ctx: EpisodeContext, events: list[SubtitleEvent], translations: dict[str, LineTranslation],
               decided: dict[str, ScriptDecision], memory: list[LineDecision]) -> list[ScriptDecision]:
    cfg = ctx.config.script_review
    static = load_prompt(ctx.paths, "script_review_system")
    messages = build_messages(static, examples_block(memory, cfg.example_limit),
                              script_payload(events, translations, decided))
    resp: ScriptReviewResponse = ctx.llm.call(cfg.role, messages, ScriptReviewResponse, task="script_review")  # type: ignore[assignment]
    known = {e.id: e for e in events}
    out = []
    for v in resp.lines:
        if v.event_id not in known or v.event_id in decided:
            continue
        if v.action == "fix" or v.reason == "ocr":
            fix = plausible_fix(known[v.event_id].zh, v.zh_fix, ctx.config) if v.evidence.strip() else None
            if fix is not None:
                out.append(ScriptDecision(event_id=v.event_id, action="fix", reason="ocr", source="llm",
                                          confidence=v.confidence, note=v.note, zh_fix=fix,
                                          evidence=v.evidence.strip()))
            else:                      # no fix, or a rewrite rather than a correction: only ask to check
                out.append(ScriptDecision(event_id=v.event_id, action="flag", reason="ocr", source="llm",
                                          confidence=v.confidence, note=v.note))
            continue
        remove = v.action == "remove" and v.confidence >= cfg.remove_confidence
        out.append(ScriptDecision(event_id=v.event_id, action="remove" if remove else "flag", reason=v.reason,
                                  source="llm", confidence=v.confidence, note=v.note))
    removals = sorted((d for d in out if d.action == "remove"), key=lambda d: -d.confidence)
    allowed = max(1, int(cfg.max_remove_share * len(events)))
    if len(removals) > allowed:
        log.warning("script review: the model wanted to remove %d of %d lines (cap %.0f%%); keeping the %d most "
                    "confident removals and flagging the rest", len(removals), len(events),
                    cfg.max_remove_share * 100, allowed)
        for d in removals[allowed:]:
            d.action = "flag"
            d.note = (d.note + " (not removed: over the safety cap)").strip()
    return out


def plausible_fix(zh: str, zh_fix: str, config) -> str | None:
    """The model's corrected Chinese when it is a correction of this line: different, not empty, and changing
    at most `fix_max_change_share` of the characters (at least `ocr_fix.max_char_changes`)."""
    from subagent.kernel.textutil import edit_distance, normalize_zh

    fix = (zh_fix or "").strip()
    if not fix or normalize_zh(fix) == normalize_zh(zh):
        return None
    limit = max(config.ocr_fix.max_char_changes, int(config.script_review.fix_max_change_share * len(zh)))
    if edit_distance(normalize_zh(fix), normalize_zh(zh)) > limit:
        return None
    if seven_is_a_number(zh, fix, config.script_review.measure_words):
        return None
    if "7了" in fix and "7了" not in zh:
        return None                  # 了 added next to the 7 instead of replacing it
    return fix


def seven_is_a_number(zh: str, fix: str, measure_words: str) -> bool:
    """The fix treats a 7 wrongly: it deletes it (a 7 is either 了 or a real number), or replaces a 7 that reads
    as a number in the original (next to another digit, after 第, or before a measure word)."""
    import difflib

    for op, i1, i2, _, _ in difflib.SequenceMatcher(None, zh, fix, autojunk=False).get_opcodes():
        if op not in ("replace", "delete"):
            continue
        for i in range(i1, i2):
            if zh[i] != "7":
                continue
            if op == "delete":
                return True          # a 7 is either the particle 了 or a real number: never just dropped
            before = zh[i - 1] if i > 0 else ""
            after = zh[i + 1] if i + 1 < len(zh) else ""
            if before.isdigit() or after.isdigit() or before == "第" or (after and after in measure_words):
                return True
    return False


def run(ctx: EpisodeContext) -> dict[str, int]:
    cfg = ctx.config.script_review
    events = read_jsonl(ctx.artifact("events.jsonl"), SubtitleEvent)
    translations = {t.event_id: t for t in read_jsonl(ctx.artifact("translations.jsonl"), LineTranslation)}
    if not cfg.enabled or not events:
        write_jsonl(ctx.artifact("script_review.jsonl"), [])
        return {"removed": 0, "flagged": 0}
    memory = MemoryStore(ctx.paths.memory_db).line_decisions()
    decisions: dict[str, ScriptDecision] = {}
    for d in find_repeats(events, cfg) + memory_removals(events, {m.zh: m for m in memory}, cfg):
        if d.event_id not in decisions or (d.action == "remove" and decisions[d.event_id].action != "remove"):
            decisions[d.event_id] = d
    for d in model_pass(ctx, events, translations, decisions, memory):
        decisions[d.event_id] = d
    ordered = sorted(decisions.values(), key=lambda d: d.event_id)
    write_jsonl(ctx.artifact("script_review.jsonl"), ordered)
    counts = {"removed": sum(d.action == "remove" for d in ordered), "flagged": sum(d.action == "flag" for d in ordered),
              "ocr_fixes": sum(d.action == "fix" for d in ordered)}
    for source in ("rule", "memory", "llm"):
        counts[f"removed_by_{source}"] = sum(d.action == "remove" and d.source == source for d in ordered)
    return counts
