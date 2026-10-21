"""Baseline freeze: a fixed copy of each finished review for benchmarks built on it.

While `baseline.name` is set, every finished review is copied to `<work>/_baseline/<name>/<episode>/`: the gold
(approved script, edits, OCR events), the machine output it was reviewed from, and in `manifest.json` the code and
memory versions it came from (`memory_at_run`: the memory the machine output was made with). Later reruns rewrite
the episode folders; the frozen copy stays. Finishing an episode again replaces its copy. `python -m subagent baseline
freeze NAME [EPISODE...]` copies finished episodes by hand; `baseline complete NAME` adds files a baseline frozen
by older code lacks, from work folders that still hold the same review, and the current OCR answer key.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from subagent.kernel.util import atomic_write_text, hash_path, now_iso, sha256_json
from subagent.settings.config import Config, Paths
from subagent.workspace.context import EpisodeContext
from subagent.workspace.state import load_state

log = logging.getLogger(__name__)
FOLDER = "_baseline"
FILES = ("approved.jsonl", "edits.jsonl", "events.jsonl", "events_raw.jsonl", "ocr_raw.jsonl", "translations.jsonl",
         "evaluations.jsonl", "speakers.jsonl", "new_voices.json", "cast.jsonl", "script_review.jsonl",
         "pinyin.jsonl", "video.json", "state.json",
         # needed to learn from the episode again in a sandbox (bench chain mode) and to check a replay's prompt
         "voice_embeddings.npz", "cast_embeddings.npy", "memory_prefix.md", "windows.json")
GOLD = ("approved.jsonl", "edits.jsonl")     # `complete` copies only while the work folder still holds this review
KEY_FILE = "answer_key.json"


def baseline_dir(paths: Paths, name: str) -> Path:
    return paths.work / FOLDER / name


def _git_head(folder: Path) -> str | None:
    from subagent.infra.media import git

    if not (folder / ".git").exists():
        return None
    return git(["rev-parse", "HEAD"], folder, check=False).strip() or None


def memory_at_run(paths: Paths, work: Path, episode_id: str) -> str | None:
    """The memory commit the episode's machine output was made with: the newest memory commit made before its
    first memory-reading stage started (an earlier episode finished again later does not count)."""
    from subagent.infra.media import git
    from subagent.pipeline import RERUN_FROM

    st = load_state(work, episode_id).stages.get(RERUN_FROM)
    if st is None or not st.started_at or not (paths.memory / ".git").exists():
        return None
    started = datetime.fromisoformat(st.started_at)
    for row in git(["log", "--format=%H %cI"], paths.memory, check=False).splitlines():
        sha, when = row.split()
        if datetime.fromisoformat(when) <= started:
            return sha
    return None


def _manifest(folder: Path, name: str) -> dict:
    path = folder / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"name": name, "episodes": {}}


def _save_manifest(folder: Path, manifest: dict) -> None:
    manifest["episodes"] = dict(sorted(manifest["episodes"].items()))
    atomic_write_text(folder / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))


def freeze_finished(ctx: EpisodeContext) -> None:
    """Pipeline after-finish hook: with `baseline.name` set, copy the finished episode into that baseline."""
    name = ctx.config.baseline.name
    if not name:
        return
    try:
        freeze_episode(ctx.config, ctx.paths, ctx.episode.id, name)
        ctx.progress.emit("baseline", "done", message=f"{ctx.episode.id} copied to baseline {name}")
    except Exception as exc:  # noqa: BLE001 - the episode is finished; the copy can be made again
        log.warning("baseline copy of %s failed: %s", ctx.episode.id, exc)
        ctx.progress.emit("baseline", "info", message=f"baseline copy failed: {exc}", error_code="baseline_failed")


def freeze_episode(config: Config, paths: Paths, episode_id: str, name: str) -> Path:
    """Copy one finished episode into the baseline and record where it came from."""
    src = paths.episode_dir(episode_id)
    if not (src / "approved.jsonl").is_file():
        raise FileNotFoundError(f"{episode_id} has no finished review (approved.jsonl)")
    folder = baseline_dir(paths, name)
    dst = folder / episode_id
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    copied = []
    for f in FILES:
        if (src / f).is_file():
            shutil.copy2(src / f, dst / f)
            copied.append(f)
    manifest_path = folder / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else \
        {"name": name, "episodes": {}}
    manifest["episodes"][episode_id] = {
        "frozen_at": now_iso(), "files": copied, "code_commit": _git_head(paths.root),
        "memory_commit": _git_head(paths.memory), "config_hash": sha256_json(config.model_dump(mode="json"))}
    manifest["episodes"] = dict(sorted(manifest["episodes"].items()))
    atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=1))
    log.info("baseline %s: %s frozen (%d files)", name, episode_id, len(copied))
    return dst


def freeze(config: Config, paths: Paths, name: str, episode_ids: list[str] | None = None) -> list[str]:
    """Freeze the given episodes, or every finished one (status done, with a finished review)."""
    from subagent.workspace.episodes import Registry

    if episode_ids is None:
        episode_ids = [e.id for e in sorted(Registry(paths).load(), key=lambda e: e.number)
                       if e.status == "done" and (paths.episode_dir(e.id) / "approved.jsonl").is_file()]
    for ep in episode_ids:
        freeze_episode(config, paths, ep, name)
    return episode_ids


def complete(paths: Paths, name: str) -> dict[str, list[str]]:
    """Add what a baseline frozen by older code lacks: missing FILES (only from a work folder whose review is still
    the frozen one), `memory_at_run`, and the current OCR answer key. Frozen files are never replaced. Returns
    episode -> files added."""
    from subagent.ocr_benchmark import FOLDER as OCR_FOLDER

    folder = baseline_dir(paths, name)
    manifest = _manifest(folder, name)
    added: dict[str, list[str]] = {}
    for ep, entry in manifest["episodes"].items():
        src, dst = paths.episode_dir(ep), folder / ep
        same = all((src / f).is_file() and hash_path(src / f) == hash_path(dst / f) for f in GOLD if (dst / f).is_file())
        new = []
        if same:
            for f in FILES:
                if not (dst / f).exists() and (src / f).is_file():
                    shutil.copy2(src / f, dst / f)
                    new.append(f)
            if entry.get("memory_at_run") is None:
                entry["memory_at_run"] = memory_at_run(paths, src, ep)
        else:
            log.warning("baseline %s: %s was reviewed again since it was frozen; nothing added", name, ep)
        entry["files"] = sorted(set(entry.get("files", [])) | set(new))
        added[ep] = new
    key = paths.work / OCR_FOLDER / KEY_FILE
    if key.is_file() and not (folder / KEY_FILE).exists():
        shutil.copy2(key, folder / KEY_FILE)
        manifest["answer_key"] = {"copied_at": now_iso(), "from": str(key)}
    _save_manifest(folder, manifest)
    return added
