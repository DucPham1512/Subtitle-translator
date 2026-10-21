"""Job locks: `work/<episode>/.lock` for episode jobs, `work/_jobs/<name>.lock` for bootstrap / dream."""

from __future__ import annotations

import os
from pathlib import Path

from subagent.config import Paths
from subagent.kernel.errors import EpisodeLockedError
from subagent.kernel.util import FileLock, lock_holder

GLOBAL_JOBS = "_jobs"


def job_lock_path(paths: Paths, name: str) -> Path:
    if name.startswith("ep"):
        return paths.episode_dir(name) / ".lock"
    return paths.work / GLOBAL_JOBS / f"{name}.lock"


def job_lock(paths: Paths, name: str) -> FileLock:
    return FileLock(job_lock_path(paths, name), error=EpisodeLockedError,
                    message=f"Another job is already running for {name}")


def running_jobs(paths: Paths, *, exclude_self: bool = True) -> list[str]:
    """Names of jobs whose lock is held by a live process."""
    if not paths.work.is_dir():
        return []
    candidates = list(paths.work.glob("*/.lock")) + list((paths.work / GLOBAL_JOBS).glob("*.lock"))
    names = []
    for lock in candidates:
        holder = lock_holder(lock)
        if holder is None or (exclude_self and holder == os.getpid()):
            continue
        names.append(lock.parent.name if lock.name == ".lock" else lock.stem)
    return sorted(names)
