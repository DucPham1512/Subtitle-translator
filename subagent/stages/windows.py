"""Stage 8: split events into scene windows at long gaps or a line cap (5.10)."""

from __future__ import annotations

from subagent.config import WindowsConfig
from subagent.context import EpisodeContext
from subagent.kernel.models import SubtitleEvent, Window
from subagent.kernel.util import atomic_write_json, read_jsonl


def build_windows(events: list[SubtitleEvent], cfg: WindowsConfig) -> list[Window]:
    windows: list[Window] = []
    current: list[SubtitleEvent] = []
    for e in events:
        if current and (e.start_ms - current[-1].end_ms > cfg.gap_ms or len(current) >= cfg.max_lines):
            windows.append(Window(index=len(windows), event_ids=[x.id for x in current]))
            current = []
        current.append(e)
    if current:
        windows.append(Window(index=len(windows), event_ids=[x.id for x in current]))
    order = [e.id for e in events]
    for w in windows:
        first = order.index(w.event_ids[0])
        w.context_ids = order[max(0, first - cfg.context_overlap):first]
    return windows


def run(ctx: EpisodeContext) -> dict[str, int]:
    events = read_jsonl(ctx.artifact("events.jsonl"), SubtitleEvent)
    windows = build_windows(events, ctx.config.windows)
    atomic_write_json(ctx.artifact("windows.json"), [w.model_dump() for w in windows])
    return {"windows": len(windows), "events": len(events)}
