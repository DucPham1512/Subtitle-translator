"""Output (5.19, 5.22, 5.23): ASS + mask + burn-in, delivery to the output folder, cleanup."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.output.delivery import (
        OnExists,
        cleanup,
        deliver,
        output_folder,
        resolve_conflict,
        reveal_in_explorer,
        target_path,
    )
    from subagent.output.render import build_mask_filter, font_files, preview_ass
    from subagent.output.render import render as render_video

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "OnExists": ("subagent.output.delivery", "OnExists"),
    "build_mask_filter": ("subagent.output.render", "build_mask_filter"),
    "cleanup": ("subagent.output.delivery", "cleanup"),
    "deliver": ("subagent.output.delivery", "deliver"),
    "font_files": ("subagent.output.render", "font_files"),
    "output_folder": ("subagent.output.delivery", "output_folder"),
    "preview_ass": ("subagent.output.render", "preview_ass"),
    "render_video": ("subagent.output.render", "render"),
    "resolve_conflict": ("subagent.output.delivery", "resolve_conflict"),
    "reveal_in_explorer": ("subagent.output.delivery", "reveal_in_explorer"),
    "target_path": ("subagent.output.delivery", "target_path"),
}

__all__ = ["OnExists", "build_mask_filter", "cleanup", "deliver", "font_files", "output_folder", "preview_ass", "render_video", "resolve_conflict", "reveal_in_explorer", "target_path"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
