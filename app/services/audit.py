"""The core as the Audit screen sees it. Views import the core only through app.services (and data types from subagent.kernel)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.bench import NO_ID_YET

# name -> (core package, attribute); loaded the first time a view uses it
_EXPORTS = {
    "NO_ID_YET": ("subagent.bench", "NO_ID_YET"),
}

__all__ = ["NO_ID_YET"]


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
