"""Pipeline errors with stable codes; the app maps codes to translated messages (6.10)."""

from __future__ import annotations


class SubagentError(Exception):
    code = "error"

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        if code:
            self.code = code


class ConfigError(SubagentError):
    code = "config_invalid"


class MissingBinaryError(SubagentError):
    code = "missing_binary"


class MediaError(SubagentError):
    code = "media_error"


class SourceMissingError(SubagentError):
    code = "source_missing"


class EpisodeNotFoundError(SubagentError):
    code = "episode_not_found"


class EpisodeLockedError(SubagentError):
    code = "episode_locked"


class LLMOutputError(SubagentError):
    code = "llm_output_invalid"


class LLMCallError(SubagentError):
    code = "llm_call_failed"


class BudgetExceeded(SubagentError):
    code = "budget_exceeded"


class ReviewIncompleteError(SubagentError):
    code = "review_incomplete"


class OutputFolderError(SubagentError):
    code = "output_folder_invalid"


class OutputExistsError(SubagentError):
    code = "output_exists"


class MemoryLockedError(SubagentError):
    code = "memory_locked"


class JobRunningError(SubagentError):
    code = "job_running"


class StageError(SubagentError):
    code = "stage_failed"


class ModelUnavailableError(SubagentError):
    code = "model_unavailable"
