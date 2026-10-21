"""The memory folder's git history: commit, history, diff, rollback."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from subagent.infra.joblock import running_jobs
from subagent.kernel.errors import JobRunningError
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
    TABLES,
    MemoryStore,
    row_key,
)

log = logging.getLogger(__name__)


class HistoryMixin:
    """The memory folder's git history: commit, history, diff, rollback. Part of MemoryManager."""

    def commit(self, message: str) -> str | None:
        from subagent.infra.media import git

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
        from subagent.infra.media import git

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
        from subagent.infra.media import require_binary, run

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
        from subagent.infra.media import git

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
        from subagent.infra.media import git

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
