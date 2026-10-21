"""Episode registry (5.21): add videos, detect episode numbers, link (never copy), relink."""

from __future__ import annotations

import hashlib
import logging
import re
from collections.abc import Callable, Iterable
from pathlib import Path

from pydantic import BaseModel

from subagent.kernel import (
    Episode,
    EpisodeNotFoundError,
    EpisodeStatus,
    FileLock,
    SourceMissingError,
    SubagentError,
    atomic_write_json,
    now_iso,
    read_json,
)
from subagent.settings import Config, Paths

log = logging.getLogger(__name__)

FINGERPRINT_CHUNK = 1 << 20


def episode_id(number: int) -> str:
    return f"ep{number:03d}"


def fingerprint(path: Path) -> str:
    """SHA-256 of size + first 1 MB + last 1 MB."""
    size = path.stat().st_size
    h = hashlib.sha256(str(size).encode("ascii"))
    with path.open("rb") as fh:
        h.update(fh.read(FINGERPRINT_CHUNK))
        if size > FINGERPRINT_CHUNK:
            fh.seek(max(0, size - FINGERPRINT_CHUNK))
            h.update(fh.read(FINGERPRINT_CHUNK))
    return h.hexdigest()


def detect_number(name: str, patterns: list[str]) -> int | None:
    """First pattern that matches the file stem wins; its first capture group is the number."""
    stem = Path(name).stem
    for pattern in patterns:
        try:
            m = re.search(pattern, stem)
        except re.error as exc:
            log.warning("Invalid episode number pattern %r: %s", pattern, exc)
            continue
        if m and m.groups():
            try:
                return int(m.group(1))
            except (TypeError, ValueError):
                continue
    return None


def scan_paths(paths: Iterable[Path], *, recursive: bool, extensions: list[str]) -> list[Path]:
    exts = {e.lower() for e in extensions}
    found: list[Path] = []
    seen: set[Path] = set()

    def consider(p: Path) -> None:
        rp = p.resolve()
        if rp not in seen and rp.suffix.lower() in exts and rp.is_file():
            seen.add(rp)
            found.append(rp)

    for path in paths:
        if path.is_dir():
            it = path.rglob("*") if recursive else path.iterdir()
            for child in sorted(it, key=lambda p: str(p).lower()):
                consider(child)
        elif path.exists():
            consider(path)
    return found


class AddCandidate(BaseModel):
    path: str
    number: int | None
    size: int
    mtime: float
    fingerprint: str
    problem: str | None = None        # no_video_stream | duplicate
    problem_detail: str = ""
    duplicate_of: str | None = None


class Registry:
    def __init__(self, paths: Paths):
        self.paths = paths
        self.file = paths.episodes_index
        self._lock_path = self.file.parent / ".lock"

    # -- persistence --------------------------------------------------------------------------------

    def load(self) -> list[Episode]:
        data = read_json(self.file, {"episodes": []}) or {"episodes": []}
        episodes = [Episode.model_validate(e) for e in data.get("episodes", [])]
        return sorted(episodes, key=lambda e: e.number)

    def _save(self, episodes: list[Episode]) -> None:
        episodes = sorted(episodes, key=lambda e: e.number)
        atomic_write_json(self.file, {"episodes": [e.model_dump(mode="json") for e in episodes]})

    def _mutate(self, fn: Callable[[list[Episode]], object]) -> object:
        with FileLock(self._lock_path, timeout=10, message="Episode registry is busy"):
            episodes = self.load()
            result = fn(episodes)
            self._save(episodes)
            return result

    # -- queries ------------------------------------------------------------------------------------

    def get(self, ep_id: str) -> Episode:
        for ep in self.load():
            if ep.id == ep_id:
                return ep
        raise EpisodeNotFoundError(f"Episode {ep_id} is not registered")

    def resolve(self, ref: str) -> Episode:
        """Accept 'ep003', '3' or '003'."""
        ref = ref.strip()
        if ref.isdigit():
            ref = episode_id(int(ref))
        return self.get(ref)

    def earlier_not_done(self, ep: Episode) -> list[Episode]:
        return [e for e in self.load() if e.number < ep.number and e.status != "done"]

    # -- adding -------------------------------------------------------------------------------------

    def prepare_add(self, inputs: Iterable[Path], config: Config, *, recursive: bool = False,
                    check_video: Callable[[Path], tuple[bool, str]] | None = None) -> list[AddCandidate]:
        """Scan inputs and detect numbers. Registers nothing; the user confirms first."""
        if check_video is None:
            from subagent.infra import has_video_stream

            check_video = has_video_stream
        existing = {e.source_fingerprint: e.id for e in self.load()}
        files = scan_paths(inputs, recursive=recursive, extensions=config.episodes.video_extensions)
        out: list[AddCandidate] = []
        batch_fps: dict[str, str] = {}
        for f in files:
            st = f.stat()
            fp = fingerprint(f)
            cand = AddCandidate(
                path=str(f), number=detect_number(f.name, config.episodes.number_patterns),
                size=st.st_size, mtime=st.st_mtime, fingerprint=fp,
            )
            if fp in existing:
                cand.problem, cand.duplicate_of = "duplicate", existing[fp]
            elif fp in batch_fps:
                cand.problem, cand.duplicate_of = "duplicate", batch_fps[fp]
            else:
                ok, detail = check_video(f)
                if not ok:
                    cand.problem, cand.problem_detail = "no_video_stream", detail
                else:
                    batch_fps[fp] = f.name
            out.append(cand)
        return out

    def validate_numbers(self, candidates: list[AddCandidate]) -> list[str]:
        """Problems that block registration: missing or clashing numbers."""
        errors: list[str] = []
        taken = {e.number: e.id for e in self.load()}
        seen: dict[int, str] = {}
        for c in candidates:
            if c.problem:
                continue
            name = Path(c.path).name
            if c.number is None:
                errors.append(f"{name}: no episode number")
            elif c.number < 0:
                errors.append(f"{name}: episode number must be positive")
            elif c.number in taken:
                errors.append(f"{name}: episode {c.number} is already registered ({taken[c.number]})")
            elif c.number in seen:
                errors.append(f"{name}: episode {c.number} is also assigned to {seen[c.number]}")
            else:
                seen[c.number] = name
        return errors

    def register(self, candidates: list[AddCandidate]) -> list[Episode]:
        errors = self.validate_numbers(candidates)
        if errors:
            raise SubagentError("Cannot register episodes:\n" + "\n".join(errors), code="episode_numbers_invalid")
        new = [
            Episode(
                id=episode_id(c.number), number=c.number, source_path=c.path, source_size=c.size,  # type: ignore[arg-type]
                source_mtime=c.mtime, source_fingerprint=c.fingerprint, added_at=now_iso(), status="new",
            )
            for c in candidates if not c.problem
        ]

        def add(episodes: list[Episode]) -> None:
            numbers = {e.number for e in episodes}
            for ep in new:
                if ep.number in numbers:
                    raise SubagentError(f"Episode {ep.number} is already registered", code="episode_numbers_invalid")
                episodes.append(ep)

        self._mutate(add)
        return new

    # -- status / links -----------------------------------------------------------------------------

    def update(self, ep_id: str, **fields: object) -> Episode:
        def change(episodes: list[Episode]) -> Episode:
            for i, e in enumerate(episodes):
                if e.id == ep_id:
                    episodes[i] = e.model_copy(update=fields)
                    return episodes[i]
            raise EpisodeNotFoundError(f"Episode {ep_id} is not registered")

        return self._mutate(change)  # type: ignore[return-value]

    def set_status(self, ep_id: str, status: EpisodeStatus) -> Episode:
        return self.update(ep_id, status=status)

    def check_source(self, ep_id: str) -> Episode:
        """Before any stage reads the video: mark `missing` and raise when the file is gone."""
        ep = self.get(ep_id)
        if not Path(ep.source_path).is_file():
            if ep.status != "missing":
                self.set_status(ep_id, "missing")
            raise SourceMissingError(
                f"The video for {ep_id} is missing: {ep.source_path}. Relink it to its new location."
            )
        if ep.status == "missing":
            ep = self.set_status(ep_id, derived_status(self.paths, ep))
        return ep

    def relink(self, ep_id: str, new_path: Path) -> tuple[Episode, bool]:
        """Point an episode at its moved video. Returns (episode, fingerprint_matches)."""
        new_path = new_path.resolve()
        if not new_path.is_file():
            raise SourceMissingError(f"File not found: {new_path}")
        ep = self.get(ep_id)
        fp = fingerprint(new_path)
        st = new_path.stat()
        matches = fp == ep.source_fingerprint
        updated = self.update(
            ep_id, source_path=str(new_path), source_size=st.st_size, source_mtime=st.st_mtime,
            source_fingerprint=fp, status=derived_status(self.paths, ep) if ep.status == "missing" else ep.status,
        )
        return updated, matches


def derived_status(paths: Paths, ep: Episode) -> EpisodeStatus:
    """Status from the work folder, used when an episode comes back from `missing`."""
    work = paths.episode_dir(ep.id)
    if ep.output_path and (work / "approved.jsonl").is_file():
        return "done"
    if (work / "review_draft.jsonl").is_file() and not (work / "approved.jsonl").is_file():
        return "awaiting_review"
    return "new"
