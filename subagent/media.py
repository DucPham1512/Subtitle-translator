"""ffmpeg / ffprobe / git helpers. Always argument lists, never shell=True (NFR-PT1)."""

from __future__ import annotations

import functools
import json
import logging
import shutil
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from subagent.errors import MediaError, MissingBinaryError
from subagent.models import VideoInfo

log = logging.getLogger(__name__)

INSTALL_HINTS = {
    "ffmpeg": "Install ffmpeg and add it to PATH (Windows: `winget install Gyan.FFmpeg`, then open a new terminal).",
    "ffprobe": "ffprobe ships with ffmpeg (Windows: `winget install Gyan.FFmpeg`).",
    "git": "Install Git for Windows: `winget install Git.Git`.",
}

# Hide console windows for child processes on Windows (the app runs jobs in the background).
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def which(name: str) -> str | None:
    return shutil.which(name)


def require_binary(name: str) -> str:
    path = which(name)
    if path is None:
        raise MissingBinaryError(f"'{name}' was not found on PATH. {INSTALL_HINTS.get(name, '')}".strip())
    return path


def missing_binaries(names: tuple[str, ...] = ("ffmpeg", "ffprobe", "git")) -> list[str]:
    return [n for n in names if which(n) is None]


def run(args: list[str], *, cwd: Path | None = None, check: bool = True, capture: bool = True,
        input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    log.debug("run: %s (cwd=%s)", args, cwd)
    try:
        proc = subprocess.run(
            args, cwd=cwd, input=input_bytes, capture_output=capture, check=False, creationflags=_NO_WINDOW,
        )
    except FileNotFoundError as exc:
        raise MissingBinaryError(f"'{args[0]}' could not be started. {INSTALL_HINTS.get(Path(args[0]).stem, '')}") from exc
    if check and proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace")[-2000:] if proc.stderr else ""
        raise MediaError(f"{Path(args[0]).name} failed (exit {proc.returncode}): {err.strip()}")
    return proc


def probe(path: Path) -> VideoInfo:
    ffprobe = require_binary("ffprobe")
    proc = run([ffprobe, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)])
    data = json.loads(proc.stdout.decode("utf-8", "replace") or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if video is None:
        raise MediaError(f"No video stream in {path.name}", code="no_video_stream")
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(data.get("format", {}).get("duration") or video.get("duration") or 0.0)
    fps = _parse_rate(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1")
    width, height = int(video["width"]), int(video["height"])
    rotation = _rotation(video)
    if rotation in (90, 270):
        width, height = height, width
    return VideoInfo(
        width=width, height=height, duration_ms=int(round(duration * 1000)), fps=fps,
        has_audio=audio is not None, audio_codec=audio.get("codec_name") if audio else None,
        video_codec=video.get("codec_name"),
    )


def has_video_stream(path: Path) -> tuple[bool, str]:
    try:
        probe(path)
        return True, ""
    except MediaError as exc:
        return False, str(exc)


def _parse_rate(rate: str) -> float:
    try:
        num, _, den = rate.partition("/")
        return float(num) / float(den or 1) if float(den or 1) else 0.0
    except ValueError:
        return 0.0


def _rotation(stream: dict) -> int:
    for sd in stream.get("side_data_list", []) or []:
        if "rotation" in sd:
            return abs(int(sd["rotation"])) % 360
    tag = (stream.get("tags") or {}).get("rotate")
    return abs(int(tag)) % 360 if tag else 0


def iter_gray_frames(path: Path, *, fps: float, crop: tuple[int, int, int, int]) -> Iterator[np.ndarray]:
    """Decode the cropped band at `fps` as raw gray frames piped into NumPy (nothing written to disk)."""
    ffmpeg = require_binary("ffmpeg")
    x, y, w, h = crop
    args = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path),
        "-vf", f"fps={fps},crop={w}:{h}:{x}:{y}", "-pix_fmt", "gray", "-f", "rawvideo", "-",
    ]
    frame_bytes = w * h
    proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=_NO_WINDOW)
    try:
        assert proc.stdout is not None
        while True:
            buf = proc.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            yield np.frombuffer(buf, dtype=np.uint8).reshape(h, w)
    finally:
        if proc.stdout:
            proc.stdout.close()
        stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        code = proc.wait()
        if proc.stderr:
            proc.stderr.close()
    if code != 0:
        raise MediaError(f"ffmpeg failed while decoding {path.name}: {stderr.strip()[-1500:]}")


def extract_frame(path: Path, t_ms: int, *, gray: bool = False, size: tuple[int, int] | None = None) -> np.ndarray:
    """One full frame at t_ms (`ffmpeg -ss <t> -frames:v 1`) as a NumPy array (BGR or gray)."""
    ffmpeg = require_binary("ffmpeg")
    if size is None:
        info = probe(path)
        size = (info.width, info.height)
    info_w, info_h = size
    pix = "gray" if gray else "bgr24"
    args = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-ss", f"{t_ms / 1000:.3f}", "-i", str(path),
        "-frames:v", "1", "-pix_fmt", pix, "-f", "rawvideo", "-",
    ]
    proc = run(args)
    channels = 1 if gray else 3
    expected = info_w * info_h * channels
    data = proc.stdout
    if len(data) < expected:
        raise MediaError(f"Could not read a frame at {t_ms} ms from {path.name}")
    arr = np.frombuffer(data[:expected], dtype=np.uint8)
    return arr.reshape(info_h, info_w) if gray else arr.reshape(info_h, info_w, 3)


def extract_clip(path: Path, start_ms: int, end_ms: int, out: Path, *, sample_rate: int = 16000) -> Path:
    """A short mono WAV of the audio between start_ms and end_ms (a voice sample to play)."""
    ffmpeg = require_binary("ffmpeg")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".tmp.wav")
    run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-ss", f"{start_ms / 1000:.3f}",
         "-t", f"{max(1, end_ms - start_ms) / 1000:.3f}", "-i", str(path), "-vn", "-ac", "1",
         "-ar", str(sample_rate), str(tmp)])
    tmp.replace(out)
    return out


@functools.lru_cache(maxsize=1)
def available_encoders() -> frozenset[str]:
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        return frozenset()
    proc = run([ffmpeg, "-hide_banner", "-encoders"], check=False)
    names = set()
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        parts = line.split()
        if len(parts) >= 2 and len(parts[0]) == 6 and parts[0][0] in "VAS":
            names.add(parts[1])
    return frozenset(names)


def imwrite_png(path: Path, image: np.ndarray) -> None:
    """cv2.imwrite fails on non-ASCII Windows paths; encode in memory and write the bytes."""
    import cv2

    ok, buf = cv2.imencode(".png", image)
    if not ok:
        raise MediaError(f"Could not encode PNG for {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(buf.tobytes())


def imread(path: Path, *, gray: bool = False) -> np.ndarray:
    import cv2

    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_GRAYSCALE if gray else cv2.IMREAD_COLOR)
    if img is None:
        raise MediaError(f"Could not read image {path}")
    return img


def git(args: list[str], cwd: Path, *, check: bool = True) -> str:
    exe = require_binary("git")
    proc = run([exe, *args], cwd=cwd, check=False)
    out = proc.stdout.decode("utf-8", "replace")
    if check and proc.returncode != 0:
        raise MediaError(f"git {' '.join(args)} failed: {proc.stderr.decode('utf-8', 'replace').strip()}",
                         code="git_failed")
    return out
