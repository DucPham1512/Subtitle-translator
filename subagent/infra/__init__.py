"""Infrastructure: ffmpeg / ffprobe media helpers, device selection, job locks."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from subagent.infra.device import describe, onnx_use_cuda, torch_device
    from subagent.infra.joblock import job_lock, job_lock_path, running_jobs
    from subagent.infra.media import (
        INSTALL_HINTS,
        available_encoders,
        extract_clip,
        extract_frame,
        git,
        has_video_stream,
        imread,
        imwrite_png,
        iter_gray_frames,
        missing_binaries,
        probe,
        require_binary,
        run,
    )

# public name -> (module, attribute); the submodule is imported the first time the name is used
_EXPORTS = {
    "INSTALL_HINTS": ("subagent.infra.media", "INSTALL_HINTS"),
    "available_encoders": ("subagent.infra.media", "available_encoders"),
    "describe": ("subagent.infra.device", "describe"),
    "extract_clip": ("subagent.infra.media", "extract_clip"),
    "extract_frame": ("subagent.infra.media", "extract_frame"),
    "git": ("subagent.infra.media", "git"),
    "has_video_stream": ("subagent.infra.media", "has_video_stream"),
    "imread": ("subagent.infra.media", "imread"),
    "imwrite_png": ("subagent.infra.media", "imwrite_png"),
    "iter_gray_frames": ("subagent.infra.media", "iter_gray_frames"),
    "job_lock": ("subagent.infra.joblock", "job_lock"),
    "job_lock_path": ("subagent.infra.joblock", "job_lock_path"),
    "missing_binaries": ("subagent.infra.media", "missing_binaries"),
    "onnx_use_cuda": ("subagent.infra.device", "onnx_use_cuda"),
    "probe": ("subagent.infra.media", "probe"),
    "require_binary": ("subagent.infra.media", "require_binary"),
    "run": ("subagent.infra.media", "run"),
    "running_jobs": ("subagent.infra.joblock", "running_jobs"),
    "torch_device": ("subagent.infra.device", "torch_device"),
}

__all__ = ["INSTALL_HINTS", "available_encoders", "describe", "extract_clip", "extract_frame", "git", "has_video_stream", "imread", "imwrite_png", "iter_gray_frames", "job_lock", "job_lock_path", "missing_binaries", "onnx_use_cuda", "probe", "require_binary", "run", "running_jobs", "torch_device"]


def __getattr__(name: str) -> object:
    try:
        module, attr = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(importlib.import_module(module), attr)
    globals()[name] = value
    return value
