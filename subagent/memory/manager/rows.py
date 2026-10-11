"""Row-level SQL helpers and the tables / columns / sources the write rules use."""

from __future__ import annotations

import logging
import sqlite3

from subagent.memory.store import (
    row_key,
)

log = logging.getLogger(__name__)


KIND_ORDER = {"character": 0, "glossary": 1, "pronoun_pair": 2, "line_decision": 3, "style_rule": 4, "briefing": 5}

KIND_TABLE = {"character": "characters", "glossary": "glossary", "pronoun_pair": "pronoun_pairs",
              "line_decision": "line_decisions"}

COLUMNS = {
    "characters": ["id", "name_zh", "name_vi", "description", "status", "status_note", "generic", "aliases"],
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

EVIDENCE_SOURCES = {"translator", "updater"}     # applied only when every evidence line was approved

BRIEFING_FILES = {"story_so_far.md", "INDEX.md"}

UPDATES_FILE = "character_updates.json"                    # updates waiting for the reviewer (5.15c)

UPDATE_REJECTIONS_FILE = "character_update_rejections.json"

BACKUP_ITEMS = ("memory.db", "briefings", "style_rules.md", "conflicts.json", "conflicts.md",
                "speaker_corrections.jsonl", UPDATES_FILE, UPDATE_REJECTIONS_FILE)

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
