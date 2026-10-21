"""The core as the Memory and Dreaming screens see it: briefings, dreaming, the voice bank. Views import the core only through app.services (and data types from subagent.kernel)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.memory import briefings, dreaming, parse_aliases, row_key
    from subagent.voice import all_similarities, voice_clips

# name -> (core package, attribute); loaded the first time a view uses it
_EXPORTS = {
    "all_similarities": ("subagent.voice", "all_similarities"),
    "briefings": ("subagent.memory", "briefings"),
    "dreaming": ("subagent.memory", "dreaming"),
    "parse_aliases": ("subagent.memory", "parse_aliases"),
    "row_key": ("subagent.memory", "row_key"),
    "voice_clips": ("subagent.voice", "voice_clips"),
}

__all__ = ["all_similarities", "briefings", "dreaming", "parse_aliases", "row_key", "voice_clips"]


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
