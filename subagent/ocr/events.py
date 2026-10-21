"""Stage 3: turn per-frame OCR readings into timed subtitle events (5.5), with non-dialogue detection."""

from __future__ import annotations

import logging
import statistics
from collections import Counter
from dataclasses import dataclass, field

from subagent.kernel import (
    OcrReading,
    SubtitleEvent,
    edit_distance,
    normalize_zh,
    read_jsonl,
    relatedness,
    write_jsonl,
)
from subagent.settings import Config, NonDialogueConfig
from subagent.workspace import EpisodeContext

log = logging.getLogger(__name__)


@dataclass
class _Group:
    start_ms: int
    readings: list[OcrReading] = field(default_factory=list)
    end_ms: int | None = None

    def matches(self, text: str, max_distance: int) -> bool:
        norm = normalize_zh(text)
        return any(edit_distance(norm, normalize_zh(r.text)) <= max_distance for r in self.readings)

    def winner(self) -> str:
        counts = Counter(r.text for r in self.readings)
        best = max(counts.values())
        tied = [t for t, c in counts.items() if c == best]
        if len(tied) == 1:
            return tied[0]
        return max(tied, key=lambda t: statistics.fmean(r.confidence for r in self.readings if r.text == t))


def group_readings(readings: list[OcrReading], max_distance: int, duration_ms: int) -> list[_Group]:
    groups: list[_Group] = []
    current: _Group | None = None
    for r in sorted(readings, key=lambda r: r.t_ms):
        if r.kind == "empty" or not r.text:
            if current:
                current.end_ms = r.t_ms
                current = None
            continue
        if current and current.matches(r.text, max_distance):
            current.readings.append(r)
            continue
        if current:
            current.end_ms = r.t_ms
        current = _Group(start_ms=r.t_ms, readings=[r])
        groups.append(current)
    if current:
        current.end_ms = max(duration_ms, current.readings[-1].t_ms + 1)
    return _merge_flicker(groups, max_distance)


def _merge_flicker(groups: list[_Group], max_distance: int) -> list[_Group]:
    """Merge back-to-back groups with matching text, and one-sample misreads between them (A, X, A)."""
    out: list[_Group] = []
    i = 0
    while i < len(groups):
        g = groups[i]
        if out and out[-1].end_ms == g.start_ms and out[-1].matches(g.winner(), max_distance):
            out[-1].readings.extend(g.readings)
            out[-1].end_ms = g.end_ms
            i += 1
            continue
        if (
            out and i + 1 < len(groups) and len(g.readings) == 1
            and out[-1].end_ms == g.start_ms and g.end_ms == groups[i + 1].start_ms
            and out[-1].matches(groups[i + 1].winner(), max_distance)
        ):
            nxt = groups[i + 1]
            out[-1].readings.extend(nxt.readings)   # drop the single misread sample
            out[-1].end_ms = nxt.end_ms
            i += 2
            continue
        out.append(g)
        i += 1
    return out


def frames_on_screen(g: _Group, frame_ms: float) -> int:
    """How many sampled frames the event spans. OCR readings only exist where the band changed, so a
    subtitle shown for seconds over a still background still has a single reading: count time, not readings."""
    return max(1, round(((g.end_ms or g.start_ms) - g.start_ms) / frame_ms))


def absorb_fragments(groups: list[_Group], max_samples: int, threshold: float, frame_ms: float) -> list[_Group]:
    """Fold events on screen for only a few sampled frames into the touching neighbour they belong to.

    Such fragments are a subtitle caught while changing, or a misread of the neighbour. The neighbour keeps
    its own text; it only takes over the fragment's time.
    """
    out: list[_Group] = []
    i = 0
    while i < len(groups):
        g = groups[i]
        if frames_on_screen(g, frame_ms) > max_samples:
            out.append(g)
            i += 1
            continue
        text = g.winner()
        prev = out[-1] if out and out[-1].end_ms == g.start_ms else None
        nxt = groups[i + 1] if i + 1 < len(groups) and g.end_ms == groups[i + 1].start_ms else None
        options = [(relatedness(text, n.winner()), len(n.readings), side, n)
                   for side, n in (("prev", prev), ("next", nxt)) if n is not None]
        options = [o for o in options if o[0] >= threshold]
        if not options:
            out.append(g)
            i += 1
            continue
        _, _, side, target = max(options, key=lambda o: (o[0], o[1]))
        if side == "prev":
            target.end_ms = g.end_ms
        else:
            target.start_ms = g.start_ms
        i += 1
    return out


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def build_events(readings: list[OcrReading], episode_id: str, duration_ms: int, config: Config) -> list[SubtitleEvent]:
    groups = group_readings(readings, config.ocr.merge_max_edit_distance, duration_ms)
    frame_ms = 1000.0 / config.video.sample_fps
    groups = absorb_fragments(groups, config.ocr.fragment_max_samples, config.ocr.fragment_merge_similarity, frame_ms)
    events: list[SubtitleEvent] = []
    for idx, g in enumerate(groups):
        text = g.winner()
        same = [r for r in g.readings if r.text == text]
        conf = statistics.fmean(r.confidence for r in g.readings)
        flags = ["ocr_low_conf"] if conf < config.ocr.min_confidence else []
        notes: list[str] = []
        frames = frames_on_screen(g, frame_ms)
        if frames <= config.ocr.fragment_max_samples:
            flags.append("ocr_fragment")
            notes.append(f"on screen for only {frames} sampled frame(s) ({(g.end_ms or g.start_ms) - g.start_ms} ms): "
                         "probably OCR noise or a subtitle caught mid-change")
        events.append(SubtitleEvent(
            id=f"{episode_id}:{idx:04d}", start_ms=g.start_ms, end_ms=int(g.end_ms or g.start_ms),
            zh_raw=text, zh=text, ocr_conf=round(conf, 4), flags=flags, notes=notes,
            box_height=_median([r.box_height for r in same if r.box_height is not None]),
            box_vcenter=_median([r.box_vcenter for r in same if r.box_vcenter is not None]),
            box_hcenter=_median([r.box_hcenter for r in same if r.box_hcenter is not None]),
            multi_row=sum(r.multi_row for r in same) * 2 > len(same),
        ))
    return events


MIN_EVENTS_FOR_GEOMETRY = 3


def flag_non_dialogue(events: list[SubtitleEvent], cfg: NonDialogueConfig) -> int:
    """Flag events whose box geometry, row count or duration deviates from normal dialogue."""
    if not cfg.enabled:
        return 0
    normal = [e for e in events if not e.multi_row and e.box_height is not None]
    med_h = _median([e.box_height for e in normal])  # type: ignore[misc]
    med_vc = _median([e.box_vcenter for e in normal if e.box_vcenter is not None])
    med_hc = _median([e.box_hcenter for e in normal if e.box_hcenter is not None])
    geometry = len(normal) >= MIN_EVENTS_FOR_GEOMETRY and med_h
    count = 0
    for e in events:
        reasons: list[str] = []
        if geometry and e.box_height is not None and abs(e.box_height - med_h) / med_h > cfg.box_height_tolerance:
            reasons.append(f"text height {e.box_height / med_h:.2f}x the episode median")
        if geometry and e.box_vcenter is not None and med_vc is not None \
                and abs(e.box_vcenter - med_vc) > cfg.box_center_tolerance:
            reasons.append("text sits higher or lower than dialogue")
        if geometry and e.box_hcenter is not None and med_hc is not None \
                and abs(e.box_hcenter - med_hc) > cfg.box_center_tolerance:
            reasons.append("text is off-center compared to dialogue")
        if e.multi_row:
            reasons.append("more than one text row")
        if e.duration_ms > cfg.max_duration_ms:
            reasons.append(f"on screen for {e.duration_ms / 1000:.1f}s")
        if reasons:
            count += 1
            if "non_dialogue_suspect" not in e.flags:
                e.flags.append("non_dialogue_suspect")
            e.notes.append("non-dialogue suspect: " + "; ".join(reasons))
    return count


def run(ctx: EpisodeContext) -> dict[str, int]:
    readings = read_jsonl(ctx.artifact("ocr_raw.jsonl"), OcrReading)
    info = ctx.video_info()
    events = build_events(readings, ctx.episode.id, info.duration_ms, ctx.config)
    suspects = flag_non_dialogue(events, ctx.config.non_dialogue)
    write_jsonl(ctx.artifact("events_raw.jsonl"), events)
    log.info("events: %d events, %d non-dialogue suspects", len(events), suspects)
    return {"events": len(events), "non_dialogue_suspect": suspects,
            "ocr_fragment": sum("ocr_fragment" in e.flags for e in events),
            "ocr_low_conf": sum("ocr_low_conf" in e.flags for e in events)}
