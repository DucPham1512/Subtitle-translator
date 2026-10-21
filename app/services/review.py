"""The core as the Review screen sees it: review flags and drafts, rule checks, character ids, cast labels. Views import the core only through app.services (and data types from subagent.kernel)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.bootstrap import name_pinyin, slugify
    from subagent.cast import NOT_A_CHARACTER
    from subagent.memory import is_auto_id, new_voice_id
    from subagent.review import (
        FLAG_ORDER,
        PARTIAL_FLAG,
        RULE_WARNING_FLAGS,
        needs_attention,
        regenerate_pinyin,
        review_order,
    )
    from subagent.translation import rule_checks

# name -> (core package, attribute); loaded the first time a view uses it
_EXPORTS = {
    "FLAG_ORDER": ("subagent.review", "FLAG_ORDER"),
    "NOT_A_CHARACTER": ("subagent.cast", "NOT_A_CHARACTER"),
    "PARTIAL_FLAG": ("subagent.review", "PARTIAL_FLAG"),
    "RULE_WARNING_FLAGS": ("subagent.review", "RULE_WARNING_FLAGS"),
    "is_auto_id": ("subagent.memory", "is_auto_id"),
    "name_pinyin": ("subagent.bootstrap", "name_pinyin"),
    "needs_attention": ("subagent.review", "needs_attention"),
    "new_voice_id": ("subagent.memory", "new_voice_id"),
    "regenerate_pinyin": ("subagent.review", "regenerate_pinyin"),
    "review_order": ("subagent.review", "review_order"),
    "rule_checks": ("subagent.translation", "rule_checks"),
    "slugify": ("subagent.bootstrap", "slugify"),
}

__all__ = ["FLAG_ORDER", "NOT_A_CHARACTER", "PARTIAL_FLAG", "RULE_WARNING_FLAGS", "is_auto_id", "name_pinyin", "needs_attention", "new_voice_id", "regenerate_pinyin", "review_order", "rule_checks", "slugify"]


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
