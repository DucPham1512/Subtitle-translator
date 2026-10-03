"""Baseline freeze: a fixed copy of finished reviews (gold + machine output + versions)."""

from __future__ import annotations

import json

import pytest

from subagent.baseline import baseline_dir, freeze, freeze_episode
from subagent.episodes import Registry
from tests.conftest import register_episode


def test_freeze_copies_finished_reviews_and_replaces_on_refreeze(project):
    config, paths = project
    ep1, ep2 = register_episode(paths, 1), register_episode(paths, 2)
    for ep in (ep1, ep2):
        work = paths.episode_dir(ep.id)
        work.mkdir(parents=True, exist_ok=True)
        (work / "approved.jsonl").write_text("one\n", encoding="utf-8")
        (work / "events.jsonl").write_text("ev\n", encoding="utf-8")
    Registry(paths).set_status(ep1.id, "done")                    # ep002 is not finished
    assert freeze(config, paths, "b") == ["ep001"]
    folder = baseline_dir(paths, "b")
    assert sorted(p.name for p in (folder / "ep001").iterdir()) == ["approved.jsonl", "events.jsonl"]
    (paths.episode_dir(ep1.id) / "approved.jsonl").write_text("two\n", encoding="utf-8")
    freeze_episode(config, paths, ep1.id, "b")                      # finished again: the copy is replaced
    assert (folder / "ep001" / "approved.jsonl").read_text(encoding="utf-8") == "two\n"
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert list(manifest["episodes"]) == ["ep001"] and manifest["episodes"]["ep001"]["config_hash"]
    (paths.episode_dir(ep2.id) / "approved.jsonl").unlink()
    with pytest.raises(FileNotFoundError):
        freeze_episode(config, paths, ep2.id, "b")
