"""Output delivery (5.22) and cleanup of temporary files (5.23)."""

from __future__ import annotations

import contextlib
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from subagent.kernel.errors import OutputExistsError, OutputFolderError
from subagent.settings.config import Config
from subagent.workspace.state import load_state, save_state

log = logging.getLogger(__name__)

OnExists = Literal["overwrite", "keep_both", "fail"]

# Temporary files, and the stages whose outputs they are (marked `purged` in state.json).
TEMPORARY = {
    "bands": "ingest",
    "audio.wav": "audio",
    "preview.ass": None,
    "calibration": None,
    "render.tmp.mp4": None,
    "sprite_frames": None,
    "fonts": None,
    "cast_frames": None,
    "ocr_samples": None,
    "ocr_crops": None,
}
KEPT = ["events.jsonl", "speakers.jsonl", "new_voices.json", "pinyin.jsonl", "translations.jsonl",
        "evaluations.jsonl", "script_review.jsonl", "cast.jsonl", "cast_embeddings.npy", "partial_review.jsonl", "audit_sample.jsonl", "audit_marks.jsonl", "review_draft.jsonl", "approved.jsonl", "edits.jsonl",
        "output.ass", "report.md", "cost.jsonl", "run.log", "state.json", "video.json"]   # documentation only


def output_folder(config: Config) -> Path:
    """The configured output folder; it must be set, exist and be writable."""
    if not config.output.folder:
        raise OutputFolderError("No output folder is set. Choose one in Settings (output.folder) before rendering.")
    folder = Path(config.output.folder).expanduser()
    if not folder.is_dir():
        raise OutputFolderError(f"The output folder does not exist: {folder}")
    try:
        fd, probe = tempfile.mkstemp(dir=folder, prefix=".write-test-")
        os.close(fd)
        os.unlink(probe)
    except OSError as exc:
        raise OutputFolderError(f"The output folder is not writable: {folder} ({exc})") from exc
    return folder


def output_name(source: Path, suffix: str) -> str:
    return f"{source.stem}{suffix}.mp4"


def target_path(config: Config, source: Path) -> Path:
    return output_folder(config) / output_name(source, config.output.name_suffix)


def keep_both_path(path: Path) -> Path:
    n = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({n}){path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def resolve_conflict(path: Path, on_exists: OnExists) -> Path:
    if not path.exists():
        return path
    if on_exists == "overwrite":
        return path
    if on_exists == "keep_both":
        return keep_both_path(path)
    raise OutputExistsError(f"The output file already exists: {path}")


def _same_drive(a: Path, b: Path) -> bool:
    try:
        return os.stat(a).st_dev == os.stat(b).st_dev
    except OSError:
        return False


def deliver(tmp: Path, final: Path, on_exists: OnExists) -> Path:
    """Move the finished render into the output folder; a half-written file never gets the final name."""
    final = resolve_conflict(final, on_exists)   # checked again just before the move
    if _same_drive(tmp, final.parent):
        os.replace(tmp, final)
        return final
    partial = final.with_name(f".{final.name}.partial")
    try:
        shutil.copyfile(tmp, partial)
        os.replace(partial, final)
    except BaseException:
        with contextlib.suppress(OSError):
            partial.unlink()
        raise
    tmp.unlink()
    return final


def cleanup(work: Path, episode_id: str) -> list[str]:
    """Delete temporary files; mark their stages `purged` so resume logic knows it was on purpose."""
    removed = []
    purged_stages = []
    for name, stage in TEMPORARY.items():
        path = work / name
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.is_file():
            path.unlink()
        else:
            continue
        removed.append(name)
        if stage:
            purged_stages.append(stage)
    if purged_stages:
        state = load_state(work, episode_id)
        for stage in purged_stages:
            if stage in state.stages:
                state.stages[stage].status = "purged"
        state.purged = sorted(set(state.purged) | set(purged_stages))
        save_state(work, state)
    log.info("cleanup %s: removed %s", episode_id, ", ".join(removed) or "nothing")
    return removed


def reveal_in_explorer(path: Path) -> None:
    """Select the file in Explorer (Windows) or open its folder elsewhere."""
    import subprocess
    import sys

    if sys.platform == "win32":
        subprocess.Popen(["explorer", f"/select,{path}"])  # noqa: S603, S607
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(path)])  # noqa: S603, S607
    else:
        subprocess.Popen(["xdg-open", str(path.parent)])  # noqa: S603, S607
