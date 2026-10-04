"""Character cards (6.4): who an id is, from what the reviewer curated or confirmed, never from machine guesses."""

from __future__ import annotations

import numpy as np
import pytest

from subagent.character_card import card_info, card_media, confirmed_box, pin_card, shown_talking_box
from subagent.models import CastBoxEdit, CastDetection, CastLine, ReviewedLine
from subagent.util import write_jsonl
from tests.conftest import register_episode, seed_memory

BOX = [100, 50, 200, 250]


def _line(eid: str, speaker: str, start: int, end: int, approved: bool = True, **cast) -> ReviewedLine:
    return ReviewedLine(event_id=eid, start_ms=start, end_ms=end, speaker=speaker, listener=None, zh="字",
                        pinyin="", vi="x", approved=approved, **cast)


def _cast(eid: str, character: str | None = None) -> CastLine:
    return CastLine(event_id=eid, talking=0, detections=[
        CastDetection(index=0, box=BOX, score=0.9, label="a cartoon fish", character=character),
        CastDetection(index=1, box=[300, 50, 400, 250], score=0.9, label="a cartoon person")])


def _setup(project):
    config, paths = project
    seed_memory(config, paths)
    ep1, ep2 = register_episode(paths, 1), register_episode(paths, 2)
    w1 = paths.episode_dir(ep1.id)
    w1.mkdir(parents=True, exist_ok=True)
    write_jsonl(w1 / "approved.jsonl", [
        _line("ep001:0000", "npc_001_01", 0, 3000),                          # longest, no confirmed box
        _line("ep001:0001", "npc_001_01", 4000, 5500, cast_talking="0"),     # the reviewer marked its talker
        _line("ep001:0002", "npc_001_01", 6000, 6300),                       # too short for a sample
        _line("ep001:0003", "lin_yuan", 7000, 9000)])
    write_jsonl(w1 / "cast.jsonl", [_cast("ep001:0000"), _cast("ep001:0001")])
    return config, paths, ep1, ep2


def test_boxes_are_trusted_only_when_confirmed():
    cast = _cast("e")
    machine = _line("e", "a", 0, 1000)
    assert shown_talking_box(machine, cast) == BOX                          # what On screen shows as talking
    assert confirmed_box(machine, cast, "a") is None                        # ...but the machine alone is no proof
    assert confirmed_box(_line("e", "a", 0, 1000, cast_talking="0"), cast, "a") == BOX
    assert confirmed_box(_line("e", "a", 0, 1000, cast_labels={"1": "b"}), cast, "b") == [300, 50, 400, 250]
    assert confirmed_box(machine, _cast("e", character="a"), "a") == BOX    # recognised by the sprite bank
    drawn = _line("e", "a", 0, 1000, cast_talking="a0", cast_added=[CastBoxEdit(box=[1, 2, 3, 4], character="a")])
    assert shown_talking_box(drawn, cast) == [1, 2, 3, 4]
    assert shown_talking_box(_line("e", "a", 0, 1000, cast_talking="none"), cast) is None


def test_card_uses_reviewed_lines_only(project):
    config, paths, ep1, ep2 = _setup(project)
    card = card_info(paths, config, "npc_001_01", current=ep2.id, draft=[])
    assert (card.source, card.first_episode, card.event_id, card.box) == ("reviewed", "ep001", "ep001:0001", BOX)
    unreviewed = card_info(paths, config, "npc_002_01", current=ep2.id,
                           draft=[_line("ep002:0001", "npc_002_01", 0, 2000, approved=False)])
    assert (unreviewed.source, unreviewed.event_id) == ("none", None)        # the machine's guess is not used
    approved = card_info(paths, config, "npc_002_01", current=ep2.id,
                         draft=[_line("ep002:0001", "npc_002_01", 0, 2000)])
    assert (approved.source, approved.first_episode, approved.box) == ("reviewed", "ep002", None)


def test_bootstrap_material_and_a_pinned_sample_come_first(project, monkeypatch):
    import subagent.media as media
    from subagent.models import VideoInfo

    config, paths, ep1, ep2 = _setup(project)
    (paths.bootstrap / "voices" / "lin_yuan").mkdir(parents=True)
    (paths.bootstrap / "voices" / "lin_yuan" / "a.wav").write_bytes(b"RIFF")
    (paths.bootstrap / "sprites" / "lin_yuan").mkdir(parents=True)
    (paths.bootstrap / "sprites" / "lin_yuan" / "t.png").write_bytes(b"png")
    card = card_info(paths, config, "lin_yuan", current=ep2.id, draft=[])
    assert card.source == "bootstrap" and card.clip.name == "a.wav" and card.picture.name == "t.png"

    def clip(path, start, end, out, sample_rate=16000):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"RIFF")
        return out

    frame = np.full((540, config.cast.frame_width * 2, 3), 255, np.uint8)
    monkeypatch.setattr(media, "extract_clip", clip)
    monkeypatch.setattr(media, "extract_frame", lambda *a, **k: frame)
    monkeypatch.setattr(media, "probe", lambda p: VideoInfo(width=frame.shape[1], height=540, duration_ms=9000,
                                                            fps=25.0, has_audio=True))
    line = _line("ep001:0003", "lin_yuan", 7000, 9000)
    pin_card(paths, config, "lin_yuan", ep1.id, line, None)                  # a narrator-like choice: no picture
    card = card_info(paths, config, "lin_yuan", current=ep2.id, draft=[])
    assert card.source == "pinned" and card.clip is not None and card.picture is None
    pin_card(paths, config, "lin_yuan", ep1.id, line, BOX)                   # changed again: with a picture
    assert card_info(paths, config, "lin_yuan", current=ep2.id, draft=[]).picture is not None


def test_card_media_cuts_the_confirmed_box(project, monkeypatch):
    import subagent.media as media
    from subagent.media import imread
    from subagent.models import VideoInfo

    config, paths, ep1, ep2 = _setup(project)
    cuts = []

    def clip(path, start, end, out, sample_rate=16000):
        cuts.append((start, end))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(b"RIFF")
        return out

    frame = np.zeros((540, config.cast.frame_width * 2, 3), np.uint8)
    frame[100:500, 200:400] = 255                                  # the box at twice the cast frame's size
    monkeypatch.setattr(media, "extract_clip", clip)
    monkeypatch.setattr(media, "extract_frame", lambda *a, **k: frame)
    monkeypatch.setattr(media, "probe", lambda p: VideoInfo(width=frame.shape[1], height=540, duration_ms=10_000,
                                                            fps=25.0, has_audio=True))
    card = card_media(paths, config, card_info(paths, config, "npc_001_01", current=ep2.id, draft=[]))
    assert cuts == [(4000, 5500)] and card.clip is not None and card.picture is not None
    assert imread(card.picture).shape[:2] == (400, 200) and imread(card.picture).mean() == 255
    card_media(paths, config, card)                               # cached: nothing is cut again
    assert len(cuts) == 1


@pytest.fixture(autouse=True)
def _no_real_ffmpeg(monkeypatch):
    """Cards never shell out in these tests unless a test fakes the media helpers."""
    import subagent.media as media

    def boom(*a, **k):
        raise AssertionError("ffmpeg called")

    monkeypatch.setattr(media, "extract_clip", boom)
    monkeypatch.setattr(media, "extract_frame", boom)
