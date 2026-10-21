"""Measurement (6.11-6.11e): audit, baseline, OCR / speaker benchmarks, the benchmark suite."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.bench import audit, suite
    from subagent.bench.audit import NO_ID_YET
    from subagent.bench.baseline import baseline_dir, complete, freeze, freeze_finished
    from subagent.bench.bench_run import run
    from subagent.bench.benchmark import benchmark_episodes, run_benchmark
    from subagent.bench.benchmark import render as render_benchmark
    from subagent.bench.ocr_benchmark import ocr_episodes, remap_key, run_ocr_benchmark
    from subagent.bench.ocr_benchmark import render as render_ocr_benchmark

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "NO_ID_YET": ("subagent.bench.audit", "NO_ID_YET"),
    "baseline_dir": ("subagent.bench.baseline", "baseline_dir"),
    "benchmark_episodes": ("subagent.bench.benchmark", "benchmark_episodes"),
    "complete": ("subagent.bench.baseline", "complete"),
    "freeze": ("subagent.bench.baseline", "freeze"),
    "freeze_finished": ("subagent.bench.baseline", "freeze_finished"),
    "ocr_episodes": ("subagent.bench.ocr_benchmark", "ocr_episodes"),
    "remap_key": ("subagent.bench.ocr_benchmark", "remap_key"),
    "render_benchmark": ("subagent.bench.benchmark", "render"),
    "render_ocr_benchmark": ("subagent.bench.ocr_benchmark", "render"),
    "run": ("subagent.bench.bench_run", "run"),
    "run_benchmark": ("subagent.bench.benchmark", "run_benchmark"),
    "run_ocr_benchmark": ("subagent.bench.ocr_benchmark", "run_ocr_benchmark"),
}

__all__ = ["NO_ID_YET", "audit", "baseline_dir", "benchmark_episodes", "complete", "freeze", "freeze_finished", "ocr_episodes", "remap_key", "render_benchmark", "render_ocr_benchmark", "run", "run_benchmark", "run_ocr_benchmark", "suite"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
