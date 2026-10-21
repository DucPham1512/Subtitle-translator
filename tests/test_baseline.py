"""Baseline freeze: a fixed copy of finished reviews (gold + machine output + versions)."""

from __future__ import annotations

import json

import pytest

from subagent.baseline import baseline_dir, freeze, freeze_episode
from subagent.workspace.episodes import Registry
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


def test_complete_adds_missing_files_only_while_the_review_is_unchanged(project):
    from subagent.baseline import complete

    config, paths = project
    ep1, ep2 = register_episode(paths, 1), register_episode(paths, 2)
    for ep in (ep1, ep2):
        work = paths.episode_dir(ep.id)
        work.mkdir(parents=True, exist_ok=True)
        (work / "approved.jsonl").write_text("one\n", encoding="utf-8")
        freeze_episode(config, paths, ep.id, "b")
        (work / "windows.json").write_text("[]", encoding="utf-8")       # a file the old freeze did not copy
    (paths.episode_dir(ep2.id) / "approved.jsonl").write_text("reviewed again\n", encoding="utf-8")
    key = paths.work / "_ocr_benchmark" / "answer_key.json"
    key.parent.mkdir(parents=True)
    key.write_text('{"corrections": {}}', encoding="utf-8")
    assert complete(paths, "b") == {"ep001": ["windows.json"], "ep002": []}
    folder = baseline_dir(paths, "b")
    assert (folder / "ep001" / "windows.json").is_file() and not (folder / "ep002" / "windows.json").exists()
    assert (folder / "answer_key.json").is_file()
    assert (folder / "ep002" / "approved.jsonl").read_text(encoding="utf-8") == "one\n"   # frozen gold untouched
