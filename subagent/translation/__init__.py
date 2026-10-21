"""Translation (5.9-5.13a): pinyin, scene windows, translate + evaluate loop, script review."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.translation.evaluate import RuleContext, rule_checks
    from subagent.translation.pinyin_gen import PinyinEngine
    from subagent.translation.script_review import han_count
    from subagent.translation.translate import rank_attempt

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "PinyinEngine": ("subagent.translation.pinyin_gen", "PinyinEngine"),
    "RuleContext": ("subagent.translation.evaluate", "RuleContext"),
    "han_count": ("subagent.translation.script_review", "han_count"),
    "rank_attempt": ("subagent.translation.translate", "rank_attempt"),
    "rule_checks": ("subagent.translation.evaluate", "rule_checks"),
}

__all__ = ["PinyinEngine", "RuleContext", "han_count", "rank_attempt", "rule_checks"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
