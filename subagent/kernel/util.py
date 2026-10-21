"""Small shared helpers: atomic writes, JSONL I/O, hashing, file locks."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tempfile
import time
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from subagent.kernel.errors import SubagentError

M = TypeVar("M", bound=BaseModel)


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        _replace_with_retry(Path(tmp), path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _replace_with_retry(src: Path, dst: Path, attempts: int = 10) -> None:
    # On Windows a reader (antivirus, file watcher) can briefly hold the target open.
    for i in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(0.05 * (i + 1))


def atomic_write_bytes(path: Path, data: bytes) -> None:
    _atomic_write(path, data)


def atomic_write_text(path: Path, text: str) -> None:
    _atomic_write(path, text.encode("utf-8"))


def atomic_write_json(path: Path, obj: object) -> None:
    atomic_write_text(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def read_json(path: Path, default: object = None) -> object:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, items: Iterable[BaseModel]) -> None:
    lines = [item.model_dump_json() for item in items]
    atomic_write_text(path, "".join(line + "\n" for line in lines))


def read_jsonl(path: Path, model: type[M]) -> list[M]:
    if not path.is_file():
        return []
    out: list[M] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(model.model_validate_json(line))
    return out


def append_jsonl(path: Path, obj: BaseModel | dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = obj.model_dump_json() if isinstance(obj, BaseModel) else json.dumps(obj, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(obj: object) -> str:
    return sha256_bytes(json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8"))


def hash_path(path: Path) -> str:
    """Content hash of a file, or a cheap listing hash (names + sizes) of a directory."""
    if path.is_dir():
        entries = sorted((p.relative_to(path).as_posix(), p.stat().st_size) for p in path.rglob("*") if p.is_file())
        return sha256_json(entries)
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == still_active
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def lock_holder(path: Path) -> int | None:
    """PID holding a lock file, or None when the lock is free or stale."""
    try:
        pid = int(path.read_text(encoding="utf-8").strip() or "0")
    except (OSError, ValueError):
        return None
    return pid if pid_alive(pid) else None


class FileLock:
    """Exclusive lock file holding the owner's PID. Stale locks (dead PID) are taken over."""

    def __init__(self, path: Path, *, timeout: float = 0.0, error: type[SubagentError] = SubagentError,
                 message: str = "locked"):
        self.path = path
        self.timeout = timeout
        self.error = error
        self.message = message
        self._held = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    fh.write(str(os.getpid()))
                self._held = True
                return
            except FileExistsError:
                holder = lock_holder(self.path)
                if holder is None or holder == os.getpid():
                    with contextlib.suppress(OSError):
                        self.path.unlink()
                    continue
                if time.monotonic() >= deadline:
                    raise self.error(f"{self.message} (held by process {holder})") from None
                time.sleep(0.1)

    def release(self) -> None:
        if self._held:
            with contextlib.suppress(OSError):
                self.path.unlink()
            self._held = False

    def __enter__(self) -> FileLock:
        self.acquire()
        return self

    def __exit__(self, *exc: object) -> None:
        self.release()


def chunked(items: list, size: int) -> Iterator[list]:
    for i in range(0, len(items), max(1, size)):
        yield items[i : i + size]
