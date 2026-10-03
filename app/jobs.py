"""Long jobs run the CLI in a child process (QProcess) with --progress json (6.1).

A crash or GPU error in a job cannot freeze or kill the app; cancelling is safe because stages resume.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, Signal


class JobRunner(QObject):
    started = Signal(str)                 # job name
    progress = Signal(dict)               # one parsed JSON progress line
    log_line = Signal(str)                # stderr (logging) and non-JSON stdout
    finished = Signal(str, int, dict)     # job name, exit code, last error payload ({} when none)

    def __init__(self, root: Path, parent: QObject | None = None):
        super().__init__(parent)
        self.root = root
        self.proc: QProcess | None = None
        self.name = ""
        self.cost = 0.0
        self._stdout_buf = b""
        self._stderr_buf = b""
        self._last_error: dict = {}
        self._cancelled = False

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.state() != QProcess.ProcessState.NotRunning

    def start(self, name: str, args: list[str]) -> bool:
        if self.is_running():
            return False
        self.name = name
        self.cost = 0.0
        self._stdout_buf = self._stderr_buf = b""
        self._last_error = {}
        self._cancelled = False
        proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUTF8", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("SUBAGENT_ROOT", str(self.root))
        proc.setProcessEnvironment(env)
        proc.setWorkingDirectory(str(self.root))
        proc.readyReadStandardOutput.connect(self._read_stdout)
        proc.readyReadStandardError.connect(self._read_stderr)
        proc.finished.connect(self._done)
        self.proc = proc
        proc.start(sys.executable, ["-m", "subagent", *args, "--progress", "json"])
        self.started.emit(name)
        return True

    def cancel(self) -> None:
        if self.is_running() and self.proc is not None:
            self._cancelled = True
            self.proc.kill()

    def _lines(self, buf: bytes, chunk: bytes) -> tuple[list[str], bytes]:
        buf += chunk
        *complete, rest = buf.split(b"\n")
        return [c.decode("utf-8", "replace").rstrip("\r") for c in complete], rest

    def _read_stdout(self) -> None:
        assert self.proc is not None
        lines, self._stdout_buf = self._lines(self._stdout_buf, bytes(self.proc.readAllStandardOutput()))
        for line in lines:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError:
                self.log_line.emit(line)
                continue
            if isinstance(payload, dict) and "stage" in payload:
                self.cost = float(payload.get("cost") or self.cost)
                if payload.get("status") == "error":
                    self._last_error = payload
                self.progress.emit(payload)
            else:
                self.log_line.emit(line)

    def _read_stderr(self) -> None:
        assert self.proc is not None
        lines, self._stderr_buf = self._lines(self._stderr_buf, bytes(self.proc.readAllStandardError()))
        for line in lines:
            if line.strip():
                self.log_line.emit(line)

    def _done(self, code: int, _status: QProcess.ExitStatus) -> None:
        self._read_stdout()
        self._read_stderr()
        name, error = self.name, self._last_error
        if self._cancelled:
            error = {"error_code": "cancelled", "message": ""}
        elif code != 0 and not error:
            error = {"error_code": "internal", "message": ""}
        self.proc = None
        self.finished.emit(name, code, error if code != 0 else {})
