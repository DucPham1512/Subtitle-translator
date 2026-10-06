"""Re-run harness for the benchmark suite (6.11e): today's code on the baseline's episodes, in a sandbox.

`<work>/_suite/<timestamp>-<label>/` holds everything: `memory/` (a git clone of the memory folder), `work/` (the
sandbox's episode folders) and `out/<episode>/` (the machine files of this run, scored by subagent/suite.py).
Nothing real is written: not the memory, not the work folders, not the registry or the output folder.

Each episode starts from the baseline's frozen files: the stages before `from_stage` are copied (OCR held fixed by
default), the stages from it to the script review run with today's code. Then the episode folder is replaced by the
frozen review, so later episodes see the reviewer corrections exactly as in the replay.

- snapshot: each episode runs with the memory it was made with in the replay (`memory_at_run` in the manifest).
  For stage experiments (OCR, prompts, evaluator, recognition); episodes are independent.
- chain: memory starts at the first episode's (the bootstrap) and learns from each frozen review in episode order
  (memory update, voice and sprite learning, as finishing a human review does), with today's code. For memory
  experiments; the run's own output is scored, the gold is learned from.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from subagent.config import Config, Paths
from subagent.util import now_iso

log = logging.getLogger(__name__)
MODES = ("snapshot", "chain")
NEEDS_RERUN = {"ocr": "ingest"}             # reads an output the baseline does not keep (the subtitle bands)
SCORED = ("events_raw.jsonl", "events.jsonl", "speakers.jsonl", "new_voices.json", "voice_embeddings.npz",
          "cast.jsonl", "cast_embeddings.npy", "pinyin.jsonl",
          "windows.json", "translations.jsonl", "evaluations.jsonl", "script_review.jsonl", "memory_prefix.md",
          "cost.jsonl", "video.json")
# files a stage writes beside its listed outputs (the pipeline's resume check does not need them, later stages do)
SIDE_OUTPUTS = {"ingest": ["changes.jsonl"], "voice": ["new_voices.json", "voice_embeddings.npz"]}
HEAVY = ("audio.wav", "cast_frames", "bands", "ocr_crops", "ocr_samples", "sprite_frames", "calibration")


def sandbox(config: Config, paths: Paths, folder: Path) -> tuple[Config, Paths]:
    cfg = config.model_copy(deep=True)
    cfg.paths.work_dir = str(folder / "work")
    cfg.baseline.name = None
    cfg.cleanup.auto = False
    sp = Paths(paths.root, cfg)
    sp.memory = folder / "memory"
    sp.memory_db = sp.memory / "memory.db"
    for p in (sp.work, sp.memory):
        if not p.resolve().is_relative_to(folder.resolve()):
            raise RuntimeError(f"bench sandbox escaped its folder: {p}")
    return cfg, sp


def checkout_memory(paths: Paths, sp: Paths, sha: str) -> None:
    """The sandbox memory at a commit of the real memory folder (cloned once; the real folder is only read)."""
    from subagent.media import git

    if not (sp.memory / ".git").exists():
        sp.memory.parent.mkdir(parents=True, exist_ok=True)
        git(["clone", "--quiet", "--no-checkout", str(paths.memory), str(sp.memory)], sp.memory.parent)
    git(["checkout", "--quiet", "--force", "--detach", sha], sp.memory)
    git(["clean", "-fdxq"], sp.memory)


def stage_plan(from_stage: str, mode: str) -> list[str]:
    """The stages that run, in pipeline order: from `from_stage` up to the script review (never the review gate)."""
    from subagent.errors import SubagentError
    from subagent.pipeline import STAGES

    names = [s.name for s in STAGES if s.name != "review"]
    if from_stage not in names:
        raise SubagentError(f"Unknown stage '{from_stage}'. Stages: {', '.join(names)}", code="unknown_stage")
    if from_stage in NEEDS_RERUN:
        raise SubagentError(f"{from_stage} reads files the baseline does not keep: start from "
                            f"{NEEDS_RERUN[from_stage]}", code="unknown_stage")
    plan = names[names.index(from_stage):]
    # voice reads the audio, which the baseline does not keep; chain mode learns voices from every episode's audio
    if ("voice" in plan or mode == "chain") and "audio" not in plan:
        plan.insert(0, "audio")
    return plan


def _frozen_inputs(src: Path, dst: Path, plan: list[str]) -> None:
    """Copy the frozen outputs of the stages that do not run."""
    from subagent.pipeline import STAGES

    keep = {"video.json"} if "ingest" not in plan else set()
    for s in STAGES:
        if s.name not in plan:
            keep.update(s.outputs + SIDE_OUTPUTS.get(s.name, []))
    for name in keep:
        if (src / name).is_file():
            shutil.copy2(src / name, dst / name)


def _install_review(src: Path, dst: Path) -> None:
    """Replace the episode's machine files by the frozen review and the files it was made from (the gold), so
    learning and the next episodes' reviewer-corrections block see what the replay saw."""
    from subagent.baseline import FILES
    from subagent.state import load_state, save_state

    for name in FILES:
        if (src / name).is_file():
            shutil.copy2(src / name, dst / name)
    state = load_state(dst, dst.name)
    for stage in ("memory", "sprites", "render"):          # learned again here, not "already done"
        state.stages.pop(stage, None)
    save_state(dst, state)


def _learn(cfg: Config, sp: Paths, ctx) -> float:
    """What finishing the review teaches memory (no validation, render or delivery). Returns its LLM cost."""
    from subagent.pipeline import Pipeline, collect_metrics

    before = collect_metrics(ctx.work, ctx.episode.id, cfg.llm.prices)["cost_total"]
    pipe = Pipeline(cfg, sp, use_cache=ctx.use_cache)
    pipe._memory_update(ctx)
    pipe._learn_voices()
    pipe._learn_sprites(ctx)
    return collect_metrics(ctx.work, ctx.episode.id, cfg.llm.prices)["cost_total"] - before


def run(config: Config, paths: Paths, gold_folder: Path, *, mode: str = "snapshot", from_stage: str | None = None,
        episodes: list[str] | None = None, label: str = "", use_cache: bool = True, progress=None,
        stage_runner=None, learner=None):
    """stage_runner(name, ctx) runs one stage and learner(cfg, sandbox_paths, ctx) -> cost learns from one frozen
    review (tests inject fakes); defaults: the real stage modules and the pipeline's finish learning."""
    from subagent import suite
    from subagent.context import EpisodeContext
    from subagent.episodes import Registry
    from subagent.errors import SubagentError
    from subagent.pipeline import _BY_NAME, RERUN_FROM, collect_metrics

    if mode not in MODES:
        raise SubagentError(f"Unknown mode '{mode}'. Modes: {', '.join(MODES)}", code="unknown_mode")
    from_stage = from_stage or RERUN_FROM
    plan = stage_plan(from_stage, mode)
    gold = suite.load_gold(gold_folder, episodes)
    every = suite.load_gold(gold_folder).episodes
    if not gold.episodes:
        raise SubagentError("no baseline episodes to run", code="no_episodes")
    stamp = now_iso().replace(":", "").replace("-", "")[:15]
    folder = paths.work / suite.FOLDER / f"{stamp}-{label or mode}"
    cfg, sp = sandbox(config, paths, folder)
    out = folder / "out"
    stage = stage_runner or (lambda name, ctx: _BY_NAME[name].run(ctx))
    learn = learner or _learn
    registry = Registry(paths)
    commits = {ep: gold.manifest["episodes"][ep].get("memory_at_run") for ep in every}
    if mode == "chain":
        checkout_memory(paths, sp, commits[every[0]])
    last = max(every.index(ep) for ep in gold.episodes)
    info = {"mode": mode, "from_stage": from_stage, "stages": plan, "label": label, "cost": 0.0, "learn_cost": 0.0,
            "prefix_same": [], "prefix_changed": []}
    for n, ep in enumerate(every[:last + 1], 1):
        src = gold_folder / ep
        ctx = EpisodeContext(cfg, sp, registry.get(ep), use_cache=use_cache, progress=progress or _null())
        work = ctx.work
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        if ep in gold.episodes:
            if mode == "snapshot":
                checkout_memory(paths, sp, commits[ep])
            _frozen_inputs(src, work, plan)
            for name in plan:
                if progress:
                    progress.emit("bench", "progress", done=n - 1, total=last + 1, message=f"{ep}: {name}")
                stage(name, ctx)
            dst = out / ep
            dst.mkdir(parents=True, exist_ok=True)
            for name in SCORED:
                if (work / name).is_file():
                    shutil.copy2(work / name, dst / name)
            info["cost"] += collect_metrics(work, ep, cfg.llm.prices)["cost_total"]
            if (src / "memory_prefix.md").is_file() and (dst / "memory_prefix.md").is_file():
                same = (src / "memory_prefix.md").read_bytes() == (dst / "memory_prefix.md").read_bytes()
                info["prefix_same" if same else "prefix_changed"].append(ep)
            (work / "cost.jsonl").unlink(missing_ok=True)
        _install_review(src, work)
        if mode == "chain" and n <= last:          # the last episode teaches nothing that is scored
            if progress:
                progress.emit("bench", "progress", done=n - 1, total=last + 1, message=f"{ep}: learning")
            info["learn_cost"] += learn(cfg, sp, ctx)
    info["cost"] = round(info["cost"] + info["learn_cost"], 4)
    info["learn_cost"] = round(info["learn_cost"], 4)
    result = suite.score(config, paths, gold, out, label=label or mode, run=info)
    suite.save(paths, result, folder)
    _drop_heavy(sp.work)
    return result


def _drop_heavy(work: Path) -> None:
    for name in HEAVY:
        for p in work.glob(f"*/{name}"):
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)


def _null():
    from subagent.progress import NULL_PROGRESS

    return NULL_PROGRESS
