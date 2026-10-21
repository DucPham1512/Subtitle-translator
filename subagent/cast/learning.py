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

from subagent.kernel.models import CastDetection, CastLine, ReviewedLine
from subagent.kernel.util import read_jsonl
from subagent.settings.config import Config, Paths

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
    from subagent.memory.evidence import is_auto_episode, trusted_auto_lines

    if is_auto_episode(paths, episode_id):
        lines = trusted_auto_lines(paths, config, episode_id, known, min_ms=0)
    else:
        lines = [x for x in read_jsonl(paths.episode_dir(episode_id) / "approved.jsonl", ReviewedLine)
                 if x.approved and not x.deleted and x.line_type == "dialogue" and x.speaker in known]
    return {x.event_id: x.speaker for x in lines if x.speaker}


@dataclass
class _Plan:
    """What one learning pass works on: the label of each detection and the exemplars' votes."""
    label: dict[int, tuple[str, float, int | None]]          # detection index -> (character, similarity, exemplar)
    right: Counter
    wrong: Counter
    result: SpriteLearnResult
    touched: set[int] = field(default_factory=set)
    confirmed: set[int] = field(default_factory=set)
    decided: set[int] = field(default_factory=set)            # boxes the reviewer labelled


def plan(lines: list[CastLine], embs: np.ndarray, speakers: dict[str, str], bank, stats: dict[int, tuple[int, int]],
         config: Config, episode_id: str, labels: dict[str, dict[str, str]] | None = None):
    """Pure learning step. Returns (additions, new stats, removals, result).

    bank: character -> (exemplar matrix, exemplar ids) as built by stages.cast.build_bank.
    stats: exemplar id -> (right, wrong) so far.
    labels: event id -> {detection position: character id or NOT_A_CHARACTER} from the reviewer.
    """
    from subagent.cast.cast import match

    cfg = config.cast
    label: dict[int, tuple[str, float, int | None]] = {}
    for ln in lines:
        for d in ln.detections:
            char, sim, ex = match(embs[d.index], bank, cfg)
            if char:
                label[d.index] = (char, sim, ex)
    st = _Plan(label=label, right=Counter({k: v[0] for k, v in stats.items()}),
               wrong=Counter({k: v[1] for k, v in stats.items()}), result=SpriteLearnResult())
    _apply_labels(st, lines, labels)
    talking = [(ln, ln.talker()) for ln in lines if ln.talker() is not None and ln.event_id in speakers
               and ln.talker().index not in st.decided]
    st.result.lines = len(talking)
    _check_talkers(st, talking, speakers)
    removals = [ex for ex in st.touched if st.wrong[ex] > st.right[ex]]
    _name_unknowns(st, lines, embs, talking, speakers, cfg)
    event_of = {d.index: ln.event_id for ln in lines for d in ln.detections}
    additions = [(char, embs[i], episode_id, event_of[i]) for i, (char, sim, _) in sorted(st.label.items())
                 if sim >= cfg.add_similarity or i in st.confirmed]
    new_stats = {ex: (st.right[ex], st.wrong[ex]) for ex in st.touched if ex not in removals}
    return additions, new_stats, removals, st.result


def _apply_labels(st: _Plan, lines: list[CastLine], labels: dict[str, dict[str, str]] | None) -> None:
    """The reviewer's box labels come first: the box is that character (or no character); the exemplar that had
    named it gains a right or a wrong."""
    from subagent.cast.cast import NOT_A_CHARACTER

    for ln in lines:
        for pos, lab in (labels or {}).get(ln.event_id, {}).items():
            if not pos.isdigit() or int(pos) >= len(ln.detections):
                continue
            d = ln.detections[int(pos)]
            st.decided.add(d.index)
            if d.index in st.label and st.label[d.index][2] is not None:
                char, _, ex = st.label[d.index]
                if char == lab:
                    st.right[ex] += 1
                else:
                    st.wrong[ex] += 1
                st.touched.add(ex)
            st.label.pop(d.index, None)
            if lab != NOT_A_CHARACTER:
                st.label[d.index] = (lab, 1.0, None)
                st.confirmed.add(d.index)
                st.result.labelled += 1


def _check_talkers(st: _Plan, talking: list, speakers: dict[str, str]) -> None:
    """A talking sprite recognised as the line's speaker confirms its exemplar; as someone else, the exemplar gains
    a wrong and the sprite counts as unknown."""
    for ln, t in talking:
        sp = speakers[ln.event_id]
        if t.index in st.label:
            char, _, ex = st.label[t.index]
            if char == sp:
                st.right[ex] += 1
                st.confirmed.add(t.index)
                st.result.confirmed += 1
            else:
                st.wrong[ex] += 1
                del st.label[t.index]      # wrongly named: counts as unknown below
                st.result.corrected += 1
            if ex is not None:
                st.touched.add(ex)


def _name_unknowns(st: _Plan, lines: list[CastLine], embs: np.ndarray, talking: list, speakers: dict[str, str],
                   cfg) -> None:
    """Unknown sprites of this episode get the speaker their talking lines vote for (a few passes, as each new name
    explains more lines)."""
    from subagent.cast.cast import group_unknowns

    unknown_idx = [d.index for ln in lines for d in ln.detections if d.index not in st.label
                   and d.index not in st.decided]
    group_of = dict(zip(unknown_idx, group_unknowns([embs[i] for i in unknown_idx], cfg.unknown_similarity),
                        strict=True))
    members: dict[int, list[int]] = {}
    for i, g in group_of.items():
        members.setdefault(g, []).append(i)
    for _ in range(PASSES):
        votes: dict[int, Counter] = {}
        for ln, t in talking:
            if t.index in group_of and t.index not in st.label:
                votes.setdefault(group_of[t.index], Counter())[speakers[ln.event_id]] += 1
        changed = False
        for g, c in votes.items():
            sp, n = c.most_common(1)[0]
            if n >= cfg.name_min_votes and n / sum(c.values()) >= cfg.name_min_share:
                for i in members[g]:
                    st.label[i] = (sp, 1.0, None)          # joins the bank below
                st.result.named[f"u{g + 1:03d}"] = sp
                changed = True
        if not changed:
            break


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
    from subagent.cast.cast import build_bank
    from subagent.memory.manager import MemoryManager

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
    from subagent.cast.cast import NOT_A_CHARACTER

    reviewed = {x.event_id: x for x in read_jsonl(work / "approved.jsonl", ReviewedLine) if not x.deleted
                and (x.cast_labels or x.cast_boxes or x.cast_added or x.cast_talking)}
    if embed is None and any(x.cast_boxes or x.cast_added for x in reviewed.values()):
        embed = frame_embedder(config, paths, episode_id)
    lines, embs, raw = apply_review_edits(lines, embs, reviewed, speakers, embed)
    labels = {e: {k: v for k, v in lab.items() if v in known or v == NOT_A_CHARACTER} for e, lab in raw.items()}
    # learning this episode again (a re-finished review) first takes back what it did last time
    prev = store.sprite_feedback(episode_id)
    prev_added = {ex for ex, (_, _, was_added) in prev.items() if was_added}
    stats = {e.id: (e.right - prev.get(e.id, (0, 0, False))[0], e.wrong - prev.get(e.id, (0, 0, False))[1])
             for e in store.sprite_exemplars() if e.id not in prev_added}
    additions, new_stats, removals, result = plan(lines, embs, speakers, build_bank(store, prev_added), stats,
                                                  config, episode_id, labels)
    generic = {c.id for c in store.characters() if c.generic}
    additions = [a for a in additions if a[0] not in generic]     # many looks under one name: never learned
    if not (additions or new_stats or removals or prev):
        return result
    with manager.locked():
        counts = manager.write_sprites(additions, new_stats, removals, max_per_character=config.cast.max_exemplars,
                                       episode_id=episode_id, base=stats, undo=prev)
        result.added, result.removed = counts["added"], counts["removed"]
        manager.commit(f"sprites from {episode_id}: +{result.added}, -{result.removed}, "
                       f"{len(result.named)} new names, {result.corrected} corrections")
    log.info("sprites: %s", result)
    return result


def frame_embedder(config: Config, paths: Paths, episode_id: str) -> EmbedFn | None:
    """Describe boxes cut from a line's analysed frame (saved by the cast stage; else cut from the video at the
    same time). None when the image model cannot load: geometry edits are then skipped, labels still count."""
    from subagent.cast.cast import crop, frame_time_ms, get_engine, load_frame
    from subagent.infra.media import extract_frame, probe
    from subagent.kernel.errors import ModelUnavailableError
    from subagent.kernel.models import SubtitleEvent
    from subagent.workspace.episodes import Registry

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
