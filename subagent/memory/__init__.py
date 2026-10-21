"""Memory (5.15-5.18): read store, the Memory Manager (sole writer), prompt prefixes, briefings, dreaming, probation, character updates."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.memory import briefings, dreaming
    from subagent.memory.characters import (
        draft_voice_ids,
        episode_character_ids,
        is_auto_id,
        load_new_voices,
        new_voice_id,
        review_voice_ids,
        save_new_voices,
    )
    from subagent.memory.evidence import is_auto_episode, trusted_auto_lines, usable_line
    from subagent.memory.manager import ApplyResult, MemoryManager
    from subagent.memory.prefix import (
        corrections_block,
        evaluator_prefix,
        new_voices_block,
        ocr_fix_prefix,
        reviewer_corrections,
        translator_prefix,
    )
    from subagent.memory.store import (
        Character,
        GlossaryEntry,
        LineDecision,
        MemoryStore,
        PronounPair,
        parse_aliases,
        row_key,
    )

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "ApplyResult": ("subagent.memory.manager", "ApplyResult"),
    "Character": ("subagent.memory.store", "Character"),
    "GlossaryEntry": ("subagent.memory.store", "GlossaryEntry"),
    "LineDecision": ("subagent.memory.store", "LineDecision"),
    "MemoryManager": ("subagent.memory.manager", "MemoryManager"),
    "MemoryStore": ("subagent.memory.store", "MemoryStore"),
    "PronounPair": ("subagent.memory.store", "PronounPair"),
    "corrections_block": ("subagent.memory.prefix", "corrections_block"),
    "draft_voice_ids": ("subagent.memory.characters", "draft_voice_ids"),
    "episode_character_ids": ("subagent.memory.characters", "episode_character_ids"),
    "evaluator_prefix": ("subagent.memory.prefix", "evaluator_prefix"),
    "is_auto_episode": ("subagent.memory.evidence", "is_auto_episode"),
    "is_auto_id": ("subagent.memory.characters", "is_auto_id"),
    "load_new_voices": ("subagent.memory.characters", "load_new_voices"),
    "new_voice_id": ("subagent.memory.characters", "new_voice_id"),
    "new_voices_block": ("subagent.memory.prefix", "new_voices_block"),
    "ocr_fix_prefix": ("subagent.memory.prefix", "ocr_fix_prefix"),
    "parse_aliases": ("subagent.memory.store", "parse_aliases"),
    "review_voice_ids": ("subagent.memory.characters", "review_voice_ids"),
    "reviewer_corrections": ("subagent.memory.prefix", "reviewer_corrections"),
    "row_key": ("subagent.memory.store", "row_key"),
    "save_new_voices": ("subagent.memory.characters", "save_new_voices"),
    "translator_prefix": ("subagent.memory.prefix", "translator_prefix"),
    "trusted_auto_lines": ("subagent.memory.evidence", "trusted_auto_lines"),
    "usable_line": ("subagent.memory.evidence", "usable_line"),
}

__all__ = ["ApplyResult", "Character", "GlossaryEntry", "LineDecision", "MemoryManager", "MemoryStore", "PronounPair", "briefings", "corrections_block", "draft_voice_ids", "dreaming", "episode_character_ids", "evaluator_prefix", "is_auto_episode", "is_auto_id", "load_new_voices", "new_voice_id", "new_voices_block", "ocr_fix_prefix", "parse_aliases", "review_voice_ids", "reviewer_corrections", "row_key", "save_new_voices", "translator_prefix", "trusted_auto_lines", "usable_line"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
