"""Partial review (6.4b): in the middle of a human review, learn from the lines approved so far and re-check
the remaining ones.

Session-only learning: memory is not changed (the real learning happens once, at finish review).

- Sprites: the sprite bank plus what this episode's approved lines teach (speakers, talking marks, box names,
  moved/drawn boxes; memory/sprite_learning.plan) re-recognises every character found in the remaining lines.
- Voices: the voice bank plus this episode's approved lines (including the episode's new voices) re-matches
  the remaining lines' audio.
- Suggestions: a remaining line whose talking character and/or voice now point to someone other than its
  speaker gets a suggested speaker with the reason. The review screen sets it as the line's speaker (flags
  `partial_speaker` + `check_pronouns`, one undo step per line); no LLM is called. A speaker set by an earlier
  partial review may be changed again; one the reviewer chose never is.

Output: partial_review.jsonl (PartialSuggestion per remaining line).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from subagent.characters import episode_character_ids
from subagent.kernel.models import CastLine, PartialSuggestion, ReviewedLine, SpeakerCandidates, SubtitleEvent
from subagent.kernel.util import read_jsonl, write_jsonl
from subagent.memory.store import MemoryStore
from subagent.settings.config import Config, Paths
from subagent.workspace.episodes import Registry

PARTIAL_FLAG = "partial_speaker"        # the speaker was set by a partial review (6.4b)

log = logging.getLogger(__name__)
OUTPUT = "partial_review.jsonl"


@dataclass
class PartialResult:
    reviewed: int = 0
    remaining: int = 0
    sprites_learned: int = 0          # exemplars this session added
    sprite_names: int = 0             # unknown sprites named from the reviewed lines
    renamed_characters: int = 0       # characters in remaining lines whose name changed
    voices_updated: list[str] = field(default_factory=list)
    voice_changed: int = 0            # remaining lines whose voice match changed
    suggestions: int = 0


def _session_bank(bank, additions, removals):
    """Sprite bank with this session's lessons, in memory only (new exemplars get negative ids)."""
    rows: dict[str, list[tuple[np.ndarray, int]]] = {}
    for char, (mat, ids) in bank.items():
        rows[char] = [(mat[i], ex) for i, ex in enumerate(ids) if ex not in removals]
    for n, (char, emb, _, _) in enumerate(additions):
        v = np.asarray(emb, np.float32)
        rows.setdefault(char, []).append((v / (np.linalg.norm(v) or 1.0), -(n + 1)))
    return {c: (np.stack([v for v, _ in r]), [i for _, i in r]) for c, r in rows.items() if r}


def _sprites(config: Config, paths: Paths, episode_id: str, draft: list[ReviewedLine], known: set[str],
             embed) -> tuple[dict[str, dict[str, tuple[str | None, float]]], dict[str, str | None], PartialResult]:
    """(event -> {position: (character, similarity)}, event -> talking character) for remaining lines."""
    from subagent.memory.sprite_learning import _frame_embedder, apply_review_edits, plan
    from subagent.stages.cast import build_bank, match

    result = PartialResult()
    work = paths.episode_dir(episode_id)
    lines = read_jsonl(work / "cast.jsonl", CastLine)
    if not lines or not (work / "cast_embeddings.npy").is_file():
        return {}, {}, result
    embs = np.load(work / "cast_embeddings.npy")
    approved = {x.event_id: x for x in draft if x.approved and not x.deleted}
    speakers = {e: x.speaker for e, x in approved.items() if x.line_type == "dialogue" and x.speaker in known}
    edited = {e: x for e, x in approved.items() if x.cast_labels or x.cast_boxes or x.cast_added or x.cast_talking}
    if embed is None and any(x.cast_boxes or x.cast_added for x in edited.values()):
        embed = _frame_embedder(config, paths, episode_id)
    lines, embs, labels = apply_review_edits(lines, embs, edited, speakers, embed)
    store = MemoryStore(paths.memory_db)
    bank = build_bank(store)
    stats = {e.id: (e.right, e.wrong) for e in store.sprite_exemplars()}
    additions, _, removals, learned = plan(lines, embs, speakers, bank, stats, config, episode_id, labels)
    result.sprites_learned, result.sprite_names = len(additions), len(learned.named)
    session = _session_bank(bank, additions, set(removals))
    names: dict[str, dict[str, tuple[str | None, float]]] = {}
    talking: dict[str, str | None] = {}
    for ln in lines:
        if ln.event_id in approved:
            continue
        found = {}
        for pos, d in enumerate(ln.detections):
            char, sim, _ = match(embs[d.index], session, config.cast)
            found[str(pos)] = (char, round(sim, 4))
            result.renamed_characters += char != d.character
        names[ln.event_id] = found
        t = ln.talker()
        talking[ln.event_id] = found[str(ln.talking)][0] if t is not None else None
    return names, talking, result


def _voices(config: Config, paths: Paths, episode_id: str, draft: list[ReviewedLine], known: set[str],
            embed) -> tuple[dict[str, SpeakerCandidates], list[str]]:
    """Remaining lines re-matched against the voice bank plus this episode's approved lines."""
    from subagent.memory.voice_learning import Clip, embed_clips, episode_samples
    from subagent.stages.voice import get_embedder, l2_normalize, match_events
    from subagent.workspace.episodes import Registry

    work = paths.episode_dir(episode_id)
    if not (work / "speakers.jsonl").is_file():
        return {}, []
    store = MemoryStore(paths.memory_db)
    skip = store.unmatchable_ids()
    bank = {k: v for k, v in store.voice_bank().items() if k not in skip}
    counts = store.voice_counts()
    embed = embed or get_embedder(config, paths).embed
    clips = [Clip(episode_id, x.event_id, x.speaker, x.start_ms, x.end_ms) for x in draft
             if x.approved and not x.deleted and x.line_type == "dialogue" and x.speaker in known
             and x.speaker not in skip and x.end_ms - x.start_ms >= config.voice.learn_min_ms]
    embs = embed_clips(paths, config, clips, embed)
    per: dict[str, list[np.ndarray]] = {}
    for c in clips:
        if (c.episode_id, c.event_id) in embs:
            per.setdefault(c.speaker, []).append(embs[(c.episode_id, c.event_id)])
    updated = []
    for char, vecs in per.items():
        if char not in bank and len(vecs) < config.voice.learn_min_clips:
            continue                      # too little to start a voice from this episode alone
        total = np.sum(vecs, axis=0)
        if char in bank:
            total = total + l2_normalize(bank[char]) * counts.get(char, 1)
        bank[char] = l2_normalize(total)
        updated.append(char)
    if not updated:
        return {}, []
    remaining = {x.event_id for x in draft if not x.approved and not x.deleted}
    events = [e for e in read_jsonl(work / "events.jsonl", SubtitleEvent) if e.id in remaining]
    samples = episode_samples(paths, config, Registry(paths).get(episode_id))
    confusable = set(store.confusable_pairs())
    out = match_events(events, samples, config.audio.sample_rate, bank, confusable, config, embed)
    return {s.event_id: s for s in out}, sorted(updated)


def suggest(line: ReviewedLine, original_speaker: str | None, talker: str | None, voice: SpeakerCandidates | None,
            ) -> tuple[str | None, str]:
    """Suggested speaker for a remaining line, or None. Never overrides a speaker the reviewer chose.

    - voice sure (fixed / new_voice): the talking character must agree, or with nobody clearly talking the voice
      alone suggests;
    - voice unsure (confusable): the talking character must be one of the voice candidates;
    - no usable voice (unknown, too short, none): the talking character alone suggests.
    """
    if line.speaker != original_speaker or line.line_type != "dialogue":
        return None, ""
    status = voice.status if voice and voice.candidates else "unknown"
    v_top = voice.candidates[0][0] if status in ("fixed", "new_voice") else None
    v_cands = [c for c, _ in voice.candidates] if voice else []
    if v_top:
        if talker and talker != v_top:
            return None, ""                      # picture and voice disagree: leave it to the reviewer
        if v_top != line.speaker:
            return v_top, "picture and voice agree" if talker else "voice"
        return None, ""
    if not talker or talker == line.speaker:
        return None, ""
    if status == "confusable":
        return (talker, "talking on screen; also a voice candidate") if talker in v_cands else (None, "")
    return talker, "talking on screen"


def partial_review(config: Config, paths: Paths, episode_id: str, *, sprite_embed: Callable | None = None,
                   voice_embed: Callable | None = None) -> PartialResult:
    from subagent.stages.review import load_draft, original_draft

    work = paths.episode_dir(episode_id)
    draft = load_draft(work)
    if not draft:
        from subagent.kernel.errors import ReviewIncompleteError

        raise ReviewIncompleteError("No review draft found; run the episode in human mode first")
    store = MemoryStore(paths.memory_db)
    number = Registry(paths).get(episode_id).number
    waiting = {c.id for c in store.returning_candidates(number, config.memory.probation_window)}
    known = episode_character_ids(work, store.character_ids(), config.voice.new_voice_prefix, waiting)
    remaining = [x for x in draft if not x.approved and not x.deleted]
    names, talking, result = ({}, {}, PartialResult())
    if config.cast.enabled:
        names, talking, result = _sprites(config, paths, episode_id, draft, known, sprite_embed)
    voices, result.voices_updated = _voices(config, paths, episode_id, draft, known, voice_embed)
    before = {s.event_id: s for s in read_jsonl(work / "speakers.jsonl", SpeakerCandidates)}
    original = {x.event_id: x.speaker for x in original_draft(work, config.review.predelete_fragments,
                                                              config.review.noise_max_han)}
    result.reviewed = sum(x.approved and not x.deleted for x in draft)
    result.remaining = len(remaining)
    out: list[PartialSuggestion] = []
    for x in remaining:
        # not re-matched (no voice changed this session): the pipeline's voice match still counts
        v = voices.get(x.event_id) or before.get(x.event_id)
        if v is not None and before.get(x.event_id) and (v.status, v.candidates[:1]) != (
                before[x.event_id].status, before[x.event_id].candidates[:1]):
            result.voice_changed += 1
        # a speaker an earlier partial review set is still the machine's; one the reviewer chose is not
        orig = x.speaker if PARTIAL_FLAG in x.flags else original.get(x.event_id)
        speaker, reason = suggest(x, orig, talking.get(x.event_id), v)
        result.suggestions += speaker is not None
        found = names.get(x.event_id, {})
        out.append(PartialSuggestion(
            event_id=x.event_id, cast={k: c for k, (c, _) in found.items()},
            similarity={k: s for k, (_, s) in found.items()}, talking=talking.get(x.event_id),
            voice=v, suggested_speaker=speaker, reason=reason))
    write_jsonl(work / OUTPUT, out)
    log.info("partial review %s: %s", episode_id, result)
    return result
