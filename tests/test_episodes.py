from __future__ import annotations

from pathlib import Path

import pytest

from subagent.episodes import Registry, detect_number, fingerprint
from subagent.kernel.errors import SourceMissingError, SubagentError


@pytest.mark.parametrize(("name", "expected"), [
    ("仙侠第3集.mp4", 3),
    ("第 12 话 终章.mkv", 12),
    ("Show.EP03.1080p.mp4", 3),
    ("show_episode-7.mkv", 7),
    ("show E05 final.mp4", 5),
    ("2024 show 17.mp4", 2024),
    ("no number here.mp4", None),
])
def test_detect_number(project, name, expected):
    config, _ = project
    assert detect_number(name, config.episodes.number_patterns) == expected


def _video(folder: Path, name: str, payload: bytes) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / name
    p.write_bytes(payload * 1000)
    return p


def test_add_register_duplicates_and_numbers(project, tmp_path):
    config, paths = project
    src = tmp_path / "videos"
    _video(src, "第1集.mp4", b"a")
    _video(src, "第2集.mkv", b"b")
    _video(src / "sub", "第3集.mp4", b"c")
    (src / "notes.txt").write_text("x", encoding="utf-8")
    reg = Registry(paths)

    flat = reg.prepare_add([src], config, check_video=lambda p: (True, ""))
    assert [c.number for c in flat] == [1, 2]
    deep = reg.prepare_add([src], config, recursive=True, check_video=lambda p: (True, ""))
    assert sorted(c.number for c in deep) == [1, 2, 3]

    registered = reg.register(deep)
    assert [e.id for e in reg.load()] == ["ep001", "ep002", "ep003"]
    assert all(Path(e.source_path).is_absolute() for e in registered)

    again = reg.prepare_add([src / "第1集.mp4"], config, check_video=lambda p: (True, ""))
    assert again[0].problem == "duplicate" and again[0].duplicate_of == "ep001"


def test_register_rejects_missing_and_clashing_numbers(project, tmp_path):
    config, paths = project
    a = _video(tmp_path / "v", "untitled.mp4", b"x")
    b = _video(tmp_path / "v", "EP01.mp4", b"y")
    c = _video(tmp_path / "v", "E01 copy.mp4", b"z")
    reg = Registry(paths)
    cands = reg.prepare_add([a, b, c], config, check_video=lambda p: (True, ""))
    errors = reg.validate_numbers(cands)
    assert any("no episode number" in e for e in errors)
    assert any("also assigned" in e for e in errors)
    with pytest.raises(SubagentError):
        reg.register(cands)


def test_no_video_stream_is_skipped(project, tmp_path):
    config, paths = project
    f = _video(tmp_path / "v", "EP04.mp4", b"q")
    cands = Registry(paths).prepare_add([f], config, check_video=lambda p: (False, "No video stream"))
    assert cands[0].problem == "no_video_stream"


def test_missing_source_and_relink(project, tmp_path):
    config, paths = project
    f = _video(tmp_path / "v", "EP01.mp4", b"m")
    reg = Registry(paths)
    reg.register(reg.prepare_add([f], config, check_video=lambda p: (True, "")))
    moved = tmp_path / "moved" / "EP01.mp4"
    moved.parent.mkdir()
    f.rename(moved)
    with pytest.raises(SourceMissingError):
        reg.check_source("ep001")
    assert reg.get("ep001").status == "missing"

    ep, matches = reg.relink("ep001", moved)
    assert matches and ep.status == "new" and ep.source_path == str(moved.resolve())

    other = _video(tmp_path / "other", "EP01.mp4", b"different")
    _, matches = reg.relink("ep001", other)
    assert not matches


def test_fingerprint_reads_head_and_tail(tmp_path):
    a = tmp_path / "a.bin"
    b = tmp_path / "b.bin"
    a.write_bytes(b"\x00" * 3_000_000 + b"end-a")
    b.write_bytes(b"\x00" * 3_000_000 + b"end-b")
    assert fingerprint(a) != fingerprint(b)
