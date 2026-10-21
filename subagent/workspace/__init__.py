"""Workspace: episode registry (5.21), per-episode context and state.json, series management (5.2a)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.workspace import series
    from subagent.workspace.context import EpisodeContext
    from subagent.workspace.episodes import AddCandidate, Registry, detect_number
    from subagent.workspace.state import load_state, save_state, state_path

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "AddCandidate": ("subagent.workspace.episodes", "AddCandidate"),
    "EpisodeContext": ("subagent.workspace.context", "EpisodeContext"),
    "Registry": ("subagent.workspace.episodes", "Registry"),
    "detect_number": ("subagent.workspace.episodes", "detect_number"),
    "load_state": ("subagent.workspace.state", "load_state"),
    "save_state": ("subagent.workspace.state", "save_state"),
    "state_path": ("subagent.workspace.state", "state_path"),
}

__all__ = ["AddCandidate", "EpisodeContext", "Registry", "detect_number", "load_state", "save_state", "series", "state_path"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
