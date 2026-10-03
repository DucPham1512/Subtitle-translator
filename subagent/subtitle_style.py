"""Generic subtitle segmentation (5.4a): learn the series' subtitle style once, then segment every band with it.

Nothing here is tuned to one show. A burned-in subtitle is text that (a) has strokes of nearly constant width,
(b) stays still while the scene behind it changes, and (c) keeps the same style through a series.

Calibration (once per series, `python -m subagent calibrate EPISODE --style`; stored in
`data/bootstrap/subtitle_style.json`):
  - bands sampled across an episode; pixels unchanged between consecutive samples are "stable";
  - MSER (maximally stable extremal regions, threshold-based) proposes regions in both polarities;
  - the stroke-width transform (SWT, edge-based: Canny edges paired across each stroke along the gradient)
    measures each region's stroke width;
  - text-like regions (consistent stroke width, letter-sized, temporally stable) vote for the polarity; their
    pixels give the fill grey range, the ring around them the outline level (if any), their stroke widths and line
    heights the series' stroke width and letter height (as shares of the band height).

Segmentation (`ocr.preprocess: segment`): pixels in the fill range are candidates (threshold); a component is
subtitle when its SWT stroke width matches the series' (edge), it is ringed by the outline when the style has one,
it is not taller than a letter, and (when ingest saved a stability map) it stayed still. The result is a mask like
`stages.ocr.subtitle_mask`, so line grouping, cropping and recognition are shared.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel

log = logging.getLogger(__name__)
STYLE_FILE = "subtitle_style.json"


class SubtitleStyle(BaseModel):
    polarity: Literal["light", "dark"]       # light: text brighter than its outline / surroundings
    fill_min: int                            # grey range of the letter fill
    fill_max: int
    outline_level: int | None = None         # outline grey (at most, light text; at least, dark text); None: no outline
    stroke: float                            # median stroke width, share of the band height
    stroke_spread: float                     # relative spread (IQR / median) of stroke widths
    letter_height: float                     # median line height, share of the band height
    regions: int = 0                         # text-like regions the style was learned from
    calibrated_from: str = ""
    calibrated_at: str = ""


def style_path(bootstrap_dir: Path) -> Path:
    return bootstrap_dir / STYLE_FILE


def load_style(bootstrap_dir: Path) -> SubtitleStyle | None:
    p = style_path(bootstrap_dir)
    return SubtitleStyle.model_validate_json(p.read_text(encoding="utf-8")) if p.is_file() else None


def save_style(bootstrap_dir: Path, style: SubtitleStyle) -> Path:
    from subagent.util import atomic_write_text

    p = style_path(bootstrap_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(p, json.dumps(style.model_dump(), ensure_ascii=False, indent=1))
    return p


# -- stroke-width transform (edge-based) ------------------------------------------------------------

def stroke_width_transform(gray: np.ndarray, light: bool, max_width: int | None = None) -> np.ndarray:
    """SWT (Epshtein et al. 2010): from every Canny edge pixel, walk along the gradient into the stroke until
    the opposite edge (gradient roughly reversed); every pixel on the ray gets the ray's length (the smallest
    over rays). Light text: walk with the gradient (dark to bright). Returns float32 widths, 0 = no stroke."""
    import cv2

    h, w = gray.shape
    max_width = max_width or h
    hi, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    edges = cv2.Canny(gray, max(1.0, hi * 0.5), max(2.0, hi)) > 0
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.hypot(gx, gy) + 1e-6
    dx, dy = gx / mag, gy / mag
    if not light:
        dx, dy = -dx, -dy
    ys, xs = np.nonzero(edges)
    swt = np.full((h, w), np.inf, np.float32)
    if len(xs) == 0:
        return np.zeros((h, w), np.float32)
    ux, uy = dx[ys, xs], dy[ys, xs]
    hit = np.full(len(xs), -1, np.int32)                 # step at which the ray met the opposite edge
    for k in range(1, max_width + 1):
        open_ = hit < 0
        if not open_.any():
            break
        px = np.rint(xs + ux * k).astype(np.int32)
        py = np.rint(ys + uy * k).astype(np.int32)
        inside = open_ & (px >= 0) & (px < w) & (py >= 0) & (py < h)
        px_c, py_c = np.clip(px, 0, w - 1), np.clip(py, 0, h - 1)
        on_edge = inside & edges[py_c, px_c]
        # opposite edge: its gradient points back (angle within about 30 degrees of reversed)
        reversed_ = (ux * dx[py_c, px_c] + uy * dy[py_c, px_c]) < -0.866
        hit[on_edge & reversed_] = k
        hit[open_ & ~inside] = 0                         # left the band: no stroke
        hit[on_edge & ~reversed_] = 0                    # met an edge of something else
    good = np.nonzero(hit > 0)[0]
    for k in range(0, max_width + 1):
        sel = good[hit[good] >= k]
        if len(sel) == 0:
            break
        px = np.clip(np.rint(xs[sel] + ux[sel] * k).astype(np.int32), 0, w - 1)
        py = np.clip(np.rint(ys[sel] + uy[sel] * k).astype(np.int32), 0, h - 1)
        np.minimum.at(swt, (py, px), hit[sel].astype(np.float32))
    swt[np.isinf(swt)] = 0
    return swt


# -- calibration (once per series) ------------------------------------------------------------------

def _region_features(gray: np.ndarray, mask: np.ndarray, swt: np.ndarray, stable: np.ndarray) -> dict | None:
    widths = swt[mask & (swt > 0)]
    if len(widths) < 5:
        return None
    ys, xs = np.nonzero(mask)
    med = float(np.median(widths))
    return {"h": int(ys.max() - ys.min() + 1), "w": int(xs.max() - xs.min() + 1), "y0": int(ys.min()),
            "y1": int(ys.max() + 1), "x0": int(xs.min()), "x1": int(xs.max() + 1), "stroke": med, "widths": widths,
            "cv": float(np.std(widths) / med), "stable": float(stable[mask].mean()), "pixels": (ys, xs)}


def propose_regions(gray: np.ndarray, light: bool, mser) -> list[np.ndarray]:
    """Candidate regions (threshold-based): MSER regions, plus connected components at a few grey levels (the Otsu
    level and fixed steps) in the given polarity. MSER can miss clean, flat regions; the levels catch those."""
    import cv2

    h = gray.shape[0]
    out = []
    regions, _ = mser.detectRegions(gray)
    for pts in regions:
        m = np.zeros(gray.shape, bool)
        m[pts[:, 1], pts[:, 0]] = True
        out.append(m)
    otsu, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    levels = {int(otsu), 96, 160, 224} if light else {int(otsu), 32, 96, 160}
    for t in sorted(levels):
        binary = (gray >= t) if light else (gray <= t)
        n, labels, stats, _ = cv2.connectedComponentsWithStats(binary.astype(np.uint8), connectivity=8)
        for i in range(1, n):
            if max(4, h // 6) <= stats[i, cv2.CC_STAT_AREA] <= h * h * 2:
                out.append(labels == i)
    return out


def calibrate(bands: list[np.ndarray], *, stable_range: int = 12, source: str = "") -> SubtitleStyle:
    """Learn the subtitle style from bands sampled in time order (consecutive samples decide stability)."""
    import cv2

    from subagent.util import now_iso

    if len(bands) < 2:
        raise ValueError("calibration needs at least two sampled bands")
    h = bands[0].shape[0]
    mser = cv2.MSER_create()
    mser.setMinArea(max(4, h // 6))
    mser.setMaxArea(h * h * 2)
    found: dict[str, list[dict]] = {"light": [], "dark": []}
    for a, b in zip(bands, bands[1:], strict=False):
        stable = np.abs(a.astype(np.int16) - b.astype(np.int16)) <= stable_range
        for pol in ("light", "dark"):
            swt = stroke_width_transform(a, light=pol == "light", max_width=max(3, h // 3))
            seen = set()
            for mask in propose_regions(a, pol == "light", mser):
                ys, xs = np.nonzero(mask)
                key = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()), int(mask.sum()))
                if key in seen:
                    continue
                seen.add(key)
                f = _region_features(a, mask, swt, stable)
                if (f and 0.15 * h <= f["h"] <= h and f["w"] <= 3 * h and f["cv"] <= 0.8
                        and f["stroke"] <= 0.4 * f["h"] and f["stable"] >= 0.8):
                    # the stroke interior (one pixel in from the edge), where the fill colour is not blended
                    inner = cv2.erode(mask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & (swt > 0)
                    f["grey"] = a[inner] if inner.any() else a[mask & (swt > 0)]
                    f["ring"] = a[cv2.dilate(mask.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~mask]
                    core, ring_mid = float(np.median(f["grey"])), float(np.median(f["ring"]))
                    f["ringed"] = (core - ring_mid > 60) if pol == "light" else (ring_mid - core > 60)
                    f["frame"] = len(found[pol])
                    found[pol].append(f)
    # the text fill is the polarity whose strokes are consistently set off from what surrounds them: an outline,
    # itself a constant-width stroke, has the fill on one side and the background on the other (mixed ring)
    def score(p: str) -> float:
        regs_p = found[p]
        if not regs_p:
            return 0.0
        return sum(len(f["grey"]) for f in regs_p) * float(np.mean([f["ringed"] for f in regs_p]))

    pol = max(found, key=score)
    regs = found[pol]
    ringed = [f for f in regs if f["ringed"]]
    if len(ringed) >= 0.5 * len(regs):
        regs = ringed            # the subtitle has an outline: learn only from regions that show it
    if len(regs) < 10:
        raise ValueError(f"only {len(regs)} text-like regions found; sample an episode with more dialogue")
    strokes = np.concatenate([f["widths"] for f in regs])        # every stroke pixel of the subtitle regions
    grey = np.concatenate([f["grey"] for f in regs])
    ring = np.concatenate([f["ring"] for f in regs])
    fill_lo, fill_hi = (int(np.percentile(grey, 5)), int(np.percentile(grey, 99.5)))
    if pol == "dark":
        fill_lo, fill_hi = int(np.percentile(grey, 0.5)), int(np.percentile(grey, 95))
    # an outline is a ring much darker (light text) or brighter (dark text) than the fill, consistently
    ring_level = int(np.percentile(ring, 60 if pol == "light" else 40))
    outline = ring_level if (pol == "light" and ring_level < fill_lo - 60) or (pol == "dark" and ring_level > fill_hi + 60) \
        else None
    # the threshold that cuts the fill out must leave room for compression and anti-aliasing inside the strokes:
    # two thirds of the way from the outline to the fill, or a fixed margin when there is no outline
    # the outline level is the lighter end of the outline (compression lightens it unevenly): a quarter of the way
    # from its typical grey towards the fill, so "is this outline?" accepts the softened pixels too
    level = outline
    if pol == "light":
        if outline is not None:
            level = int(outline + (fill_lo - outline) / 4)
        fill_lo = int(outline + (fill_lo - outline) * 2 / 3) if outline is not None else max(0, fill_lo - 40)
    else:
        if outline is not None:
            level = int(outline - (outline - fill_hi) / 4)
        fill_hi = int(outline - (outline - fill_hi) * 2 / 3) if outline is not None else min(255, fill_hi + 40)
    q1, q3 = np.percentile(strokes, [25, 75])
    heights = np.array([f["h"] for f in regs])
    return SubtitleStyle(
        polarity=pol, fill_min=fill_lo, fill_max=fill_hi, outline_level=level,
        stroke=round(float(np.median(strokes)) / h, 4), stroke_spread=round(float((q3 - q1) / np.median(strokes)), 3),
        letter_height=round(float(np.percentile(heights, 90)) / h, 4), regions=len(regs),
        calibrated_from=source, calibrated_at=now_iso())


# -- segmentation (every band) ----------------------------------------------------------------------

def segment_mask(band: np.ndarray, style: SubtitleStyle, *, stroke_tolerance: float, outline_share: float,
                 max_height: float, min_stable: float, stable: np.ndarray | None = None,
                 max_width: float = 2.0) -> np.ndarray:
    """Black text on white: the components that look like this series' subtitle text."""
    import cv2

    h = band.shape[0]
    light = style.polarity == "light"
    fill = ((band >= style.fill_min) & (band <= style.fill_max)).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(fill, connectivity=8)
    swt = stroke_width_transform(band, light=light, max_width=max(3, h // 3))
    lab = labels.ravel()
    has = (swt > 0).ravel()
    counts = np.bincount(lab[has], minlength=n)
    # median stroke width per component (sorted by component, then width)
    order = np.lexsort((swt.ravel()[has], lab[has]))
    sorted_lab, sorted_w = lab[has][order], swt.ravel()[has][order]
    starts = np.searchsorted(sorted_lab, np.arange(n))
    med = np.zeros(n, np.float32)
    for i in np.nonzero(counts >= 3)[0]:
        med[i] = sorted_w[starts[i] + counts[i] // 2]
    target = style.stroke * h
    stroke_ok = (counts >= 3) & (np.abs(med - target) <= stroke_tolerance * max(target, 1.0))
    ok = stats[:, cv2.CC_STAT_HEIGHT] <= max_height * style.letter_height * h
    ok &= stats[:, cv2.CC_STAT_WIDTH] <= max_width * style.letter_height * h      # one piece is at most ~2 letters
    ok[0] = False
    if style.outline_level is not None:
        ring = cv2.dilate(fill, np.ones((5, 5), np.uint8)).astype(bool) & ~fill.astype(bool)
        near = labels_near(labels, ring)
        outlined = (band <= style.outline_level) if light else (band >= style.outline_level)
        ring_all = np.bincount(near[ring], minlength=n)
        ring_out = np.bincount(near[ring & outlined], minlength=n)
        ok &= ring_out >= outline_share * np.maximum(ring_all, 1)
    if stable is not None:
        st = np.bincount(lab, weights=stable.ravel().astype(np.float64), minlength=n)
        ok &= st >= min_stable * np.maximum(stats[:, cv2.CC_STAT_AREA], 1)
    keep = grow_line(stats, ok & stroke_ok, ok, style.letter_height * h)
    out = np.full(band.shape, 255, np.uint8)
    out[keep[labels]] = 0
    return out


def grow_line(stats: np.ndarray, seed: np.ndarray, allowed: np.ndarray, letter_px: float) -> np.ndarray:
    """Region growing: start from the components that pass every test (`seed`) and add `allowed` components
    (all tests but the stroke width) that sit on the same rows and within a letter of what is kept, so letters
    at the ends of a line whose stroke width measured off still widen the line."""
    import cv2

    keep = seed.copy()
    x0, y0 = stats[:, cv2.CC_STAT_LEFT], stats[:, cv2.CC_STAT_TOP]
    x1, y1 = x0 + stats[:, cv2.CC_STAT_WIDTH], y0 + stats[:, cv2.CC_STAT_HEIGHT]
    for _ in range(20):
        if not keep.any():
            break
        top, bottom = np.median(y0[keep]), np.median(y1[keep])
        left, right = x0[keep].min(), x1[keep].max()
        overlap = np.clip(np.minimum(y1, bottom) - np.maximum(y0, top), 0, None) / np.maximum(y1 - y0, 1)
        gap = np.maximum(0, np.maximum(x0 - right, left - x1))
        add = allowed & ~keep & (overlap >= 0.5) & (gap <= letter_px)
        if not add.any():
            break
        keep |= add
    return keep


def labels_near(labels: np.ndarray, ring: np.ndarray) -> np.ndarray:
    """For ring pixels, the label of the component they surround (dilated labels; larger label wins ties)."""
    import cv2

    grown = cv2.dilate(labels.astype(np.float32), np.ones((5, 5), np.uint8)).astype(np.int32)
    return np.where(ring, grown, 0)


def style_preview(bands: list[np.ndarray], style: SubtitleStyle, ocr_cfg) -> np.ndarray:
    """Rows of three per band: the band, its segmentation mask (black = kept as subtitle), and the crop OCR reads
    (original pixels at their position; grey where nothing is read)."""
    from subagent.stages.ocr import line_span

    rows = []
    for b in bands:
        mask = segment_mask(b, style, stroke_tolerance=ocr_cfg.seg_stroke_tolerance,
                            outline_share=ocr_cfg.seg_outline_share, max_height=ocr_cfg.seg_max_height,
                            min_stable=ocr_cfg.seg_min_stable, max_width=ocr_cfg.seg_max_width)
        crop_row = np.full(b.shape, 128, np.uint8)
        span = line_span(mask, ocr_cfg)
        if span is not None:
            g = ocr_cfg.isolate_grow_px
            x0, x1 = max(0, span[0] - g), min(b.shape[1], span[2] + g)
            crop_row[:, x0:x1] = b[:, x0:x1]
        sep = np.full((4, b.shape[1]), 128, np.uint8)
        rows += [b, mask, crop_row, sep, sep]
    return np.vstack(rows)
