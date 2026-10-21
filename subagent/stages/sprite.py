"""Stage 10 (optional): resolve low-confidence speakers with on-screen character art (5.13)."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from subagent.context import EpisodeContext
from subagent.kernel.models import LineTranslation, SpeakerCandidates, SubtitleEvent
from subagent.kernel.util import atomic_write_json, read_jsonl, write_jsonl
from subagent.media import extract_frame, imread, imwrite_png
from subagent.memory.store import MemoryStore
from subagent.settings.config import Paths, SpriteConfig

log = logging.getLogger(__name__)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def load_templates(paths: Paths) -> dict[str, list[np.ndarray]]:
    root = paths.bootstrap / "sprites"
    out: dict[str, list[np.ndarray]] = {}
    if not root.is_dir():
        return out
    for char_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        imgs = [imread(f, gray=True) for f in sorted(char_dir.iterdir()) if f.suffix.lower() in IMAGE_EXTS]
        if imgs:
            out[char_dir.name] = imgs
    return out


def best_match(frame_gray: np.ndarray, templates: list[np.ndarray], scales: list[float]) -> float:
    import cv2

    best = -1.0
    fh, fw = frame_gray.shape[:2]
    for tpl in templates:
        for s in scales:
            th, tw = int(tpl.shape[0] * s), int(tpl.shape[1] * s)
            if th < 8 or tw < 8 or th > fh or tw > fw:
                continue
            scaled = cv2.resize(tpl, (tw, th), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_LINEAR)
            res = cv2.matchTemplate(frame_gray, scaled, cv2.TM_CCOEFF_NORMED)
            best = max(best, float(res.max()))
    return best


def decide(scores: dict[str, float], threshold: float) -> str | None:
    """Exactly one candidate above the threshold resolves the speaker."""
    above = [c for c, s in scores.items() if s >= threshold]
    return above[0] if len(above) == 1 else None


def candidates_for(line: LineTranslation, cands: SpeakerCandidates | None, templates: dict) -> list[str]:
    ids = [c for c, _ in cands.candidates] if cands and cands.candidates else list(templates)
    if line.speaker and line.speaker not in ids:   # without voice candidates every character is tested
        ids.insert(0, line.speaker)
    return [c for c in ids if c in templates]


def run(ctx: EpisodeContext, frame_reader=None) -> dict[str, int]:
    lines = read_jsonl(ctx.artifact("translations.jsonl"), LineTranslation)
    cfg: SpriteConfig = ctx.config.sprite
    triggered = [ln for ln in lines if "low_speaker_conf" in ln.flags]
    if not cfg.enabled or not triggered:
        write_jsonl(ctx.artifact("translations.jsonl"), lines)
        return {"triggered": 0 if not cfg.enabled else len(triggered), "resolved": 0, "unresolved": 0}

    templates = load_templates(ctx.paths)
    events = {e.id: e for e in read_jsonl(ctx.artifact("events.jsonl"), SubtitleEvent)}
    speakers = {s.event_id: s for s in read_jsonl(ctx.artifact("speakers.jsonl"), SpeakerCandidates)}
    frames_dir = ctx.artifact("sprite_frames")
    if frame_reader is None:
        source = ctx.require_source()
        info = ctx.video_info()

        def frame_reader(t_ms: int) -> np.ndarray:
            return extract_frame(source, t_ms, gray=True, size=(info.width, info.height))

    known = MemoryStore(ctx.paths.memory_db).character_ids()
    log_rows, resolved, unresolved = [], 0, 0
    for i, line in enumerate(triggered, 1):
        ctx.progress.emit("sprite", "progress", done=i, total=len(triggered))
        cand_ids = candidates_for(line, speakers.get(line.event_id), templates)
        if not cand_ids:
            log_rows.append({"event_id": line.event_id, "result": "no_templates"})
            continue
        event = events[line.event_id]
        t_mid = (event.start_ms + event.end_ms) // 2
        frame = frame_reader(t_mid)
        imwrite_png(frames_dir / f"{t_mid}.png", frame)
        scores = {c: best_match(frame, templates[c], cfg.scales) for c in cand_ids}
        winner = decide(scores, cfg.match_threshold)
        line.flags = [f for f in line.flags if f != "low_speaker_conf"]
        if winner and winner in known:
            line.speaker = winner
            resolved += 1
            result = "resolved"
        else:
            line.flags.append("sprite_unresolved")
            unresolved += 1
            result = "unresolved"
        log_rows.append({"event_id": line.event_id, "result": result, "scores": {k: round(v, 3) for k, v in scores.items()}})
    atomic_write_json(ctx.artifact("sprite.json"), log_rows)
    write_jsonl(ctx.artifact("translations.jsonl"), lines)
    return {"triggered": len(triggered), "resolved": resolved, "unresolved": unresolved}


def save_template(paths: Paths, char_id: str, image: np.ndarray, name: str) -> Path:
    """Used by the bootstrap wizard to store a cropped sprite template."""
    path = paths.bootstrap / "sprites" / char_id / f"{name}.png"
    imwrite_png(path, image)
    return path
