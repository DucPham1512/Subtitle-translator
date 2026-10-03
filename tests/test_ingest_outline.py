"""Frame sampling: only bands with outlined (subtitle-like) text count as text."""

from __future__ import annotations

import numpy as np

from subagent.stages.ingest import binarize, detect_changes, has_subtitle, outlined_ratio


def _band(background: int) -> np.ndarray:
    return np.full((40, 200), background, dtype=np.uint8)


def _outlined_text(background: int = 128) -> np.ndarray:
    band = _band(background)
    band[10:30, 40:160] = 0          # dark outline box
    band[13:27, 43:157] = 255        # bright strokes inside it
    return band


def _bright_patch(background: int = 128) -> np.ndarray:
    band = _band(background)
    band[5:35, 20:180] = 255         # snow / sky: bright, no dark rim
    return band


def test_outlined_text_counts_and_bare_bright_areas_do_not(project):
    config, _ = project
    cfg = config.video
    text, snow = _outlined_text(), _bright_patch()
    assert outlined_ratio(text, binarize(text, cfg.text_threshold), cfg) >= cfg.min_outlined_ratio
    assert has_subtitle(text, binarize(text, cfg.text_threshold), cfg)
    assert not has_subtitle(snow, binarize(snow, cfg.text_threshold), cfg)
    cfg.subtitle_detection = "bright"                      # old behaviour on request
    assert has_subtitle(snow, binarize(snow, cfg.text_threshold), cfg)


def test_bright_background_is_not_sent_to_ocr(project):
    config, _ = project
    stats: dict[str, int] = {}
    frames = [_bright_patch(), _outlined_text(), _outlined_text(), _bright_patch(), _band(128)]
    changes = list(detect_changes(frames, fps=4, cfg=config.video, stats=stats))
    assert [(c.t_ms, c.kind) for c in changes] == [(250, "text"), (750, "empty")]
    assert stats == {"bright_without_outline": 2}
