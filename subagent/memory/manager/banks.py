"""The voice bank, confusable pairs and sprite bank (5.8a, 5.8b)."""

from __future__ import annotations

import logging

import numpy as np

from subagent.memory.manager.proposals import (  # noqa: F401
    _PUNCT,
    merge_proposals,
    replaced_term,
    reviewed_glossary,
)
from subagent.memory.manager.results import (  # noqa: F401
    ApplyResult,
    CommitInfo,
    Conflict,
    MemoryDiff,
    PendingUpdate,
    TableDiff,
    describe_update,
    dumps_aliases,
    held_updates,
)
from subagent.memory.manager.rows import (  # noqa: F401
    BACKUP_ITEMS,
    BRIEFING_FILES,
    COLUMNS,
    EVIDENCE_SOURCES,
    KIND_ORDER,
    KIND_TABLE,
    LOCKING_SOURCES,
    REQUIRED,
    UPDATE_REJECTIONS_FILE,
    UPDATES_FILE,
    _content,
    _current_evidence,
    _delete,
    _fetch,
    _insert,
    _loggable,
    _update,
    _where,
)
from subagent.util import (
    now_iso,
)

log = logging.getLogger(__name__)


class BanksMixin:
    """The voice bank, confusable pairs and sprite bank (5.8a, 5.8b). Part of MemoryManager."""

    def write_sprites(self, add: list[tuple[str, np.ndarray, str, str]], stats: dict[int, tuple[int, int]],
                      remove: list[int], *, max_per_character: int, source: str = "system",
                      episode_id: str | None = None, base: dict[int, tuple[int, int]] | None = None,
                      undo: dict[int, tuple[int, int, bool]] | None = None) -> dict[str, int]:
        """Sprite bank update in one transaction: new exemplars (character, embedding, episode, event),
        right/wrong counts, removals; then each character keeps its `max_per_character` best-confirmed.

        With `episode_id` the update is that episode's learning and is re-finish safe: `undo` (what learning it
        did last time, `MemoryStore.sprite_feedback`) is reversed first (its added exemplars deleted, its votes
        taken back to `base`, the counts without them), and this run's votes and additions are recorded."""
        self._ensure_schema()
        now = now_iso()
        added: dict[str, int] = {}
        dropped: dict[str, int] = {}
        base = base or {}
        with self._transaction() as conn:
            known = {r["id"] for r in conn.execute("SELECT id FROM characters")}
            if episode_id is not None:
                for ex_id, (_, _, was_added) in (undo or {}).items():
                    if was_added:
                        row = conn.execute("SELECT character_id FROM sprite_bank WHERE id=?", (ex_id,)).fetchone()
                        if row:
                            conn.execute("DELETE FROM sprite_bank WHERE id=?", (ex_id,))
                            dropped[row["character_id"]] = dropped.get(row["character_id"], 0) + 1
                    elif ex_id in base:
                        conn.execute("UPDATE sprite_bank SET right=?, wrong=? WHERE id=?", (*base[ex_id], ex_id))
                conn.execute("DELETE FROM sprite_feedback WHERE episode_id=?", (episode_id,))
            for ex_id, (right, wrong) in stats.items():
                conn.execute("UPDATE sprite_bank SET right=?, wrong=? WHERE id=?", (right, wrong, ex_id))
                if episode_id is not None:
                    b_right, b_wrong = base.get(ex_id, (0, 0))
                    if (right, wrong) != (b_right, b_wrong):
                        conn.execute("INSERT INTO sprite_feedback (exemplar_id, episode_id, right, wrong, added) "
                                     "VALUES (?,?,?,?,0)", (ex_id, episode_id, right - b_right, wrong - b_wrong))
            for ex_id in remove:
                row = conn.execute("SELECT character_id FROM sprite_bank WHERE id=?", (ex_id,)).fetchone()
                if row:
                    conn.execute("DELETE FROM sprite_bank WHERE id=?", (ex_id,))
                    dropped[row["character_id"]] = dropped.get(row["character_id"], 0) + 1
            for char, emb, ep, event in add:
                if char not in known:
                    continue
                vec = np.asarray(emb, np.float32)
                vec = (vec / (np.linalg.norm(vec) or 1.0)).astype(np.float16)
                cur = conn.execute("INSERT INTO sprite_bank (character_id, embedding, episode_id, event_id, right, "
                                   "wrong, added_at) VALUES (?,?,?,?,0,0,?)", (char, vec.tobytes(), ep, event, now))
                if episode_id is not None:
                    conn.execute("INSERT INTO sprite_feedback (exemplar_id, episode_id, right, wrong, added) "
                                 "VALUES (?,?,0,0,1)", (cur.lastrowid, episode_id))
                added[char] = added.get(char, 0) + 1
            for char in {r["character_id"] for r in conn.execute("SELECT DISTINCT character_id FROM sprite_bank")}:
                ids = [r["id"] for r in conn.execute(
                    "SELECT id FROM sprite_bank WHERE character_id=? ORDER BY (right - wrong) DESC, id DESC", (char,))]
                for ex_id in ids[max_per_character:]:
                    conn.execute("DELETE FROM sprite_bank WHERE id=?", (ex_id,))
                    dropped[char] = dropped.get(char, 0) + 1
            conn.execute("DELETE FROM sprite_feedback WHERE exemplar_id NOT IN (SELECT id FROM sprite_bank)")
            for char in sorted(set(added) | set(dropped)):
                self._log(conn, "update", "sprite_bank", char, None,
                          {"added": added.get(char, 0), "removed": dropped.get(char, 0)}, None,
                          added.get(char, 0), source=source)
        return {"added": sum(added.values()), "removed": sum(dropped.values())}


    def write_voices(self, centroids: dict[str, tuple[np.ndarray, int]], *, source: str = "bootstrap") -> None:
        self._ensure_schema()
        with self._transaction() as conn:
            for char_id, (emb, n_clips) in centroids.items():
                emb = np.asarray(emb, dtype=np.float32)
                norm = float(np.linalg.norm(emb))
                emb = emb / norm if norm else emb
                before = _fetch(conn, "voice_bank", char_id)
                row = {"character_id": char_id, "embedding": emb.tobytes(), "n_clips": int(n_clips),
                       "updated_at": now_iso()}
                conn.execute("INSERT OR REPLACE INTO voice_bank VALUES (:character_id, :embedding, :n_clips, :updated_at)", row)
                self._log(conn, "update" if before else "insert", "voice_bank", char_id, before, row, None,
                          int(n_clips), source=source)


    def write_confusable_pairs(self, pairs: dict[tuple[str, str], float], *, involving: set[str] | None = None,
                               source: str = "bootstrap") -> None:
        """Replace all pairs, or only the pairs involving the given characters."""
        self._ensure_schema()
        with self._transaction() as conn:
            if involving is None:
                conn.execute("DELETE FROM confusable_pairs")
            else:
                for c in involving:
                    conn.execute("DELETE FROM confusable_pairs WHERE a=? OR b=?", (c, c))
            for (a, b), sim in pairs.items():
                a, b = sorted((a, b))
                conn.execute("INSERT OR REPLACE INTO confusable_pairs VALUES (?,?,?)", (a, b, float(sim)))
                self._log(conn, "insert", "confusable_pairs", f"{a}|{b}", None,
                          {"a": a, "b": b, "similarity": float(sim)}, None, 0, source=source)
