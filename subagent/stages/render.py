"""Stage 14: ASS subtitles (pinyin + Vietnamese), mask and burn-in in one ffmpeg pass (5.19).

`build_ass` and `build_mask_filter` are the only places that define subtitle styling and masking; the
app's live preview uses them too, so the preview matches the final render.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from pathlib import Path

import pysubs2

from subagent.context import EpisodeContext
from subagent.kernel.errors import MediaError, SubagentError
from subagent.kernel.models import ReviewedLine
from subagent.kernel.textutil import balanced_wrap, split_explicit_lines, wrap_words
from subagent.kernel.util import read_jsonl
from subagent.media import available_encoders, require_binary
from subagent.settings.config import Config, Paths

log = logging.getLogger(__name__)

FONT_EXTS = {".ttf", ".otf", ".ttc"}
MP4_AUDIO = {"aac", "mp3", "opus"}
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


# -- ASS -------------------------------------------------------------------------------------------

def _color(value: str) -> pysubs2.Color:
    """'&HAABBGGRR' → pysubs2.Color (ASS alpha: 00 = opaque)."""
    v = value.strip().upper().removeprefix("&H").removesuffix("&").rjust(8, "0")
    a, b, g, r = (int(v[i:i + 2], 16) for i in (0, 2, 4, 6))
    return pysubs2.Color(r, g, b, a)


def _ass_text(text: str) -> str:
    """Neutralize ASS override syntax in user text; keep explicit line breaks."""
    text = text.replace("\\N", "\n").replace("\\", "⧵").replace("{", "｛").replace("}", "｝")
    return "\\N".join(part.strip() for part in text.split("\n"))


class Layout:
    def __init__(self, config: Config, width: int, height: int):
        r = config.render
        self.config = config
        self.width, self.height = width, height
        self.scale = height / 1080
        self.band_x, self.band_y, self.band_w, self.band_h = config.video.subtitle_band.pixels(width, height)
        self.vi_size = r.vi_font_size * self.scale
        self.py_size = r.pinyin_font_size * self.scale
        self.outline = r.outline * self.scale
        self.shadow = r.shadow * self.scale
        self.margin_l = self.band_x
        self.margin_r = max(0, width - (self.band_x + self.band_w))

    def text_width(self, text: str, size: float) -> float:
        return len(text) * self.config.render.avg_char_width * size

    def line_height(self, size: float) -> float:
        return size * self.config.render.line_spacing

    def fit_pinyin(self, pinyin: str) -> tuple[float, list[str]]:
        """Shrink long pinyin down to pinyin_min_scale, then wrap to more lines (5.19)."""
        width = self.text_width(pinyin, self.py_size)
        if width <= self.band_w or not pinyin:
            return 1.0, [pinyin] if pinyin else []
        needed = self.band_w / width
        if needed >= self.config.render.pinyin_min_scale:
            return needed, [pinyin]
        scale = self.config.render.pinyin_min_scale
        max_chars = max(8, int(self.band_w / (self.config.render.avg_char_width * self.py_size * scale)))
        lines = wrap_words(pinyin, max_chars)
        if len(lines) == 2:
            lines = balanced_wrap(pinyin, max_chars)
        return scale, lines

    def vi_lines(self, vi: str) -> list[str]:
        explicit = split_explicit_lines(vi)
        if len(explicit) > 1:
            return explicit
        max_chars = self.config.translate.max_line_chars
        by_width = int(self.band_w / (self.config.render.avg_char_width * self.vi_size))
        return balanced_wrap(vi, max(8, min(max_chars, by_width)))

    def bottom_margin(self, total_text_height: float) -> int:
        """Center the block vertically inside the band; overflow grows upward."""
        band_bottom = self.height - (self.band_y + self.band_h)
        return int(round(band_bottom + max(0.0, (self.band_h - total_text_height) / 2)))


def _style(layout: Layout, size: float, italic: bool = False) -> pysubs2.SSAStyle:
    r = layout.config.render
    return pysubs2.SSAStyle(
        fontname=r.font_name, fontsize=round(size, 1), primarycolor=_color(r.primary_color),
        secondarycolor=_color(r.primary_color), outlinecolor=_color(r.outline_color),
        backcolor=_color(r.outline_color), bold=False, italic=italic, outline=round(layout.outline, 2),
        shadow=round(layout.shadow, 2), alignment=pysubs2.Alignment.BOTTOM_CENTER, marginl=layout.margin_l,
        marginr=layout.margin_r, marginv=layout.bottom_margin(0), encoding=1,
    )


def build_ass(lines: list[ReviewedLine], config: Config, width: int, height: int) -> pysubs2.SSAFile:
    layout = Layout(config, width, height)
    subs = pysubs2.SSAFile()
    subs.info.update({"PlayResX": str(width), "PlayResY": str(height), "WrapStyle": "2",
                      "ScaledBorderAndShadow": "yes", "Title": "Subtitle Agent"})
    subs.styles = {
        "Pinyin": _style(layout, layout.py_size),
        "Vi": _style(layout, layout.vi_size),
        "Sign": _style(layout, layout.vi_size, italic=True),
    }
    for line in sorted((x for x in lines if not x.deleted), key=lambda x: x.start_ms):
        dialogue = line.line_type == "dialogue"
        vi_lines = layout.vi_lines(line.vi) if line.vi.strip() else []
        if dialogue:
            py_scale, py_lines = layout.fit_pinyin(line.pinyin.strip())
        else:
            py_scale, py_lines = 1.0, [line.pinyin.strip()] if line.pinyin.strip() else []
        vi_h = len(vi_lines) * layout.line_height(layout.vi_size)
        py_h = len(py_lines) * layout.line_height(layout.py_size * py_scale)
        bottom = layout.bottom_margin(vi_h + py_h)
        if vi_lines:
            subs.append(pysubs2.SSAEvent(
                start=line.start_ms, end=line.end_ms, style="Vi" if dialogue else "Sign",
                marginv=bottom, text=_ass_text("\n".join(vi_lines)), name=line.speaker or "",
            ))
        if py_lines:
            prefix = f"{{\\fs{layout.py_size * py_scale:.1f}}}" if py_scale < 1.0 else ""
            subs.append(pysubs2.SSAEvent(
                start=line.start_ms, end=line.end_ms, style="Pinyin", marginv=int(round(bottom + vi_h)),
                text=prefix + _ass_text("\n".join(py_lines)), name=line.speaker or "",
            ))
    return subs


def write_ass(path: Path, lines: list[ReviewedLine], config: Config, width: int, height: int) -> None:
    from subagent.kernel.util import atomic_write_text

    atomic_write_text(path, build_ass(lines, config, width, height).to_string("ass"))


# -- mask ------------------------------------------------------------------------------------------

def build_mask_filter(config: Config, width: int, height: int) -> str:
    """A single-input, single-output filter graph usable with ffmpeg -vf and mpv vf=lavfi=[...]."""
    x, y, w, h = config.video.subtitle_band.pixels(width, height)
    r = config.render
    if r.mask == "box":
        return f"drawbox=x={x}:y={y}:w={w}:h={h}:color={r.mask_color}@1:t=fill"
    luma = max(1, min(r.blur_radius, h // 2 - 1, w // 2 - 1))
    chroma = max(0, min(luma, h // 4 - 1, w // 4 - 1))
    return (f"split[mask_base][mask_src];[mask_src]crop={w}:{h}:{x}:{y},boxblur={luma}:2:{chroma}:2[mask_blur];"
            f"[mask_base][mask_blur]overlay={x}:{y}")


# -- fonts -----------------------------------------------------------------------------------------

def font_files(paths: Paths) -> list[Path]:
    if not paths.fonts.is_dir():
        return []
    return sorted(p for p in paths.fonts.iterdir() if p.suffix.lower() in FONT_EXTS)


def check_fonts(paths: Paths) -> None:
    if not font_files(paths):
        raise SubagentError(
            f"No subtitle font found in {paths.fonts}. Put a font covering Vietnamese diacritics and pinyin "
            "tone marks there (e.g. NotoSans-Regular.ttf).", code="font_missing")


def sync_fonts(paths: Paths, work: Path) -> None:
    dst = work / "fonts"
    dst.mkdir(parents=True, exist_ok=True)
    for f in font_files(paths):
        target = dst / f.name
        if not target.is_file() or target.stat().st_size != f.stat().st_size:
            shutil.copy2(f, target)


# -- encode ----------------------------------------------------------------------------------------

def choose_encoder(config: Config) -> str:
    wanted = config.render.encoder
    if wanted == "libx264":
        return "libx264"
    if "h264_nvenc" in available_encoders() and config.device != "cpu":
        return "h264_nvenc"
    if wanted == "h264_nvenc":
        log.warning("h264_nvenc is not available in this ffmpeg; using libx264")
    return "libx264"


def encoder_args(encoder: str, quality: int) -> list[str]:
    if encoder == "h264_nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", str(quality), "-b:v", "0"]
    return ["-c:v", "libx264", "-preset", "medium", "-crf", str(quality)]


def ffmpeg_args(source: Path, vf: str, encoder: str, quality: int, audio_codec: str | None, has_audio: bool,
                out_name: str) -> list[str]:
    args = [require_binary("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(source),
            "-vf", vf, "-map", "0:v:0"]
    if has_audio:
        args += ["-map", "0:a:0"]
        args += ["-c:a", "copy"] if (audio_codec or "").lower() in MP4_AUDIO else ["-c:a", "aac", "-b:a", "192k"]
    args += encoder_args(encoder, quality) + ["-pix_fmt", "yuv420p", "-movflags", "+faststart",
                                              "-progress", "pipe:1", "-nostats", out_name]
    return args


def _run_ffmpeg(args: list[str], cwd: Path, duration_ms: int, progress) -> None:
    proc = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=_NO_WINDOW, text=True, encoding="utf-8", errors="replace")
    assert proc.stdout is not None
    for raw in proc.stdout:
        key, _, value = raw.strip().partition("=")
        if key == "out_time_us" and value.isdigit() and progress:
            done = min(duration_ms, int(value) // 1000)
            progress.emit("render", "progress", done=done, total=duration_ms)
    stderr = proc.stderr.read() if proc.stderr else ""
    if proc.wait() != 0:
        raise MediaError(f"ffmpeg render failed: {stderr.strip()[-2000:]}", code="render_failed")


def render(ctx: EpisodeContext) -> Path:
    """Write output.ass and burn it in; returns work/<episode>/render.tmp.mp4."""
    source = ctx.require_source()
    check_fonts(ctx.paths)
    info = ctx.video_info()
    lines = read_jsonl(ctx.artifact("approved.jsonl"), ReviewedLine)
    if not lines:
        raise SubagentError("approved.jsonl is empty or missing; finish the review first", code="review_incomplete")
    write_ass(ctx.artifact("output.ass"), lines, ctx.config, info.width, info.height)
    sync_fonts(ctx.paths, ctx.work)
    # Relative paths only: the ass= filter breaks on Windows drive letters and backslashes.
    vf = f"{build_mask_filter(ctx.config, info.width, info.height)},ass=output.ass:fontsdir=fonts"
    tmp_name = "render.tmp.mp4"
    encoder = choose_encoder(ctx.config)
    try:
        _run_ffmpeg(ffmpeg_args(source, vf, encoder, ctx.config.render.quality, info.audio_codec, info.has_audio,
                                tmp_name), ctx.work, info.duration_ms, ctx.progress)
    except MediaError:
        if encoder != "h264_nvenc":
            raise
        log.warning("NVENC encode failed; retrying with libx264")
        _run_ffmpeg(ffmpeg_args(source, vf, "libx264", ctx.config.render.quality, info.audio_codec, info.has_audio,
                                tmp_name), ctx.work, info.duration_ms, ctx.progress)
    out = ctx.artifact(tmp_name)
    if not out.is_file() or out.stat().st_size == 0:
        raise MediaError("ffmpeg finished but produced no video", code="render_failed")
    return out


def preview_ass(work: Path, lines: list[ReviewedLine], config: Config, width: int, height: int) -> Path:
    """Draft subtitles for the app's live preview (work/<episode>/preview.ass)."""
    path = work / "preview.ass"
    write_ass(path, lines, config, width, height)
    return path
