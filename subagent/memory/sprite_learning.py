"""Learn how characters look from finished episodes (5.8b).

The speakers of an episode's trusted lines (every approved line in human mode; in auto mode only lines every
independent signal agrees on) teach the sprite bank through the line's talking sprite:

- the talking sprite was recognised as the speaker: the exemplar that named it gains a "right";
- it was recognised as someone else: that exemplar gains a "wrong" (exemplars with more wrongs than rights are
  removed) and the sprite counts as unknown for the votes below;
- an unknown talking sprite gets a vote for the speaker. A per-episode unknown sprite with at least
  `cast.name_min_votes` votes and `cast.name_min_share` of them for one character becomes that character:
  its crops join the bank. Votes repeat a few passes, as each new name explains more lines.
- recognitions at least `cast.add_similarity` sure, and confirmed talkers, join the bank too (new poses).

Box edits the reviewer made in the review screen come first. Moved/resized boxes and boxes drawn around
missed characters are cut from the analysed frame and described again; a box the reviewer marked as talking on
a line with a trusted speaker is labelled as that speaker (unless the reviewer named it explicitly).
Box labels the reviewer set come first: a labelled box is that character (its crop joins
the bank; the exemplar that had named it differently gains a "wrong"), and a box labelled "not a character"
is never learned and never votes.

Each character keeps its `cast.max_exemplars` best-confirmed exemplars. Writes go through the Memory Manager.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from subagent.config import Config, Paths
from subagent.models import CastDetection, CastLine, ReviewedLine
from subagent.util import read_jsonl

log = logging.getLogger(__name__)
PASSES = 3


@dataclass
class SpriteLearnResult:
    lines: int = 0                 # trusted lines with a talking sprite
    confirmed: int = 0
    corrected: int = 0
    labelled: int = 0              # boxes the reviewer labelled
    named: dict[str, str] = field(default_factory=dict)   # unknown sprite -> character
    added: int = 0
    removed: int = 0


def trusted_speakers(paths: Paths, config: Config, episode_id: str, known: set[str]) -> dict[str, str]:
    """event id -> speaker for the lines whose speaker can teach (see module docstring)."""
    from subagent.memory.voice_learning import is_auto_episode, trusted_auto_lines

    if is_auto_episode(paths, episode_id):
        lines = trusted_auto_lines(paths, config, episode_id, known, min_ms=0)
    else:
        lines = [x for x in read_jsonl(paths.episode_dir(episode_id) / "approved.jsonl", ReviewedLine)
                 if x.approved and not x.deleted and x.line_type == "dialogue" and x.speaker in known]
    return {x.event_id: x.speaker for x in lines if x.speaker}


def plan(lines: list[CastLine], embs: np.ndarray, speakers: dict[str, str], bank, stats: dict[int, tuple[int, int]],
         config: Config, episode_id: str, labels: dict[str, dict[str, str]] | None = None):
    """Pure learning step. Returns (additions, new stats, removals, result).

    bank: character -> (exemplar matrix, exemplar ids) as built by stages.cast.build_bank.
    stats: exemplar id -> (right, wrong) so far.
    labels: event id -> {detection position: character id or NOT_A_CHARACTER} from the reviewer.
    """
    from subagent.stages.cast import NOT_A_CHARACTER, group_unknowns, match

    cfg = config.cast
    result = SpriteLearnResult()
    label: dict[int, tuple[str, float, int | None]] = {}      # detection index -> (character, similarity, exemplar)
    for ln in lines:
        for d in ln.detections:
            char, sim, ex = match(embs[d.index], bank, cfg)
            if char:
                label[d.index] = (char, sim, ex)
    right: Counter = Counter({k: v[0] for k, v in stats.items()})
    wrong: Counter = Counter({k: v[1] for k, v in stats.items()})
    touched: set[int] = set()
    confirmed: set[int] = set()
    decided: set[int] = set()                  # boxes the reviewer labelled
    for ln in lines:
        for pos, lab in (labels or {}).get(ln.event_id, {}).items():
            if not pos.isdigit() or int(pos) >= len(ln.detections):
                continue
            d = ln.detections[int(pos)]
            decided.add(d.index)
            if d.index in label and label[d.index][2] is not None:
                char, _, ex = label[d.index]
                if char == lab:
                    right[ex] += 1
                else:
                    wrong[ex] += 1
                touched.add(ex)
            label.pop(d.index, None)
            if lab != NOT_A_CHARACTER:
                label[d.index] = (lab, 1.0, None)
                confirmed.add(d.index)
                result.labelled += 1
    talking = [(ln, ln.talker()) for ln in lines if ln.talker() is not None and ln.event_id in speakers
               and ln.talker().index not in decided]
    result.lines = len(talking)
    for ln, t in talking:
        sp = speakers[ln.event_id]
        if t.index in label:
            char, _, ex = label[t.index]
            if char == sp:
                right[ex] += 1
                confirmed.add(t.index)
                result.confirmed += 1
            else:
                wrong[ex] += 1
                del label[t.index]      # wrongly named: counts as unknown below
                result.corrected += 1
            if ex is not None:
                touched.add(ex)
    removals = [ex for ex in touched if wrong[ex] > right[ex]]
    # unknown sprites of this episode (everything not recognised now)
    unknown_idx = [d.index for ln in lines for d in ln.detections if d.index not in label and d.index not in decided]
    group_of = dict(zip(unknown_idx, group_unknowns([embs[i] for i in unknown_idx], cfg.unknown_similarity),
                        strict=True))
    members: dict[int, list[int]] = {}
    for i, g in group_of.items():
        members.setdefault(g, []).append(i)
    for _ in range(PASSES):
        votes: dict[int, Counter] = {}
        for ln, t in talking:
            if t.index in group_of and t.index not in label:
                votes.setdefault(group_of[t.index], Counter())[speakers[ln.event_id]] += 1
        changed = False
        for g, c in votes.items():
            sp, n = c.most_common(1)[0]
            if n >= cfg.name_min_votes and n / sum(c.values()) >= cfg.name_min_share:
                for i in members[g]:
                    label[i] = (sp, 1.0, None)          # joins the bank below
                result.named[f"u{g + 1:03d}"] = sp
                changed = True
        if not changed:
            break
    event_of = {d.index: ln.event_id for ln in lines for d in ln.detections}
    additions = [(char, embs[i], episode_id, event_of[i]) for i, (char, sim, _) in sorted(label.items())
                 if sim >= cfg.add_similarity or i in confirmed]
    new_stats = {ex: (right[ex], wrong[ex]) for ex in touched if ex not in removals}
    return additions, new_stats, removals, result


EmbedFn = Callable[[str, list[list[float]]], np.ndarray | None]


def apply_review_edits(lines: list[CastLine], embs: np.ndarray, reviewed: dict[str, ReviewedLine],
                       speakers: dict[str, str], embed: EmbedFn | None):
    """Fold the reviewer's box edits into the cast data. Returns (lines, embeddings, labels).

    embed(event_id, boxes) describes boxes cut from that line's analysed frame (None: not available, the
    geometry edits are then skipped). Labels: event id -> {position: character or NOT_A_CHARACTER}.
    """

    lines = [ln.model_copy(deep=True) for ln in lines]
    rows = [embs[i] for i in range(len(embs))]
    labels: dict[str, dict[str, str]] = {}
    for ln in lines:
        x = reviewed.get(ln.event_id)
        if x is None:
            continue
        lab = dict(x.cast_labels)
        moved = {int(k): v for k, v in x.cast_boxes.items() if k.isdigit() and int(k) < len(ln.detections)}
        added = [a for a in x.cast_added if a.character]
        boxes = [moved[k] for k in sorted(moved)] + [a.box for a in added]
        feats = embed(ln.event_id, boxes) if boxes and embed is not None else None
        if feats is not None and len(feats) == len(boxes):
            for n, k in enumerate(sorted(moved)):
                ln.detections[k].box = moved[k]
                ln.detections[k].index = len(rows)
                rows.append(feats[n])
            for n, a in enumerate(added, start=len(moved)):
                pos = len(ln.detections)
                ln.detections.append(CastDetection(index=len(rows), box=a.box, score=1.0, label="reviewer"))
                rows.append(feats[n])
                lab[str(pos)] = a.character
                if x.cast_talking == f"a{x.cast_added.index(a)}":
                    ln.talking = pos
        if x.cast_talking == "none":
            ln.talking = None
        elif x.cast_talking and x.cast_talking.isdigit() and int(x.cast_talking) < len(ln.detections):
            ln.talking = int(x.cast_talking)
        sp = speakers.get(ln.event_id)
        if x.cast_talking and x.cast_talking != "none" and sp and ln.talking is not None:
            lab.setdefault(str(ln.talking), sp)        # the reviewer saw this box talk: it is the speaker
        if lab:
            labels[ln.event_id] = {k: v for k, v in lab.items() if v}
    return lines, (np.stack(rows) if rows else embs), labels


def learn_sprites(config: Config, paths: Paths, episode_id: str, embed: EmbedFn | None = None) -> SpriteLearnResult:
    """Teach the sprite bank from one finished episode and commit the change to memory."""
    from subagent.memory.manager import MemoryManager
    from subagent.stages.cast import build_bank

    work = paths.episode_dir(episode_id)
    lines = read_jsonl(work / "cast.jsonl", CastLine)
    if not lines or not (work / "cast_embeddings.npy").is_file():
        return SpriteLearnResult()
    embs = np.load(work / "cast_embeddings.npy")
    manager = MemoryManager(paths, config)
    manager.ensure_repo()
    store = manager.store
    known = store.character_ids()
    speakers = trusted_speakers(paths, config, episode_id, known)
    from subagent.stages.cast import NOT_A_CHARACTER

    reviewed = {x.event_id: x for x in read_jsonl(work / "approved.jsonl", ReviewedLine) if not x.deleted
                and (x.cast_labels or x.cast_boxes or x.cast_added or x.cast_talking)}
    if embed is None and any(x.cast_boxes or x.cast_added for x in reviewed.values()):
        embed = _frame_embedder(config, paths, episode_id)
    lines, embs, raw = apply_review_edits(lines, embs, reviewed, speakers, embed)
    labels = {e: {k: v for k, v in lab.items() if v in known or v == NOT_A_CHARACTER} for e, lab in raw.items()}
    stats = {e.id: (e.right, e.wrong) for e in store.sprite_exemplars()}
    additions, new_stats, removals, result = plan(lines, embs, speakers, build_bank(store), stats, config, episode_id,
                                                  labels)
    generic = {c.id for c in store.characters() if c.generic}
    additions = [a for a in additions if a[0] not in generic]     # many looks under one name: never learned
    if not (additions or new_stats or removals):
        return result
    with manager.locked():
        counts = manager.write_sprites(additions, new_stats, removals, max_per_character=config.cast.max_exemplars)
        result.added, result.removed = counts["added"], counts["removed"]
        manager.commit(f"sprites from {episode_id}: +{result.added}, -{result.removed}, "
                       f"{len(result.named)} new names, {result.corrected} corrections")
    log.info("sprites: %s", result)
    return result


def _frame_embedder(config: Config, paths: Paths, episode_id: str) -> EmbedFn | None:
    """Describe boxes cut from a line's analysed frame (saved by the cast stage; else cut from the video at the
    same time). None when the image model cannot load: geometry edits are then skipped, labels still count."""
    from subagent.episodes import Registry
    from subagent.errors import ModelUnavailableError
    from subagent.media import extract_frame, probe
    from subagent.models import SubtitleEvent
    from subagent.stages.cast import crop, frame_time_ms, get_engine, load_frame

    try:
        engine = get_engine(config, paths)
    except ModelUnavailableError as exc:
        log.warning("sprites: reviewer box edits skipped: %s", exc)
        return None
    work = paths.episode_dir(episode_id)
    events = {e.id: e for e in read_jsonl(work / "events.jsonl", SubtitleEvent)}
    source = Registry(paths).get(episode_id).source_path

    def embed(event_id: str, boxes: list[list[float]]) -> np.ndarray | None:
        frame = load_frame(work, event_id)
        if frame is None and event_id in events:
            info = probe(Path(source))
            w = config.cast.frame_width
            h = int(round(w * info.height / info.width / 2)) * 2
            frame = extract_frame(Path(source), frame_time_ms(events[event_id], config.cast.sample_fps),
                                  size=(info.width, info.height))[:, :, ::-1]
            frame = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA)
        if frame is None:
            return None
        return engine.embed([crop(frame, b) for b in boxes])

    return embed
