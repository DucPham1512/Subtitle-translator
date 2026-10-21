"""The core as the app's shell and Settings screen see it: settings files, series, translation styles, device. Views import the core only through app.services (and data types from subagent.kernel)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.infra import describe
    from subagent.llm import LLMClient
    from subagent.settings import (
        TEMPLATE,
        find_root,
        list_registers,
        list_series,
        save_config_text,
        save_register,
        save_settings,
        schema,
        split_terms,
        update_config_values,
    )
    from subagent.workspace import detect_number, series

# name -> (core package, attribute); loaded the first time a view uses it
_EXPORTS = {
    "LLMClient": ("subagent.llm", "LLMClient"),
    "TEMPLATE": ("subagent.settings", "TEMPLATE"),
    "describe": ("subagent.infra", "describe"),
    "detect_number": ("subagent.workspace", "detect_number"),
    "find_root": ("subagent.settings", "find_root"),
    "list_registers": ("subagent.settings", "list_registers"),
    "list_series": ("subagent.settings", "list_series"),
    "save_config_text": ("subagent.settings", "save_config_text"),
    "save_register": ("subagent.settings", "save_register"),
    "save_settings": ("subagent.settings", "save_settings"),
    "schema": ("subagent.settings", "schema"),
    "series": ("subagent.workspace", "series"),
    "split_terms": ("subagent.settings", "split_terms"),
    "update_config_values": ("subagent.settings", "update_config_values"),
}

__all__ = ["LLMClient", "TEMPLATE", "describe", "detect_number", "find_root", "list_registers", "list_series", "save_config_text", "save_register", "save_settings", "schema", "series", "split_terms", "update_config_values"]


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
