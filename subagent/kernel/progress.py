"""Progress reporting. With `--progress json`, one JSON object per line on stdout (used by the app)."""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
from typing import IO, Literal

log = logging.getLogger("subagent.kernel.progress")

Status = Literal["start", "progress", "done", "skipped", "error", "info", "awaiting_review", "finished"]


class Progress:
    def __init__(self, mode: Literal["json", "text", "none"] = "text", stream: IO[str] | None = None,
                 min_interval_s: float = 0.25):
        self.mode = mode
        self.stream = stream or sys.stdout
        self.cost = 0.0
        self._lock = threading.Lock()
        self._last_progress: dict[str, float] = {}
        self._min_interval = min_interval_s

    def set_cost(self, cost: float) -> None:
        self.cost = cost

    def emit(self, stage: str, status: Status, *, done: int | None = None, total: int | None = None,
             message: str = "", error_code: str | None = None, **extra: object) -> None:
        if status == "progress":
            now = time.monotonic()
            last = self._last_progress.get(stage, 0.0)
            if now - last < self._min_interval and not (done is not None and done == total):
                return
            self._last_progress[stage] = now
        payload = {
            "stage": stage, "status": status, "done": done, "total": total,
            "cost": round(self.cost, 6), "message": message, "error_code": error_code, **extra,
        }
        with self._lock:
            if self.mode == "json":
                self.stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
                self.stream.flush()
            elif self.mode == "text":
                if status == "progress":
                    return
                parts = [f"[{stage}] {status}"]
                if total:
                    parts.append(f"{done}/{total}")
                if message:
                    parts.append(message)
                log.info(" ".join(parts))


NULL_PROGRESS = Progress("none")
