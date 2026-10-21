"""Stages 1-4: change detection, OCR readings, event building, OCR correction."""

from __future__ import annotations

import numpy as np

from subagent.kernel.models import ChangeRecord, OcrReading, SubtitleEvent
from subagent.kernel.util import read_jsonl, write_jsonl
from subagent.ocr import events as events_stage
from subagent.ocr import ocr as ocr_stage
from subagent.ocr import ocr_fix
from subagent.ocr.ingest import detect_changes
from subagent.workspace.context import EpisodeContext
from tests.conftest import make_episode, make_llm, user_json, write_events

# -- ingest ----------------------------------------------------------------------------------------

def _band(pattern: int | None) -> np.ndarray:
    band = np.zeros((40, 200), dtype=np.uint8)
    if pattern is not None:
        band[10:30, 20 + pattern * 30: 60 + pattern * 30] = 255
    return band


def test_detect_changes_emits_text_and_empty(project):
    config, _ = project
    frames = [_band(None), _band(0), _band(0), _band(1), _band(1), _band(None), _band(None), _band(2)]
    changes = list(detect_changes(frames, fps=4, cfg=config.video))
    assert [(c.t_ms, c.kind) for c in changes] == [(250, "text"), (750, "text"), (1250, "empty"), (1750, "text")]
    assert changes[0].band is not None and changes[2].band is None


def test_small_noise_is_not_a_change(project):
    config, _ = project
    a = _band(0)
    b = a.copy()
    b[0, 0] = 255   # one pixel
    assert len(list(detect_changes([a, b], fps=4, cfg=config.video))) == 1


# -- OCR -------------------------------------------------------------------------------------------

def _box(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def test_reading_joins_boxes_left_to_right_and_filters(project):
    config, _ = project
    raw = [(_box(110, 10, 190, 30), "筑基了。", 0.9), (_box(10, 12, 100, 31), "弟子abc已经", 0.8)]
    r = ocr_stage.reading_from_boxes(0, raw, 200, 40, config.ocr)
    assert r.text == "弟子已经筑基了。"
    assert not r.multi_row and not r.low_conf
    assert 0.8 < r.confidence < 0.9
    assert abs(r.box_hcenter - 0.5) < 0.01


def test_reading_detects_multiple_rows_and_low_confidence(project):
    config, _ = project
    raw = [(_box(10, 2, 190, 15), "第一行", 0.4), (_box(10, 25, 190, 38), "第二行", 0.5)]
    r = ocr_stage.reading_from_boxes(0, raw, 200, 40, config.ocr)
    assert r.multi_row and r.low_conf and r.text == "第一行第二行"


def test_ocr_stage_with_fake_engine(project):
    config, paths = project
    from subagent.infra.media import imwrite_png

    ctx = EpisodeContext(config, paths, make_episode(paths))
    ctx.work.mkdir(parents=True)
    write_jsonl(ctx.artifact("changes.jsonl"), [ChangeRecord(t_ms=0, kind="text"), ChangeRecord(t_ms=500, kind="empty")])
    imwrite_png(ctx.artifact("bands") / "0.png", _band(0))
    counts = ocr_stage.run(ctx, engine=lambda img: [(_box(10, 5, 100, 35), "你好", 0.99)])
    readings = read_jsonl(ctx.artifact("ocr_raw.jsonl"), OcrReading)
    assert [r.kind for r in readings] == ["text", "empty"] and readings[0].text == "你好"
    assert counts["readings"] == 1


# -- events ----------------------------------------------------------------------------------------

def _r(t, text, conf=0.9, h=0.4, vc=0.5, hc=0.5, kind="text", multi=False):
    return OcrReading(t_ms=t, kind=kind, text=text, confidence=conf, box_height=h, box_vcenter=vc, box_hcenter=hc,
                      multi_row=multi)


def test_events_merge_similar_readings_and_pick_the_most_frequent(project):
    config, _ = project
    readings = [_r(0, "弟子已经筑基了"), _r(250, "弟子己经筑基了"), _r(500, "弟子已经筑基了"),
                _r(750, "", kind="empty"), _r(1000, "很好"), _r(1500, "下山")]
    evs = events_stage.build_events(readings, "ep001", 3000, config)
    assert [(e.zh_raw, e.start_ms, e.end_ms) for e in evs] == [
        ("弟子已经筑基了", 0, 750), ("很好", 1000, 1500), ("下山", 1500, 3000)]
    assert evs[0].id == "ep001:0000"


def test_single_misread_between_matching_readings_is_absorbed(project):
    config, _ = project
    readings = [_r(0, "外面很危险"), _r(250, "外面很危险"), _r(500, "列面很危睑"), _r(750, "外面很危险"),
                _r(1000, "", kind="empty")]
    evs = events_stage.build_events(readings, "ep001", 2000, config)
    assert len(evs) == 1 and evs[0].zh_raw == "外面很危险" and evs[0].end_ms == 1000


def test_non_dialogue_detection(project):
    config, _ = project
    readings = []
    t = 0
    for text in ["一", "二", "三", "四"]:
        readings += [_r(t, text * 3), _r(t + 1000, "", kind="empty")]
        t += 2000
    readings += [_r(t, "大字标题", h=0.9), _r(t + 1000, "", kind="empty")]                 # tall text
    readings += [_r(t + 2000, "角落招牌", hc=0.15), _r(t + 3000, "", kind="empty")]       # off-center
    readings += [_r(t + 4000, "两行字", multi=True), _r(t + 5000, "", kind="empty")]       # two rows
    readings += [_r(t + 6000, "很久很久"), _r(t + 20000, "", kind="empty")]               # 14 s on screen
    evs = events_stage.build_events(readings, "ep001", t + 30000, config)
    n = events_stage.flag_non_dialogue(evs, config.non_dialogue)
    assert n == 4
    assert [e.suspect for e in evs] == [False] * 4 + [True] * 4
    assert any("more than one text row" in note for note in evs[6].notes)


# -- OCR correction --------------------------------------------------------------------------------

def test_apply_fixes_accepts_small_changes_and_flags_big_ones():
    evs = [SubtitleEvent(id="ep001:0000", start_ms=0, end_ms=1, zh_raw="弟子己经筑基了", zh="弟子己经筑基了", ocr_conf=0.9),
           SubtitleEvent(id="ep001:0001", start_ms=1, end_ms=2, zh_raw="很好", zh="很好", ocr_conf=0.9)]
    fixed, rejected = ocr_fix.apply_fixes(evs, [
        ocr_fix.OcrFixChange(event_id="ep001:0000", zh="弟子已经筑基了", reason="己→已"),
        ocr_fix.OcrFixChange(event_id="ep001:0001", zh="完全不同的句子", reason="rewrite"),
    ], max_char_changes=2)
    assert (fixed, rejected) == (1, 1)
    assert evs[0].zh == "弟子已经筑基了" and evs[0].ocr_fixed
    assert evs[1].zh == "很好" and "ocr_uncertain" in evs[1].flags


def test_ocr_fix_stage_batches_and_uses_known_terms(project):
    config, paths = project
    from tests.conftest import sample_events, seed_memory

    seed_memory(config, paths)
    ctx = EpisodeContext(config, paths, make_episode(paths))
    evs = sample_events()
    evs[0].zh_raw = evs[0].zh = "师尊，弟子已经筑墓了。"
    write_events(ctx.work, evs, "events_raw.jsonl")
    seen = []

    def handler(messages):
        seen.append(messages[0]["content"])
        lines = user_json(messages, "Subtitle lines, in order")
        return {"changes": [{"event_id": x["event_id"], "zh": x["zh"].replace("筑墓", "筑基"), "reason": "term"}
                            for x in lines if "筑墓" in x["zh"]]}

    config.ocr_fix.batch_size = 3
    ctx.llm_override, _ = make_llm(config, paths, {"utility": handler})
    counts = ocr_fix.run(ctx)
    assert counts == {"events": 4, "fixed": 1, "ocr_uncertain": 0}
    assert len(seen) == 2 and "筑基" in seen[0]          # 2 batches; glossary terms in the memory prefix
    assert seen[0] == seen[1]                            # system message identical across calls (prefix cache)
    out = read_jsonl(ctx.artifact("events.jsonl"), SubtitleEvent)
    assert out[0].zh == "师尊，弟子已经筑基了。" and out[0].zh_raw == "师尊，弟子已经筑墓了。"
