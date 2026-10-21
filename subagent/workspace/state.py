"""work/<episode>/state.json: per-stage input/output hashes, timings and purge marks (NFR-R1)."""

from __future__ import annotations

from pathlib import Path

from subagent.kernel import EpisodeState, atomic_write_text


def state_path(work: Path) -> Path:
    return work / "state.json"


def load_state(work: Path, episode_id: str) -> EpisodeState:
    path = state_path(work)
    if path.is_file():
        return EpisodeState.model_validate_json(path.read_text(encoding="utf-8"))
    return EpisodeState(episode_id=episode_id)


def save_state(work: Path, state: EpisodeState) -> None:
    atomic_write_text(state_path(work), state.model_dump_json(indent=2))
