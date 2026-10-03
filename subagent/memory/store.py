"""SQLite memory access (4.1). Public functions only read; writes live in memory/manager.py.

Connections are opened read-only and closed after every query, so a rollback can replace the file.
"""

from __future__ import annotations

import contextlib
import json
import re
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pydantic import BaseModel

SCHEMA = """
CREATE TABLE IF NOT EXISTS characters (
  id TEXT PRIMARY KEY,
  name_zh TEXT NOT NULL,
  name_vi TEXT NOT NULL,
  description TEXT,
  locked INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active',     -- active | kept | archived (character lifecycle)
  status_note TEXT,                          -- why the status was set
  generic INTEGER NOT NULL DEFAULT 0         -- stands for many individuals (all fish, passers-by): never voice/picture
);
CREATE TABLE IF NOT EXISTS glossary (
  zh TEXT PRIMARY KEY,
  vi TEXT NOT NULL,
  pinyin TEXT,
  type TEXT,
  notes TEXT,
  locked INTEGER NOT NULL DEFAULT 0,
  source TEXT NOT NULL,
  first_episode TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pronoun_pairs (
  speaker_id TEXT NOT NULL REFERENCES characters(id),
  listener_id TEXT NOT NULL REFERENCES characters(id),
  self_term TEXT NOT NULL,
  address_term TEXT NOT NULL,
  context TEXT NOT NULL DEFAULT '',   -- '' = default; NULL would allow duplicate primary keys in SQLite
  since_episode TEXT,
  locked INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (speaker_id, listener_id, context)
);
CREATE TABLE IF NOT EXISTS voice_bank (
  character_id TEXT PRIMARY KEY REFERENCES characters(id),
  embedding BLOB NOT NULL,
  n_clips INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS confusable_pairs (
  a TEXT NOT NULL, b TEXT NOT NULL,
  similarity REAL NOT NULL,
  PRIMARY KEY (a, b)
);
CREATE TABLE IF NOT EXISTS memory_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  op TEXT NOT NULL,
  tbl TEXT NOT NULL,
  key TEXT NOT NULL,
  before_json TEXT,
  after_json TEXT,
  source TEXT NOT NULL,
  reason TEXT,
  commit_sha TEXT,
  evidence_count INTEGER NOT NULL DEFAULT 0   -- used by the conflict rule (more evidence wins)
);
CREATE INDEX IF NOT EXISTS memory_log_key ON memory_log (tbl, key);
CREATE TABLE IF NOT EXISTS appearances (
  character_id TEXT NOT NULL,
  episode_id TEXT NOT NULL,
  lines INTEGER NOT NULL,                    -- approved lines with the character as speaker or listener
  PRIMARY KEY (character_id, episode_id)
);
CREATE TABLE IF NOT EXISTS sprite_bank (       -- how each character looks (5.8b)
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  character_id TEXT NOT NULL,
  embedding BLOB NOT NULL,                   -- float16, L2-normalized image features of one crop
  episode_id TEXT,
  event_id TEXT,
  right INTEGER NOT NULL DEFAULT 0,          -- times it named the reviewed speaker of a talking sprite
  wrong INTEGER NOT NULL DEFAULT 0,          -- times it named someone else
  added_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS line_decisions (
  zh TEXT PRIMARY KEY,                       -- normalized Chinese text of a line
  remove_count INTEGER NOT NULL DEFAULT 0,   -- times the reviewer removed a line with this text
  keep_count INTEGER NOT NULL DEFAULT 0,     -- times the reviewer kept it (short lines, restored lines)
  last_episode TEXT,
  locked INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candidates (        -- new characters on probation (5.15b)
  id TEXT PRIMARY KEY,                       -- npc_005_02, or the id the translator proposed
  first_episode TEXT NOT NULL,
  name_zh TEXT, name_vi TEXT, description TEXT,
  embedding BLOB,                            -- float32 voice of its approved lines, L2-normalized (may be missing)
  n_lines INTEGER NOT NULL,                  -- approved lines it speaks in the first episode
  pending_json TEXT NOT NULL DEFAULT '[]',   -- proposals that wait for the promotion (pronoun pairs)
  status TEXT NOT NULL DEFAULT 'candidate',  -- candidate | promoted | dropped
  status_note TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS candidate_sprites (  -- how a candidate looks: its talking sprites (float16)
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id TEXT NOT NULL,
  embedding BLOB NOT NULL,
  episode_id TEXT, event_id TEXT
);
"""

TABLES = ("characters", "glossary", "pronoun_pairs", "voice_bank", "confusable_pairs", "line_decisions", "appearances",
          "sprite_bank", "candidates")
STATUSES = ("active", "kept", "archived")
# columns added after the first release: (table, column, definition)
MIGRATIONS = [("characters", "status", "TEXT NOT NULL DEFAULT 'active'"), ("characters", "status_note", "TEXT"),
              ("characters", "generic", "INTEGER NOT NULL DEFAULT 0")]


def episode_number(episode_id: str) -> int | None:
    m = re.fullmatch(r"ep(\d+)", episode_id or "")
    return int(m.group(1)) if m else None


def migrate(conn: sqlite3.Connection) -> None:
    """Add columns that an older memory.db lacks (CREATE TABLE IF NOT EXISTS does not change old tables)."""
    for table, column, definition in MIGRATIONS:
        have = {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}  # noqa: S608 - fixed names
        if have and column not in have:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")  # noqa: S608


class Character(BaseModel):
    id: str
    name_zh: str
    name_vi: str
    description: str | None = None
    locked: bool = False
    updated_at: str = ""
    status: str = "active"          # active | kept | archived
    status_note: str | None = None
    generic: bool = False           # many individuals under one name: not matched or learned by voice / picture

    @property
    def archived(self) -> bool:
        return self.status == "archived"


@dataclass
class Candidate:
    """A new character on probation (5.15b): known for one episode, a character once it comes back."""
    id: str
    first_episode: str
    n_lines: int
    status: str = "candidate"
    name_zh: str | None = None
    name_vi: str | None = None
    description: str | None = None
    embedding: np.ndarray | None = None
    pending: list[dict] = None  # type: ignore[assignment]
    status_note: str | None = None


@dataclass
class SpriteExemplar:
    id: int
    character_id: str
    embedding: np.ndarray
    right: int = 0
    wrong: int = 0


class GlossaryEntry(BaseModel):
    zh: str
    vi: str
    pinyin: str | None = None
    type: str | None = None
    notes: str | None = None
    locked: bool = False
    source: str = ""
    first_episode: str | None = None
    updated_at: str = ""


class PronounPair(BaseModel):
    speaker_id: str
    listener_id: str
    self_term: str
    address_term: str
    context: str = ""
    since_episode: str | None = None
    locked: bool = False
    updated_at: str = ""


class VoiceEntry(BaseModel):
    character_id: str
    n_clips: int
    updated_at: str
    embedding: list[float]


class LineDecision(BaseModel):
    zh: str
    remove_count: int = 0
    keep_count: int = 0
    last_episode: str | None = None
    locked: bool = False
    updated_at: str = ""


class LogEntry(BaseModel):
    id: int
    ts: str
    op: str
    tbl: str
    key: str
    before_json: str | None
    after_json: str | None
    source: str
    reason: str | None
    commit_sha: str | None
    evidence_count: int = 0


def row_key(table: str, row: dict) -> str:
    if table == "characters":
        return str(row["id"])
    if table == "glossary":
        return str(row["zh"])
    if table == "pronoun_pairs":
        return f"{row['speaker_id']}|{row['listener_id']}|{row.get('context') or ''}"
    if table == "voice_bank":
        return str(row["character_id"])
    if table == "confusable_pairs":
        return f"{row['a']}|{row['b']}"
    if table == "line_decisions":
        return str(row["zh"])
    if table == "appearances":
        return f"{row['character_id']}|{row['episode_id']}"
    if table == "sprite_bank":
        return str(row["id"])
    if table == "candidates":
        return str(row["id"])
    raise ValueError(table)


class MemoryStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    @contextlib.contextmanager
    def _ro(self) -> Iterator[sqlite3.Connection | None]:
        if not self.db_path.is_file():
            yield None
            return
        conn = sqlite3.connect(f"{self.db_path.resolve().as_uri()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _rows(self, sql: str, params: tuple = ()) -> list[dict]:
        with self._ro() as conn:
            if conn is None:
                return []
            try:
                return [dict(r) for r in conn.execute(sql, params).fetchall()]
            except sqlite3.OperationalError:
                return []   # table not created yet

    # -- characters / glossary / pronouns -----------------------------------------------------------

    def characters(self, *, active_only: bool = False) -> list[Character]:
        """All characters; `active_only` leaves out archived ones (prompts, voice matching)."""
        chars = [Character.model_validate(r) for r in self._rows("SELECT * FROM characters ORDER BY id")]
        return [c for c in chars if not c.archived] if active_only else chars

    def sprite_exemplars(self) -> list[SpriteExemplar]:
        rows = self._rows("SELECT * FROM sprite_bank ORDER BY character_id, id")
        return [SpriteExemplar(id=r["id"], character_id=r["character_id"],
                               embedding=np.frombuffer(r["embedding"], dtype=np.float16).astype(np.float32),
                               right=r["right"], wrong=r["wrong"]) for r in rows]

    def unmatchable_ids(self) -> set[str]:
        """Characters left out of voice and picture matching and learning: archived or generic."""
        return {c.id for c in self.characters() if c.archived or c.generic}

    def appearances(self) -> list[dict]:
        return self._rows("SELECT * FROM appearances ORDER BY character_id, episode_id")

    def character_ids(self) -> set[str]:
        return {c.id for c in self.characters()}

    def glossary(self) -> list[GlossaryEntry]:
        # longest terms first: matching prefers the longest phrase
        rows = self._rows("SELECT * FROM glossary ORDER BY length(zh) DESC, zh")
        return [GlossaryEntry.model_validate(r) for r in rows]

    def glossary_in(self, zh: str) -> list[GlossaryEntry]:
        """Glossary terms present in a Chinese line, longest first, overlapping shorter terms dropped."""
        found: list[GlossaryEntry] = []
        covered = [False] * len(zh)
        for entry in self.glossary():
            start = zh.find(entry.zh)
            while start != -1:
                end = start + len(entry.zh)
                if not any(covered[start:end]):
                    for i in range(start, end):
                        covered[i] = True
                    if entry not in found:
                        found.append(entry)
                start = zh.find(entry.zh, start + 1)
        return found

    def pronoun_pairs(self) -> list[PronounPair]:
        rows = self._rows("SELECT * FROM pronoun_pairs ORDER BY speaker_id, listener_id, context")
        return [PronounPair.model_validate(r) for r in rows]

    def pronoun_variants(self, speaker_id: str, listener_id: str) -> list[PronounPair]:
        rows = self._rows(
            "SELECT * FROM pronoun_pairs WHERE speaker_id=? AND listener_id=? ORDER BY context",
            (speaker_id, listener_id),
        )
        return [PronounPair.model_validate(r) for r in rows]

    # -- voices -------------------------------------------------------------------------------------

    def voice_bank(self) -> dict[str, np.ndarray]:
        rows = self._rows("SELECT character_id, embedding FROM voice_bank ORDER BY character_id")
        return {r["character_id"]: np.frombuffer(r["embedding"], dtype=np.float32).copy() for r in rows}

    def candidates(self, status: str | None = "candidate") -> list[Candidate]:
        """Characters on probation (5.15b); `status=None` returns every row (promoted and dropped too)."""
        rows = self._rows("SELECT * FROM candidates ORDER BY first_episode, id")
        out = []
        for r in rows:
            if status is not None and r["status"] != status:
                continue
            emb = np.frombuffer(r["embedding"], dtype=np.float32).copy() if r["embedding"] else None
            out.append(Candidate(id=r["id"], first_episode=r["first_episode"], n_lines=r["n_lines"],
                                 status=r["status"], name_zh=r["name_zh"], name_vi=r["name_vi"],
                                 description=r["description"], embedding=emb,
                                 pending=json.loads(r["pending_json"] or "[]"), status_note=r["status_note"]))
        return out

    def returning_candidates(self, number: int, window: int) -> list[Candidate]:
        """Candidates that may come back in episode `number`: first heard 1..`window` episodes before it."""
        out = []
        for c in self.candidates():
            first = episode_number(c.first_episode)
            if first is not None and first < number <= first + window:
                out.append(c)
        return out

    def candidate_sprites(self, candidate_id: str) -> list[np.ndarray]:
        rows = self._rows("SELECT embedding FROM candidate_sprites WHERE candidate_id=? ORDER BY id", (candidate_id,))
        return [np.frombuffer(r["embedding"], dtype=np.float16).astype(np.float32) for r in rows]

    def voice_counts(self) -> dict[str, int]:
        return {r["character_id"]: r["n_clips"] for r in self._rows("SELECT character_id, n_clips FROM voice_bank")}

    def line_decisions(self) -> list[LineDecision]:
        rows = self._rows("SELECT * FROM line_decisions ORDER BY zh")
        return [LineDecision.model_validate(r) for r in rows]

    def confusable_pairs(self) -> dict[tuple[str, str], float]:
        return {(r["a"], r["b"]): r["similarity"] for r in self._rows("SELECT * FROM confusable_pairs")}

    # -- generic / log ------------------------------------------------------------------------------

    def get_row(self, table: str, key: str) -> dict | None:
        if table not in TABLES:
            raise ValueError(table)
        for row in self._rows(f"SELECT * FROM {table}"):  # noqa: S608 - table name whitelisted
            if row_key(table, row) == key:
                if "embedding" in row:
                    row["embedding"] = f"<{len(row['embedding']) // 4} floats>"
                return row
        return None

    def table_rows(self, table: str) -> list[dict]:
        if table not in TABLES:
            raise ValueError(table)
        rows = self._rows(f"SELECT * FROM {table}")  # noqa: S608
        for row in rows:
            if isinstance(row.get("embedding"), bytes):
                row["embedding"] = f"<{len(row['embedding']) // 4} floats>"
        return rows

    def log(self, *, table: str | None = None, key: str | None = None, commit_sha: str | None = None,
            limit: int = 500) -> list[LogEntry]:
        sql, params = "SELECT * FROM memory_log WHERE 1=1", []
        if table:
            sql += " AND tbl=?"
            params.append(table)
        if key is not None:
            sql += " AND key=?"
            params.append(key)
        if commit_sha:
            sql += " AND commit_sha=?"
            params.append(commit_sha)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        return [LogEntry.model_validate(r) for r in self._rows(sql, tuple(params))]

    def current_evidence(self, table: str, key: str) -> int:
        rows = self._rows(
            "SELECT evidence_count FROM memory_log WHERE tbl=? AND key=? AND op IN ('insert','update') "
            "ORDER BY id DESC LIMIT 1", (table, key),
        )
        return int(rows[0]["evidence_count"]) if rows else 0


def dumps(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)
