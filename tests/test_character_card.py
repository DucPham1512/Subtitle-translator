"""Character cards (6.4): who an id is, from the lines it speaks in reviewed episodes."""

from __future__ import annotations

import numpy as np

from subagent.character_card import card_info, card_media
from subagent.models import CastDetection, CastLine, ReviewedLine
from subagent.util import write_jsonl
from tests.conftest import register_episode, seed_memory


def _line(eid: str, speaker: str, start: int, end: int) -> ReviewedLine:
    return ReviewedLine(event_id=eid, start_ms=start, end_ms=end, speaker=speaker, listener=None, zh="字",
                        pinyin="", vi="x", approved=True)


def _setup(project):
    config, paths = project
    seed_memory(config, paths)
    ep1, ep2 = register_episode(paths, 1), register_episode(paths, 2)
    w1 = paths.episode_dir(ep1.id)
    w1.mkdir(parents=True, exist_ok=True)
    write_jsonl(w1 / "approved.jsonl", [
        _line("ep001:0000", "npc_001_01", 0, 3000),              # longest, but nobody is seen talking
        _line("ep001:0001", "npc_001_01", 4000, 5500),           # the talking sprite on screen: preferred
        _line("ep001:0002", "npc_001_01", 6000, 6300),           # too short for a sample
        _line("ep001:0003", "lin_yuan", 7000, 9000)])
    write_jsonl(w1 / "cast.jsonl", [CastLine(event_id="ep001:0001", talking=0, detections=[
        CastDetection(index=0, box=[100, 50, 200, 250], score=0.9, label="a cartoon fish")])])
    return config, paths, ep1, ep2


def test_card_picks_a_talking_line_from_the_earliest_reviews(project):
    config, paths, ep1, ep2 = _setup(project)
    card = card_info(paths, config, "npc_001_01", current=ep2.id, draft=[_line("ep002:0000", "npc_001_01", 0, 900)])
    assert (card.kind, card.first_episode, card.episode_id, card.event_id) == ("new", "ep001", "ep001", "ep001:0001")
    assert card.box == [100, 50, 200, 250]
    named = card_info(paths, config, "lin_yuan", current=ep2.id, draft=[])
    assert (named.name, named.description, named.kind, named.box) == ("Lâm Uyên", "đệ tử", "character", None)
    fresh = card_info(paths, config, "npc_002_01", current=ep2.id, draft=[_line("ep002:0001", "npc_002_01", 0, 2000)])
    assert (fresh.first_episode, fresh.event_id) == ("ep002", "ep002:0001")   # only heard in this episode so far


def test_card_media_cuts_the_clip_and_the_talking_box(project, monkeypatch):
    import subagent.media as media
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
    from subagent.media import imread

    assert imread(card.picture).shape[:2] == (400, 200) and imread(card.picture).mean() == 255
    card_media(paths, config, card)                               # cached: nothing is cut again
    assert len(cuts) == 1
