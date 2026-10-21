"""What finishing an episode writes (5.15): the update itself, lifecycle (5.15a), line decisions, edit mining (5.16), briefings."""

from __future__ import annotations

import contextlib
import json
import logging
import shutil
import sqlite3
import tempfile
from collections.abc import Iterator
from pathlib import Path

from subagent.kernel import (
    EditRecord,
    LineTranslation,
    MemoryProposal,
    NewVoice,
    ReviewedLine,
    append_jsonl,
    atomic_write_text,
    now_iso,
)
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
    episode_number,
)

log = logging.getLogger(__name__)


class EpisodeMixin:
    """What finishing an episode writes (5.15): the update itself, lifecycle (5.15a), line decisions, edit mining (5.16), briefings. Part of MemoryManager."""

    def episode_update(self, episode_id: str, approved: list[ReviewedLine], translations: list[LineTranslation],
                       edits: list[EditRecord], llm: object | None,
                       line_decisions: tuple[list[str], list[str]] | None = None,
                       new_voices: list[NewVoice] | None = None, mode: str = "human") -> ApplyResult:
        """After an episode: apply approved + human-edit proposals, write briefings, commit. All or nothing."""
        self._ensure_schema()
        with self.locked(), self._backup():
            approved = [line for line in approved if not line.deleted]
            approved_ids = {line.event_id for line in approved if line.approved}
            proposals = reviewed_glossary([p for t in translations if t.event_id in approved_ids
                                           for p in t.proposals], edits)
            # character identification off (5.11a): no characters, pronoun pairs, probation or lifecycle
            identify = self.config.show.character_identification
            if not identify:
                proposals = [p for p in proposals if p.kind not in ("character", "pronoun_pair")]
            held: list[dict] = []
            updating = identify and self.config.memory.character_updates and llm is not None
            if updating:
                updates, held = self.character_updates(episode_id, approved, new_voices or [], mode, llm)
                proposals += updates
            probation: dict[str, int] = {}
            if identify and self.config.memory.probation:
                proposals, probation, extra_ids = self.probation(episode_id, approved, approved_ids, proposals,
                                                                 new_voices or [], mode)
                approved_ids |= extra_ids
            elif identify:
                proposals = self.new_voice_characters(episode_id, approved, new_voices or []) + proposals
            proposals += self.mine_edits(episode_id, approved, translations, edits)
            result = self.apply(proposals, approved_ids=approved_ids, episode_id=episode_id)
            result.probation = probation
            result.held = held + result.held
            if updating:
                self._write_held(episode_id, result.held, approved)
            if line_decisions is not None:
                self.record_line_decisions(episode_id, *line_decisions)
            fates = self.update_briefings(episode_id, approved, llm) if llm is not None else []
            result.lifecycle = self.update_lifecycle(episode_id, approved, fates) if identify else {}
            moved = "".join(f", {n} {status}" for status, n in sorted(result.lifecycle.items()))
            moved += "".join(f", {n} {kind}" for kind, n in sorted(probation.items()) if n)
            if result.held:
                moved += f", {len(result.held)} held for review"
            self.commit(f"episode {episode_id}: {result.writes} writes{moved}")
        return result


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
        with self._transaction() as conn:
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
        from subagent.kernel import normalize_zh

        changes: dict[str, tuple[int, int]] = {}
        for texts, idx in ((removed, 0), (kept, 1)):
            for zh in texts:
                key = normalize_zh(zh)
                if key:
                    rem, keep = changes.get(key, (0, 0))
                    changes[key] = (rem + 1, keep) if idx == 0 else (rem, keep + 1)
        self._ensure_schema()
        written = 0
        with self._transaction() as conn:
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
        return written


    @contextlib.contextmanager
    def _backup(self) -> Iterator[None]:
        """Snapshot the memory files; restore them if the block fails (NFR-R4)."""
        tmp = Path(tempfile.mkdtemp(prefix="memory-backup-"))
        try:
            for item in BACKUP_ITEMS:
                src = self.dir / item
                if src.is_dir():
                    shutil.copytree(src, tmp / item)
                elif src.is_file():
                    shutil.copy2(src, tmp / item)
            try:
                yield
            except BaseException:
                log.warning("Memory update failed; restoring the previous memory files")
                for item in BACKUP_ITEMS:
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
        from subagent.kernel import read_jsonl
        from subagent.workspace import Registry

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
