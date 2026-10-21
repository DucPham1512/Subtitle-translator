"""Resolve the compute device for torch (voice) and ONNX Runtime (OCR). CPU always works (NFR-P1)."""

from __future__ import annotations

import contextlib
import ctypes
import functools
import io
import logging
import sys
from pathlib import Path

from subagent.settings.config import Config

log = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def torch_cuda_available() -> bool:
    try:
        import torch
    except ImportError:
        return False
    try:
        return bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001 - broken CUDA install falls back to CPU
        return False


@functools.lru_cache(maxsize=1)
def onnx_cuda_available() -> bool:
    """True only when the CUDA provider can really load (it is listed even when CUDA/cuDNN DLLs are missing)."""
    # PyTorch (voice) and ONNX Runtime (OCR) each ship their own cuDNN build. Whichever loads first owns the
    # cuDNN DLL names for the whole process; when ONNX Runtime's copy is first, `import torch` fails with
    # WinError 127 on cudnn_cnn64_9.dll. Loading torch first lets both work (OCR stays on the GPU).
    with contextlib.suppress(Exception):
        import torch  # noqa: F401
    try:
        import onnxruntime as ort
    except ImportError:
        return False
    if "CUDAExecutionProvider" not in ort.get_available_providers():
        return False
    if hasattr(ort, "preload_dlls"):   # CUDA / cuDNN from the nvidia-* pip packages, when installed
        # it prints failures to stdout, which must stay clean for --progress json
        with contextlib.suppress(Exception), contextlib.redirect_stdout(io.StringIO()):
            ort.preload_dlls()
    name = "onnxruntime_providers_cuda.dll" if sys.platform == "win32" else "libonnxruntime_providers_cuda.so"
    lib = Path(ort.__file__).parent / "capi" / name
    try:
        ctypes.CDLL(str(lib))
    except OSError as exc:
        log.info("ONNX Runtime CUDA provider unavailable (%s); OCR runs on the CPU", exc)
        return False
    return True


def torch_device(config: Config) -> str:
    if config.device == "cpu":
        return "cpu"
    if torch_cuda_available():
        return "cuda:0"   # SpeechBrain needs an explicit device index
    if config.device == "cuda":
        log.warning("device=cuda but torch has no CUDA support; using CPU")
    return "cpu"


def onnx_use_cuda(config: Config) -> bool:
    if config.device == "cpu":
        return False
    if onnx_cuda_available():
        return True
    if config.device == "cuda":
        log.warning("device=cuda but onnxruntime has no CUDA provider; using CPU")
    return False


def describe(config: Config) -> str:
    """Short label for the status bar: GPU when any accelerated path is active."""
    if config.device == "cpu":
        return "CPU"
    return "GPU" if (onnx_cuda_available() or torch_cuda_available()) else "CPU"
