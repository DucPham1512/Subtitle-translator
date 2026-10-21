"""Subtitle extraction (5.3-5.6): frame sampling, OCR, event building, OCR correction, series subtitle style."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.ocr.ingest import calibrate as calibrate_band
    from subagent.ocr.ocr import crop_path
    from subagent.ocr.subtitle_style import calibrate as calibrate_style
    from subagent.ocr.subtitle_style import load_style, save_style, style_preview

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "calibrate_band": ("subagent.ocr.ingest", "calibrate"),
    "calibrate_style": ("subagent.ocr.subtitle_style", "calibrate"),
    "crop_path": ("subagent.ocr.ocr", "crop_path"),
    "load_style": ("subagent.ocr.subtitle_style", "load_style"),
    "save_style": ("subagent.ocr.subtitle_style", "save_style"),
    "style_preview": ("subagent.ocr.subtitle_style", "style_preview"),
}

__all__ = ["calibrate_band", "calibrate_style", "crop_path", "load_style", "save_style", "style_preview"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
