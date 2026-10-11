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

import json
import logging
import shutil
from pathlib import Path

from subagent.config import Config, Paths
from subagent.util import atomic_write_text, now_iso

log = logging.getLogger(__name__)
MODES = ("snapshot", "chain")
STATE = "run.json"                          # the run's settings and progress, for --resume
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
        stage_runner=None, learner=None, resume: Path | None = None):
    """stage_runner(name, ctx) runs one stage and learner(cfg, sandbox_paths, ctx) -> cost learns from one frozen
    review (tests inject fakes); defaults: the real stage modules and the pipeline's finish learning.

    `resume`: a run folder stopped before the end. Its settings (run.json) replace the arguments; the episodes it
    finished are skipped, the one it was in is done again from the start, and in chain mode the memory goes back
    to the commit after the last finished episode."""
    from subagent import suite
    from subagent.baseline import _git_head
    from subagent.context import EpisodeContext
    from subagent.episodes import Registry
    from subagent.errors import SubagentError
    from subagent.pipeline import _BY_NAME

    state, folder = _start_or_resume(paths, mode, from_stage, episodes, label, use_cache, resume)
    mode, from_stage, episodes, label = state["mode"], state["from_stage"], state["episodes"], state["label"]
    use_cache = state.get("use_cache", use_cache)
    plan = stage_plan(from_stage, mode)
    gold = suite.load_gold(gold_folder, episodes)
    every = suite.load_gold(gold_folder).episodes
    if not gold.episodes:
        raise SubagentError("no baseline episodes to run", code="no_episodes")
    cfg, sp = sandbox(config, paths, folder)
    folder.mkdir(parents=True, exist_ok=True)
    _save_state(folder, state)
    out = folder / "out"
    stage = stage_runner or (lambda name, ctx: _BY_NAME[name].run(ctx))
    learn = learner or _learn
    registry = Registry(paths)
    commits = {ep: gold.manifest["episodes"][ep].get("memory_at_run") for ep in every}
    last = max(every.index(ep) for ep in gold.episodes)
    if mode == "chain":
        finished = [ep for ep in every if ep in state["done"]]
        sha = state["memory"].get(finished[-1]) if finished else commits[every[0]]
        if sha is None:
            raise SubagentError(f"chain run {folder.name}: no memory recorded after {finished[-1]}", code="no_run")
        checkout_memory(paths, sp, sha)
    for n, ep in enumerate(every[:last + 1], 1):
        if ep in state["done"]:
            continue
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
            report = (lambda msg, n=n: progress.emit("bench", "progress", done=n - 1, total=last + 1,
                                                     message=msg)) if progress else None
            _rerun_episode(ctx, plan, stage, out / ep, report)
        _install_review(src, work)
        if mode == "chain" and n <= last:          # the last episode teaches nothing that is scored
            if progress:
                progress.emit("bench", "progress", done=n - 1, total=last + 1, message=f"{ep}: learning")
            learn(cfg, sp, ctx)
            state["memory"][ep] = _git_head(sp.memory)
        state["done"].append(ep)
        _save_state(folder, state)
    info = _run_info(cfg, gold, gold_folder, sp, out, state, plan)
    result = suite.score(config, paths, gold, out, label=label or mode, run=info)
    suite.save(paths, result, folder)
    _drop_heavy(sp.work)
    return result


def _start_or_resume(paths: Paths, mode: str, from_stage: str | None, episodes: list[str] | None, label: str,
                     use_cache: bool, resume: Path | None) -> tuple[dict, Path]:
    """(run state, run folder): a new run's settings, or a stopped run's own (run.json)."""
    from subagent import suite
    from subagent.errors import SubagentError
    from subagent.pipeline import RERUN_FROM

    if resume is not None:
        if not (resume / STATE).is_file():
            raise SubagentError(f"not a benchmark run folder (no {STATE}): {resume}", code="no_run")
        return json.loads((resume / STATE).read_text(encoding="utf-8")), resume
    if mode not in MODES:
        raise SubagentError(f"Unknown mode '{mode}'. Modes: {', '.join(MODES)}", code="unknown_mode")
    from_stage = from_stage or RERUN_FROM
    stamp = now_iso().replace(":", "").replace("-", "")[:15]
    folder = paths.work / suite.FOLDER / f"{stamp}-{label or mode}"
    return {"mode": mode, "from_stage": from_stage, "episodes": episodes, "label": label,
            "use_cache": use_cache, "started_at": now_iso(), "done": [], "memory": {}}, folder


def _rerun_episode(ctx, plan: list[str], stage, dst: Path, report) -> None:
    """Run the plan's stages on one episode and keep its scored machine files in `dst`."""
    work = ctx.work
    for name in plan:
        if report:
            report(f"{ctx.episode.id}: {name}")
        stage(name, ctx)
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for name in SCORED:
        if (work / name).is_file():
            shutil.copy2(work / name, dst / name)
    (work / "cost.jsonl").unlink(missing_ok=True)       # kept in out/; what stays in work/ is learning cost


def _save_state(folder: Path, state: dict) -> None:
    atomic_write_text(folder / STATE, json.dumps(state, ensure_ascii=False, indent=1))


def _run_info(cfg: Config, gold, gold_folder: Path, sp: Paths, out: Path, state: dict, plan: list[str]) -> dict:
    """What the run did and cost, from its folders (the same whether it ran in one go or was resumed)."""
    from subagent.pipeline import collect_metrics

    prices = cfg.llm.prices
    cost = sum(collect_metrics(out / ep, ep, prices)["cost_total"] for ep in gold.episodes if (out / ep).is_dir())
    learn_cost = 0.0
    if state["mode"] == "chain":
        learn_cost = sum(collect_metrics(sp.episode_dir(ep), ep, prices)["cost_total"] for ep in state["done"]
                         if sp.episode_dir(ep).is_dir())
    same, changed = [], []
    for ep in gold.episodes:
        a, b = gold_folder / ep / "memory_prefix.md", out / ep / "memory_prefix.md"
        if a.is_file() and b.is_file():
            (same if a.read_bytes() == b.read_bytes() else changed).append(ep)
    return {"mode": state["mode"], "from_stage": state["from_stage"], "stages": plan, "label": state["label"],
            "cost": round(cost + learn_cost, 4), "learn_cost": round(learn_cost, 4), "prefix_same": same,
            "prefix_changed": changed, "started_at": state.get("started_at")}


def _drop_heavy(work: Path) -> None:
    for name in HEAVY:
        for p in work.glob(f"*/{name}"):
            shutil.rmtree(p, ignore_errors=True) if p.is_dir() else p.unlink(missing_ok=True)


def _null():
    from subagent.progress import NULL_PROGRESS

    return NULL_PROGRESS
