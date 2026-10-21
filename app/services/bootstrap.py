"""The core as the Bootstrap wizard sees it: the seed, calibration, clips and sprites. Views import the core only through app.services (and data types from subagent.kernel)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.bootstrap import seed
    from subagent.cast import save_template
    from subagent.infra import extract_frame, imread
    from subagent.ocr import load_style
    from subagent.settings import Band, update_config_values
    from subagent.voice import voice_clips

# name -> (core package, attribute); loaded the first time a view uses it
_EXPORTS = {
    "Band": ("subagent.settings", "Band"),
    "extract_frame": ("subagent.infra", "extract_frame"),
    "imread": ("subagent.infra", "imread"),
    "load_style": ("subagent.ocr", "load_style"),
    "save_template": ("subagent.cast", "save_template"),
    "seed": ("subagent.bootstrap", "seed"),
    "update_config_values": ("subagent.settings", "update_config_values"),
    "voice_clips": ("subagent.voice", "voice_clips"),
}

__all__ = ["Band", "extract_frame", "imread", "load_style", "save_template", "seed", "update_config_values", "voice_clips"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    package = importlib.import_module(module)
    try:
        value = getattr(package, attr)
    except AttributeError:          # a public submodule (namespace) not imported yet
        value = importlib.import_module(f"{module}.{attr}")
    globals()[name] = value
    return value
