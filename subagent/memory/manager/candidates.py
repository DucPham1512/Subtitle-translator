"""New characters on probation (5.15b): candidates, promotion, their updates."""

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass, field

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
from subagent.memory.store import (
    episode_number,
    parse_aliases,
)
from subagent.models import MemoryProposal, NewVoice, ReviewedLine
from subagent.util import (
    now_iso,
)

log = logging.getLogger(__name__)


@dataclass
class _Run:
    """What one probation pass works on (one transaction)."""
    episode_id: str
    current: int | None
    approved: list
    approved_ids: set[str]
    mode: str
    now: str
    cast: dict
    cast_embs: np.ndarray | None
    line_voices: dict
    conn: sqlite3.Connection | None = None
    known: set[str] = field(default_factory=set)
    rows: dict[str, dict] = field(default_factory=dict)
    trusted: set[str] | None = None
    counts: dict[str, int] = field(default_factory=lambda: {"candidates": 0, "promoted": 0, "dropped": 0})


class CandidatesMixin:
    """New characters on probation (5.15b): candidates, promotion, their updates. Part of MemoryManager."""

    def probation(self, episode_id: str, approved: list[ReviewedLine], approved_ids: set[str],
                  proposals: list[MemoryProposal], voices: list[NewVoice], mode: str,
                  ) -> tuple[list[MemoryProposal], dict[str, int], set[str]]:
        """New characters wait on probation (5.15b). In one transaction: promote the candidates that came back,
        make this episode's new voices and new names candidates, hold the proposals about candidates, drop the
        candidates whose window has passed. Returns the proposals to apply now, counts, and evidence ids of
        held proposals released by a promotion."""
        from subagent.memory.voice_learning import trusted_auto_lines
        from subagent.models import CastLine
        from subagent.stages.voice import load_line_voices
        from subagent.util import read_jsonl

        work = self.paths.episode_dir(episode_id)
        cast_embs = np.load(work / "cast_embeddings.npy") if (work / "cast_embeddings.npy").is_file() else None
        if cast_embs is not None and (cast_embs.ndim != 2 or not cast_embs.size):
            cast_embs = None
        run = _Run(episode_id=episode_id, current=episode_number(episode_id), approved=approved,
                   approved_ids=approved_ids, mode=mode, now=now_iso(),
                   cast={c.event_id: c for c in read_jsonl(work / "cast.jsonl", CastLine)}, cast_embs=cast_embs,
                   line_voices=load_line_voices(work / "voice_embeddings.npz"))
        with self._transaction(lock=False) as conn:
            run.conn = conn
            run.known = {r["id"] for r in conn.execute("SELECT id FROM characters")}
            run.rows = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM candidates")}
            for cid, r in list(run.rows.items()):         # rerun-safe: this episode's candidates are rebuilt
                if r["first_episode"] == episode_id and r["status"] == "candidate":
                    conn.execute("DELETE FROM candidate_sprites WHERE candidate_id=?", (cid,))
                    conn.execute("DELETE FROM candidates WHERE id=?", (cid,))
                    del run.rows[cid]
            if mode == "auto":
                run.trusted = {x.event_id for x in trusted_auto_lines(self.paths, self.config, episode_id,
                                                                       run.known | set(run.rows), min_ms=0)}
            released_proposals = self._promote_returning(run)
            self._add_candidates(run, proposals, voices)
            keep = released_proposals + self._hold_proposals(run, proposals)
            self._drop_expired(run)
        released = {e for p in released_proposals for e in p.evidence}
        return keep, run.counts, released

    def _promote_returning(self, run: _Run) -> list[MemoryProposal]:
        """1. Candidates that came back within their window become characters; returns their waiting proposals."""
        from subagent.memory import probation as pb

        window = self.config.memory.probation_window
        released: list[MemoryProposal] = []
        for cid, r in sorted(run.rows.items()):
            first = episode_number(r["first_episode"])
            if (r["status"] != "candidate" or cid in run.known or first is None or run.current is None
                    or not first < run.current <= first + window):
                continue
            lines = pb.speaker_lines(run.approved, cid)
            if run.trusted is not None:
                lines = [x for x in lines if x.event_id in run.trusted]
            if not lines:
                continue
            sprites = [np.frombuffer(s["embedding"], dtype=np.float16).astype(np.float32) for s in
                       run.conn.execute("SELECT embedding FROM candidate_sprites WHERE candidate_id=?", (cid,))]
            check = pb.check_return(lines, run.cast, run.cast_embs, sprites, self.config.cast.match_similarity)
            if not check.promote and run.mode != "human":
                log.info("probation: %s is back in %s but its look disagrees: %s", cid, run.episode_id,
                         check.describe())
                continue
            # human mode: the reviewer assigned these lines, so the picture cannot veto the return; a look
            # the picture disagrees with is not copied into the sprite bank (sprite learning relearns it)
            evidence = check.describe() if check.promote else f"assigned by the reviewer; {check.describe()}"
            self._promote(run.conn, r, run.episode_id, evidence, run.now, with_look=check.promote)
            run.known.add(cid)
            run.counts["promoted"] += 1
            released += [MemoryProposal.model_validate(d) for d in json.loads(r["pending_json"] or "[]")]
        return released

    def _add_candidates(self, run: _Run, proposals: list[MemoryProposal], voices: list[NewVoice]) -> None:
        """2. This episode's new voices and new names become candidates (with enough lines as speaker)."""
        from subagent.memory import probation as pb

        named: dict[str, MemoryProposal] = {}
        for p in proposals:
            cid = str(p.payload.get("id") or "")
            if p.kind == "character" and p.source == "translator" and cid and cid not in run.known:
                named.setdefault(cid, p)
        for cid in dict.fromkeys([v.id for v in voices if not v.returning_from] + sorted(named)):
            if cid in run.known or cid in run.rows:
                continue
            lines = pb.speaker_lines(run.approved, cid)
            if len(lines) < self.config.memory.probation_min_lines:
                continue
            payload = named[cid].payload if cid in named and set(named[cid].evidence) <= run.approved_ids else {}
            voice = pb.candidate_voice(lines, run.line_voices)
            row = {"id": cid, "first_episode": run.episode_id, "name_zh": payload.get("name_zh") or None,
                   "name_vi": payload.get("name_vi") or None, "description": payload.get("description") or None,
                   "embedding": voice.astype(np.float32).tobytes() if voice is not None else None,
                   "n_lines": len(lines), "pending_json": "[]", "status": "candidate",
                   "status_note": f"{len(lines)} lines in {run.episode_id}", "updated_at": run.now}
            _insert(run.conn, "candidates", row)
            for event_id, emb in pb.candidate_looks(lines, run.cast, run.cast_embs):
                run.conn.execute("INSERT INTO candidate_sprites (candidate_id, embedding, episode_id, event_id) "
                                 "VALUES (?,?,?,?)", (cid, emb.astype(np.float16).tobytes(), run.episode_id,
                                                      event_id))
            self._log(run.conn, "insert", "candidates", cid, None, row, None, len(lines), source="system",
                      reason=f"on probation: {len(lines)} lines in {run.episode_id}")
            run.rows[cid] = row
            run.counts["candidates"] += 1

    def _hold_proposals(self, run: _Run, proposals: list[MemoryProposal]) -> list[MemoryProposal]:
        """3. Proposals about candidates wait for the promotion (names and updates go on the candidate, pronoun
        pairs into its pending_json); returns the proposals to apply now."""
        waiting = {cid for cid, r in run.rows.items() if r["status"] == "candidate" and cid not in run.known}
        pending: dict[str, list[dict]] = {}
        keep: list[MemoryProposal] = []
        for p in proposals:
            cid = str(p.payload.get("id") or "")
            if p.kind == "character" and p.source in EVIDENCE_SOURCES and cid and cid not in run.known:
                if cid in waiting and set(p.evidence) <= run.approved_ids:
                    if p.source == "updater":
                        self._update_candidate(run.conn, run.rows[cid], p, run.now)
                    else:
                        self._name_candidate(run.conn, run.rows[cid], p, run.now)
                else:
                    self._log(run.conn, "rejected", "characters", cid or "?", None, p.payload, p,
                              len(p.evidence), reason="probation: fewer than "
                              f"{self.config.memory.probation_min_lines} approved lines as speaker")
                continue
            if p.kind == "pronoun_pair":
                ids = {str(p.payload.get("speaker_id")), str(p.payload.get("listener_id"))}
                held = sorted(ids & waiting)
                if held and not ids - run.known - waiting and set(p.evidence) <= run.approved_ids:
                    pending.setdefault(held[0], []).append(p.model_dump())
                    continue
            keep.append(p)
        for cid, items in pending.items():
            before = json.loads(run.rows[cid]["pending_json"] or "[]")
            run.conn.execute("UPDATE candidates SET pending_json=?, updated_at=? WHERE id=?",
                             (json.dumps(before + items, ensure_ascii=False), run.now, cid))
        return keep

    def _drop_expired(self, run: _Run) -> None:
        """4. Candidates whose window has passed are dropped (rows stay, status `dropped`)."""
        window = self.config.memory.probation_window
        for cid, r in sorted(run.rows.items()):
            first = episode_number(r["first_episode"])
            if (r["status"] == "candidate" and cid not in run.known and first is not None and run.current is not None
                    and run.current > first + window):
                note = f"not back within {window} episodes (checked at {run.episode_id})"
                run.conn.execute("UPDATE candidates SET status='dropped', status_note=?, updated_at=? WHERE id=?",
                                 (note, run.now, cid))
                self._log(run.conn, "update", "candidates", cid, r, {**r, "status": "dropped"}, None, 0,
                          source="system", reason=note)
                run.counts["dropped"] += 1

    def _promote(self, conn: sqlite3.Connection, cand: dict, episode_id: str, evidence: str, now: str,
                 with_look: bool = True) -> None:
        """A candidate that came back becomes a character, with its voice, look (unless `with_look` is false)
        and first appearance."""
        cid = cand["id"]
        row = {"id": cid, "name_zh": cand["name_zh"] or cid, "name_vi": cand["name_vi"] or cid,
               "description": cand["description"] or f"Voice found automatically in {cand['first_episode']}; "
                                                     f"back in {episode_id}",
               "locked": 0, "updated_at": now, "status": "active", "status_note": None, "generic": 0,
               "aliases": cand.get("aliases") or "[]"}
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


    def _update_candidate(self, conn: sqlite3.Connection, cand: dict, p: MemoryProposal, now: str) -> None:
        """A character update for a candidate (5.15c): a name if it has none yet, the new description, more aliases.
        They move to the character on promotion."""
        pl = p.payload
        after = dict(cand)
        if pl.get("name_vi") and (not cand.get("name_vi") or cand["name_vi"] == cand["id"]):
            after["name_zh"], after["name_vi"] = pl.get("name_zh") or cand.get("name_zh"), pl["name_vi"]
        if pl.get("description"):
            after["description"] = pl["description"]
        if "aliases" in pl:
            after["aliases"] = dumps_aliases(parse_aliases(cand.get("aliases")) + parse_aliases(pl["aliases"]))
        if all(after.get(f) == cand.get(f) for f in ("name_zh", "name_vi", "description", "aliases")):
            return
        after["updated_at"] = now
        conn.execute("UPDATE candidates SET name_zh=?, name_vi=?, description=?, aliases=?, updated_at=? WHERE id=?",
                     (after["name_zh"], after["name_vi"], after["description"], after.get("aliases") or "[]", now,
                      cand["id"]))
        self._log(conn, "update", "candidates", cand["id"], cand, after, p, len(p.evidence))
        cand.update(after)
