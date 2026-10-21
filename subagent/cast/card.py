"""Character cards for the review screen (6.4): who an id is, so a returning NPC gets the same id again.

A card has the character's name and description (memory, or the candidate on probation), the episode it was first
seen in, a voice sample and a picture. Where the sample comes from, most trusted first:

1. the reviewer's own choice ("Use this line", `pin_card`), kept in `data/character_cards/<id>/`;
2. the bootstrap material the reviewer curated: `data/bootstrap/voices/<id>/*.wav`, `sprites/<id>/*.png`;
3. a line the reviewer approved (a finished episode, or approved in the review under way) with that speaker: the
   longest one, preferring one with a confirmed box. A box is confirmed when the reviewer marked it talking or
   named it this character in the On screen view, or the sprite bank recognised it as this character. The
   machine's talking sprite alone is not trusted (it is often someone else).

Unreviewed lines are never used. Clips and pictures cut from the video are cached in `cache/character_cards/<id>/`.
Nothing here writes memory: a pinned sample changes the card only.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from subagent.kernel.models import CastLine, ReviewedLine, SubtitleEvent
from subagent.kernel.util import atomic_write_text, now_iso, read_jsonl
from subagent.memory.store import MemoryStore
from subagent.settings.config import Config, Paths

log = logging.getLogger(__name__)
CLIP_MAX_MS = 4000
PIN = "pin.json"


@dataclass
class CharacterCard:
    id: str
    name: str                              # the Vietnamese name, or the id while it has none
    description: str = ""
    aliases: list[str] = field(default_factory=list)   # titles and other names (5.15c)
    first_episode: str | None = None
    kind: str = "character"                # character | candidate | new
    source: str = "none"                   # pinned | bootstrap | reviewed | none: where the sample comes from
    episode_id: str | None = None          # where the example line is (reviewed)
    start_ms: int = 0
    end_ms: int = 0
    event_id: str | None = None
    box: list[float] | None = None         # its confirmed box on that line (cast frame coordinates)
    clip: Path | None = None
    picture: Path | None = None


def pin_dir(paths: Paths, char_id: str) -> Path:
    return paths.card_pins / char_id


def _episode_ids(paths: Paths) -> list[str]:
    from subagent.workspace.episodes import Registry

    return [e.id for e in sorted(Registry(paths).load(), key=lambda e: e.number)]


def shown_talking_box(line: ReviewedLine, cast: CastLine | None) -> list[float] | None:
    """The box the On screen view shows as talking: the reviewer's mark (moved / drawn boxes included), else the
    machine's talking sprite. None when nobody is marked talking."""
    if line.cast_talking == "none":
        return None
    if line.cast_talking:
        if line.cast_talking.startswith("a"):
            i = int(line.cast_talking[1:])
            return line.cast_added[i].box if i < len(line.cast_added) else None
        pos = line.cast_talking
    elif cast is not None and cast.talking is not None:
        pos = str(cast.talking)
    else:
        return None
    if pos in line.cast_boxes:
        return line.cast_boxes[pos]
    return cast.detections[int(pos)].box if cast is not None and int(pos) < len(cast.detections) else None


def confirmed_box(line: ReviewedLine, cast: CastLine | None, char_id: str) -> list[float] | None:
    """A box on an approved line that is surely this character: marked talking by the reviewer on its own line,
    named it by the reviewer, or recognised as it by the sprite bank."""
    if line.cast_talking and line.cast_talking != "none" and line.speaker == char_id:
        return shown_talking_box(line, cast)
    for pos, label in line.cast_labels.items():
        if label == char_id and pos.isdigit():
            if pos in line.cast_boxes:
                return line.cast_boxes[pos]
            if cast is not None and int(pos) < len(cast.detections):
                return cast.detections[int(pos)].box
    for added in line.cast_added:
        if added.character == char_id:
            return added.box
    if cast is not None:
        for pos, d in enumerate(cast.detections):
            if d.character == char_id and line.cast_labels.get(str(pos)) in (None, char_id):
                return line.cast_boxes.get(str(pos), d.box)
    return None


def card_info(paths: Paths, config: Config, char_id: str, *, current: str | None = None,
              draft: list[ReviewedLine] | None = None) -> CharacterCard:
    """Name, description, first episode and where the sample comes from (fast: no video is read). `draft`: the lines
    of the episode under review (`current`); only its approved lines are used."""
    store = MemoryStore(paths.memory_db)
    card = CharacterCard(id=char_id, name=char_id, kind="new")
    row = next((c for c in store.characters() if c.id == char_id), None)
    if row is not None:
        card.name, card.description, card.kind = row.name_vi or char_id, row.description or "", "character"
        card.aliases = list(row.aliases)
    else:
        cand = next((c for c in store.candidates() if c.id == char_id), None)
        if cand is not None:
            card.name = cand.name_vi or char_id
            card.description, card.kind, card.first_episode = cand.description or "", "candidate", cand.first_episode
            card.aliases = list(cand.aliases)
    order = _episode_ids(paths)
    seen = sorted({a["episode_id"] for a in store.appearances() if a["character_id"] == char_id},
                  key=lambda e: order.index(e) if e in order else len(order))
    card.first_episode = card.first_episode or (seen[0] if seen else None)

    best: tuple[bool, int] | None = None           # (has a confirmed box, clip length) of the example so far
    sources = [(ep, paths.episode_dir(ep) / "approved.jsonl") for ep in order if ep != current]
    for ep, path in sources + ([(current, None)] if current else []):
        lines = [x for x in (draft or []) if x.approved] if path is None else \
            (read_jsonl(path, ReviewedLine) if path.is_file() else [])
        mine = [x for x in lines if x.speaker == char_id and not x.deleted]
        if not mine:
            continue
        card.first_episode = card.first_episode or ep
        cast = {c.event_id: c for c in read_jsonl(paths.episode_dir(ep) / "cast.jsonl", CastLine)}
        for line in mine:
            length = line.end_ms - line.start_ms
            if line.line_type != "dialogue" or length < config.voice.learn_min_ms:
                continue
            box = confirmed_box(line, cast.get(line.event_id), char_id)
            key = (box is not None, min(length, CLIP_MAX_MS))
            if best is None or key > best:
                best = key
                card.episode_id, card.event_id, card.box = ep, line.event_id, box
                card.start_ms, card.end_ms = line.start_ms, line.end_ms
    if card.event_id is not None:
        card.source = "reviewed"
    voices = sorted((paths.bootstrap / "voices" / char_id).glob("*.wav"))
    sprites = sorted((paths.bootstrap / "sprites" / char_id).glob("*.png"))
    if voices or sprites:
        card.source = "bootstrap"
        card.clip = voices[0] if voices else None
        card.picture = sprites[0] if sprites else None
    pin = pin_dir(paths, char_id)
    if (pin / PIN).is_file():
        card.source = "pinned"
        card.clip = pin / "sample.wav" if (pin / "sample.wav").is_file() else None
        card.picture = pin / "picture.png" if (pin / "picture.png").is_file() else None
    return card


def _frame(paths: Paths, config: Config, episode_id: str, event_id: str, start_ms: int, end_ms: int,
           source: Path) -> np.ndarray | None:
    """The frame the cast stage analysed for a line (BGR), else the video frame at the same time."""
    from subagent.cast.cast import frame_time_ms, load_frame
    from subagent.infra.media import extract_frame, probe

    work = paths.episode_dir(episode_id)
    frame = load_frame(work, event_id)                      # RGB, until cleanup
    if frame is not None:
        return frame[:, :, ::-1]
    if not source.is_file():
        return None
    event = next((e for e in read_jsonl(work / "events.jsonl", SubtitleEvent) if e.id == event_id), None)
    info = probe(source)
    t_ms = frame_time_ms(event, config.cast.sample_fps) if event else (start_ms + end_ms) // 2
    return extract_frame(source, t_ms, size=(info.width, info.height))


def _source(paths: Paths, episode_id: str) -> Path:
    from subagent.workspace.episodes import Registry

    return Path(Registry(paths).get(episode_id).source_path)


def _cut_clip(paths: Paths, config: Config, episode_id: str, start_ms: int, end_ms: int, out: Path) -> None:
    from subagent.infra.media import extract_clip

    source = _source(paths, episode_id)
    if source.is_file():
        extract_clip(source, start_ms, min(end_ms, start_ms + CLIP_MAX_MS), out, sample_rate=config.audio.sample_rate)


def _cut_picture(paths: Paths, config: Config, episode_id: str, event_id: str, start_ms: int, end_ms: int,
                 box: list[float], out: Path) -> None:
    """The picture of `box` (cast frame coordinates) on the line's frame."""
    from subagent.infra.media import imwrite_png

    frame = _frame(paths, config, episode_id, event_id, start_ms, end_ms, _source(paths, episode_id))
    if frame is None:
        return
    scale = frame.shape[1] / config.cast.frame_width
    x0, y0, x1, y1 = (int(round(v * scale)) for v in box)
    crop = frame[max(0, y0):max(y0 + 1, y1), max(0, x0):max(x0 + 1, x1)]
    if crop.size:
        imwrite_png(out, crop)


def card_media(paths: Paths, config: Config, card: CharacterCard) -> CharacterCard:
    """For a sample from a reviewed line: cut its voice clip and the picture of its confirmed box (cached)."""
    if card.source != "reviewed" or card.episode_id is None or card.event_id is None:
        return card
    folder = paths.card_cache / card.id
    stem = card.event_id.replace(":", "_")
    clip, picture = folder / f"{stem}.wav", folder / f"{stem}.png"
    try:
        if not clip.is_file():
            _cut_clip(paths, config, card.episode_id, card.start_ms, card.end_ms, clip)
        if card.box is not None and not picture.is_file():
            _cut_picture(paths, config, card.episode_id, card.event_id, card.start_ms, card.end_ms, card.box, picture)
    except Exception as exc:  # noqa: BLE001 - a card without media is still useful
        log.warning("character card %s: %s", card.id, exc)
    card.clip = clip if clip.is_file() else None
    card.picture = picture if card.box is not None and picture.is_file() else None
    return card


def pin_card(paths: Paths, config: Config, char_id: str, episode_id: str, line: ReviewedLine,
             box: list[float] | None) -> Path:
    """The reviewer's choice ("Use this line"): this line's voice and the picture of `box` become the character's
    card sample (no box: no picture, e.g. a narrator). Only the card changes; memory learns nothing from it."""
    folder = pin_dir(paths, char_id)
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("sample.wav", "picture.png"):
        (folder / name).unlink(missing_ok=True)
    _cut_clip(paths, config, episode_id, line.start_ms, line.end_ms, folder / "sample.wav")
    if box is not None:
        _cut_picture(paths, config, episode_id, line.event_id, line.start_ms, line.end_ms, box,
                     folder / "picture.png")
    atomic_write_text(folder / PIN, json.dumps({"episode": episode_id, "event_id": line.event_id, "box": box,
                                                "at": now_iso()}, ensure_ascii=False, indent=1))
    return folder
