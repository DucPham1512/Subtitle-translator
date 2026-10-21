"""Generic subtitle segmentation (5.4a): stroke-width transform, once-per-series calibration, segmentation."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from subagent.ocr.subtitle_style import (
    SubtitleStyle,
    calibrate,
    load_style,
    save_style,
    segment_mask,
    stroke_width_transform,
)

H, W, STROKE = 48, 400, 6


def _glyphs(band: np.ndarray, x0: int) -> None:
    """Three outlined 'letters' (white strokes of STROKE px, 3 px black outline) starting at x0."""
    for x in (x0, x0 + 40, x0 + 80):
        for pts in (((x, 8), (x, 40)), ((x, 8), (x + 26, 8)), ((x + 26, 8), (x + 26, 40)), ((x, 24), (x + 26, 24))):
            cv2.line(band, *pts, 0, STROKE + 6)
        for pts in (((x, 8), (x, 40)), ((x, 8), (x + 26, 8)), ((x + 26, 8), (x + 26, 40)), ((x, 24), (x + 26, 24))):
            cv2.line(band, *pts, 255, STROKE)


def _bands(n: int = 12, seed: int = 0) -> list[np.ndarray]:
    """A subtitle that stays for 4 samples at a time over a background that changes every sample."""
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        band = cv2.GaussianBlur(rng.integers(90, 170, (H, W)).astype(np.uint8), (9, 9), 0)
        cv2.rectangle(band, (300, 4), (390, 44), 235, -1)          # a light prop with a wide surface
        _glyphs(band, 120 + 0 * (i // 4))
        out.append(band)
    # the subtitle is static while shown, the background is not: copy the text pixels between samples
    for i in range(1, n):
        text = (out[0] == 255) | (out[0] == 0)
        out[i][text] = out[0][text]
    return out


def test_stroke_width_transform_measures_strokes():
    band = _bands(1)[0]
    swt = stroke_width_transform(band, light=True, max_width=H // 3)
    widths = swt[10:38, 117:124]                               # inside the first letter's vertical stroke
    assert np.median(widths[widths > 0]) == pytest.approx(STROKE, abs=2)


def test_calibration_learns_light_outlined_text_and_segmentation_uses_it(tmp_path):
    bands = _bands()
    style = calibrate(bands, stable_range=12, source="ep001")
    assert style.polarity == "light" and style.outline_level is not None and style.fill_min > 150
    assert style.stroke * H == pytest.approx(STROKE, abs=2.5)
    save_style(tmp_path, style)
    assert load_style(tmp_path) == style
    mask = segment_mask(bands[1], style, stroke_tolerance=0.6, outline_share=0.5, max_height=1.3, min_stable=0.6)
    assert (mask[10:38, 117:124] == 0).mean() > 0.5            # the text strokes
    assert (mask[:, 300:391] == 255).all()                     # the prop's wide surface is not text
    assert (mask[:, :100] == 255).mean() > 0.98                # nor the background


def test_unstable_components_are_dropped():
    bands = _bands()
    style = SubtitleStyle(polarity="light", fill_min=200, fill_max=255, outline_level=40, stroke=STROKE / H,
                          stroke_spread=0.3, letter_height=0.7)
    still = np.ones((H, W), bool)
    moving = still.copy()
    moving[:, 100:260] = False                                 # the text area changed while it was shown
    kw = dict(stroke_tolerance=0.6, outline_share=0.5, max_height=1.3, min_stable=0.6)
    assert (segment_mask(bands[0], style, stable=still, **kw)[10:38, 117:124] == 0).any()
    assert (segment_mask(bands[0], style, stable=moving, **kw)[:, 100:260] == 255).all()


def test_a_new_style_reruns_ocr_only_with_segmentation(project):
    from subagent.pipeline import STAGE_BY_NAME, Runner
    from subagent.workspace.context import EpisodeContext
    from tests.conftest import register_episode

    config, paths = project
    ep = register_episode(paths, 1)
    style = SubtitleStyle(polarity="light", fill_min=200, fill_max=255, outline_level=40, stroke=0.12,
                          stroke_spread=0.3, letter_height=0.7, calibrated_from="ep001")

    def ocr_hash(cfg) -> str:
        return Runner(EpisodeContext(cfg, paths, ep), "auto").input_hash(STAGE_BY_NAME["ocr"])

    plain = ocr_hash(config)
    save_style(paths.bootstrap, style)
    assert ocr_hash(config) == plain                  # without segmentation the style is never read
    seg = config.model_copy(deep=True)
    seg.ocr.preprocess = "segment"
    first = ocr_hash(seg)
    save_style(paths.bootstrap, style.model_copy(update={"calibrated_at": "later", "regions": 99}))
    assert ocr_hash(seg) == first                     # only the bookkeeping changed: nothing to read again
    save_style(paths.bootstrap, style.model_copy(update={"outline_level": 72}))
    assert ocr_hash(seg) != first                     # a new style re-runs OCR
