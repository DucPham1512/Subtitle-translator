"""Pipeline: the stage table, the runner that executes it with resume (NFR-R1), and the episode report (5.20)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.pipeline.report import AGENT_NAMES, collect_metrics, episode_status, write_report
    from subagent.pipeline.runner import BatchItem, Pipeline, Runner, prompt_hash
    from subagent.pipeline.stages import RERUN_FROM, STAGE_BY_NAME, STAGE_NAMES, STAGES, StageDef, run_stage

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "AGENT_NAMES": ("subagent.pipeline.report", "AGENT_NAMES"),
    "BatchItem": ("subagent.pipeline.runner", "BatchItem"),
    "Pipeline": ("subagent.pipeline.runner", "Pipeline"),
    "RERUN_FROM": ("subagent.pipeline.stages", "RERUN_FROM"),
    "Runner": ("subagent.pipeline.runner", "Runner"),
    "STAGES": ("subagent.pipeline.stages", "STAGES"),
    "STAGE_BY_NAME": ("subagent.pipeline.stages", "STAGE_BY_NAME"),
    "STAGE_NAMES": ("subagent.pipeline.stages", "STAGE_NAMES"),
    "StageDef": ("subagent.pipeline.stages", "StageDef"),
    "collect_metrics": ("subagent.pipeline.report", "collect_metrics"),
    "episode_status": ("subagent.pipeline.report", "episode_status"),
    "prompt_hash": ("subagent.pipeline.runner", "prompt_hash"),
    "run_stage": ("subagent.pipeline.stages", "run_stage"),
    "write_report": ("subagent.pipeline.report", "write_report"),
}

__all__ = ["AGENT_NAMES", "BatchItem", "Pipeline", "RERUN_FROM", "Runner", "STAGES", "STAGE_BY_NAME", "STAGE_NAMES", "StageDef", "collect_metrics", "episode_status", "prompt_hash", "run_stage", "write_report"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
