"""Stage 2: OCR of saved subtitle bands with RapidOCR (5.4)."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Sequence

import numpy as np

from subagent.config import Band, Config, OcrConfig
from subagent.context import EpisodeContext
from subagent.device import onnx_use_cuda
from subagent.errors import ModelUnavailableError
from subagent.media import imread
from subagent.models import ChangeRecord, OcrBox, OcrReading, VideoInfo
from subagent.textutil import keep_cjk
from subagent.util import read_jsonl, write_jsonl

log = logging.getLogger(__name__)

# One detection: (polygon points [[x, y], ...], text, score)
RawBox = tuple[Sequence[Sequence[float]], str, float]
OcrEngine = Callable[[np.ndarray], list[RawBox]]

_ENGINES: dict[tuple, OcrEngine] = {}


def _engine_key(config: Config) -> tuple:
    o = config.ocr
    return (onnx_use_cuda(config), o.det_limit_type, o.det_limit_side_len, o.use_cls, _line_mode(o))


def _line_mode(cfg: OcrConfig) -> bool:
    return cfg.recognize == "line" and cfg.preprocess in ("mask", "segment")


def create_engine(config: Config) -> OcrEngine:
    """RapidOCR (PaddleOCR models on ONNX Runtime); CUDA provider when available, CPU otherwise."""
    use_cuda = onnx_use_cuda(config)
    o = config.ocr
    try:
        from rapidocr import RapidOCR  # rapidocr >= 2

        params: dict = {"Det.limit_type": o.det_limit_type, "Det.limit_side_len": o.det_limit_side_len,
                        "Global.use_cls": o.use_cls}
        line = _line_mode(o)
        if line:
            params.update({"Global.use_det": False, "Global.use_cls": False})
        if use_cuda:
            params["EngineConfig.onnxruntime.use_cuda"] = True
        engine = RapidOCR(params=params)
        providers = _providers(engine)

        def run_new(img: np.ndarray) -> list[RawBox]:
            out = engine(img)
            boxes, txts, scores = getattr(out, "boxes", None), getattr(out, "txts", None), getattr(out, "scores", None)
            if line and txts:                 # recognition only: the whole image is the one text line
                h, w = img.shape[:2]
                return [([[0, 0], [w, 0], [w, h], [0, h]], str(txts[0]), float(scores[0]))]
            if boxes is None or txts is None:
                return []
            return [(np.asarray(b).tolist(), str(t), float(s)) for b, t, s in zip(boxes, txts, scores, strict=False)]

        log.info("OCR: rapidocr on %s (%s)", providers or ("CUDA requested" if use_cuda else "CPU"),
                 "recognition of the masked line" if line else
                 f"det {o.det_limit_type} {o.det_limit_side_len}, cls {'on' if o.use_cls else 'off'}")
        return run_new
    except ImportError:
        pass
    try:
        from rapidocr_onnxruntime import RapidOCR as LegacyRapidOCR

        legacy = LegacyRapidOCR(det_use_cuda=use_cuda, cls_use_cuda=use_cuda, rec_use_cuda=use_cuda)

        def run_legacy(img: np.ndarray) -> list[RawBox]:
            result, _ = legacy(img)
            return [(box, str(text), float(score)) for box, text, score in (result or [])]

        log.info("OCR: rapidocr_onnxruntime (%s)", "CUDA" if use_cuda else "CPU")
        return run_legacy
    except ImportError as exc:
        raise ModelUnavailableError(
            "RapidOCR is not installed. Install it with: pip install rapidocr onnxruntime-gpu"
        ) from exc


def _providers(engine) -> str:
    """The execution provider the detector really runs on (RapidOCR silently falls back to the CPU)."""
    try:
        session = engine.text_det.session
        session = getattr(session, "session", session)
        return session.get_providers()[0].replace("ExecutionProvider", "")
    except Exception:  # noqa: BLE001 - internal attribute, may change between RapidOCR versions
        return ""


def get_engine(config: Config) -> OcrEngine:
    """Models load once per process (NFR-P3), once per engine setting."""
    key = _engine_key(config)
    if key not in _ENGINES:
        _ENGINES[key] = create_engine(config)
    return _ENGINES[key]


# -- pre-processing ---------------------------------------------------------------------------------

def subtitle_mask(band: np.ndarray, cfg: OcrConfig) -> np.ndarray:
    """Keep only what looks like burned-in subtitle text: bright strokes whose edge is mostly ringed by a dark
    outline, at most glyph-sized. Scenery (sky, snow, a white cooler with black writing, nets) is dropped.
    Returns black text on white, the same size as the band."""
    import cv2

    h, w = band.shape[:2]
    bright = (band >= cfg.mask_bright).astype(np.uint8)
    dark = (band <= cfg.mask_dark).astype(np.uint8)
    k = 2 * cfg.mask_reach_px + 1
    near_dark = cv2.dilate(dark, np.ones((k, k), np.uint8)).astype(bool)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(bright, connectivity=8)
    edge = bright.astype(bool) & ~cv2.erode(bright, np.ones((3, 3), np.uint8)).astype(bool)
    edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = False      # strokes cut by the band border
    edge_all = np.bincount(labels[edge], minlength=n)
    edge_dark = np.bincount(labels[edge & near_dark], minlength=n)
    mean = np.bincount(labels.ravel(), weights=band.ravel().astype(np.float64), minlength=n) / np.maximum(stats[:, 4], 1)
    stroke = np.zeros(n, np.float32)
    if cfg.mask_max_stroke > 0:          # how far the inside of each bright area is from its edge
        dist = cv2.distanceTransform(bright, cv2.DIST_L2, 3)
        np.maximum.at(stroke, labels.ravel(), dist.ravel())
    keep = np.zeros(n, bool)
    for i in range(1, n):
        x, y, cw, ch, area = stats[i]
        if (area >= cfg.mask_min_area and ch <= cfg.mask_max_height * h and cw <= cfg.mask_max_width * h
                and edge_all[i] and edge_dark[i] / edge_all[i] >= cfg.mask_min_outline
                and (cfg.mask_max_stroke <= 0 or stroke[i] <= cfg.mask_max_stroke * h)
                and mean[i] >= cfg.mask_min_mean):
            keep[i] = True
    out = np.full((h, w), 255, np.uint8)
    out[keep[labels]] = 0
    return out


def line_span(clean: np.ndarray, cfg: OcrConfig) -> tuple[int, int, int, int] | None:
    """(x0, y0, x1, y1) of the subtitle line in a mask: black components grouped left to right while the gap is
    at most `box_max_gap` band heights; the group with the most ink wins; None when it is only specks."""
    import cv2

    h = clean.shape[0]
    n, _, stats, _ = cv2.connectedComponentsWithStats((clean == 0).astype(np.uint8), connectivity=8)
    comps = sorted((tuple(stats[i]) for i in range(1, n)), key=lambda s: s[0])
    groups: list[list[tuple]] = []
    for c in comps:
        if groups and c[0] - max(g[0] + g[2] for g in groups[-1]) <= cfg.box_max_gap * h:
            groups[-1].append(c)
        else:
            groups.append([c])
    if not groups:
        return None
    best = max(groups, key=lambda g: sum(c[4] for c in g))
    x0, y0 = min(c[0] for c in best), min(c[1] for c in best)
    x1, y1 = max(c[0] + c[2] for c in best), max(c[1] + c[3] for c in best)
    return (x0, y0, x1, y1) if y1 - y0 >= cfg.line_min_height * h else None


def symmetric_span(span: tuple[int, int, int, int], center_x: float,
                   tolerance: float) -> tuple[int, int, int, int] | None:
    """The line span with the side farther from the frame's centre trimmed to the other side's length, leaving
    `tolerance` line heights of difference (a letter segmentation missed at the short end is not answered by
    cutting a real one off the long end). None when the span does not reach across the centre: subtitles are
    centred, so a line wholly on one side is not one."""
    x0, y0, x1, y1 = span
    if not x0 < center_x < x1:
        return None
    left, right = center_x - x0, x1 - center_x
    slack = tolerance * (y1 - y0)
    if left > right + slack:
        x0 = math.floor(center_x - right - slack)
    elif right > left + slack:
        x1 = math.ceil(center_x + left + slack)
    return x0, y0, x1, y1


def center_in_band(info: VideoInfo, band: Band) -> float:
    """The frame's centre column in band coordinates."""
    return info.width / 2 - band.pixels(info.width, info.height)[0]


def prepare(band: np.ndarray, cfg: OcrConfig, style=None, stable: np.ndarray | None = None,
            center_x: float | None = None) -> tuple[np.ndarray, float, int | tuple[int, int]]:
    """The image OCR reads, with the scale and padding that map its coordinates back to the band.

    In line mode the image is only the subtitle line (full band height); the returned padding is negative
    by the crop's left edge so `to_band_coords` still maps back. An empty line gives an empty image.
    `center_x` (the frame's centre column in the band) is needed for `symmetric_crop`."""
    import cv2

    if cfg.preprocess == "none":
        return band, 1.0, 0
    if cfg.preprocess == "segment":
        from subagent.subtitle_style import segment_mask

        if style is None:
            raise ModelUnavailableError("ocr.preprocess is 'segment' but the series has no subtitle style yet: "
                                        "run `python -m subagent calibrate EPISODE --style` once")
        mask = segment_mask(band, style, stroke_tolerance=cfg.seg_stroke_tolerance,
                            outline_share=cfg.seg_outline_share, max_height=cfg.seg_max_height,
                            min_stable=cfg.seg_min_stable, stable=stable, max_width=cfg.seg_max_width)
    else:
        mask = subtitle_mask(band, cfg)
    clean = mask
    if cfg.mask_image == "original":
        clean = band
    elif cfg.mask_image == "isolated":
        k = 2 * cfg.isolate_grow_px + 1
        keep = cv2.dilate((mask == 0).astype(np.uint8), np.ones((k, k), np.uint8)).astype(bool)
        clean = np.where(keep, band, 0).astype(np.uint8)
    offset = 0
    if _line_mode(cfg):
        span = line_span(mask, cfg)
        if span is not None and cfg.symmetric_crop and center_x is not None:
            span = symmetric_span(span, center_x, cfg.symmetric_crop_tolerance)
        if span is None:
            return np.zeros((0, 0), np.uint8), 1.0, 0
        grow = cfg.isolate_grow_px
        offset = max(0, span[0] - grow)
        clean = clean[:, offset:min(band.shape[1], span[2] + grow)]
        if cfg.line_crop_vertical:
            clean = clean[max(0, span[1] - grow):min(band.shape[0], span[3] + grow)]
    if cfg.mask_scale != 1.0:
        clean = cv2.resize(clean, None, fx=cfg.mask_scale, fy=cfg.mask_scale, interpolation=cv2.INTER_CUBIC)
    pad = cfg.mask_pad
    fill = 255 if cfg.mask_image == "mask" else 0         # outlined white text reads best on a dark margin
    clean = cv2.copyMakeBorder(clean, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=fill)
    return clean, cfg.mask_scale, (pad, offset) if offset else pad


def to_band_coords(raw: list[RawBox], scale: float, pad: int | tuple[int, int]) -> list[RawBox]:
    """Map points of the prepared image back to the band. `pad` may be (padding, crop offset in band px)."""
    pad, offset = pad if isinstance(pad, tuple) else (pad, 0)
    if scale == 1.0 and pad == 0 and offset == 0:
        return raw
    return [([[(float(p[0]) - pad) / scale + offset, (float(p[1]) - pad) / scale] for p in pts], text, score)
            for pts, text, score in raw]


def filter_boxes(boxes: list[OcrBox], band_w: int, band_h: int, cfg: OcrConfig) -> list[OcrBox]:
    """The subtitle is one line of uniform height: keep the main box (most characters) and the boxes beside it
    that are about as tall and close to it; drop props and numbers next to the line."""
    if not cfg.box_filter or len(boxes) < 2:
        return boxes
    main = max(boxes, key=lambda b: (len(b.text), b.x1 - b.x0))
    line_h = main.height * band_h
    kept = [main]
    rest = sorted((b for b in boxes if b is not main), key=lambda b: abs((b.x0 + b.x1) - (main.x0 + main.x1)))
    for b in rest:
        if b.height * band_h < cfg.box_min_height * line_h:
            continue
        x0, x1 = min(k.x0 for k in kept), max(k.x1 for k in kept)
        gap = max(0.0, b.x0 - x1, x0 - b.x1) * band_w
        if gap > cfg.box_max_gap * line_h:
            continue
        kept.append(b)
    return kept


def crop_view(band: np.ndarray, image: np.ndarray, scale: float, pad: int | tuple[int, int]) -> np.ndarray:
    """What OCR read, drawn where it sits in the band (band-sized, grey elsewhere), to show under the original."""
    import cv2

    out = np.full(band.shape, 128, np.uint8)
    if not image.size:
        return out
    pad, offset = pad if isinstance(pad, tuple) else (pad, 0)
    inner = image[pad:image.shape[0] - pad, pad:image.shape[1] - pad] if pad else image
    if scale != 1.0:
        inner = cv2.resize(inner, (max(1, round(inner.shape[1] / scale)), max(1, round(inner.shape[0] / scale))),
                           interpolation=cv2.INTER_AREA)
    ih, iw = min(inner.shape[0], band.shape[0]), min(inner.shape[1], band.shape[1] - offset)
    top = 0 if ih == band.shape[0] else (band.shape[0] - ih) // 2
    out[top:top + ih, offset:offset + iw] = inner[:ih, :iw]
    return out


def crop_path(work, t_ms: int):
    return work / "ocr_crops" / f"{t_ms}.png"


def save_sample(folder, t_ms: int, band: np.ndarray, prepared: np.ndarray, text: str) -> None:
    """Before (top) and after (bottom) pre-processing, at the same width (ocr_samples/, temporary)."""
    import cv2

    from subagent.media import imwrite_png

    w = prepared.shape[1]
    top = cv2.resize(band, (w, max(1, round(band.shape[0] * w / band.shape[1]))), interpolation=cv2.INTER_NEAREST)
    sep = np.full((4, w), 128, np.uint8)
    imwrite_png(folder / f"{t_ms}.png", np.vstack([top, sep, prepared]))
    (folder / f"{t_ms}.txt").write_text(text + "\n", encoding="utf-8")


def _to_box(raw: RawBox, band_w: int, band_h: int) -> OcrBox | None:
    points, text, score = raw
    text = keep_cjk(text)
    if not text:
        return None
    xs = [float(p[0]) for p in points]
    ys = [float(p[1]) for p in points]
    return OcrBox(
        text=text, confidence=float(score),
        x0=min(xs) / band_w, x1=max(xs) / band_w, y0=min(ys) / band_h, y1=max(ys) / band_h,
    )


def group_rows(boxes: list[OcrBox]) -> list[list[OcrBox]]:
    """Group boxes into text rows by vertical overlap; rows top to bottom, boxes left to right."""
    rows: list[list[OcrBox]] = []
    for box in sorted(boxes, key=lambda b: b.vcenter):
        for row in rows:
            top = min(b.y0 for b in row)
            bottom = max(b.y1 for b in row)
            row_center = (top + bottom) / 2
            if abs(box.vcenter - row_center) <= max(bottom - top, box.height) / 2:
                row.append(box)
                break
        else:
            rows.append([box])
    return [sorted(row, key=lambda b: b.x0) for row in rows]


def reading_from_boxes(t_ms: int, raw: list[RawBox], band_w: int, band_h: int, cfg: OcrConfig) -> OcrReading:
    boxes = [b for b in (_to_box(r, band_w, band_h) for r in raw) if b is not None]
    boxes = filter_boxes(boxes, band_w, band_h, cfg)
    if not boxes:
        return OcrReading(t_ms=t_ms, kind="text", text="", confidence=0.0)
    rows = group_rows(boxes)
    text = "".join(b.text for row in rows for b in row)
    weights = [len(b.text) for b in boxes]
    confidence = float(np.average([b.confidence for b in boxes], weights=weights))
    y0, y1 = min(b.y0 for b in boxes), max(b.y1 for b in boxes)
    x0, x1 = min(b.x0 for b in boxes), max(b.x1 for b in boxes)
    return OcrReading(
        t_ms=t_ms, kind="text", text=text, confidence=confidence, boxes=[b for row in rows for b in row],
        multi_row=len(rows) > 1, low_conf=confidence < cfg.min_confidence,
        box_height=y1 - y0, box_vcenter=(y0 + y1) / 2, box_hcenter=(x0 + x1) / 2,
    )


def run(ctx: EpisodeContext, engine: OcrEngine | None = None) -> dict[str, int]:
    import cv2

    changes = read_jsonl(ctx.artifact("changes.jsonl"), ChangeRecord)
    text_changes = [c for c in changes if c.kind == "text"]
    engine = engine or get_engine(ctx.config)
    cfg = ctx.config.ocr
    samples = ctx.artifact("ocr_samples")
    crops = ctx.artifact("ocr_crops")
    keep_crops = cfg.save_crops and cfg.preprocess != "none"
    for folder in (samples, crops):
        if folder.exists():
            import shutil

            shutil.rmtree(folder)
    step = max(1, len(text_changes) // cfg.sample_images) if cfg.sample_images else 0
    style = None
    if cfg.preprocess == "segment":
        from subagent.subtitle_style import load_style

        style = load_style(ctx.paths.bootstrap)
    center_x = center_in_band(ctx.video_info(), ctx.config.video.subtitle_band) if cfg.symmetric_crop else None
    readings: list[OcrReading] = []
    done = 0
    for change in changes:
        if change.kind == "empty":
            readings.append(OcrReading(t_ms=change.t_ms, kind="empty"))
            continue
        band = imread(ctx.artifact("bands") / f"{change.t_ms}.png", gray=True)
        h, w = band.shape[:2]
        stable_png = ctx.artifact("bands") / f"{change.t_ms}.stable.png"
        stable = imread(stable_png, gray=True) > 0 if stable_png.is_file() else None
        image, scale, pad = prepare(band, cfg, style, stable, center_x)
        raw = to_band_coords(engine(cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)), scale, pad) if image.size else []
        reading = reading_from_boxes(change.t_ms, raw, w, h, cfg)
        readings.append(reading)
        if keep_crops:
            from subagent.media import imwrite_png

            imwrite_png(crop_path(ctx.work, change.t_ms), crop_view(band, image, scale, pad))
        if step and done % step == 0 and done // step < cfg.sample_images and image.size:
            save_sample(samples, change.t_ms, band, image, reading.text)
        done += 1
        ctx.progress.emit("ocr", "progress", done=done, total=len(text_changes))
    write_jsonl(ctx.artifact("ocr_raw.jsonl"), readings)
    low = sum(1 for r in readings if r.low_conf)
    multi = sum(1 for r in readings if r.multi_row)
    return {"readings": done, "low_confidence": low, "multi_row": multi}
