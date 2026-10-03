"""Character cards for the review screen (6.4): who an id is, so a returning NPC gets the same id again.

A card has the character's name and description (memory, or the candidate on probation), the episode it was first
seen in, and an example line it speaks: the longest reviewed dialogue line, preferably one where it is the talking
sprite on screen. From that line come a short voice clip and a picture of its talking box, cut from the source
video once and cached in `cache/character_cards/<id>/` (not committed). Reading only; nothing here writes memory.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from subagent.config import Config, Paths
from subagent.memory.store import MemoryStore
from subagent.models import CastLine, ReviewedLine, SubtitleEvent
from subagent.util import read_jsonl

log = logging.getLogger(__name__)
CLIP_MAX_MS = 4000


@dataclass
class CharacterCard:
    id: str
    name: str                              # the Vietnamese name, or the id while it has none
    description: str = ""
    first_episode: str | None = None
    kind: str = "character"                # character | candidate | new
    episode_id: str | None = None          # where the example line is
    start_ms: int = 0
    end_ms: int = 0
    event_id: str | None = None
    box: list[float] | None = None         # its talking box on that line (cast frame coordinates)
    clip: Path | None = None
    picture: Path | None = None


def _episode_ids(paths: Paths) -> list[str]:
    from subagent.episodes import Registry

    return [e.id for e in sorted(Registry(paths).load(), key=lambda e: e.number)]


def _talking_box(cast: CastLine | None, char_id: str) -> list[float] | None:
    """The box of the character on a line: the talking sprite, else a box recognised as it."""
    if cast is None:
        return None
    if cast.talking is not None and cast.talking < len(cast.detections):
        return cast.detections[cast.talking].box
    named = [d.box for d in cast.detections if d.character == char_id]
    return named[0] if named else None


def card_info(paths: Paths, config: Config, char_id: str, *, current: str | None = None,
              draft: list[ReviewedLine] | None = None) -> CharacterCard:
    """Name, description, first episode and the example line (fast: no video is read). `draft`: the lines of the
    episode under review (`current`), searched after the reviewed episodes."""
    store = MemoryStore(paths.memory_db)
    card = CharacterCard(id=char_id, name=char_id, kind="new")
    row = next((c for c in store.characters() if c.id == char_id), None)
    if row is not None:
        card.name, card.description, card.kind = row.name_vi or char_id, row.description or "", "character"
    else:
        cand = next((c for c in store.candidates() if c.id == char_id), None)
        if cand is not None:
            card.name = cand.name_vi or char_id
            card.description, card.kind, card.first_episode = cand.description or "", "candidate", cand.first_episode
    order = _episode_ids(paths)
    seen = sorted({a["episode_id"] for a in store.appearances() if a["character_id"] == char_id},
                  key=lambda e: order.index(e) if e in order else len(order))
    card.first_episode = card.first_episode or (seen[0] if seen else None)

    best: tuple[bool, int] | None = None          # (has a talking box, clip length) of the example so far
    sources = [(ep, paths.episode_dir(ep) / "approved.jsonl") for ep in order if ep != current]
    for ep, path in sources + ([(current, None)] if current else []):
        lines = draft or [] if path is None else (read_jsonl(path, ReviewedLine) if path.is_file() else [])
        mine = [x for x in lines if x.speaker == char_id and not x.deleted]
        if not mine:
            continue
        card.first_episode = card.first_episode or ep
        cast = {c.event_id: c for c in read_jsonl(paths.episode_dir(ep) / "cast.jsonl", CastLine)}
        for line in mine:
            length = line.end_ms - line.start_ms
            if line.line_type != "dialogue" or length < config.voice.learn_min_ms:
                continue
            box = _talking_box(cast.get(line.event_id), char_id)
            key = (box is not None, min(length, CLIP_MAX_MS))
            if best is None or key > best:
                best = key
                card.episode_id, card.event_id, card.box = ep, line.event_id, box
                card.start_ms, card.end_ms = line.start_ms, line.end_ms
    return card


def card_media(paths: Paths, config: Config, card: CharacterCard) -> CharacterCard:
    """Cut the example line's voice clip and the picture of its talking box (cached); missing video: none."""
    from subagent.episodes import Registry
    from subagent.media import extract_clip, extract_frame, imwrite_png, probe
    from subagent.stages.cast import frame_time_ms, load_frame

    if card.episode_id is None or card.event_id is None:
        return card
    source = Path(Registry(paths).get(card.episode_id).source_path)
    folder = paths.cache / "character_cards" / card.id
    stem = card.event_id.replace(":", "_")
    clip, picture = folder / f"{stem}.wav", folder / f"{stem}.png"
    try:
        if not clip.is_file() and source.is_file():
            end = min(card.end_ms, card.start_ms + CLIP_MAX_MS)
            extract_clip(source, card.start_ms, end, clip, sample_rate=config.audio.sample_rate)
        if card.box is not None and not picture.is_file():
            work = paths.episode_dir(card.episode_id)
            event = next((e for e in read_jsonl(work / "events.jsonl", SubtitleEvent) if e.id == card.event_id), None)
            frame = load_frame(work, card.event_id)            # the analysed frame (RGB), until cleanup
            if frame is not None:
                frame = frame[:, :, ::-1]
            elif source.is_file():
                info = probe(source)
                t_ms = frame_time_ms(event, config.cast.sample_fps) if event else (card.start_ms + card.end_ms) // 2
                frame = extract_frame(source, t_ms, size=(info.width, info.height))
            if frame is not None:
                scale = frame.shape[1] / config.cast.frame_width
                x0, y0, x1, y1 = (int(round(v * scale)) for v in card.box)
                crop = frame[max(0, y0):max(y0 + 1, y1), max(0, x0):max(x0 + 1, x1)]
                if crop.size:
                    imwrite_png(picture, crop)
    except Exception as exc:  # noqa: BLE001 - a card without media is still useful
        log.warning("character card %s: %s", card.id, exc)
    card.clip = clip if clip.is_file() else None
    card.picture = picture if picture.is_file() else None
    return card
