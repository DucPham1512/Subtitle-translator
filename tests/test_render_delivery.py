from __future__ import annotations

import pysubs2
import pytest

from subagent.delivery import cleanup, deliver, keep_both_path, output_name, resolve_conflict
from subagent.kernel.errors import OutputExistsError, OutputFolderError
from subagent.kernel.models import ReviewedLine, StageState
from subagent.settings.config import Band
from subagent.stages.render import Layout, build_ass, build_mask_filter
from subagent.state import load_state, save_state


def _line(i, vi, pinyin="nǐ hǎo", line_type="dialogue"):
    return ReviewedLine(event_id=f"ep001:{i:04d}", start_ms=i * 1000, end_ms=i * 1000 + 900, speaker="a",
                        listener=None, zh="你好", pinyin=pinyin, vi=vi, line_type=line_type, approved=True)


def test_ass_has_two_events_per_line_with_same_timing(project):
    config, _ = project
    subs = build_ass([_line(0, "Xin chào"), _line(1, "Cửa hàng", line_type="sign")], config, 1920, 1080)
    assert subs.info["PlayResX"] == "1920" and subs.info["PlayResY"] == "1080"
    assert set(subs.styles) == {"Pinyin", "Vi", "Sign"} and subs.styles["Sign"].italic
    assert [(e.style, e.start, e.end) for e in subs] == [("Vi", 0, 900), ("Pinyin", 0, 900),
                                                         ("Sign", 1000, 1900), ("Pinyin", 1000, 1900)]
    vi, py = subs[0], subs[1]
    assert py.marginv > vi.marginv          # pinyin sits above the Vietnamese line
    text = subs.to_string("ass")
    assert "Xin chào" in text and "nǐ hǎo" in text


def test_font_sizes_scale_with_height(project):
    config, _ = project
    subs = build_ass([_line(0, "x")], config, 1280, 720)
    assert subs.styles["Vi"].fontsize == pytest.approx(config.render.vi_font_size * 720 / 1080, abs=0.1)


def test_long_pinyin_shrinks_then_wraps(project):
    config, _ = project
    config.video.subtitle_band = Band()          # expected values assume the default band, not yours
    layout = Layout(config, 1920, 1080)
    scale, lines = layout.fit_pinyin("a" * 60)
    assert scale == 1.0 and len(lines) == 1
    words = " ".join(["zhōngguó"] * 12)
    scale, lines = layout.fit_pinyin(words)
    assert config.render.pinyin_min_scale <= scale < 1.0 and len(lines) == 1
    words = " ".join(["zhōngguó"] * 30)
    scale, lines = layout.fit_pinyin(words)
    assert scale == config.render.pinyin_min_scale and len(lines) >= 2


def test_user_text_cannot_inject_ass_overrides(project):
    config, _ = project
    subs = build_ass([_line(0, "{\\b1}bold")], config, 1920, 1080)
    assert "{\\b1}" not in subs[0].text
    loaded = pysubs2.SSAFile.from_string(subs.to_string("ass"))
    assert len(loaded) == 2


def test_mask_filters(project):
    config, _ = project
    config.video.subtitle_band = Band()          # expected values assume the default band, not yours
    blur = build_mask_filter(config, 1920, 1080)
    assert blur.startswith("split[") and "boxblur=" in blur and blur.endswith("overlay=96:864")
    config.render.mask = "box"
    assert build_mask_filter(config, 1920, 1080).startswith("drawbox=x=96:y=864")


def test_output_names_and_conflicts(tmp_path):
    src = tmp_path / "ep03.mkv"
    assert output_name(src, "_vi") == "ep03_vi.mp4"
    target = tmp_path / "ep03_vi.mp4"
    assert resolve_conflict(target, "fail") == target
    target.write_bytes(b"old")
    with pytest.raises(OutputExistsError):
        resolve_conflict(target, "fail")
    assert resolve_conflict(target, "overwrite") == target
    assert keep_both_path(target).name == "ep03_vi (2).mp4"
    (tmp_path / "ep03_vi (2).mp4").write_bytes(b"x")
    assert keep_both_path(target).name == "ep03_vi (3).mp4"


def test_deliver_moves_and_never_overwrites_silently(tmp_path):
    tmp = tmp_path / "work" / "render.tmp.mp4"
    tmp.parent.mkdir()
    tmp.write_bytes(b"video")
    out = tmp_path / "out"
    out.mkdir()
    final = deliver(tmp, out / "a_vi.mp4", "fail")
    assert final.read_bytes() == b"video" and not tmp.exists()
    tmp.write_bytes(b"video2")
    assert deliver(tmp, out / "a_vi.mp4", "keep_both").name == "a_vi (2).mp4"


def test_output_folder_required(project):
    from subagent.delivery import output_folder

    config, _ = project
    config.output.folder = None
    with pytest.raises(OutputFolderError):
        output_folder(config)


def test_cleanup_keeps_script_and_marks_purged(tmp_path):
    work = tmp_path / "ep001"
    (work / "bands").mkdir(parents=True)
    (work / "bands" / "0.png").write_bytes(b"x")
    for name in ("audio.wav", "preview.ass", "render.tmp.mp4", "events.jsonl", "approved.jsonl"):
        (work / name).write_bytes(b"x")
    state = load_state(work, "ep001")
    state.stages["ingest"] = StageState()
    state.stages["audio"] = StageState()
    save_state(work, state)
    removed = cleanup(work, "ep001")
    assert set(removed) == {"bands", "audio.wav", "preview.ass", "render.tmp.mp4"}
    assert (work / "events.jsonl").exists() and (work / "approved.jsonl").exists()
    state = load_state(work, "ep001")
    assert state.stages["ingest"].status == "purged" and state.stages["audio"].status == "purged"


def test_deleted_lines_are_not_rendered(project):
    config, _ = project
    deleted = _line(1, "Rác OCR").model_copy(update={"deleted": True})
    subs = build_ass([_line(0, "Xin chào"), deleted], config, 1920, 1080)
    assert len(subs) == 2 and "Rác OCR" not in subs.to_string("ass")
