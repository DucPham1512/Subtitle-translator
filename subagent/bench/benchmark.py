"""Speaker benchmark (6.11b): score the current system against the audited answers, with no new hand checking.

Audited lines with a speaker verdict are the reference ("gold"): a ✓ line's speaker as it was when marked, a ✗
line's correct speaker as the auditor picked it. A benchmark run copies each audited episode's corrected
Chinese text (events.jsonl) into a sandbox under `<work>/_benchmark/<run>/`, re-runs audio, voice match, cast,
scene windows and translation there with today's code and memory (memory is only read; nothing is learned and
nothing is rendered), and compares the speakers it now chooses with the gold. OCR is held fixed, so the score
moves only with speaker decisions. Each run is appended to `_benchmark/history.jsonl` for comparison.

Caveat: memory already learned from the audited episodes when they were processed, so absolute scores may be
optimistic; compare runs with each other.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from subagent.bench.audit import auditable_lines, gold_speakers, is_flagged, load_sample, stratified, wilson
from subagent.kernel import LineTranslation, append_jsonl, atomic_write_text, now_iso, read_jsonl
from subagent.settings import Config, Paths

log = logging.getLogger(__name__)
COPY = ("events.jsonl", "video.json")
STAGES = ("audio", "voice", "cast", "windows", "translate")


@dataclass
class EpisodeScore:
    episode_id: str
    gold: int = 0
    right: int = 0
    before_right: int = 0          # the episode's own output when it was audited
    changed: list[dict] = field(default_factory=list)   # lines whose speaker differs from the audited output


@dataclass
class BenchmarkResult:
    label: str
    started_at: str
    folder: str
    speaker: dict = field(default_factory=dict)          # stratified estimate over all lines (random sample)
    speaker_before: dict = field(default_factory=dict)
    disagreement: dict = field(default_factory=dict)
    episodes: list[EpisodeScore] = field(default_factory=list)
    cost: float = 0.0


def benchmark_episodes(paths: Paths) -> list[str]:
    from subagent.workspace import Registry

    return [e.id for e in sorted(Registry(paths).load(), key=lambda e: e.number)
            if gold_speakers(paths.episode_dir(e.id))]


def _sandbox_paths(config: Config, paths: Paths, folder: Path) -> tuple[Config, Paths]:
    cfg = config.model_copy(deep=True)
    cfg.paths.work_dir = str(folder)
    sandbox = Paths(paths.root, cfg)
    if not sandbox.work.resolve().is_relative_to(folder.resolve()):
        raise RuntimeError(f"benchmark sandbox escaped its folder: {sandbox.work}")
    return cfg, sandbox


def _copy_reviewer_context(paths: Paths, sandbox: Paths, skip: set[str]) -> None:
    """The translator's prompt includes recent reviewer corrections read from other episodes' edits: copy those
    small files so the sandboxed prompt matches a real run."""
    from subagent.workspace import Registry

    for ep in Registry(paths).load():
        if ep.id in skip:
            continue
        src, dst = paths.episode_dir(ep.id), sandbox.episode_dir(ep.id)
        for name in ("approved.jsonl", "edits.jsonl"):
            if (src / name).is_file():
                dst.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src / name, dst / name)


def run_benchmark(config: Config, paths: Paths, episode_ids: list[str] | None = None, *, label: str = "",
                  use_cache: bool = True, progress=None, stage_runner=None) -> BenchmarkResult:
    """stage_runner(name, ctx) runs one stage (tests inject fakes); default: the real stage modules."""
    from subagent.pipeline import collect_metrics, run_stage
    from subagent.workspace import EpisodeContext, Registry

    episode_ids = episode_ids or benchmark_episodes(paths)
    stamp = now_iso().replace(":", "").replace("-", "")[:15]
    folder = paths.work / "_benchmark" / f"{stamp}-{label or 'run'}"
    cfg, sandbox = _sandbox_paths(config, paths, folder)
    registry = Registry(paths)
    _copy_reviewer_context(paths, sandbox, set(episode_ids))
    run = stage_runner or run_stage
    result = BenchmarkResult(label=label, started_at=now_iso(), folder=str(folder))
    cells, before_cells = [], []
    dis = [0, 0]
    for n, ep_id in enumerate(episode_ids, 1):
        src = paths.episode_dir(ep_id)
        gold = gold_speakers(src)
        if not gold:
            continue
        work = sandbox.episode_dir(ep_id)
        work.mkdir(parents=True, exist_ok=True)
        for name in COPY:
            if (src / name).is_file():
                shutil.copy2(src / name, work / name)
        ctx = EpisodeContext(cfg, sandbox, registry.get(ep_id), use_cache=use_cache)
        for stage in STAGES:
            if progress:
                progress.emit("benchmark", "progress", done=n - 1, total=len(episode_ids), message=f"{ep_id}: {stage}")
            run(stage, ctx)
        result.cost += collect_metrics(work, ep_id, cfg.llm.prices)["cost_total"]
        predicted = {t.event_id: t.speaker for t in read_jsonl(work / "translations.jsonl", LineTranslation)}
        audited = {x.event_id: x for x in auditable_lines(src)}
        sample = {s.event_id: s for s in load_sample(src)}
        score = EpisodeScore(ep_id)
        lines = list(audited.values())
        ignore = config.audit.ignore_flags
        sizes = {True: sum(is_flagged(x, ignore) for x in lines), False: sum(not is_flagged(x, ignore) for x in lines)}
        per = {True: [0, 0, 0], False: [0, 0, 0]}          # [checked, wrong now, wrong before]
        for e, g in gold.items():
            now_ok = predicted.get(e) == g
            before_ok = audited[e].speaker == g if e in audited else False
            score.gold += 1
            score.right += now_ok
            score.before_right += before_ok
            if predicted.get(e) != (audited[e].speaker if e in audited else None):
                score.changed.append({"event_id": e, "before": audited[e].speaker if e in audited else None,
                                      "now": predicted.get(e), "gold": g})
            s = sample.get(e)
            if s is not None and s.kind == "random":
                per[s.flagged][0] += 1
                per[s.flagged][1] += not now_ok
                per[s.flagged][2] += not before_ok
            elif s is not None:
                dis[0] += not now_ok
                dis[1] += 1
        for f in (True, False):
            cells.append((sizes[f], per[f][0], per[f][1]))
            before_cells.append((sizes[f], per[f][0], per[f][2]))
        result.episodes.append(score)
    result.speaker = asdict(stratified(cells))
    result.speaker_before = asdict(stratified(before_cells))
    result.disagreement = asdict(wilson(*dis))
    folder.mkdir(parents=True, exist_ok=True)
    atomic_write_text(folder / "report.md", render(result))
    atomic_write_text(folder / "summary.json", json.dumps(asdict(result), ensure_ascii=False, indent=1))
    append_jsonl(paths.work / "_benchmark" / "history.jsonl", {
        "label": label, "at": result.started_at, "folder": str(folder), "cost": round(result.cost, 4),
        "speaker_accuracy": round(1 - result.speaker["errors"], 4) if result.speaker["checked"] else None,
        "speaker_accuracy_before": round(1 - result.speaker_before["errors"], 4)
        if result.speaker_before["checked"] else None,
        "episodes": [e.episode_id for e in result.episodes]})
    _drop_heavy_files(folder)
    return result


def _drop_heavy_files(folder: Path) -> None:
    """Keep the sandbox small: the scores need only the small text artifacts."""
    for pattern in ("*/audio.wav", "*/cast_frames", "*/cast_embeddings.npy"):
        for p in folder.glob(pattern):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)


def _acc(r: dict) -> str:
    if not r or not r.get("checked"):
        return "n/a"
    return (f"{(1 - r['errors']) * 100:.0f}% (95%: {(1 - r['high']) * 100:.0f}–{(1 - r['low']) * 100:.0f}%, "
            f"{r['checked']} lines)")


def render(r: BenchmarkResult) -> str:
    out = [f"# Speaker benchmark{': ' + r.label if r.label else ''}", "", f"Run: {r.started_at} · cost ${r.cost:.4f}", "",
           f"- Speaker accuracy now: {_acc(r.speaker)}",
           f"- Speaker accuracy of the audited output: {_acc(r.speaker_before)}",
           f"- Lines where signals disagreed, correct now: {_acc(r.disagreement)}", "",
           "Memory already learned from these episodes, so compare runs with each other rather than trusting the "
           "absolute number.", "", "| episode | gold lines | right now | right before | changed |", "|---|---|---|---|---|"]
    for e in r.episodes:
        out.append(f"| {e.episode_id} | {e.gold} | {e.right} | {e.before_right} | {len(e.changed)} |")
    changed = [c | {"episode": e.episode_id} for e in r.episodes for c in e.changed]
    if changed:
        out += ["", "## Lines whose speaker changed", "", "| line | before | now | gold |", "|---|---|---|---|"]
        for c in changed:
            mark = "✓" if c["now"] == c["gold"] else "✗"
            out.append(f"| {c['event_id']} | {c['before'] or '—'} | {c['now'] or '—'} {mark} | {c['gold']} |")
    return "\n".join(out) + "\n"
