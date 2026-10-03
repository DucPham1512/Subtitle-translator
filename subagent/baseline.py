"""Baseline freeze: a fixed copy of each finished review for benchmarks built on it.

While `baseline.name` is set, every finished review is copied to `<work>/_baseline/<name>/<episode>/`: the gold
(approved script, edits, OCR events), the machine output it was reviewed from, and in `manifest.json` the code and
memory versions it came from. Later reruns rewrite the episode folders; the frozen copy stays. Finishing an episode
again replaces its copy. `python -m subagent baseline freeze NAME [EPISODE...]` copies finished episodes by hand.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from subagent.config import Config, Paths
from subagent.util import atomic_write_text, now_iso, sha256_json

log = logging.getLogger(__name__)
FOLDER = "_baseline"
FILES = ("approved.jsonl", "edits.jsonl", "events.jsonl", "events_raw.jsonl", "ocr_raw.jsonl", "translations.jsonl",
         "evaluations.jsonl", "speakers.jsonl", "new_voices.json", "cast.jsonl", "script_review.jsonl",
         "pinyin.jsonl", "video.json", "state.json")


def baseline_dir(paths: Paths, name: str) -> Path:
    return paths.work / FOLDER / name


def _git_head(folder: Path) -> str | None:
    from subagent.media import git

    if not (folder / ".git").exists():
        return None
    return git(["rev-parse", "HEAD"], folder, check=False).strip() or None


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
    from subagent.episodes import Registry

    if episode_ids is None:
        episode_ids = [e.id for e in sorted(Registry(paths).load(), key=lambda e: e.number)
                       if e.status == "done" and (paths.episode_dir(e.id) / "approved.jsonl").is_file()]
    for ep in episode_ids:
        freeze_episode(config, paths, ep, name)
    return episode_ids
