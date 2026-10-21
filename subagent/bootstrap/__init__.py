"""Memory bootstrap (5.17): the seed draft from the cast list, clips and sprites."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.bootstrap import seed
    from subagent.bootstrap.seed import name_pinyin, slugify

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "name_pinyin": ("subagent.bootstrap.seed", "name_pinyin"),
    "slugify": ("subagent.bootstrap.seed", "slugify"),
}

__all__ = ["name_pinyin", "seed", "slugify"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
