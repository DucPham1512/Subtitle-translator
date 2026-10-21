"""Review (5.14, 6.4b): the review gate, drafts, finishing, partial review."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.review.partial import OUTPUT, PARTIAL_FLAG, partial_review
    from subagent.review.review import (
        FLAG_ORDER,
        RULE_WARNING_FLAGS,
        finish_review,
        gate,
        load_draft,
        needs_attention,
        original_draft,
        regenerate_pinyin,
        review_order,
        save_draft,
    )

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "FLAG_ORDER": ("subagent.review.review", "FLAG_ORDER"),
    "OUTPUT": ("subagent.review.partial", "OUTPUT"),
    "PARTIAL_FLAG": ("subagent.review.partial", "PARTIAL_FLAG"),
    "RULE_WARNING_FLAGS": ("subagent.review.review", "RULE_WARNING_FLAGS"),
    "finish_review": ("subagent.review.review", "finish_review"),
    "gate": ("subagent.review.review", "gate"),
    "load_draft": ("subagent.review.review", "load_draft"),
    "needs_attention": ("subagent.review.review", "needs_attention"),
    "original_draft": ("subagent.review.review", "original_draft"),
    "partial_review": ("subagent.review.partial", "partial_review"),
    "regenerate_pinyin": ("subagent.review.review", "regenerate_pinyin"),
    "review_order": ("subagent.review.review", "review_order"),
    "save_draft": ("subagent.review.review", "save_draft"),
}

__all__ = ["FLAG_ORDER", "OUTPUT", "PARTIAL_FLAG", "RULE_WARNING_FLAGS", "finish_review", "gate", "load_draft", "needs_attention", "original_draft", "partial_review", "regenerate_pinyin", "review_order", "save_draft"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
