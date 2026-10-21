"""Memory Manager (5.15): the only component allowed to write memory.

Write rules:
- A locked entry changes only through a human proposal (bootstrap seeds are human-reviewed, so they count too).
- Translator proposals apply only when every evidence line was approved.
- Human and bootstrap writes lock the entry.
- A proposal that conflicts with an unlocked entry applies only with more evidence than the current entry;
  otherwise it goes to conflicts.md (and conflicts.json, its machine-readable twin) for review.
- Every write runs in a transaction and adds a memory_log row; rejections are logged as op="rejected".

The manager is assembled from one module per responsibility (rule 9: memory is written only by
this package): apply, banks, episode, candidates, updates, history; rows / results / proposals hold
the helpers they share.
"""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Iterator

from subagent.kernel.errors import MemoryLockedError
from subagent.kernel.util import (
    FileLock,
    atomic_write_text,
)
from subagent.memory import briefings as bf
from subagent.memory.manager.apply import ApplyMixin
from subagent.memory.manager.banks import BanksMixin
from subagent.memory.manager.candidates import CandidatesMixin
from subagent.memory.manager.episode import EpisodeMixin
from subagent.memory.manager.history import HistoryMixin
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
from subagent.memory.manager.updates import UpdatesMixin
from subagent.memory.store import (
    SCHEMA,
    MemoryStore,
    migrate,
)
from subagent.settings.config import Config, Paths


class MemoryManager(ApplyMixin, EpisodeMixin, CandidatesMixin, UpdatesMixin, BanksMixin, HistoryMixin):
    """The only writer of memory (5.15)."""

    def __init__(self, paths: Paths, config: Config):
        self.paths = paths
        self.config = config
        self.dir = paths.memory
        self.db = paths.memory_db
        self.store = MemoryStore(self.db)
        self._lock_depth = 0
        self._lock = FileLock(self.dir / ".lock", timeout=30, error=MemoryLockedError,
                              message="Memory is being written by another process")

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

    @contextlib.contextmanager
    def _transaction(self, *, lock: bool = True) -> Iterator[sqlite3.Connection]:
        """One write transaction: BEGIN IMMEDIATE, COMMIT, or ROLLBACK on any error. `lock`: hold the memory lock
        (False only inside a caller that already holds it)."""
        with self.locked() if lock else contextlib.nullcontext(), self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except BaseException:
                conn.execute("ROLLBACK")
                raise

    def _ensure_schema(self) -> None:
        if not self.db.is_file() or not (self.dir / ".git").exists():
            self.ensure_repo()
            return
        with self._connect() as conn:   # tables added in later versions (CREATE ... IF NOT EXISTS)
            conn.executescript(SCHEMA)
            migrate(conn)


__all__ = ["MemoryManager", "KIND_ORDER", "KIND_TABLE", "COLUMNS", "REQUIRED", "LOCKING_SOURCES", "EVIDENCE_SOURCES", "BRIEFING_FILES", "UPDATES_FILE", "UPDATE_REJECTIONS_FILE", "BACKUP_ITEMS", "ApplyResult", "Conflict", "PendingUpdate", "CommitInfo", "TableDiff", "MemoryDiff", "dumps_aliases", "held_updates", "describe_update", "merge_proposals", "replaced_term", "reviewed_glossary"]
