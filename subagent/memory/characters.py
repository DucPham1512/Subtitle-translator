"""Characters found automatically from new voices.

The voice stage gives each group of lines that sound alike but match no known character a neutral id
(`npc_005_01`: episode 5, voice 1). The id never changes; until the dialogue or a person gives the character a
name, its name is the id itself ("unnamed"). An unnamed character takes the first name proposed for it.
"""

from __future__ import annotations

import re
from pathlib import Path

from subagent.kernel import NewVoice, ReviewedLine, atomic_write_json, read_json, read_jsonl

NEW_VOICES_FILE = "new_voices.json"


def new_voice_id(prefix: str, episode_number: int, index: int) -> str:
    return f"{prefix}_{episode_number:03d}_{index:02d}"


def is_auto_id(character_id: str | None, prefix: str) -> bool:
    return bool(character_id) and re.fullmatch(rf"{re.escape(prefix)}_\d{{3}}_\d{{2}}", character_id) is not None


def is_unnamed(row: dict, prefix: str) -> bool:
    """An automatically found character that nobody has named yet."""
    cid = row.get("id")
    return is_auto_id(cid, prefix) and (row.get("name_vi") or "").strip() in ("", cid)


def load_new_voices(work: Path) -> list[NewVoice]:
    return [NewVoice.model_validate(v) for v in read_json(work / NEW_VOICES_FILE, []) or []]


def save_new_voices(work: Path, voices: list[NewVoice]) -> None:
    atomic_write_json(work / NEW_VOICES_FILE, [v.model_dump() for v in voices])


def review_voice_ids(lines: list[ReviewedLine], prefix: str) -> set[str]:
    """Automatic ids of the lines' own episode that the reviewer created in review ("New NPC", 6.4)."""
    out = set()
    for x in lines:
        m = re.fullmatch(r"ep(\d+):\d+", x.event_id)
        if m is None:
            continue
        for cid in (x.speaker, x.listener):
            if is_auto_id(cid, prefix) and int(cid.rsplit("_", 2)[-2]) == int(m.group(1)):
                out.add(cid)
    return out


def draft_voice_ids(work: Path, prefix: str) -> set[str]:
    """`review_voice_ids` over the review draft and the approved script of an episode."""
    lines = read_jsonl(work / "review_draft.jsonl", ReviewedLine) + read_jsonl(work / "approved.jsonl", ReviewedLine)
    return review_voice_ids(lines, prefix)


def episode_character_ids(work: Path, known: set[str], prefix: str = "npc", extra: set[str] | frozenset = frozenset(),
                          ) -> set[str]:
    """Ids a line of this episode may use: memory's characters, the episode's new voices, the NPCs the reviewer
    created in review, and `extra` (candidates on probation that may come back in this episode, 5.15b)."""
    return set(known) | {v.id for v in load_new_voices(work)} | draft_voice_ids(work, prefix) | set(extra)
