"""OCR pre-processing (5.4): subtitle mask, box filter, coordinates; OCR benchmark scoring (6.11c)."""

from __future__ import annotations

import cv2
import numpy as np

from subagent.models import OcrBox, ReviewedLine, SubtitleEvent
from subagent.ocr_benchmark import score_episode
from subagent.stages.ocr import filter_boxes, prepare, subtitle_mask, to_band_coords


def _band() -> np.ndarray:
    """A grey band with an outlined white 'subtitle' (left) and dark writing on a white prop (right)."""
    band = np.full((48, 400), 120, np.uint8)
    for x in (40, 80, 120):                                    # three outlined "glyphs"
        cv2.rectangle(band, (x - 3, 7), (x + 25, 41), 0, -1)   # black outline
        cv2.rectangle(band, (x, 10), (x + 22, 38), 255, -1)    # white fill
        cv2.line(band, (x + 11, 12), (x + 11, 36), 0, 3)       # a stroke gap (two components per glyph)
    cv2.rectangle(band, (280, 2), (390, 46), 250, -1)          # a white cooler...
    cv2.putText(band, "X", (320, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 20, 3)   # ...with dark writing on it
    return band


def test_mask_keeps_outlined_subtitle_and_drops_props(project):
    config, _ = project
    out = subtitle_mask(_band(), config.ocr)
    assert out.dtype == np.uint8 and set(np.unique(out)) <= {0, 255}
    assert (out[10:38, 40:63] == 0).mean() > 0.6                  # subtitle fill became black text
    assert (out[:, 270:] == 255).all()                            # the cooler and its writing are gone
    assert (out[:, :30] == 255).all()                             # plain background is white


def test_prepare_scales_pads_and_maps_back(project):
    config, _ = project
    config.ocr.preprocess = "mask"
    img, scale, pad = prepare(_band(), config.ocr)
    assert img.shape == (48 * 2 + 2 * pad, 400 * 2 + 2 * pad) and (scale, pad) == (2.0, config.ocr.mask_pad)
    raw = [([[pad + 80, pad + 20], [pad + 120, pad + 20], [pad + 120, pad + 76], [pad + 80, pad + 76]], "字", 0.9)]
    (pts, _, _), = to_band_coords(raw, scale, pad)
    assert pts[0] == [40.0, 10.0] and pts[2] == [60.0, 38.0]
    config.ocr.preprocess = "none"
    band = _band()
    assert prepare(band, config.ocr)[0] is band


def _box(text: str, x0: float, x1: float, y0: float = 0.0, y1: float = 1.0) -> OcrBox:
    return OcrBox(text=text, confidence=0.9, x0=x0, x1=x1, y0=y0, y1=y1)


def test_box_filter_drops_short_and_distant_boxes(project):
    config, _ = project
    main, near = _box("竿门开", 0.40, 0.60), _box("了", 0.61, 0.64)
    short = _box("楚", 0.626, 0.657, 0.0, 0.5)                    # half as tall: a prop label
    far = _box("史", 0.82, 0.90)                                  # same height, far from the line
    boxes = [main, near, short, far]
    assert filter_boxes(boxes, 772, 48, config.ocr) == boxes      # off by default
    config.ocr.box_filter = True
    assert filter_boxes(boxes, 772, 48, config.ocr) == [main, near]


def _gold(i: int, zh: str, start: int) -> ReviewedLine:
    return ReviewedLine(event_id=f"ep001:{i:04d}", start_ms=start, end_ms=start + 900, speaker=None, listener=None,
                        zh=zh, pinyin="", vi="x", approved=True)


def _event(i: int, zh: str, start: int, end: int) -> SubtitleEvent:
    return SubtitleEvent(id=f"ep001:{i:04d}", start_ms=start, end_ms=end, zh_raw=zh, zh=zh, ocr_conf=0.9)


def test_benchmark_scores_by_time_overlap():
    gold = [_gold(0, "你终于来了！", 0), _gold(1, "竿门开", 1000), _gold(2, "走吧", 5000)]
    events = [_event(0, "你终于来了", 0, 900), _event(1, "竿门开楚", 950, 1900), _event(2, "465", 3000, 3250)]
    s = score_episode("ep001", gold, events)
    assert (s.lines, s.exact, s.missed, s.junk) == (3, 1, 1, 1)   # punctuation ignored; 走吧 missed; 465 junk
    assert s.char_errors == 1 + 2 and s.chars == 5 + 3 + 2
    assert s.wrong[0] == {"event_id": "ep001:0001", "gold": "竿门开", "got": "竿门开楚"}


def test_answer_key_corrects_and_excludes_lines(project):
    import json

    from subagent.ocr_benchmark import FOLDER, KEY_FILE, _norm, gold_lines, load_key
    from subagent.util import write_jsonl

    config, paths = project
    work = paths.episode_dir("ep001")
    work.mkdir(parents=True)
    write_jsonl(work / "approved.jsonl", [_gold(0, "姬有巨物", 0), _gold(1, "北匕", 1000), _gold(2, "走吧", 2000)])
    assert [g.zh for g in gold_lines(work, load_key(paths))] == ["姬有巨物", "北匕", "走吧"]     # no key yet
    (paths.work / FOLDER).mkdir(parents=True)
    (paths.work / FOLDER / KEY_FILE).write_text(json.dumps({
        "corrections": {"ep001:0000": "有巨物", "ep001:0001": "北鼻"}, "excluded": {"ep001:0002": "no subtitle"}},
        ensure_ascii=False), encoding="utf-8")
    assert [(g.event_id, g.zh) for g in gold_lines(work, load_key(paths))] == [
        ("ep001:0000", "有巨物"), ("ep001:0001", "北鼻")]
    assert _norm("別逞强了！") == _norm("别逞强了")                      # variants and punctuation are equal


def test_stroke_and_brightness_tests_drop_outlined_surfaces(project):
    config, _ = project
    band = _band()
    cv2.rectangle(band, (180, 3), (240, 45), 0, -1)                # a dark-edged prop...
    cv2.rectangle(band, (183, 6), (237, 42), 225, -1)              # ...with a wide, light-grey (not white) surface
    config.ocr.mask_max_stroke, config.ocr.mask_min_mean = 0.0, 0
    assert (subtitle_mask(band, config.ocr)[:, 183:238] == 0).any()   # passes the outline test alone
    config.ocr.mask_max_stroke = 0.14
    out = subtitle_mask(band, config.ocr)
    assert (out[:, 183:238] == 255).all() and (out[10:38, 40:63] == 0).mean() > 0.6   # too wide: dropped
    config.ocr.mask_max_stroke, config.ocr.mask_min_mean = 0.0, 238
    assert (subtitle_mask(band, config.ocr)[:, 183:238] == 255).all()                 # not white enough: dropped


def test_frames_showing_the_same_subtitle_are_fused():
    from subagent.config import VideoConfig
    from subagent.stages.ingest import detect_changes, fuse

    text = np.full((20, 60), 30, np.uint8)
    cv2.rectangle(text, (10, 5), (50, 15), 255, -1)
    noisy = [np.clip(text.astype(int) + d, 0, 255).astype(np.uint8) for d in (-6, 0, 6)]
    changes = list(detect_changes(noisy, 4, VideoConfig(subtitle_detection="bright"), repeats=True))
    assert [c.kind for c in changes] == ["text", "same", "same"]
    assert (fuse([c.band for c in changes]) == text).all()                          # median removes the noise
    assert [c.kind for c in detect_changes(noisy, 4, VideoConfig(subtitle_detection="bright"))] == ["text"]


def test_crop_view_places_what_ocr_read_in_the_band(project):
    from subagent.stages.ocr import crop_view

    config, _ = project
    config.ocr.preprocess, config.ocr.recognize, config.ocr.mask_image, config.ocr.mask_scale = "mask", "line", "original", 1.0
    band = _band()
    image, scale, pad = prepare(band, config.ocr)
    view = crop_view(band, image, scale, pad)
    assert view.shape == band.shape
    x0 = pad[1] if isinstance(pad, tuple) else 0
    assert (view[:, x0:x0 + 20] == band[:, x0:x0 + 20]).all()        # original pixels at their place
    assert (view[:, 300:] == 128).all()                              # the prop was not read: grey
    assert (crop_view(band, np.zeros((0, 0), np.uint8), 1.0, 0) == 128).all()
