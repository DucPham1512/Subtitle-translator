"""What an episode's artifacts say about its approved lines, for learning: which lines can be trusted in auto mode
(5.8a) and each line's voice (5.15b). Reads files only; no models."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from subagent.config import Config, Paths
from subagent.kernel.models import Evaluation, LineTranslation, ReviewedLine, SpeakerCandidates
from subagent.kernel.util import read_jsonl
from subagent.state import load_state


def is_auto_episode(paths: Paths, episode_id: str) -> bool:
    """Approved without a person: speakers there are machine guesses."""
    return load_state(paths.episode_dir(episode_id), episode_id).mode == "auto"


def usable_line(x: ReviewedLine, config: Config, known: set[str], min_ms: int | None = None) -> bool:
    min_ms = config.voice.learn_min_ms if min_ms is None else min_ms
    return (x.approved and not x.deleted and x.line_type == "dialogue" and x.speaker in known
            and x.end_ms - x.start_ms >= min_ms)


def trusted_auto_lines(paths: Paths, config: Config, episode_id: str, known: set[str],
                       min_ms: int | None = None) -> list[ReviewedLine]:
    """The lines of one auto-mode episode whose speaker every independent signal agrees on (see auto_clips)."""
    v = config.voice
    allowed = set(v.learn_auto_allowed_flags)
    work = paths.episode_dir(episode_id)
    if not (work / "speakers.jsonl").is_file():
        return []
    voices = {s.event_id: s for s in read_jsonl(work / "speakers.jsonl", SpeakerCandidates)}
    translated = {t.event_id: t for t in read_jsonl(work / "translations.jsonl", LineTranslation)}
    first_pass = {e.event_id for e in read_jsonl(work / "evaluations.jsonl", Evaluation)
                  if e.attempt == 1 and e.passed}
    out = []
    for x in read_jsonl(work / "approved.jsonl", ReviewedLine):
        s, t = voices.get(x.event_id), translated.get(x.event_id)
        if not (usable_line(x, config, known, min_ms) and s and t and s.status in ("fixed", "new_voice")
                and s.candidates):
            continue
        top, score = s.candidates[0]
        margin = score - (s.candidates[1][1] if len(s.candidates) > 1 else -1.0)
        if (top == x.speaker == t.speaker and score >= v.learn_auto_min_score
                and margin >= v.learn_auto_min_margin and x.event_id in first_pass
                and set(x.flags) <= allowed and set(t.flags) <= allowed):
            out.append(x)
    return out


def load_line_voices(path: Path) -> dict[str, np.ndarray]:
    """voice_embeddings.npz (written by the voice stage): event id -> its voice."""
    if not path.is_file():
        return {}
    with np.load(path) as data:
        return {str(i): data["embs"][n] for n, i in enumerate(data["ids"])}
