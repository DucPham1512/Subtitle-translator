"""Stage 5: audio extraction (5.7): mono 16 kHz WAV. Slicing happens in memory in voice match."""

from __future__ import annotations

import contextlib
import os
import wave

from subagent.infra import require_binary
from subagent.infra import run as run_cmd
from subagent.workspace import EpisodeContext


def write_silence(path: os.PathLike, sample_rate: int) -> None:
    with wave.open(os.fspath(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"")


def run(ctx: EpisodeContext) -> dict[str, int]:
    source = ctx.require_source()
    info = ctx.video_info()
    sr = ctx.config.audio.sample_rate
    out = ctx.artifact("audio.wav")
    tmp = ctx.artifact("audio.tmp.wav")
    try:
        if not info.has_audio:
            write_silence(tmp, sr)
        else:
            ffmpeg = require_binary("ffmpeg")
            run_cmd([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(source),
                     "-vn", "-ac", "1", "-ar", str(sr), "-c:a", "pcm_s16le", str(tmp)])
        os.replace(tmp, out)
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink()
    return {"has_audio": int(info.has_audio), "bytes": out.stat().st_size}
