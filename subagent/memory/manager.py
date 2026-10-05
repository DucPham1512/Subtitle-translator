"""Memory Manager (5.15): the only component allowed to write memory.

Write rules:
- A locked entry changes only through a human proposal (bootstrap seeds are human-reviewed, so they count too).
- Translator proposals apply only when every evidence line was approved.
- Human and bootstrap writes lock the entry.
- A proposal that conflicts with an unlocked entry applies only with more evidence than the current entry;
  otherwise it goes to conflicts.md (and conflicts.json, its machine-readable twin) for review.
- Every write runs in a transaction and adds a memory_log row; rejections are logged as op="rejected".
"""

from __future__ import annotations

import contextlib
import difflib
import json
import logging
import re
import shutil
import sqlite3
import tempfile
from collections.abc import Iterator
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field

from subagent.characters import is_unnamed
from subagent.config import Config, Paths
from subagent.errors import JobRunningError, MemoryLockedError, SubagentError
from subagent.joblock import running_jobs
from subagent.memory import briefings as bf
from subagent.memory.store import (
    SCHEMA,
    STATUSES,
    TABLES,
    MemoryStore,
    dumps,
    episode_number,
    migrate,
    row_key,
)
from subagent.models import EditRecord, LineTranslation, MemoryProposal, NewVoice, ReviewedLine
from subagent.textutil import contains_term
from subagent.util import (
    FileLock,
    append_jsonl,
    atomic_write_json,
    atomic_write_text,
    now_iso,
    read_json,
    sha256_json,
)

log = logging.getLogger(__name__)

KIND_ORDER = {"character": 0, "glossary": 1, "pronoun_pair": 2, "line_decision": 3, "style_rule": 4, "briefing": 5}
KIND_TABLE = {"character": "characters", "glossary": "glossary", "pronoun_pair": "pronoun_pairs",
              "line_decision": "line_decisions"}
COLUMNS = {
    "characters": ["id", "name_zh", "name_vi", "description", "status", "status_note", "generic"],
    "glossary": ["zh", "vi", "pinyin", "type", "notes", "first_episode"],
    "pronoun_pairs": ["speaker_id", "listener_id", "self_term", "address_term", "context", "since_episode"],
    "line_decisions": ["zh", "remove_count", "keep_count", "last_episode"],
}
REQUIRED = {
    "characters": ["id", "name_zh", "name_vi"],
    "glossary": ["zh", "vi"],
    "pronoun_pairs": ["speaker_id", "listener_id", "self_term", "address_term"],
    "line_decisions": ["zh"],
}
LOCKING_SOURCES = {"human", "bootstrap"}
BRIEFING_FILES = {"story_so_far.md", "INDEX.md"}


class ApplyResult(BaseModel):
    applied: list[str] = Field(default_factory=list)       # "table:key"
    unchanged: list[str] = Field(default_factory=list)
    rejected: list[tuple[str, str]] = Field(default_factory=list)   # ("table:key", reason)
    conflicts: list[str] = Field(default_factory=list)
    renamed: list[tuple[str, str]] = Field(default_factory=list)    # (character id, new name): first names
    lifecycle: dict[str, int] = Field(default_factory=dict)         # status -> characters moved to it
    probation: dict[str, int] = Field(default_factory=dict)         # candidates / promoted / dropped (5.15b)

    @property
    def writes(self) -> int:
        return len(self.applied)


class Conflict(BaseModel):
    id: str
    ts: str
    kind: str
    table: str
    key: str
    current: dict
    proposed: dict
    source: str
    evidence: list[str]
    reason: str


class CommitInfo(BaseModel):
    sha: str
    date: str
    message: str
    changes: int | None = None


class TableDiff(BaseModel):
    added: list[dict] = Field(default_factory=list)
    changed: list[tuple[dict, dict]] = Field(default_factory=list)
    removed: list[dict] = Field(default_factory=list)


class MemoryDiff(BaseModel):
    sha: str
    parent: str | None
    tables: dict[str, TableDiff] = Field(default_factory=dict)
    text_diff: str = ""


class MemoryManager:
    def __init__(self, paths: Paths, config: Config):
        self.paths = paths
        self.config = config
        self.dir = paths.memory
        self.db = paths.memory_db
        self.store = MemoryStore(self.db)
        self._lock_depth = 0
        self._lock = FileLock(self.dir / ".lock", timeout=30, error=MemoryLockedError,
                              message="Memory is being written by another process")

    # -- setup / locking ----------------------------------------------------------------------------

    def ensure_repo(self) -> None:
        from subagent.media import git

        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "briefings").mkdir(exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)
        if not (self.dir / "briefings" / "INDEX.md").is_file():
            atomic_write_text(self.dir / "briefings" / "INDEX.md", bf.render_index([]))
        if not (self.dir / "style_rules.md").is_file():
            atomic_write_text(self.dir / "style_rules.md", bf.render_style_rules([]))
        if not (self.dir / ".git").exists():
            git(["init", "-q"], self.dir)
            git(["config", "core.autocrlf", "false"], self.dir)
            if not git(["config", "user.email"], self.dir, check=False).strip():
                git(["config", "user.email", "subagent@localhost"], self.dir)
                git(["config", "user.name", "Subtitle Agent"], self.dir)
            atomic_write_text(self.dir / ".gitignore", ".lock\n*.tmp\n")
            atomic_write_text(self.dir / ".gitattributes", "*.db binary\n")
            self.commit("init memory")

    @contextlib.contextmanager
    def locked(self) -> Iterator[None]:
        """Reentrant within this process; excludes other processes via data/memory/.lock."""
        if self._lock_depth == 0:
            self.dir.mkdir(parents=True, exist_ok=True)
            self._lock.acquire()
        self._lock_depth += 1
        try:
            yield
        finally:
            self._lock_depth -= 1
            if self._lock_depth == 0:
                self._lock.release()

    @contextlib.contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.dir.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        if not self.db.is_file() or not (self.dir / ".git").exists():
            self.ensure_repo()
            return
        with self._connect() as conn:   # tables added in later versions (CREATE ... IF NOT EXISTS)
            conn.executescript(SCHEMA)
            migrate(conn)

    # -- apply --------------------------------------------------------------------------------------

    def apply(self, proposals: list[MemoryProposal], *, approved_ids: set[str] | None = None,
              episode_id: str | None = None) -> ApplyResult:
        self._ensure_schema()
        result = ApplyResult()
        proposals = sorted(merge_proposals(proposals), key=lambda p: KIND_ORDER.get(p.kind, 9))
        file_ops: list[MemoryProposal] = []
        with self.locked(), self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                for p in proposals:
                    if p.kind in ("style_rule", "briefing"):
                        file_ops.append(p)
                        continue
                    self._apply_row(conn, p, approved_ids, episode_id, result)
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            self._apply_files(file_ops, result)
            if result.renamed:
                self._name_in_briefings(result.renamed)
            if result.conflicts:
                self._render_conflicts()
        return result

    def _apply_row(self, conn: sqlite3.Connection, p: MemoryProposal, approved_ids: set[str] | None,
                   episode_id: str | None, result: ApplyResult) -> None:
        table = KIND_TABLE[p.kind]
        payload = {k: v for k, v in p.payload.items() if k in COLUMNS[table] or k == "_delete"}
        # the app's lock toggle: only a human may set the lock explicitly (including unlocking)
        explicit_lock = p.payload.get("_locked") if p.source == "human" else None
        if table == "pronoun_pairs":
            payload["context"] = (payload.get("context") or "").strip()
        for k, v in list(payload.items()):
            if isinstance(v, str):
                payload[k] = v.strip()
        if table == "characters":
            # the lifecycle status is set by the lifecycle rules or by a person, never by a model's proposal
            if p.source != "human":
                payload.pop("generic", None)
            elif "generic" in payload:
                payload["generic"] = int(str(payload["generic"]).strip().lower() in ("1", "true", "yes"))
            if p.source != "human" or not payload.get("status"):
                payload.pop("status", None)
                payload.pop("status_note", None)
            elif payload["status"] not in STATUSES:
                self._reject(conn, result, table, str(payload.get("id", "?")), p,
                             f"status must be one of {', '.join(STATUSES)}")
                return
        try:
            key = row_key(table, payload)
        except KeyError:
            self._reject(conn, result, table, "?", p, "missing key fields")
            return
        label = f"{table}:{key}"

        if p.source == "translator" and (approved_ids is None or not p.evidence or not set(p.evidence) <= approved_ids):
            self._reject(conn, result, table, key, p, "evidence lines not approved")
            return

        existing = _fetch(conn, table, key)
        if payload.pop("_delete", False):
            if existing is None:
                result.unchanged.append(label)
                return
            if existing["locked"] and p.source != "human":
                self._reject(conn, result, table, key, p, "entry is locked")
                return
            if p.source not in ("human",):
                self._reject(conn, result, table, key, p, "only human edits may delete entries")
                return
            _delete(conn, table, key)
            self._log(conn, "delete", table, key, existing, None, p, len(p.evidence))
            result.applied.append(label)
            return

        if existing is not None:
            changes = {k: v for k, v in payload.items() if k in COLUMNS[table] and existing.get(k) != v
                       and not (v in (None, "") and existing.get(k) in (None, ""))}
            target_lock = (int(bool(explicit_lock)) if explicit_lock is not None
                           else 1 if p.source in LOCKING_SOURCES else existing["locked"])
            if not changes and target_lock == existing["locked"]:
                result.unchanged.append(label)
                return
            if existing["locked"] and p.source not in LOCKING_SOURCES:
                self._reject(conn, result, table, key, p, "entry is locked")
                return
            # an automatically found character nobody has named yet takes the first name proposed for it
            first_name = (table == "characters" and is_unnamed(existing, self.config.voice.new_voice_prefix)
                          and bool(changes.get("name_vi")) and changes["name_vi"] != key)
            if not existing["locked"] and p.source not in LOCKING_SOURCES and changes and not first_name:
                current_evidence = _current_evidence(conn, table, key)
                if len(p.evidence) <= current_evidence:
                    self._conflict(conn, result, table, key, existing, p,
                                   f"{len(p.evidence)} evidence vs {current_evidence} for the current entry")
                    return
            after = {**existing, **changes, "updated_at": now_iso(), "locked": target_lock}
            if table == "glossary":
                after["source"] = p.source
            _update(conn, table, key, after)
            self._log(conn, "update", table, key, existing, after, p, len(p.evidence))
            result.applied.append(label)
            if first_name:
                result.renamed.append((key, after["name_vi"]))
            return

        missing = [c for c in REQUIRED[table] if not payload.get(c)]
        if missing:
            self._reject(conn, result, table, key, p, f"missing fields: {', '.join(missing)}")
            return
        if table == "pronoun_pairs":
            unknown = [c for c in (payload["speaker_id"], payload["listener_id"]) if _fetch(conn, "characters", c) is None]
            if unknown:
                self._reject(conn, result, table, key, p, f"unknown character(s): {', '.join(unknown)}")
                return
            payload.setdefault("since_episode", episode_id)
        row = {c: payload.get(c) for c in COLUMNS[table]}
        if table == "glossary":
            row["source"] = p.source
            row["first_episode"] = row.get("first_episode") or episode_id
        row["locked"] = (int(bool(explicit_lock)) if explicit_lock is not None
                         else 1 if p.source in LOCKING_SOURCES else 0)
        row["updated_at"] = now_iso()
        if table == "characters":
            row["status"] = row.get("status") or "active"
            row["generic"] = int(row.get("generic") or 0)
        _insert(conn, table, row)
        self._log(conn, "insert", table, key, None, row, p, len(p.evidence))
        result.applied.append(label)

    def _log(self, conn: sqlite3.Connection, op: str, table: str, key: str, before: dict | None,
             after: dict | None, p: MemoryProposal | None, evidence: int, source: str | None = None,
             reason: str | None = None) -> None:
        conn.execute(
            "INSERT INTO memory_log (ts, op, tbl, key, before_json, after_json, source, reason, evidence_count) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (now_iso(), op, table, key, dumps(_loggable(before)) if before is not None else None,
             dumps(_loggable(after)) if after is not None else None, source or (p.source if p else "system"),
             reason or (", ".join(p.evidence[:20]) if p and p.evidence else None), evidence),
        )

    def _reject(self, conn: sqlite3.Connection, result: ApplyResult, table: str, key: str,
                p: MemoryProposal, reason: str) -> None:
        self._log(conn, "rejected", table, key, None, p.payload, p, len(p.evidence), reason=reason)
        result.rejected.append((f"{table}:{key}", reason))

    def _conflict(self, conn: sqlite3.Connection, result: ApplyResult, table: str, key: str, existing: dict,
                  p: MemoryProposal, reason: str) -> None:
        self._reject(conn, result, table, key, p, f"conflict: {reason}")
        conflicts = self.conflicts()
        ts = now_iso()
        conflicts.append(Conflict(
            id="c" + sha256_json([table, key, p.payload, p.evidence, ts])[:10], ts=ts,
            kind=p.kind, table=table, key=key, current=_loggable(existing), proposed=p.payload, source=p.source,
            evidence=p.evidence, reason=reason,
        ))
        atomic_write_json(self.dir / "conflicts.json", [c.model_dump() for c in conflicts])
        result.conflicts.append(f"{table}:{key}")

    # -- markdown-backed proposals ------------------------------------------------------------------

    def _apply_files(self, ops: list[MemoryProposal], result: ApplyResult) -> None:
        style_ops = [p for p in ops if p.kind == "style_rule"]
        if style_ops:
            rules = bf.read_style_rules(self.dir)
            for p in style_ops:
                action = p.payload.get("action", "add")
                text = str(p.payload.get("rule", "")).strip()
                if not text:
                    result.rejected.append(("style_rules:?", "empty rule"))
                    continue
                match = next((r for r in rules if r.rule.lower() == text.lower()), None)
                if action == "remove":
                    rules = [r for r in rules if r is not match]
                elif match is not None:
                    match.uses += int(p.payload.get("uses", 1))
                    if p.payload.get("example"):
                        match.example = str(p.payload["example"])
                else:
                    rules.append(bf.StyleRule(rule=text, example=str(p.payload.get("example", "")),
                                              uses=int(p.payload.get("uses", 1))))
                result.applied.append(f"style_rules:{text[:60]}")
            rules = bf.cap_style_rules(rules, self.config.memory.style_rules_max)
            atomic_write_text(self.dir / "style_rules.md", bf.render_style_rules(rules))
            self._log_file("style_rules.md", style_ops[0].source)
        for p in (p for p in ops if p.kind == "briefing"):
            name = str(p.payload.get("file", ""))
            content = str(p.payload.get("content", ""))
            if not (name in BRIEFING_FILES or (name.startswith("ep") and name.endswith(".md") and "/" not in name
                                               and "\\" not in name)):
                result.rejected.append((f"briefings:{name}", "unknown briefing file"))
                continue
            atomic_write_text(self.dir / "briefings" / name, content.rstrip() + "\n")
            self._log_file(f"briefings/{name}", p.source)
            result.applied.append(f"briefings:{name}")

    def _name_in_briefings(self, renamed: list[tuple[str, str]]) -> None:
        """Briefings written while a character had no name mention its id; use the new name in every episode."""
        folder = self.dir / "briefings"
        for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
            text = path.read_text(encoding="utf-8")
            new = text
            for cid, name in renamed:
                new = re.sub(rf"(?<![\w]){re.escape(cid)}(?![\w])", name, new)
            if new != text:
                atomic_write_text(path, new)
                self._log_file(f"briefings/{path.name}", "system")

    def _log_file(self, name: str, source: str) -> None:
        with self._connect() as conn:
            self._log(conn, "update", "files", name, None, None, None, 0, source=source)

    # -- sprites ------------------------------------------------------------------------------------

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
        with self.locked(), self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
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
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return {"added": sum(added.values()), "removed": sum(dropped.values())}

    # -- voices -------------------------------------------------------------------------------------

    def write_voices(self, centroids: dict[str, tuple[np.ndarray, int]], *, source: str = "bootstrap") -> None:
        self._ensure_schema()
        with self.locked(), self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
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
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    def write_confusable_pairs(self, pairs: dict[tuple[str, str], float], *, involving: set[str] | None = None,
                               source: str = "bootstrap") -> None:
        """Replace all pairs, or only the pairs involving the given characters."""
        self._ensure_schema()
        with self.locked(), self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
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
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    # -- episode update -----------------------------------------------------------------------------

    def episode_update(self, episode_id: str, approved: list[ReviewedLine], translations: list[LineTranslation],
                       edits: list[EditRecord], llm: object | None,
                       line_decisions: tuple[list[str], list[str]] | None = None,
                       new_voices: list[NewVoice] | None = None, mode: str = "human") -> ApplyResult:
        """After an episode: apply approved + human-edit proposals, write briefings, commit. All or nothing."""
        self._ensure_schema()
        with self.locked(), self._backup():
            approved = [line for line in approved if not line.deleted]
            approved_ids = {line.event_id for line in approved if line.approved}
            proposals = [p for t in translations if t.event_id in approved_ids for p in t.proposals]
            probation: dict[str, int] = {}
            if self.config.memory.probation:
                proposals, probation, extra_ids = self.probation(episode_id, approved, approved_ids, proposals,
                                                                 new_voices or [], mode)
                approved_ids |= extra_ids
            else:
                proposals = self.new_voice_characters(episode_id, approved, new_voices or []) + proposals
            proposals += self.mine_edits(episode_id, approved, translations, edits)
            result = self.apply(proposals, approved_ids=approved_ids, episode_id=episode_id)
            result.probation = probation
            if line_decisions is not None:
                self.record_line_decisions(episode_id, *line_decisions)
            fates = self.update_briefings(episode_id, approved, llm) if llm is not None else []
            result.lifecycle = self.update_lifecycle(episode_id, approved, fates)
            moved = "".join(f", {n} {status}" for status, n in sorted(result.lifecycle.items()))
            moved += "".join(f", {n} {kind}" for kind, n in sorted(probation.items()) if n)
            self.commit(f"episode {episode_id}: {result.writes} writes{moved}")
        return result

    def probation(self, episode_id: str, approved: list[ReviewedLine], approved_ids: set[str],
                  proposals: list[MemoryProposal], voices: list[NewVoice], mode: str,
                  ) -> tuple[list[MemoryProposal], dict[str, int], set[str]]:
        """New characters wait on probation (5.15b). In one transaction: promote the candidates that came back,
        make this episode's new voices and new names candidates, hold the proposals about candidates, drop the
        candidates whose window has passed. Returns the proposals to apply now, counts, and evidence ids of
        held proposals released by a promotion."""
        from subagent.memory import probation as pb
        from subagent.memory.voice_learning import trusted_auto_lines
        from subagent.models import CastLine
        from subagent.stages.voice import load_line_voices
        from subagent.util import read_jsonl

        cfg = self.config.memory
        work = self.paths.episode_dir(episode_id)
        current = episode_number(episode_id)
        cast = {c.event_id: c for c in read_jsonl(work / "cast.jsonl", CastLine)}
        cast_embs = np.load(work / "cast_embeddings.npy") if (work / "cast_embeddings.npy").is_file() else None
        if cast_embs is not None and (cast_embs.ndim != 2 or not cast_embs.size):
            cast_embs = None
        line_voices = load_line_voices(work / "voice_embeddings.npz")
        counts = {"candidates": 0, "promoted": 0, "dropped": 0}
        keep: list[MemoryProposal] = []
        released: set[str] = set()
        now = now_iso()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                known = {r["id"] for r in conn.execute("SELECT id FROM characters")}
                rows = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM candidates")}
                for cid, r in list(rows.items()):         # rerun-safe: this episode's candidates are rebuilt
                    if r["first_episode"] == episode_id and r["status"] == "candidate":
                        conn.execute("DELETE FROM candidate_sprites WHERE candidate_id=?", (cid,))
                        conn.execute("DELETE FROM candidates WHERE id=?", (cid,))
                        del rows[cid]
                trusted = None
                if mode == "auto":
                    trusted = {x.event_id for x in trusted_auto_lines(self.paths, self.config, episode_id,
                                                                       known | set(rows), min_ms=0)}
                # 1. candidates that came back within their window
                for cid, r in sorted(rows.items()):
                    first = episode_number(r["first_episode"])
                    if (r["status"] != "candidate" or cid in known or first is None or current is None
                            or not first < current <= first + cfg.probation_window):
                        continue
                    lines = pb.speaker_lines(approved, cid)
                    if trusted is not None:
                        lines = [x for x in lines if x.event_id in trusted]
                    if not lines:
                        continue
                    sprites = [np.frombuffer(s["embedding"], dtype=np.float16).astype(np.float32) for s in
                               conn.execute("SELECT embedding FROM candidate_sprites WHERE candidate_id=?", (cid,))]
                    check = pb.check_return(lines, cast, cast_embs, sprites, self.config.cast.match_similarity)
                    if not check.promote and mode != "human":
                        log.info("probation: %s is back in %s but its look disagrees: %s", cid, episode_id,
                                 check.describe())
                        continue
                    # human mode: the reviewer assigned these lines, so the picture cannot veto the return; a look
                    # the picture disagrees with is not copied into the sprite bank (sprite learning relearns it)
                    evidence = check.describe() if check.promote else f"assigned by the reviewer; {check.describe()}"
                    self._promote(conn, r, episode_id, evidence, now, with_look=check.promote)
                    known.add(cid)
                    counts["promoted"] += 1
                    for d in json.loads(r["pending_json"] or "[]"):
                        p = MemoryProposal.model_validate(d)
                        keep.append(p)
                        released |= set(p.evidence)
                # 2. this episode's new voices and new names become candidates
                named: dict[str, MemoryProposal] = {}
                for p in proposals:
                    cid = str(p.payload.get("id") or "")
                    if p.kind == "character" and p.source == "translator" and cid and cid not in known:
                        named.setdefault(cid, p)
                for cid in dict.fromkeys([v.id for v in voices if not v.returning_from] + sorted(named)):
                    if cid in known or cid in rows:
                        continue
                    lines = pb.speaker_lines(approved, cid)
                    if len(lines) < cfg.probation_min_lines:
                        continue
                    payload = named[cid].payload if cid in named and set(named[cid].evidence) <= approved_ids else {}
                    voice = pb.candidate_voice(lines, line_voices)
                    row = {"id": cid, "first_episode": episode_id, "name_zh": payload.get("name_zh") or None,
                           "name_vi": payload.get("name_vi") or None, "description": payload.get("description") or None,
                           "embedding": voice.astype(np.float32).tobytes() if voice is not None else None,
                           "n_lines": len(lines), "pending_json": "[]", "status": "candidate",
                           "status_note": f"{len(lines)} lines in {episode_id}", "updated_at": now}
                    _insert(conn, "candidates", row)
                    for event_id, emb in pb.candidate_looks(lines, cast, cast_embs):
                        conn.execute("INSERT INTO candidate_sprites (candidate_id, embedding, episode_id, event_id) "
                                     "VALUES (?,?,?,?)", (cid, emb.astype(np.float16).tobytes(), episode_id, event_id))
                    self._log(conn, "insert", "candidates", cid, None, row, None, len(lines), source="system",
                              reason=f"on probation: {len(lines)} lines in {episode_id}")
                    rows[cid] = row
                    counts["candidates"] += 1
                # 3. proposals about candidates wait for the promotion
                waiting = {cid for cid, r in rows.items() if r["status"] == "candidate" and cid not in known}
                pending: dict[str, list[dict]] = {}
                for p in proposals:
                    cid = str(p.payload.get("id") or "")
                    if p.kind == "character" and p.source == "translator" and cid and cid not in known:
                        if cid in waiting and set(p.evidence) <= approved_ids:
                            self._name_candidate(conn, rows[cid], p, now)
                        else:
                            self._log(conn, "rejected", "characters", cid or "?", None, p.payload, p,
                                      len(p.evidence), reason="probation: fewer than "
                                      f"{cfg.probation_min_lines} approved lines as speaker")
                        continue
                    if p.kind == "pronoun_pair":
                        ids = {str(p.payload.get("speaker_id")), str(p.payload.get("listener_id"))}
                        held = sorted(ids & waiting)
                        if held and not ids - known - waiting and set(p.evidence) <= approved_ids:
                            pending.setdefault(held[0], []).append(p.model_dump())
                            continue
                    keep.append(p)
                for cid, items in pending.items():
                    before = json.loads(rows[cid]["pending_json"] or "[]")
                    conn.execute("UPDATE candidates SET pending_json=?, updated_at=? WHERE id=?",
                                 (json.dumps(before + items, ensure_ascii=False), now, cid))
                # 4. candidates whose window has passed
                for cid, r in sorted(rows.items()):
                    first = episode_number(r["first_episode"])
                    if (r["status"] == "candidate" and cid not in known and first is not None and current is not None
                            and current > first + cfg.probation_window):
                        note = f"not back within {cfg.probation_window} episodes (checked at {episode_id})"
                        conn.execute("UPDATE candidates SET status='dropped', status_note=?, updated_at=? WHERE id=?",
                                     (note, now, cid))
                        self._log(conn, "update", "candidates", cid, r, {**r, "status": "dropped"}, None, 0,
                                  source="system", reason=note)
                        counts["dropped"] += 1
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return keep, counts, released

    def _promote(self, conn: sqlite3.Connection, cand: dict, episode_id: str, evidence: str, now: str,
                 with_look: bool = True) -> None:
        """A candidate that came back becomes a character, with its voice, look (unless `with_look` is false)
        and first appearance."""
        cid = cand["id"]
        row = {"id": cid, "name_zh": cand["name_zh"] or cid, "name_vi": cand["name_vi"] or cid,
               "description": cand["description"] or f"Voice found automatically in {cand['first_episode']}; "
                                                     f"back in {episode_id}",
               "locked": 0, "updated_at": now, "status": "active", "status_note": None, "generic": 0}
        _insert(conn, "characters", row)
        reason = f"promoted from probation: back in {episode_id}, {evidence}"
        self._log(conn, "insert", "characters", cid, None, row, None, cand["n_lines"], source="system", reason=reason)
        if cand["embedding"] and _fetch(conn, "voice_bank", cid) is None:
            conn.execute("INSERT INTO voice_bank VALUES (?,?,?,?)", (cid, cand["embedding"], cand["n_lines"], now))
        looks = conn.execute("SELECT * FROM candidate_sprites WHERE candidate_id=?", (cid,)).fetchall() \
            if with_look else []
        for s in looks:
            conn.execute("INSERT INTO sprite_bank (character_id, embedding, episode_id, event_id, right, wrong, added_at) "
                         "VALUES (?,?,?,?,0,0,?)", (cid, s["embedding"], s["episode_id"], s["event_id"], now))
        conn.execute("INSERT OR REPLACE INTO appearances (character_id, episode_id, lines) VALUES (?,?,?)",
                     (cid, cand["first_episode"], cand["n_lines"]))
        conn.execute("UPDATE candidates SET status='promoted', status_note=?, updated_at=? WHERE id=?", (reason, now, cid))
        cand["status"] = "promoted"

    def _name_candidate(self, conn: sqlite3.Connection, cand: dict, p: MemoryProposal, now: str) -> None:
        """A name for a candidate: the first one proposed is kept (as for unnamed characters)."""
        if cand.get("name_vi") and cand["name_vi"] != cand["id"]:
            return
        name_vi = str(p.payload.get("name_vi") or "").strip()
        if not name_vi or name_vi == cand["id"]:
            return
        after = {**cand, "name_zh": str(p.payload.get("name_zh") or "").strip() or cand.get("name_zh"),
                 "name_vi": name_vi, "description": p.payload.get("description") or cand.get("description"),
                 "updated_at": now}
        conn.execute("UPDATE candidates SET name_zh=?, name_vi=?, description=?, updated_at=? WHERE id=?",
                     (after["name_zh"], after["name_vi"], after["description"], now, cand["id"]))
        self._log(conn, "update", "candidates", cand["id"], cand, after, p, len(p.evidence))
        cand.update(after)

    def update_lifecycle(self, episode_id: str, approved: list[ReviewedLine], fates: list | None = None) -> dict[str, int]:
        """Record who appears in this episode, then keep, archive or bring back unlocked characters (5.15a).

        kept: seen in two consecutive episodes, or the story says they return. archived: not seen for
        `memory.archive_after_absent` episodes (one-offs only), or the story says they died or left for good.
        Archived characters leave prompts and voice matching; a later approved line brings them back.
        Locked characters (confirmed by a person) are never changed here.
        """
        self._ensure_schema()
        present: dict[str, int] = {}
        for x in approved:
            if x.approved and not x.deleted:
                for cid in {x.speaker, x.listener} - {None}:
                    present[cid] = present.get(cid, 0) + 1
        fate_by_id = {f.id: f for f in fates or []}
        moved: dict[str, int] = {}
        with self.locked(), self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                known = {r["id"] for r in conn.execute("SELECT id FROM characters")}
                if conn.execute("SELECT COUNT(*) FROM appearances").fetchone()[0] == 0:
                    self._backfill_appearances(conn, known, skip=episode_id)
                conn.execute("DELETE FROM appearances WHERE episode_id=?", (episode_id,))   # rerun-safe
                for cid, n in sorted(present.items()):
                    if cid in known:
                        conn.execute("INSERT INTO appearances (character_id, episode_id, lines) VALUES (?,?,?)",
                                     (cid, episode_id, n))
                if self.config.memory.character_lifecycle:
                    seen: dict[str, set[int]] = {}
                    for r in conn.execute("SELECT character_id, episode_id FROM appearances"):
                        number = episode_number(r["episode_id"])
                        if number is not None:
                            seen.setdefault(r["character_id"], set()).add(number)
                    processed = set().union(*seen.values()) if seen else set()
                    current = episode_number(episode_id)
                    for row in [dict(r) for r in conn.execute("SELECT * FROM characters WHERE locked=0 AND generic=0")]:
                        status, note = _next_status(row, seen.get(row["id"], set()), processed, current,
                                                    fate_by_id.get(row["id"]), episode_id,
                                                    self.config.memory.archive_after_absent)
                        if status == (row.get("status") or "active"):
                            continue
                        after = {**row, "status": status, "status_note": note, "updated_at": now_iso()}
                        _update(conn, "characters", row["id"], after)
                        self._log(conn, "update", "characters", row["id"], row, after, None, 0, source="system",
                                  reason=note)
                        moved[status] = moved.get(status, 0) + 1
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return moved

    def new_voice_characters(self, episode_id: str, approved: list[ReviewedLine],
                             voices: list[NewVoice]) -> list[MemoryProposal]:
        """New voices that approved lines still use become characters, unnamed (their name is their id)."""
        known = self.store.character_ids()
        out = []
        for v in voices:
            used = [x.event_id for x in approved if x.approved and v.id in (x.speaker, x.listener)]
            if used and v.id not in known:
                out.append(MemoryProposal(kind="character", source="translator", evidence=used, payload={
                    "id": v.id, "name_zh": v.id, "name_vi": v.id,
                    "description": f"Voice found automatically in {episode_id}; not named yet"}))
        return out

    def record_line_decisions(self, episode_id: str, removed: list[str], kept: list[str]) -> int:
        """The reviewer's remove / keep decisions, counted per normalized text (memory of the script reviewer).
        Locked rows (edited by hand in the Memory screen) are not changed. Each episode's share is kept apart
        (`line_decision_episodes`), so recording an episode again replaces its share instead of adding to it."""
        from subagent.textutil import normalize_zh

        changes: dict[str, tuple[int, int]] = {}
        for texts, idx in ((removed, 0), (kept, 1)):
            for zh in texts:
                key = normalize_zh(zh)
                if key:
                    rem, keep = changes.get(key, (0, 0))
                    changes[key] = (rem + 1, keep) if idx == 0 else (rem, keep + 1)
        self._ensure_schema()
        written = 0
        with self.locked(), self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                old = {r["zh"]: (r["removed"], r["kept"]) for r in conn.execute(
                    "SELECT zh, removed, kept FROM line_decision_episodes WHERE episode_id=?", (episode_id,))}
                conn.execute("DELETE FROM line_decision_episodes WHERE episode_id=?", (episode_id,))
                conn.executemany("INSERT INTO line_decision_episodes (zh, episode_id, removed, kept) VALUES (?,?,?,?)",
                                 [(key, episode_id, rem, keep) for key, (rem, keep) in changes.items()])
                for key in sorted(set(changes) | set(old)):
                    rem, keep = changes.get(key, (0, 0))
                    old_rem, old_keep = old.get(key, (0, 0))
                    if (rem, keep) == (old_rem, old_keep):
                        continue                   # this episode's share is unchanged
                    before = _fetch(conn, "line_decisions", key)
                    if before and before["locked"]:
                        continue
                    after = {"zh": key,
                             "remove_count": max(0, (before["remove_count"] if before else 0) - old_rem + rem),
                             "keep_count": max(0, (before["keep_count"] if before else 0) - old_keep + keep),
                             "last_episode": episode_id, "locked": 0, "updated_at": now_iso()}
                    conn.execute("INSERT OR REPLACE INTO line_decisions (zh, remove_count, keep_count, last_episode, "
                                 "locked, updated_at) VALUES (:zh, :remove_count, :keep_count, :last_episode, :locked, "
                                 ":updated_at)", after)
                    self._log(conn, "update" if before else "insert", "line_decisions", key, before, after, None,
                              rem + keep, source="human", reason=f"review of {episode_id}")
                    written += 1
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise
        return written

    @contextlib.contextmanager
    def _backup(self) -> Iterator[None]:
        """Snapshot the memory files; restore them if the block fails (NFR-R4)."""
        tmp = Path(tempfile.mkdtemp(prefix="memory-backup-"))
        try:
            for item in ("memory.db", "briefings", "style_rules.md", "conflicts.json", "conflicts.md",
                         "speaker_corrections.jsonl"):
                src = self.dir / item
                if src.is_dir():
                    shutil.copytree(src, tmp / item)
                elif src.is_file():
                    shutil.copy2(src, tmp / item)
            try:
                yield
            except BaseException:
                log.warning("Memory update failed; restoring the previous memory files")
                for item in ("memory.db", "briefings", "style_rules.md", "conflicts.json", "conflicts.md",
                             "speaker_corrections.jsonl"):
                    dst, src = self.dir / item, tmp / item
                    if dst.is_dir():
                        shutil.rmtree(dst)
                    elif dst.is_file():
                        dst.unlink()
                    if src.is_dir():
                        shutil.copytree(src, dst)
                    elif src.is_file():
                        shutil.copy2(src, dst)
                raise
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def mine_edits(self, episode_id: str, approved: list[ReviewedLine], translations: list[LineTranslation],
                   edits: list[EditRecord]) -> list[MemoryProposal]:
        """5.16: speaker corrections are logged for dreaming; glossary changes become human proposals."""
        by_id = {line.event_id: line for line in approved}
        proposals: list[MemoryProposal] = []
        corrections = self.dir / "speaker_corrections.jsonl"
        if corrections.is_file():                  # mining an episode again replaces its entries
            kept = [ln for ln in corrections.read_text(encoding="utf-8").splitlines()
                    if ln.strip() and json.loads(ln).get("episode") != episode_id]
            atomic_write_text(corrections, "".join(f"{ln}\n" for ln in kept))
        for edit in edits:
            line = by_id.get(edit.event_id)
            if line is None:
                continue
            if edit.field in ("speaker", "listener"):
                append_jsonl(corrections, {"episode": episode_id, "event_id": edit.event_id, "field": edit.field,
                                           "before": edit.before, "after": edit.after, "zh": line.zh,
                                           "vi": line.vi, "ts": now_iso()})
            elif edit.field == "vi" and edit.before and edit.after:
                for entry in self.store.glossary_in(line.zh):
                    new_vi = replaced_term(edit.before, edit.after, entry.vi)
                    if new_vi and new_vi.lower() != entry.vi.lower():
                        proposals.append(MemoryProposal(
                            kind="glossary", payload={"zh": entry.zh, "vi": new_vi}, source="human",
                            evidence=[edit.edit_id],
                        ))
        return proposals

    def _backfill_appearances(self, conn: sqlite3.Connection, known: set[str], skip: str) -> None:
        """First lifecycle run: count appearances in the episodes finished before it existed."""
        from subagent.episodes import Registry
        from subagent.util import read_jsonl

        for ep in Registry(self.paths).load():
            if ep.id == skip:
                continue
            present: dict[str, int] = {}
            for x in read_jsonl(self.paths.episode_dir(ep.id) / "approved.jsonl", ReviewedLine):
                if x.approved and not x.deleted:
                    for cid in {x.speaker, x.listener} - {None}:
                        present[cid] = present.get(cid, 0) + 1
            for cid, n in sorted(present.items()):
                if cid in known:
                    conn.execute("INSERT OR REPLACE INTO appearances (character_id, episode_id, lines) VALUES (?,?,?)",
                                 (cid, ep.id, n))

    def update_briefings(self, episode_id: str, approved: list[ReviewedLine], llm: object) -> list:
        """Write the episode briefing; returns the character fates the script states (for the lifecycle)."""
        from subagent.memory.briefing_gen import generate_briefing

        brief = generate_briefing(self.paths, self.config, self.store, episode_id, approved, llm)
        index = bf.upsert_index(bf.read_index(self.dir), bf.IndexEntry(
            episode_id=episode_id, summary=brief.summary_sentence, characters=brief.characters_introduced,
            file=f"{episode_id}.md",
        ))
        self._apply_files([
            MemoryProposal(kind="briefing", source="translator", payload={"file": f"{episode_id}.md",
                                                                          "content": brief.episode_markdown}),
            MemoryProposal(kind="briefing", source="translator", payload={"file": "story_so_far.md",
                                                                          "content": brief.story_so_far}),
            MemoryProposal(kind="briefing", source="translator", payload={"file": "INDEX.md",
                                                                          "content": bf.render_index(index)}),
        ], ApplyResult())
        return brief.character_fates

    def manual_edit(self, proposals: list[MemoryProposal]) -> ApplyResult:
        """Edits from the app: source=human, locked, one commit per save."""
        self._refuse_while_jobs_run()
        for p in proposals:
            p.source = "human"
        with self.locked():
            result = self.apply(proposals)
            self.commit(f"manual edit: {result.writes} changes")
        return result

    def write_text_file(self, name: str, content: str) -> None:
        """Manual edit of a briefing or style_rules.md from the app's Markdown editor."""
        self._refuse_while_jobs_run()
        with self.locked():
            if name == "style_rules.md":
                atomic_write_text(self.dir / name, content.rstrip() + "\n")
                self._log_file(name, "human")
            else:
                self._apply_files([MemoryProposal(kind="briefing", source="human",
                                                  payload={"file": name, "content": content})], ApplyResult())
            self.commit("manual edit: 1 changes")

    AUX_FILES = ("dream_proposals.json", "dream_state.json", "dream_rejections.json")

    def write_aux(self, name: str, obj: object | None) -> None:
        """Dreaming's bookkeeping files in the memory folder; None deletes the file."""
        if name not in self.AUX_FILES:
            raise ValueError(name)
        path = self.dir / name
        with self.locked():
            if obj is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write_json(path, obj)

    # -- conflicts ----------------------------------------------------------------------------------

    def conflicts(self) -> list[Conflict]:
        data = read_json(self.dir / "conflicts.json", []) or []
        return [Conflict.model_validate(c) for c in data]

    def _render_conflicts(self) -> None:
        lines = ["# Memory conflicts", "", "Proposals that disagree with an existing entry and lacked more evidence.", ""]
        for c in self.conflicts():
            lines += [f"## {c.id}: {c.table} `{c.key}`", "",
                      f"- source: {c.source}, evidence: {', '.join(c.evidence) or '-'}",
                      f"- reason: {c.reason}",
                      f"- current: `{json.dumps(c.current, ensure_ascii=False)}`",
                      f"- proposed: `{json.dumps(c.proposed, ensure_ascii=False)}`", ""]
        atomic_write_text(self.dir / "conflicts.md", "\n".join(lines) + "\n")

    def resolve_conflict(self, conflict_id: str, accept: bool) -> None:
        self._refuse_while_jobs_run()
        with self.locked():
            conflicts = self.conflicts()
            target = next((c for c in conflicts if c.id == conflict_id), None)
            if target is None:
                raise SubagentError(f"Conflict {conflict_id} not found", code="conflict_not_found")
            if accept:
                self.apply([MemoryProposal(kind=target.kind, payload=target.proposed, source="human",  # type: ignore[arg-type]
                                           evidence=target.evidence)])
            atomic_write_json(self.dir / "conflicts.json", [c.model_dump() for c in conflicts if c.id != conflict_id])
            self._render_conflicts()
            self.commit(f"conflict {conflict_id}: {'accepted' if accept else 'rejected'}")

    # -- git ----------------------------------------------------------------------------------------

    def commit(self, message: str) -> str | None:
        from subagent.media import git

        with self.locked():
            git(["add", "-A"], self.dir)
            if not git(["status", "--porcelain"], self.dir).strip():
                return None
            git(["commit", "-q", "-m", message], self.dir)
            sha = git(["rev-parse", "HEAD"], self.dir).strip()
            if self.db.is_file():
                with self._connect() as conn:
                    conn.execute("UPDATE memory_log SET commit_sha=? WHERE commit_sha IS NULL", (sha,))
            return sha

    def history(self, limit: int = 100) -> list[CommitInfo]:
        from subagent.media import git

        if not (self.dir / ".git").exists():
            return []
        out = git(["log", f"-n{limit}", "--format=%H%x1f%aI%x1f%s"], self.dir, check=False)
        commits = []
        for line in out.splitlines():
            parts = line.split("\x1f")
            if len(parts) == 3:
                sha, date, msg = parts
                changes = sum(1 for e in self.store.log(commit_sha=sha, limit=10000) if e.op != "rejected")
                commits.append(CommitInfo(sha=sha, date=date, message=msg, changes=changes or None))
        return commits

    def _snapshot_rows(self, sha: str | None) -> dict[str, dict[str, dict]]:
        from subagent.media import require_binary, run

        if sha is None:
            return {t: {} for t in TABLES}
        proc = run([require_binary("git"), "show", f"{sha}:memory.db"], cwd=self.dir, check=False)
        if proc.returncode != 0 or not proc.stdout:
            return {t: {} for t in TABLES}
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "snapshot.db"
            db.write_bytes(proc.stdout)
            store = MemoryStore(db)
            return {t: {row_key(t, r): r for r in store.table_rows(t)} for t in TABLES}

    def diff(self, sha: str) -> MemoryDiff:
        from subagent.media import git

        parent = git(["rev-parse", "--verify", "-q", f"{sha}^"], self.dir, check=False).strip() or None
        after, before = self._snapshot_rows(sha), self._snapshot_rows(parent)
        tables: dict[str, TableDiff] = {}
        for t in TABLES:
            d = TableDiff()
            for key, row in after[t].items():
                old = before[t].get(key)
                if old is None:
                    d.added.append(row)
                elif _content(old) != _content(row):
                    d.changed.append((old, row))
            d.removed = [row for key, row in before[t].items() if key not in after[t]]
            if d.added or d.changed or d.removed:
                tables[t] = d
        text = ""
        if parent:
            text = git(["diff", parent, sha, "--", "*.md"], self.dir, check=False)
        else:
            text = git(["show", "--format=", sha, "--", "*.md"], self.dir, check=False)
        return MemoryDiff(sha=sha, parent=parent, tables=tables, text_diff=text)

    def entry_history(self, table: str, key: str) -> list:
        return self.store.log(table=table, key=key)

    def rollback(self, sha: str) -> str | None:
        """Restore the memory folder to `sha` as a new commit; history is never rewritten."""
        from subagent.media import git

        self._refuse_while_jobs_run()
        with self.locked():
            full = git(["rev-parse", "--verify", f"{sha}^{{commit}}"], self.dir).strip()
            target_files = set(git(["ls-tree", "-r", "--name-only", full], self.dir).splitlines())
            current_files = set(git(["ls-files"], self.dir).splitlines())
            for extra in sorted(current_files - target_files):
                git(["rm", "-q", "--", extra], self.dir)
            git(["checkout", full, "--", "."], self.dir)
            return self.commit(f"rollback to {full[:10]}")

    def _refuse_while_jobs_run(self) -> None:
        jobs = running_jobs(self.paths)
        if jobs:
            raise JobRunningError(f"Not allowed while a job is running ({', '.join(jobs)})")


# -- helpers ---------------------------------------------------------------------------------------

def _next_status(row: dict, seen: set[int], processed: set[int], current: int | None, fate, episode_id: str,
                 archive_after: int) -> tuple[str, str | None]:
    status, note = row.get("status") or "active", row.get("status_note")
    if fate is not None and fate.fate in ("dies", "leaves"):
        return "archived", f"{fate.fate} in {episode_id}: {fate.evidence}".strip()
    if status == "archived":
        if current is not None and current in seen:
            status, note = "active", f"back in {episode_id}"
        else:
            return status, note
    if fate is not None and fate.fate == "returns":
        return "kept", f"returns ({episode_id}): {fate.evidence}".strip()
    if status == "active" and any(n + 1 in seen for n in seen):
        return "kept", "appears in consecutive episodes"
    if status == "active" and seen:
        last = max(seen)
        if sum(1 for n in processed if n > last) >= archive_after:
            return "archived", f"not seen since ep{last:03d}"
    return status, note


def merge_proposals(proposals: list[MemoryProposal]) -> list[MemoryProposal]:
    """Identical proposals (same kind, source and payload) merge, pooling their evidence."""
    merged: dict[str, MemoryProposal] = {}
    for p in proposals:
        key = dumps([p.kind, p.source, p.payload])
        if key in merged:
            ev = merged[key].evidence
            merged[key].evidence = ev + [e for e in p.evidence if e not in ev]
        else:
            merged[key] = p.model_copy(deep=True)
    return list(merged.values())


def replaced_term(before: str, after: str, term: str) -> str | None:
    """If `term` was in `before` and a human replaced exactly it, return the replacement text."""
    if not contains_term(before, term) or contains_term(after, term):
        return None
    a, b = before.split(), after.split()
    t_words = term.split()
    lowered = [w.lower().strip(".,!?;:…\"'“”") for w in a]
    start = next((i for i in range(len(a) - len(t_words) + 1)
                  if lowered[i:i + len(t_words)] == [w.lower() for w in t_words]), None)
    if start is None:
        return None
    end = start + len(t_words)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "replace" and i1 <= start and end <= i2 and (i2 - i1) <= len(t_words) + 1:
            return " ".join(b[j1:j2]).strip(".,!?;:…\"'“”") or None
    return None


def _fetch(conn: sqlite3.Connection, table: str, key: str) -> dict | None:
    for row in conn.execute(f"SELECT * FROM {table}"):  # noqa: S608 - whitelisted table
        r = dict(row)
        if row_key(table, r) == key:
            return r
    return None


def _where(table: str, key: str) -> tuple[str, tuple]:
    if table == "characters":
        return "id=?", (key,)
    if table == "glossary":
        return "zh=?", (key,)
    if table == "pronoun_pairs":
        s, listener, ctx = key.split("|", 2)
        return "speaker_id=? AND listener_id=? AND context=?", (s, listener, ctx)
    if table == "voice_bank":
        return "character_id=?", (key,)
    if table == "line_decisions":
        return "zh=?", (key,)
    raise ValueError(table)


def _insert(conn: sqlite3.Connection, table: str, row: dict) -> None:
    cols = list(row)
    conn.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",  # noqa: S608
                 tuple(row[c] for c in cols))


def _update(conn: sqlite3.Connection, table: str, key: str, row: dict) -> None:
    where, params = _where(table, key)
    cols = [c for c in row if c not in ("rowid",)]
    conn.execute(f"UPDATE {table} SET {', '.join(f'{c}=?' for c in cols)} WHERE {where}",  # noqa: S608
                 tuple(row[c] for c in cols) + params)


def _delete(conn: sqlite3.Connection, table: str, key: str) -> None:
    where, params = _where(table, key)
    if table == "characters":
        conn.execute("DELETE FROM pronoun_pairs WHERE speaker_id=? OR listener_id=?", (key, key))
        conn.execute("DELETE FROM voice_bank WHERE character_id=?", (key,))
        conn.execute("DELETE FROM confusable_pairs WHERE a=? OR b=?", (key, key))
        conn.execute("DELETE FROM sprite_bank WHERE character_id=?", (key,))
    conn.execute(f"DELETE FROM {table} WHERE {where}", params)  # noqa: S608


def _current_evidence(conn: sqlite3.Connection, table: str, key: str) -> int:
    row = conn.execute(
        "SELECT evidence_count FROM memory_log WHERE tbl=? AND key=? AND op IN ('insert','update') "
        "ORDER BY id DESC LIMIT 1", (table, key),
    ).fetchone()
    return int(row[0]) if row else 0


def _loggable(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {k: (f"<{len(v) // 4} floats>" if isinstance(v, bytes) else v) for k, v in row.items()}


def _content(row: dict) -> dict:
    return {k: v for k, v in row.items() if k != "updated_at"}
