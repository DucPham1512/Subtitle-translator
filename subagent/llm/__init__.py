"""The LLM client (5.1): providers, disk cache, cost records, budget, prompt loading."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.llm.client import LLMClient, build_messages, load_prompt, missing_prices, record_cost

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "LLMClient": ("subagent.llm.client", "LLMClient"),
    "build_messages": ("subagent.llm.client", "build_messages"),
    "load_prompt": ("subagent.llm.client", "load_prompt"),
    "missing_prices": ("subagent.llm.client", "missing_prices"),
    "record_cost": ("subagent.llm.client", "record_cost"),
}

__all__ = ["LLMClient", "build_messages", "load_prompt", "missing_prices", "record_cost"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
