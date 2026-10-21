"""Shared kernel: artifact models (4), errors, file and text helpers, progress reporting."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.kernel.errors import (
        BudgetExceeded,
        ConfigError,
        EpisodeLockedError,
        EpisodeNotFoundError,
        JobRunningError,
        LLMCallError,
        LLMOutputError,
        MediaError,
        MemoryLockedError,
        MissingBinaryError,
        ModelUnavailableError,
        OutputExistsError,
        OutputFolderError,
        ReviewIncompleteError,
        SourceMissingError,
        SubagentError,
    )
    from subagent.kernel.models import (
        AUDIT_ASPECTS,
        AuditMark,
        AuditSample,
        CastBoxEdit,
        CastDetection,
        CastLine,
        ChangeRecord,
        CostRecord,
        EditRecord,
        Episode,
        EpisodeState,
        EpisodeStatus,
        Evaluation,
        LineTranslation,
        LineType,
        MemoryProposal,
        NewVoice,
        OcrBox,
        OcrReading,
        PartialSuggestion,
        PinyinLine,
        ReviewedLine,
        ScriptDecision,
        SpeakerCandidates,
        StageState,
        SubtitleEvent,
        VideoInfo,
        Window,
    )
    from subagent.kernel.progress import NULL_PROGRESS, Progress
    from subagent.kernel.textutil import (
        balanced_wrap,
        contains_term,
        edit_distance,
        found_terms,
        is_han,
        keep_cjk,
        normalize_zh,
        relatedness,
        split_explicit_lines,
        visible_chars,
        wrap_words,
    )
    from subagent.kernel.util import (
        FileLock,
        append_jsonl,
        atomic_write_json,
        atomic_write_text,
        chunked,
        hash_path,
        lock_holder,
        now_iso,
        read_json,
        read_jsonl,
        sha256_json,
        write_jsonl,
    )

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "AUDIT_ASPECTS": ("subagent.kernel.models", "AUDIT_ASPECTS"),
    "AuditMark": ("subagent.kernel.models", "AuditMark"),
    "AuditSample": ("subagent.kernel.models", "AuditSample"),
    "BudgetExceeded": ("subagent.kernel.errors", "BudgetExceeded"),
    "CastBoxEdit": ("subagent.kernel.models", "CastBoxEdit"),
    "CastDetection": ("subagent.kernel.models", "CastDetection"),
    "CastLine": ("subagent.kernel.models", "CastLine"),
    "ChangeRecord": ("subagent.kernel.models", "ChangeRecord"),
    "ConfigError": ("subagent.kernel.errors", "ConfigError"),
    "CostRecord": ("subagent.kernel.models", "CostRecord"),
    "EditRecord": ("subagent.kernel.models", "EditRecord"),
    "Episode": ("subagent.kernel.models", "Episode"),
    "EpisodeLockedError": ("subagent.kernel.errors", "EpisodeLockedError"),
    "EpisodeNotFoundError": ("subagent.kernel.errors", "EpisodeNotFoundError"),
    "EpisodeState": ("subagent.kernel.models", "EpisodeState"),
    "EpisodeStatus": ("subagent.kernel.models", "EpisodeStatus"),
    "Evaluation": ("subagent.kernel.models", "Evaluation"),
    "FileLock": ("subagent.kernel.util", "FileLock"),
    "JobRunningError": ("subagent.kernel.errors", "JobRunningError"),
    "LLMCallError": ("subagent.kernel.errors", "LLMCallError"),
    "LLMOutputError": ("subagent.kernel.errors", "LLMOutputError"),
    "LineTranslation": ("subagent.kernel.models", "LineTranslation"),
    "LineType": ("subagent.kernel.models", "LineType"),
    "MediaError": ("subagent.kernel.errors", "MediaError"),
    "MemoryLockedError": ("subagent.kernel.errors", "MemoryLockedError"),
    "MemoryProposal": ("subagent.kernel.models", "MemoryProposal"),
    "MissingBinaryError": ("subagent.kernel.errors", "MissingBinaryError"),
    "ModelUnavailableError": ("subagent.kernel.errors", "ModelUnavailableError"),
    "NULL_PROGRESS": ("subagent.kernel.progress", "NULL_PROGRESS"),
    "NewVoice": ("subagent.kernel.models", "NewVoice"),
    "OcrBox": ("subagent.kernel.models", "OcrBox"),
    "OcrReading": ("subagent.kernel.models", "OcrReading"),
    "OutputExistsError": ("subagent.kernel.errors", "OutputExistsError"),
    "OutputFolderError": ("subagent.kernel.errors", "OutputFolderError"),
    "PartialSuggestion": ("subagent.kernel.models", "PartialSuggestion"),
    "PinyinLine": ("subagent.kernel.models", "PinyinLine"),
    "Progress": ("subagent.kernel.progress", "Progress"),
    "ReviewIncompleteError": ("subagent.kernel.errors", "ReviewIncompleteError"),
    "ReviewedLine": ("subagent.kernel.models", "ReviewedLine"),
    "ScriptDecision": ("subagent.kernel.models", "ScriptDecision"),
    "SourceMissingError": ("subagent.kernel.errors", "SourceMissingError"),
    "SpeakerCandidates": ("subagent.kernel.models", "SpeakerCandidates"),
    "StageState": ("subagent.kernel.models", "StageState"),
    "SubagentError": ("subagent.kernel.errors", "SubagentError"),
    "SubtitleEvent": ("subagent.kernel.models", "SubtitleEvent"),
    "VideoInfo": ("subagent.kernel.models", "VideoInfo"),
    "Window": ("subagent.kernel.models", "Window"),
    "append_jsonl": ("subagent.kernel.util", "append_jsonl"),
    "atomic_write_json": ("subagent.kernel.util", "atomic_write_json"),
    "atomic_write_text": ("subagent.kernel.util", "atomic_write_text"),
    "balanced_wrap": ("subagent.kernel.textutil", "balanced_wrap"),
    "chunked": ("subagent.kernel.util", "chunked"),
    "contains_term": ("subagent.kernel.textutil", "contains_term"),
    "edit_distance": ("subagent.kernel.textutil", "edit_distance"),
    "found_terms": ("subagent.kernel.textutil", "found_terms"),
    "hash_path": ("subagent.kernel.util", "hash_path"),
    "is_han": ("subagent.kernel.textutil", "is_han"),
    "keep_cjk": ("subagent.kernel.textutil", "keep_cjk"),
    "lock_holder": ("subagent.kernel.util", "lock_holder"),
    "normalize_zh": ("subagent.kernel.textutil", "normalize_zh"),
    "now_iso": ("subagent.kernel.util", "now_iso"),
    "read_json": ("subagent.kernel.util", "read_json"),
    "read_jsonl": ("subagent.kernel.util", "read_jsonl"),
    "relatedness": ("subagent.kernel.textutil", "relatedness"),
    "sha256_json": ("subagent.kernel.util", "sha256_json"),
    "split_explicit_lines": ("subagent.kernel.textutil", "split_explicit_lines"),
    "visible_chars": ("subagent.kernel.textutil", "visible_chars"),
    "wrap_words": ("subagent.kernel.textutil", "wrap_words"),
    "write_jsonl": ("subagent.kernel.util", "write_jsonl"),
}

__all__ = ["AUDIT_ASPECTS", "AuditMark", "AuditSample", "BudgetExceeded", "CastBoxEdit", "CastDetection", "CastLine", "ChangeRecord", "ConfigError", "CostRecord", "EditRecord", "Episode", "EpisodeLockedError", "EpisodeNotFoundError", "EpisodeState", "EpisodeStatus", "Evaluation", "FileLock", "JobRunningError", "LLMCallError", "LLMOutputError", "LineTranslation", "LineType", "MediaError", "MemoryLockedError", "MemoryProposal", "MissingBinaryError", "ModelUnavailableError", "NULL_PROGRESS", "NewVoice", "OcrBox", "OcrReading", "OutputExistsError", "OutputFolderError", "PartialSuggestion", "PinyinLine", "Progress", "ReviewIncompleteError", "ReviewedLine", "ScriptDecision", "SourceMissingError", "SpeakerCandidates", "StageState", "SubagentError", "SubtitleEvent", "VideoInfo", "Window", "append_jsonl", "atomic_write_json", "atomic_write_text", "balanced_wrap", "chunked", "contains_term", "edit_distance", "found_terms", "hash_path", "is_han", "keep_cjk", "lock_holder", "normalize_zh", "now_iso", "read_json", "read_jsonl", "relatedness", "sha256_json", "split_explicit_lines", "visible_chars", "wrap_words", "write_jsonl"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
