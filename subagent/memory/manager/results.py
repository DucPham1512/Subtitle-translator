"""What Memory Manager operations return, and the waiting character updates (5.15c)."""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field

from subagent.kernel import MemoryProposal
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
from subagent.memory.store import (
    parse_aliases,
)

log = logging.getLogger(__name__)


class ApplyResult(BaseModel):
    applied: list[str] = Field(default_factory=list)       # "table:key"
    unchanged: list[str] = Field(default_factory=list)
    rejected: list[tuple[str, str]] = Field(default_factory=list)   # ("table:key", reason)
    conflicts: list[str] = Field(default_factory=list)
    renamed: list[tuple[str, str]] = Field(default_factory=list)    # (character id, new name): first names
    lifecycle: dict[str, int] = Field(default_factory=dict)         # status -> characters moved to it
    probation: dict[str, int] = Field(default_factory=dict)         # candidates / promoted / dropped (5.15b)
    held: list[dict] = Field(default_factory=list)                  # updater changes waiting for review (5.15c)

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


class PendingUpdate(BaseModel):
    """A character update from an episode that waits for the reviewer (5.15c): one field of one entry."""
    id: str                         # "<table>:<key>:<field>"; a newer update of the same field replaces it
    episode: str
    table: str                      # characters | pronoun_pairs
    key: str
    field: str                      # name | description | aliases | pair
    current: dict
    proposed: dict                  # aliases: only the ones to add
    evidence: list[str]
    lines: list[str] = Field(default_factory=list)   # "event id: zh | vi" of the evidence
    reason: str                     # locked | untrusted (auto mode: evidence not on trusted lines)
    signature: str
    ts: str = ""


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


def dumps_aliases(value: object) -> str:
    return json.dumps(parse_aliases(value), ensure_ascii=False)


def held_updates(table: str, key: str, current: dict, changes: dict, p: MemoryProposal, reason: str) -> list[dict]:
    """One waiting update per changed field of a character (name, description, aliases) or one per pronoun pair."""
    out = []

    def add(field: str, cur: dict, proposed: dict) -> None:
        sig = f"{table}|{key}|{field}|{json.dumps(proposed, ensure_ascii=False, sort_keys=True).lower()}"
        out.append({"id": f"{table}:{key}:{field}", "table": table, "key": key, "field": field, "current": cur,
                    "proposed": proposed, "evidence": list(p.evidence), "reason": reason, "signature": sig})

    if table == "pronoun_pairs":
        if changes:
            fields = ("speaker_id", "listener_id", "self_term", "address_term", "context")
            add("pair", {f: current.get(f) for f in ("self_term", "address_term")} if current else {},
                {f: p.payload.get(f) or "" for f in fields})
        return out
    if "name_vi" in changes or "name_zh" in changes:
        add("name", {"name_zh": current.get("name_zh"), "name_vi": current.get("name_vi")},
            {"name_zh": p.payload.get("name_zh") or current.get("name_zh"),
             "name_vi": p.payload.get("name_vi") or current.get("name_vi")})
    if "description" in changes:
        add("description", {"description": current.get("description")}, {"description": changes["description"]})
    if "aliases" in changes:
        have = parse_aliases(current.get("aliases"))
        new = [a for a in parse_aliases(changes["aliases"]) if a not in have]
        if new:
            add("aliases", {"aliases": have}, {"aliases": new})
    return out


def describe_update(item: PendingUpdate) -> str:
    if item.table == "pronoun_pairs":
        pl = item.proposed
        ctx = f" ({pl.get('context')})" if pl.get("context") else ""
        return (f"pronouns {pl.get('speaker_id')} → {pl.get('listener_id')}{ctx}: "
                f"{pl.get('self_term')} / {pl.get('address_term')}")
    return f"{item.key} {item.field}: {json.dumps(item.proposed, ensure_ascii=False)}"
