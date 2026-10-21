"""Stage 1: frame sampling + change detection (5.3). Only changed, non-empty bands are saved."""

from __future__ import annotations

import logging
import shutil
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import numpy as np

from subagent.infra import imwrite_png, iter_gray_frames, probe
from subagent.kernel import ChangeRecord, atomic_write_text, write_jsonl
from subagent.settings import VideoConfig
from subagent.workspace import EpisodeContext

log = logging.getLogger(__name__)


def binarize(band: np.ndarray, threshold: int) -> np.ndarray:
    return band >= threshold


def change_fraction(prev: np.ndarray, cur: np.ndarray) -> float:
    return float(np.mean(prev != cur))


def text_ratio(binary: np.ndarray) -> float:
    return float(np.mean(binary))


def outlined_ratio(band: np.ndarray, binary: np.ndarray, cfg: VideoConfig) -> float:
    """Share of the band that is bright AND within outline_reach_px of a dark pixel (outlined text)."""
    import cv2

    size = 2 * cfg.outline_reach_px + 1
    near_dark = cv2.dilate((band <= cfg.outline_dark_threshold).astype(np.uint8), np.ones((size, size), np.uint8))
    return float(np.mean(binary & (near_dark > 0)))


def has_subtitle(band: np.ndarray, binary: np.ndarray, cfg: VideoConfig) -> bool:
    if text_ratio(binary) < cfg.empty_text_ratio:
        return False
    if cfg.subtitle_detection == "bright":
        return True
    return outlined_ratio(band, binary, cfg) >= cfg.min_outlined_ratio


@dataclass
class Change:
    t_ms: int
    kind: str                 # "text" | "empty"
    band: np.ndarray | None   # grayscale band for "text" changes


def detect_changes(frames: Iterable[np.ndarray], fps: float, cfg: VideoConfig,
                   stats: dict[str, int] | None = None, repeats: bool = False) -> Iterator[Change]:
    """Yield a Change whenever the binarized band differs from the previous sample.

    A band without a subtitle is "empty"; an empty change is yielded only when text ends. `stats` counts the
    bands that are bright but have no outlined text (skipped instead of being sent to OCR). With `repeats`,
    frames that still show the same subtitle are yielded too, as kind "same" (for multi-frame fusion).
    """
    prev: np.ndarray | None = None
    showing_text = False
    for i, frame in enumerate(frames):
        t_ms = int(round(i * 1000.0 / fps))
        binary = binarize(frame, cfg.text_threshold)
        if not has_subtitle(frame, binary, cfg):
            if stats is not None and text_ratio(binary) >= cfg.empty_text_ratio:
                stats["bright_without_outline"] = stats.get("bright_without_outline", 0) + 1
            if showing_text:
                yield Change(t_ms, "empty", None)
                showing_text = False
        elif not showing_text or prev is None or change_fraction(prev, binary) > cfg.change_threshold:
            yield Change(t_ms, "text", frame.copy())
            showing_text = True
        elif repeats:
            yield Change(t_ms, "same", frame.copy())
        prev = binary


def fuse(frames: list[np.ndarray]) -> np.ndarray:
    """Per-pixel median of frames showing the same subtitle (5.3)."""
    return frames[0] if len(frames) == 1 else np.median(np.stack(frames), axis=0).astype(np.uint8)


def run(ctx: EpisodeContext) -> dict[str, int]:
    source = ctx.require_source()
    cfg = ctx.config.video
    info = probe(source)
    atomic_write_text(ctx.artifact("video.json"), info.model_dump_json(indent=2))
    crop = cfg.subtitle_band.pixels(info.width, info.height)

    bands_dir = ctx.artifact("bands")
    if bands_dir.exists():
        shutil.rmtree(bands_dir)
    bands_dir.mkdir(parents=True)

    total = max(1, int(info.duration_ms / 1000 * cfg.sample_fps))
    records: list[ChangeRecord] = []
    counter = {"frames": 0}
    stats: dict[str, int] = {}

    def counted(frames: Iterator[np.ndarray]) -> Iterator[np.ndarray]:
        for frame in frames:
            counter["frames"] += 1
            if counter["frames"] % 50 == 0:
                ctx.progress.emit("ingest", "progress", done=min(counter["frames"], total), total=total)
            yield frame

    frames = counted(iter_gray_frames(source, fps=cfg.sample_fps, crop=crop))
    pending: tuple[int, list[np.ndarray]] | None = None     # the text change being fused, and its frames

    def flush() -> None:
        if pending is not None:
            imwrite_png(bands_dir / f"{pending[0]}.png", fuse(pending[1]))
            if len(pending[1]) > 1:      # which pixels stayed still while the subtitle was shown (5.4a)
                stack = np.stack(pending[1])
                stable = (stack.max(axis=0).astype(np.int16) - stack.min(axis=0)) <= cfg.stable_range
                imwrite_png(bands_dir / f"{pending[0]}.stable.png", stable.astype(np.uint8) * 255)

    for change in detect_changes(frames, cfg.sample_fps, cfg, stats, repeats=cfg.band_frames > 1):
        if change.kind == "same":
            if pending is not None and len(pending[1]) < cfg.band_frames:
                pending[1].append(change.band)
            continue
        records.append(ChangeRecord(t_ms=change.t_ms, kind=change.kind))  # type: ignore[arg-type]
        flush()
        pending = (change.t_ms, [change.band]) if change.band is not None else None
    flush()

    write_jsonl(ctx.artifact("changes.jsonl"), records)
    text_changes = sum(1 for r in records if r.kind == "text")
    skipped = stats.get("bright_without_outline", 0)
    log.info("ingest: %d frames sampled, %d text changes, %d empty, %d bright frames without outlined text skipped",
             counter["frames"], text_changes, len(records) - text_changes, skipped)
    return {"frames": counter["frames"], "text_changes": text_changes, "empty_changes": len(records) - text_changes,
            "no_subtitle_frames": skipped}


def draw_band(frame: np.ndarray, crop: tuple[int, int, int, int]) -> np.ndarray:
    import cv2

    x, y, w, h = crop
    out = frame.copy()
    thickness = max(2, frame.shape[0] // 360)
    cv2.rectangle(out, (x, y), (x + w - 1, y + h - 1), (0, 0, 255), thickness)
    return out


def calibrate(ctx: EpisodeContext, count: int = 6) -> list:
    """Save sample frames with the configured subtitle band drawn, to tune video.subtitle_band once."""
    from subagent.infra import extract_frame

    source = ctx.require_source()
    info = probe(source)
    crop = ctx.config.video.subtitle_band.pixels(info.width, info.height)
    out_dir = ctx.artifact("calibration")
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for i in range(count):
        t_ms = int(info.duration_ms * (0.05 + 0.9 * i / max(1, count - 1)))
        frame = extract_frame(source, t_ms, size=(info.width, info.height))
        path = out_dir / f"frame_{t_ms:08d}.png"
        imwrite_png(path, draw_band(frame, crop))
        saved.append(path)
    return saved
