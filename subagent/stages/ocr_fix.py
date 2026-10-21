"""Stage 4: fix OCR character errors with context and the glossary (5.6)."""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field

from subagent.context import EpisodeContext
from subagent.kernel.models import SubtitleEvent
from subagent.kernel.textutil import edit_distance, keep_cjk
from subagent.kernel.util import chunked, read_jsonl, write_jsonl
from subagent.llm.client import build_messages, load_prompt
from subagent.memory.prefix import ocr_fix_prefix
from subagent.memory.store import MemoryStore

log = logging.getLogger(__name__)


class OcrFixChange(BaseModel):
    event_id: str
    zh: str = Field(description="corrected Chinese line")
    reason: str = ""


class OcrFixResponse(BaseModel):
    changes: list[OcrFixChange] = Field(default_factory=list, description="only the lines you changed")


def apply_fixes(events: list[SubtitleEvent], changes: list[OcrFixChange], max_char_changes: int) -> tuple[int, int]:
    """Apply accepted fixes in place. Returns (fixed, rejected)."""
    by_id = {e.id: e for e in events}
    fixed = rejected = 0
    for change in changes:
        event = by_id.get(change.event_id)
        new = keep_cjk(change.zh.strip())
        if event is None or not new or new == event.zh:
            continue
        distance = edit_distance(event.zh_raw, new)
        if distance > max_char_changes:
            if "ocr_uncertain" not in event.flags:
                event.flags.append("ocr_uncertain")
            event.notes.append(f"OCR fix rejected ({distance} characters changed): {new} — {change.reason}")
            rejected += 1
            continue
        event.zh = new
        event.ocr_fixed = True
        event.notes.append(f"OCR fix: {event.zh_raw} → {new} ({change.reason})")
        fixed += 1
    return fixed, rejected


def batch_payload(batch: list[SubtitleEvent]) -> str:
    rows = [{"event_id": e.id, "zh": e.zh} for e in batch]
    return "Subtitle lines, in order:\n" + json.dumps(rows, ensure_ascii=False, indent=0)


def run(ctx: EpisodeContext) -> dict[str, int]:
    events = read_jsonl(ctx.artifact("events_raw.jsonl"), SubtitleEvent)
    static = load_prompt(ctx.paths, "ocr_fix_system")
    prefix = ocr_fix_prefix(MemoryStore(ctx.paths.memory_db))
    fixed = rejected = 0
    batches = list(chunked(events, ctx.config.ocr_fix.batch_size))
    for i, batch in enumerate(batches, 1):
        messages = build_messages(static, prefix, batch_payload(batch))
        resp: OcrFixResponse = ctx.llm.call("utility", messages, OcrFixResponse, task="ocr_fix")  # type: ignore[assignment]
        f, r = apply_fixes(events, resp.changes, ctx.config.ocr_fix.max_char_changes)
        fixed, rejected = fixed + f, rejected + r
        ctx.progress.emit("ocr_fix", "progress", done=i, total=len(batches))
    write_jsonl(ctx.artifact("events.jsonl"), events)
    return {"events": len(events), "fixed": fixed, "ocr_uncertain": rejected}
