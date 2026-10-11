"""Applying proposals under the write rules (5.15), Markdown-backed memory, manual edits, conflicts."""

from __future__ import annotations

import json
import logging
import re
import sqlite3

from subagent.characters import is_unnamed
from subagent.errors import SubagentError
from subagent.memory import briefings as bf
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
from subagent.memory.store import (
    STATUSES,
    dumps,
    row_key,
)
from subagent.models import MemoryProposal
from subagent.util import (
    atomic_write_json,
    atomic_write_text,
    now_iso,
    read_json,
    sha256_json,
)

log = logging.getLogger(__name__)


class ApplyMixin:
    """Applying proposals under the write rules (5.15), Markdown-backed memory, manual edits, conflicts. Part of MemoryManager."""

    AUX_FILES = ("dream_proposals.json", "dream_state.json", "dream_rejections.json")

    def apply(self, proposals: list[MemoryProposal], *, approved_ids: set[str] | None = None,
              episode_id: str | None = None) -> ApplyResult:
        self._ensure_schema()
        result = ApplyResult()
        proposals = sorted(merge_proposals(proposals), key=lambda p: KIND_ORDER.get(p.kind, 9))
        file_ops: list[MemoryProposal] = []
        with self.locked():
            with self._transaction() as conn:
                for p in proposals:
                    if p.kind in ("style_rule", "briefing"):
                        file_ops.append(p)
                        continue
                    self._apply_row(conn, p, approved_ids, episode_id, result)
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
        if table == "characters" and "aliases" in payload:
            payload["aliases"] = dumps_aliases(payload["aliases"])
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

        if p.source in EVIDENCE_SOURCES and (approved_ids is None or not p.evidence
                                             or not set(p.evidence) <= approved_ids):
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
            if existing["locked"] and p.source == "updater":
                result.held += held_updates(table, key, existing, changes, p, "locked")
                return
            if existing["locked"] and p.source not in LOCKING_SOURCES:
                self._reject(conn, result, table, key, p, "entry is locked")
                return
            # an automatically found character nobody has named yet takes the first name proposed for it
            first_name = (table == "characters" and is_unnamed(existing, self.config.voice.new_voice_prefix)
                          and bool(changes.get("name_vi")) and changes["name_vi"] != key)
            # character updates (5.15c) replace what an unlocked entry says: no evidence comparison
            if (not existing["locked"] and p.source not in LOCKING_SOURCES and p.source != "updater" and changes
                    and not first_name):
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
            row["aliases"] = row.get("aliases") or "[]"
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
