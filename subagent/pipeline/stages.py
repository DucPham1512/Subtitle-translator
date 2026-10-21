"""The stage table: what each stage reads, writes and depends on (3.2); one stage run directly."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

from subagent.workspace.context import EpisodeContext
from subagent.workspace.state import load_state

log = logging.getLogger(__name__)


# -- stage table -----------------------------------------------------------------------------------

@dataclass
class StageDef:
    name: str
    run: Callable[[EpisodeContext], dict]
    upstream: list[str]
    config: list[str]
    outputs: list[str]
    prompts: list[str] = field(default_factory=list)
    llm_roles: list[str] = field(default_factory=list)
    extra: Callable[[EpisodeContext], object] | None = None
    identification: bool = False          # skipped while show.character_identification is off (5.11a)


def _source_key(ctx: EpisodeContext) -> object:
    return ctx.episode.source_fingerprint


def _style_key(ctx: EpisodeContext) -> object:
    """Segmentation reads the series' calibrated subtitle style (5.4a), so a new calibration re-runs OCR. Only the
    values segmentation uses count; recalibrating to the same values changes nothing."""
    if ctx.config.ocr.preprocess != "segment":
        return None
    from subagent.ocr.subtitle_style import load_style

    style = load_style(ctx.paths.bootstrap)
    return style.model_dump(exclude={"regions", "calibrated_from", "calibrated_at"}) if style else None


def _review_run(ctx: EpisodeContext) -> dict:
    from subagent.review.review import gate

    mode = load_state(ctx.work, ctx.episode.id).mode or ctx.config.review.mode
    result = gate(ctx.work, mode, ctx.config.review.predelete_fragments, ctx.config.review.noise_max_han)
    return {"approved": int(result == "approved")}


def _lazy(module: str) -> Callable[[EpisodeContext], dict]:
    """The `run` of a stage module, imported on first use (heavy models load only when a stage runs)."""
    def run(ctx: EpisodeContext) -> dict:
        import importlib

        return importlib.import_module(module).run(ctx)

    run.__name__ = f"run_{module.rsplit('.', 1)[-1]}"
    return run


STAGES: list[StageDef] = [
    StageDef("ingest", _lazy("subagent.ocr.ingest"), [], ["video"], ["bands", "changes.jsonl", "video.json"], extra=_source_key),
    StageDef("ocr", _lazy("subagent.ocr.ocr"), ["ingest"], ["ocr", "device"], ["ocr_raw.jsonl"], extra=_style_key),
    StageDef("events", _lazy("subagent.ocr.events"), ["ocr"], ["ocr", "non_dialogue"], ["events_raw.jsonl"]),
    StageDef("ocr_fix", _lazy("subagent.ocr.ocr_fix"), ["events"], ["ocr_fix"], ["events.jsonl"],
             prompts=["ocr_fix_system"], llm_roles=["utility"]),
    StageDef("audio", _lazy("subagent.voice.audio"), [], ["audio"], ["audio.wav"], extra=_source_key, identification=True),
    StageDef("voice", _lazy("subagent.voice.voice"), ["ocr_fix", "audio"], ["voice", "audio"], ["speakers.jsonl"],
             identification=True),
    StageDef("cast", _lazy("subagent.cast.cast"), ["ocr_fix"], ["cast", "video", "device"], ["cast.jsonl", "cast_embeddings.npy"],
             extra=_source_key, identification=True),
    StageDef("pinyin", _lazy("subagent.translation.pinyin_gen"), ["ocr_fix"], ["pinyin"], ["pinyin.jsonl"],
             prompts=["polyphone_system"], llm_roles=["utility"]),
    StageDef("windows", _lazy("subagent.translation.windows"), ["ocr_fix"], ["windows"], ["windows.json"]),
    StageDef("translate", _lazy("subagent.translation.translate"), ["ocr_fix", "voice", "cast", "windows"],
             ["translate", "evaluate", "show", "sprite"], ["translations.jsonl", "evaluations.jsonl"],
             prompts=["translator_system", "evaluator_system"], llm_roles=["translator", "evaluator"]),
    StageDef("sprite", _lazy("subagent.cast.sprite"), ["translate"], ["sprite"], ["translations.jsonl"], identification=True),
    StageDef("script_review", _lazy("subagent.translation.script_review"), ["translate", "sprite"], ["script_review"],
             ["script_review.jsonl"], prompts=["script_review_system"], llm_roles=["utility"]),
    StageDef("review", _review_run, ["pinyin", "sprite", "script_review"], ["review"], []),
]
STAGE_NAMES = [s.name for s in STAGES] + ["memory", "render", "report", "cleanup"]


def run_stage(name: str, ctx: EpisodeContext) -> dict:
    """One stage's `run(ctx)`, directly: no resume, state or progress (benchmarks)."""
    return next(s for s in STAGES if s.name == name).run(ctx)


STAGE_BY_NAME = {s.name: s for s in STAGES}


def review_outputs(mode: str) -> list[str]:
    return ["approved.jsonl", "edits.jsonl"] if mode == "auto" else ["review_draft.jsonl"]


RERUN_FROM = "ocr_fix"
