"""Where the subtitle line sits in a band mask: shared by OCR line mode and style calibration (5.4, 5.4a)."""

from __future__ import annotations

import math

import numpy as np

from subagent.settings import OcrConfig


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
