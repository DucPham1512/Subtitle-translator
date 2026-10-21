"""The core as the Episodes and Run screens see it: stages, the registry, output delivery. Views import the core only through app.services (and data types from subagent.kernel)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.output import reveal_in_explorer
    from subagent.pipeline import RERUN_FROM, STAGE_NAMES, STAGES
    from subagent.workspace import AddCandidate, load_state

# name -> (core package, attribute); loaded the first time a view uses it
_EXPORTS = {
    "AddCandidate": ("subagent.workspace", "AddCandidate"),
    "RERUN_FROM": ("subagent.pipeline", "RERUN_FROM"),
    "STAGES": ("subagent.pipeline", "STAGES"),
    "STAGE_NAMES": ("subagent.pipeline", "STAGE_NAMES"),
    "load_state": ("subagent.workspace", "load_state"),
    "reveal_in_explorer": ("subagent.output", "reveal_in_explorer"),
}

__all__ = ["AddCandidate", "RERUN_FROM", "STAGES", "STAGE_NAMES", "load_state", "reveal_in_explorer"]


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
