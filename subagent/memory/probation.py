"""Probation for new characters (5.15b): pure decisions, no I/O.

A voice (or a name the translator proposes) that is new in an episode does not become a character at once. With
at least `memory.probation_min_lines` approved lines as speaker it becomes a *candidate*: its voice and look are
remembered apart from the real banks, and it stays out of the Characters list and the prompts. When it speaks
again within `memory.probation_window` episodes, with a look that does not contradict it, it is promoted to a
character; otherwise it is dropped. The Memory Manager does the writes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from subagent.kernel.models import CastLine, ReviewedLine


@dataclass
class ReturnCheck:
    """How a candidate's lines in a later episode agree with its look."""
    lines: list[str] = field(default_factory=list)     # counting lines (approved; trusted ones in auto mode)
    agree: int = 0          # its talking sprite looks like the candidate
    neutral: int = 0        # no talking sprite, or no look remembered for the candidate
    disagree: int = 0       # someone recognised, or someone who looks different, is talking

    @property
    def promote(self) -> bool:
        """Back, and the picture does not mostly say it is someone else."""
        return bool(self.lines) and self.disagree < self.agree + self.neutral

    def describe(self) -> str:
        return f"{len(self.lines)} lines (look: {self.agree} agree, {self.neutral} n/a, {self.disagree} disagree)"


def speaker_lines(approved: list[ReviewedLine], cid: str) -> list[ReviewedLine]:
    return [x for x in approved if x.approved and not x.deleted and x.line_type == "dialogue" and x.speaker == cid]


def _unit(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, np.float32)
    n = float(np.linalg.norm(v))
    return v / n if n else v


def check_return(lines: list[ReviewedLine], cast: dict[str, CastLine], cast_embs: np.ndarray | None,
                 sprites: list[np.ndarray], similarity: float) -> ReturnCheck:
    """Compare each counting line's talking sprite with the candidate's remembered look."""
    out = ReturnCheck(lines=[x.event_id for x in lines])
    looks = np.stack([_unit(s) for s in sprites]) if sprites else None
    for x in lines:
        c = cast.get(x.event_id)
        talker = c.talker() if c is not None else None
        if talker is None:
            out.neutral += 1
        elif talker.character:
            out.disagree += 1                       # a known character is the one talking
        elif looks is None or cast_embs is None or talker.index >= len(cast_embs):
            out.neutral += 1
        elif float(np.max(looks @ _unit(cast_embs[talker.index]))) >= similarity:
            out.agree += 1
        else:
            out.disagree += 1
    return out


def candidate_voice(lines: list[ReviewedLine], voices: dict[str, np.ndarray]) -> np.ndarray | None:
    """Mean voice of the candidate's lines (from voice_embeddings.npz); None when none was saved."""
    vecs = [_unit(voices[x.event_id]) for x in lines if x.event_id in voices]
    return _unit(np.mean(vecs, axis=0)) if vecs else None


def candidate_looks(lines: list[ReviewedLine], cast: dict[str, CastLine],
                    cast_embs: np.ndarray | None) -> list[tuple[str, np.ndarray]]:
    """The unrecognised talking sprites on the candidate's lines: (event id, image features)."""
    out = []
    if cast_embs is None:
        return out
    for x in lines:
        c = cast.get(x.event_id)
        talker = c.talker() if c is not None else None
        if talker is not None and not talker.character and talker.index < len(cast_embs):
            out.append((x.event_id, _unit(cast_embs[talker.index])))
    return out
