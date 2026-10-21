"""Settings: config.yaml / series.yaml loading and validation (5.2, 5.2a), translation styles, the settings form schema, in-place YAML edits."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.settings import schema
    from subagent.settings.config import (
        SERIES_FILE,
        SERIES_SECTIONS,
        Band,
        CastConfig,
        Config,
        NonDialogueConfig,
        OcrConfig,
        Paths,
        ScriptReviewConfig,
        ShowConfig,
        SpriteConfig,
        VideoConfig,
        VoiceConfig,
        WindowsConfig,
        find_root,
        list_series,
        load_config,
        save_config_text,
        save_settings,
        series_root,
        update_config_values,
    )
    from subagent.settings.registers import (
        TEMPLATE,
        list_registers,
        load_register,
        save_register,
        split_terms,
    )

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "Band": ("subagent.settings.config", "Band"),
    "CastConfig": ("subagent.settings.config", "CastConfig"),
    "Config": ("subagent.settings.config", "Config"),
    "NonDialogueConfig": ("subagent.settings.config", "NonDialogueConfig"),
    "OcrConfig": ("subagent.settings.config", "OcrConfig"),
    "Paths": ("subagent.settings.config", "Paths"),
    "SERIES_FILE": ("subagent.settings.config", "SERIES_FILE"),
    "SERIES_SECTIONS": ("subagent.settings.config", "SERIES_SECTIONS"),
    "ScriptReviewConfig": ("subagent.settings.config", "ScriptReviewConfig"),
    "ShowConfig": ("subagent.settings.config", "ShowConfig"),
    "SpriteConfig": ("subagent.settings.config", "SpriteConfig"),
    "TEMPLATE": ("subagent.settings.registers", "TEMPLATE"),
    "VideoConfig": ("subagent.settings.config", "VideoConfig"),
    "VoiceConfig": ("subagent.settings.config", "VoiceConfig"),
    "WindowsConfig": ("subagent.settings.config", "WindowsConfig"),
    "find_root": ("subagent.settings.config", "find_root"),
    "list_registers": ("subagent.settings.registers", "list_registers"),
    "list_series": ("subagent.settings.config", "list_series"),
    "load_config": ("subagent.settings.config", "load_config"),
    "load_register": ("subagent.settings.registers", "load_register"),
    "save_config_text": ("subagent.settings.config", "save_config_text"),
    "save_register": ("subagent.settings.registers", "save_register"),
    "save_settings": ("subagent.settings.config", "save_settings"),
    "series_root": ("subagent.settings.config", "series_root"),
    "split_terms": ("subagent.settings.registers", "split_terms"),
    "update_config_values": ("subagent.settings.config", "update_config_values"),
}

__all__ = ["Band", "CastConfig", "Config", "NonDialogueConfig", "OcrConfig", "Paths", "SERIES_FILE", "SERIES_SECTIONS", "ScriptReviewConfig", "ShowConfig", "SpriteConfig", "TEMPLATE", "VideoConfig", "VoiceConfig", "WindowsConfig", "find_root", "list_registers", "list_series", "load_config", "load_register", "save_config_text", "save_register", "save_settings", "schema", "series_root", "split_terms", "update_config_values"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
