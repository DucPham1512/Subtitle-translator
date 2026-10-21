"""Character updates from an episode (5.15c) and the updates waiting for review."""

from __future__ import annotations

import logging

from subagent.kernel.errors import SubagentError
from subagent.kernel.models import MemoryProposal, NewVoice, ReviewedLine
from subagent.kernel.util import (
    atomic_write_json,
    now_iso,
    read_json,
)
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
    parse_aliases,
    row_key,
)

log = logging.getLogger(__name__)


class UpdatesMixin:
    """Character updates from an episode (5.15c) and the updates waiting for review. Part of MemoryManager."""

    def character_updates(self, episode_id: str, approved: list[ReviewedLine], voices: list[NewVoice], mode: str,
                          llm: object) -> tuple[list[MemoryProposal], list[dict]]:
        """The updater's checked proposals for this episode, and (auto mode) the ones held because their evidence
        is not on trusted lines. Updates of a candidate or new voice without trusted evidence are dropped."""
        from subagent.memory import character_updates as cu
        from subagent.memory.evidence import trusted_auto_lines

        lines = [x for x in approved if x.approved and not x.deleted]
        proposals = cu.propose(self.paths, self.config, self.store, episode_id, lines, llm)
        if mode != "auto":
            return proposals, []
        chars = self.store.character_ids()
        known = chars | {c.id for c in self.store.candidates()} | {v.id for v in voices}
        trusted = {x.event_id for x in trusted_auto_lines(self.paths, self.config, episode_id, known, min_ms=0)}
        keep: list[MemoryProposal] = []
        held: list[dict] = []
        for p in proposals:
            if set(p.evidence) <= trusted:
                keep.append(p)
                continue
            table = KIND_TABLE[p.kind]
            key = row_key(table, {**p.payload, "context": p.payload.get("context") or ""})
            ids = ({p.payload.get("id")} if p.kind == "character"
                   else {p.payload.get("speaker_id"), p.payload.get("listener_id")})
            if not ids <= chars:
                log.info("character updates: %s %s dropped (auto mode, evidence not trusted)", p.kind, key)
                continue
            existing = self.store.get_row(table, key) or {}
            payload = dict(p.payload)
            if "aliases" in payload:
                payload["aliases"] = dumps_aliases(payload["aliases"])
            changes = {k: v for k, v in payload.items() if k in COLUMNS[table] and existing.get(k) != v}
            held += held_updates(table, key, existing, changes, p, "untrusted")
        return keep, held


    def _write_held(self, episode_id: str, held: list[dict], approved: list[ReviewedLine]) -> None:
        """Replace this episode's waiting updates; a newer update of the same field replaces an older one, and one
        the reviewer rejected before is not added again."""
        by_id = {x.event_id: x for x in approved}
        rejected = {r["signature"] for r in read_json(self.dir / UPDATE_REJECTIONS_FILE, []) or []}
        items = [i for i in self.pending_updates() if i.episode != episode_id]
        now = now_iso()
        for h in held:
            if h["signature"] in rejected:
                continue
            item = PendingUpdate(episode=episode_id, ts=now, lines=[
                f"{e}: {by_id[e].zh} | {by_id[e].vi}" for e in h["evidence"] if e in by_id], **h)
            items = [i for i in items if i.id != item.id] + [item]
        if items or (self.dir / UPDATES_FILE).is_file():
            atomic_write_json(self.dir / UPDATES_FILE, [i.model_dump() for i in items])


    def pending_updates(self) -> list[PendingUpdate]:
        return [PendingUpdate.model_validate(d) for d in read_json(self.dir / UPDATES_FILE, []) or []]


    def resolve_update(self, update_id: str, accept: bool) -> None:
        """Accept (a human edit: applied and locked) or reject (never proposed again) one waiting update."""
        self._refuse_while_jobs_run()
        with self.locked():
            items = self.pending_updates()
            item = next((i for i in items if i.id == update_id), None)
            if item is None:
                raise SubagentError(f"Character update {update_id} not found", code="update_not_found")
            if accept:
                payload = dict(item.proposed)
                if item.table == "characters":
                    payload["id"] = item.key
                    if item.field == "aliases":
                        current = self.store.get_row("characters", item.key) or {}
                        payload["aliases"] = parse_aliases(current.get("aliases")) + parse_aliases(payload["aliases"])
                kind = "character" if item.table == "characters" else "pronoun_pair"
                result = self.apply([MemoryProposal(kind=kind, payload=payload, source="human",
                                                    evidence=item.evidence)])
                if result.rejected:
                    raise SubagentError(f"Character update {update_id} not applied: {result.rejected[0][1]}",
                                        code="update_rejected")
            else:
                known = read_json(self.dir / UPDATE_REJECTIONS_FILE, []) or []
                known.append({"signature": item.signature, "description": describe_update(item), "date": now_iso()})
                atomic_write_json(self.dir / UPDATE_REJECTIONS_FILE, known)
            atomic_write_json(self.dir / UPDATES_FILE, [i.model_dump() for i in items if i.id != update_id])
            self.commit(f"character update {update_id}: {'accepted' if accept else 'rejected'}")
