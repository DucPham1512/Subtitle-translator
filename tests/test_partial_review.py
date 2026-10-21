"""Partial review: learn from the approved lines mid-review, re-check the remaining ones (session only)."""

from __future__ import annotations

import wave

import numpy as np

from subagent.kernel.models import (
    CastDetection,
    CastLine,
    EpisodeState,
    LineTranslation,
    PinyinLine,
    ReviewedLine,
    SpeakerCandidates,
)
from subagent.kernel.util import read_jsonl, write_jsonl
from subagent.memory.store import MemoryStore
from subagent.review.partial import OUTPUT, partial_review, suggest
from subagent.review.review import gate, load_draft, save_draft
from subagent.workspace.state import save_state
from tests.conftest import register_episode, sample_events, seed_memory, write_events

DIM = 8


def _vec(k: int, wobble: float = 0.0) -> np.ndarray:
    v = np.zeros(DIM, np.float32)
    v[k] = 1.0
    v[(k + 3) % DIM] = wobble
    return v / np.linalg.norm(v)


def _line(speaker: str | None = "lin_yuan") -> ReviewedLine:
    return ReviewedLine(event_id="ep001:0002", start_ms=0, end_ms=1, speaker=speaker, listener=None, zh="字",
                        pinyin="", vi="x")


def _voice(status: str, *cands: str) -> SpeakerCandidates:
    return SpeakerCandidates(event_id="ep001:0002", status=status,  # type: ignore[arg-type]
                             candidates=[(c, 0.7 - 0.1 * i) for i, c in enumerate(cands)])


def test_suggestion_rules():
    line = _line()
    assert suggest(line, "lin_yuan", "shi_zun", None) == ("shi_zun", "talking on screen")
    assert suggest(line, "lin_yuan", "shi_zun", _voice("unknown"))[0] == "shi_zun"
    assert suggest(line, "lin_yuan", "shi_zun", _voice("fixed", "shi_zun"))[1] == "picture and voice agree"
    assert suggest(line, "lin_yuan", "shi_zun", _voice("fixed", "npc_001_01")) == (None, "")     # they disagree
    assert suggest(line, "lin_yuan", None, _voice("new_voice", "npc_001_01")) == ("npc_001_01", "voice")
    assert suggest(line, "lin_yuan", "shi_zun", _voice("confusable", "lin_yuan", "shi_zun"))[0] == "shi_zun"
    assert suggest(line, "lin_yuan", "shi_zun", _voice("confusable", "lin_yuan", "npc_001_01")) == (None, "")
    assert suggest(line, "lin_yuan", "lin_yuan", None) == (None, "")                            # already right
    assert suggest(line, "bai", "shi_zun", None) == (None, "")          # the reviewer changed the speaker already


def _episode(project, *, voices: bool = False):
    """4 lines: 0 and 1 approved by the reviewer, 2 and 3 remaining. On screen: lin_yuan's look (0) and a
    stranger's (2); the stranger talks in every line."""
    config, paths = project
    seed_memory(config, paths)
    ep = register_episode(paths, 1)
    work = paths.episode_dir(ep.id)
    events = sample_events()
    write_events(work, events)
    write_jsonl(work / "pinyin.jsonl", [PinyinLine(event_id=e.id, pinyin="x") for e in events])
    write_jsonl(work / "translations.jsonl", [
        LineTranslation(event_id=e.id, speaker="lin_yuan", listener=None, speaker_conf=0.5, vi="Câu.", attempts=1)
        for e in events])
    save_state(work, EpisodeState(episode_id=ep.id, mode="human"))
    gate(work, "human")
    draft = load_draft(work)
    # the reviewer: line 0 spoken by shi_zun, who is the talking (unknown) sprite; line 1 the same, no marks
    draft[0] = draft[0].model_copy(update={"approved": True, "speaker": "shi_zun", "cast_talking": "1"})
    draft[1] = draft[1].model_copy(update={"approved": True, "speaker": "shi_zun"})
    draft[3] = draft[3].model_copy(update={"speaker": "shi_zun"})          # already fixed by hand, not approved
    save_draft(work, draft)
    lines, embs = [], []
    for e in events:
        dets = []
        for look in (0, 2):
            dets.append(CastDetection(index=len(embs), box=[0, 0, 1, 1], score=0.5, label="c"))
            embs.append(_vec(look, 0.05))
        lines.append(CastLine(event_id=e.id, detections=dets, talking=1))
    write_jsonl(work / "cast.jsonl", lines)
    np.save(work / "cast_embeddings.npy", np.stack(embs))
    config.cast.enabled = True
    return config, paths, ep, work


def test_partial_review_names_the_talking_sprite_and_suggests_without_touching_memory(project):
    config, paths, ep, work = _episode(project)
    r = partial_review(config, paths, ep.id)
    assert (r.reviewed, r.remaining, r.suggestions) == (2, 2, 1)
    out = {s.event_id: s for s in read_jsonl(work / OUTPUT, type(_sug_model()))}
    assert out["ep001:0002"].talking == "shi_zun" and out["ep001:0002"].cast["1"] == "shi_zun"
    assert out["ep001:0002"].suggested_speaker == "shi_zun" and out["ep001:0002"].reason == "talking on screen"
    assert out["ep001:0003"].suggested_speaker is None              # the reviewer already chose its speaker
    assert MemoryStore(paths.memory_db).sprite_exemplars() == []    # session only


def test_a_speaker_set_by_an_earlier_partial_review_may_change_again(project):
    config, paths, ep, work = _episode(project)
    draft = load_draft(work)
    # an earlier partial review set ep001:0003's speaker (it differs from the pipeline's): still the machine's
    draft[3] = draft[3].model_copy(update={"speaker": "npc_001_01", "flags": ["partial_speaker", "check_pronouns"]})
    save_draft(work, draft)
    partial_review(config, paths, ep.id)
    out = {s.event_id: s for s in read_jsonl(work / OUTPUT, type(_sug_model()))}
    assert out["ep001:0003"].suggested_speaker == "shi_zun"


def test_without_a_voice_update_the_pipeline_voice_still_counts(project, monkeypatch):
    config, paths, ep, work = _episode(project)
    monkeypatch.setattr("subagent.review.partial._voices", lambda *a, **k: ({}, []))   # nothing re-matched
    write_jsonl(work / "speakers.jsonl", [SpeakerCandidates(event_id="ep001:0002", status="fixed",
                                                            candidates=[("lin_yuan", 0.8), ("shi_zun", 0.4)])])
    partial_review(config, paths, ep.id)
    out = {s.event_id: s for s in read_jsonl(work / OUTPUT, type(_sug_model()))}
    assert out["ep001:0002"].suggested_speaker is None      # sure voice vs talking sprite: left to the reviewer


def _sug_model():
    from subagent.kernel.models import PartialSuggestion

    return PartialSuggestion(event_id="x")


def test_partial_review_learns_this_episodes_voices(project):
    config, paths, ep, work = _episode(project)
    sr, pitch = 16000, {"shi_zun": 2000, "lin_yuan": 300}
    events = sample_events()
    audio = np.zeros(sr * 12, np.float32)
    for e in events:                                   # shi_zun really speaks every line
        t = np.arange(int((e.end_ms - e.start_ms) * sr / 1000)) / sr
        a = int(e.start_ms * sr / 1000)
        audio[a:a + len(t)] = 0.3 * np.sin(2 * np.pi * pitch["shi_zun"] * t)
    with wave.open(str(work / "audio.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((audio * 32767).astype("<i2").tobytes())
    write_jsonl(work / "speakers.jsonl", [SpeakerCandidates(event_id=e.id, status="unknown") for e in events])
    config.voice.learn_min_clips = 2
    config.cast.enabled = False                        # voices alone

    def fake_embed(samples):
        spectrum = np.abs(np.fft.rfft(samples))
        freq = np.argmax(spectrum) * sr / len(samples)
        v = np.zeros(8, np.float32)
        v[min(7, int(freq // 300))] = 1.0
        return v

    r = partial_review(config, paths, ep.id, voice_embed=fake_embed)
    assert r.voices_updated == ["shi_zun"]
    out = {s.event_id: s for s in read_jsonl(work / OUTPUT, type(_sug_model()))}
    assert out["ep001:0002"].voice.candidates[0][0] == "shi_zun" and out["ep001:0002"].voice.status == "fixed"
    assert out["ep001:0002"].suggested_speaker == "shi_zun" and out["ep001:0002"].reason == "voice"
    assert MemoryStore(paths.memory_db).voice_bank() == {}         # session only
