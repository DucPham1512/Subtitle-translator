"""Voice bank learned from reviewed lines (fake embedder: a voice = its dominant pitch)."""

from __future__ import annotations

import wave

import numpy as np
import pytest

from subagent.memory import voice_learning as vl
from subagent.memory.store import MemoryStore
from subagent.models import ReviewedLine
from subagent.util import write_jsonl
from tests.conftest import register_episode, seed_memory

SR = 16000
PITCH = {"lin_yuan": 300, "shi_zun": 2000}


def _fake_embed(samples: np.ndarray) -> np.ndarray:
    spectrum = np.abs(np.fft.rfft(samples))
    freq = np.argmax(spectrum) * SR / len(samples)
    v = np.zeros(8, np.float32)
    v[min(7, int(freq // 300))] = 1.0
    return v


def _episode(paths, number: int, script: list[tuple[str | None, int, int]], *, deleted: set[int] = frozenset()):
    """script: (speaker, start_ms, end_ms); the audio at each line is that speaker's pitch."""
    ep = register_episode(paths, number)
    work = paths.episode_dir(ep.id)
    work.mkdir(parents=True, exist_ok=True)
    audio = np.zeros(SR * 20, np.float32)
    lines = []
    for i, (speaker, a, b) in enumerate(script):
        t = np.arange(int((b - a) * SR / 1000)) / SR
        if speaker:
            audio[int(a * SR / 1000):int(a * SR / 1000) + len(t)] = 0.3 * np.sin(2 * np.pi * PITCH[speaker] * t)
        lines.append(ReviewedLine(event_id=f"{ep.id}:{i:04d}", start_ms=a, end_ms=b, speaker=speaker, listener=None,
                                  zh="字", pinyin="", vi="x", approved=True, deleted=i in deleted))
    with wave.open(str(work / "audio.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((audio * 32767).astype("<i2").tobytes())
    write_jsonl(work / "approved.jsonl", lines)
    return ep


SCRIPT = [("lin_yuan", 0, 1500), ("shi_zun", 2000, 3500), ("lin_yuan", 4000, 5200), ("shi_zun", 6000, 7500),
          ("lin_yuan", 8000, 9500), ("shi_zun", 10000, 11200), ("lin_yuan", 12000, 12500), (None, 13000, 14500)]


def test_reviewed_clips_keep_only_usable_lines(project):
    config, paths = project
    seed_memory(config, paths)
    _episode(paths, 1, SCRIPT, deleted={4})
    clips = vl.reviewed_clips(paths, config, MemoryStore(paths.memory_db).character_ids())
    # line 4 deleted, line 6 too short (500 ms), line 7 has no speaker
    assert [c.event_id[-4:] for c in clips] == ["0000", "0001", "0002", "0003", "0005"]


def test_outliers_are_dropped_from_large_samples(project):
    config, _ = project
    good = [np.array([1, 0], np.float32)] * 9
    centroids = vl.build_centroids({"a": good + [np.array([0, 1], np.float32)], "b": good[:2]}, config)
    assert "b" not in centroids                                   # fewer than learn_min_clips
    vec, n = centroids["a"]
    assert n == 9 and vec[0] == pytest.approx(1.0)                # the mislabelled sample was dropped


def test_learn_writes_bank_and_evaluate_reports_accuracy(project):
    config, paths = project
    seed_memory(config, paths)
    _episode(paths, 1, SCRIPT)
    _episode(paths, 2, SCRIPT)
    result = vl.learn_voices(config, paths, embed=_fake_embed)
    assert result.voices == {"lin_yuan": 6, "shi_zun": 6}          # 3 usable lines each, in two episodes
    assert set(MemoryStore(paths.memory_db).voice_bank()) == {"lin_yuan", "shi_zun"}
    assert result.episodes == ["ep001", "ep002"]

    report = vl.evaluate(config, paths, embed=_fake_embed)
    assert report.lines == 12 and report.top1 == 12               # 6 usable lines per episode, all recognised
    assert report.by_episode == {"ep001": (6, 6), "ep002": (6, 6)}
    assert report.sweep and all(prec == 1.0 for _, _, prec, _ in report.sweep)


def test_finish_review_never_fails_on_missing_voice_model(project, monkeypatch):
    from subagent.errors import ModelUnavailableError
    from subagent.pipeline import Pipeline

    config, paths = project

    def boom(*a, **k):
        raise ModelUnavailableError("speechbrain is not installed")

    monkeypatch.setattr("subagent.memory.voice_learning.learn_voices", boom)
    Pipeline(config, paths)._learn_voices()                       # reports, does not raise


# -- auto-mode episodes ----------------------------------------------------------------------------

AUTO_SCRIPT = [("lin_yuan" if i % 2 == 0 else "shi_zun", i * 2000, i * 2000 + 1500) for i in range(10)]


def _auto_episode(paths, number: int, labels: list[str], *, score: float = 0.9, flags=None, failed=frozenset()):
    """Audio follows AUTO_SCRIPT; the machine labelled line i as labels[i] (voice and translator agreeing)."""
    from subagent.models import EpisodeState, Evaluation, LineTranslation, SpeakerCandidates
    from subagent.state import save_state

    ep = _episode(paths, number, AUTO_SCRIPT)
    work = paths.episode_dir(ep.id)
    flags = flags or {}
    lines = [x.model_copy(update={"speaker": labels[i], "flags": flags.get(i, [])})
             for i, x in enumerate(vl.read_jsonl(work / "approved.jsonl", ReviewedLine))]
    write_jsonl(work / "approved.jsonl", lines)
    other = {"lin_yuan": "shi_zun", "shi_zun": "lin_yuan"}
    write_jsonl(work / "speakers.jsonl", [
        SpeakerCandidates(event_id=x.event_id, candidates=[(x.speaker, score), (other[x.speaker], 0.3)], status="fixed")
        for x in lines])
    write_jsonl(work / "translations.jsonl", [
        LineTranslation(event_id=x.event_id, speaker=x.speaker, listener=None, speaker_conf=score, vi="x",
                        attempts=1, flags=x.flags) for x in lines])
    write_jsonl(work / "evaluations.jsonl", [
        Evaluation(event_id=x.event_id, attempt=1, passed=i not in failed, scores={}, feedback="")
        for i, x in enumerate(lines)])
    save_state(work, EpisodeState(episode_id=ep.id, mode="auto"))
    return ep


def test_auto_lines_pass_only_when_every_signal_agrees(project):
    config, paths = project
    seed_memory(config, paths)
    _episode(paths, 1, SCRIPT)
    labels = [s for s, _, _ in AUTO_SCRIPT]
    _auto_episode(paths, 2, labels, flags={1: ["low_speaker_conf"], 2: ["cps_exceeded"]}, failed={3})
    known = MemoryStore(paths.memory_db).character_ids()
    assert {c.episode_id for c in vl.reviewed_clips(paths, config, known)} == {"ep001"}   # auto is not "reviewed"
    picked = [c.event_id[-2:] for c in vl.auto_clips(paths, config, known)]
    assert picked == ["00", "02", "04", "05", "06", "07", "08", "09"]   # 1 flagged, 3 failed first evaluation

    _auto_episode(paths, 3, labels, score=0.65)                          # "fixed", but not clearly enough
    assert {c.episode_id for c in vl.auto_clips(paths, config, known)} == {"ep002"}


def test_auto_lines_that_hurt_accuracy_are_not_learned(project):
    config, paths = project
    config.voice.learn_auto_min_test_lines = 1
    seed_memory(config, paths)
    _episode(paths, 1, SCRIPT)
    _episode(paths, 2, SCRIPT)
    swapped = ["shi_zun" if s == "lin_yuan" else "lin_yuan" for s, _, _ in AUTO_SCRIPT]   # confidently wrong
    _auto_episode(paths, 3, swapped)
    result = vl.learn_voices(config, paths, embed=_fake_embed)
    assert result.auto.offered == 10 and not result.auto.accepted
    assert result.auto.baseline == 1.0 and result.auto.candidate < 1.0
    assert result.voices == {"lin_yuan": 6, "shi_zun": 6} and result.episodes == ["ep001", "ep002"]


def test_auto_lines_that_keep_accuracy_are_learned(project):
    config, paths = project
    config.voice.learn_auto_min_test_lines = 1
    seed_memory(config, paths)
    _episode(paths, 1, SCRIPT)
    _episode(paths, 2, SCRIPT)
    _auto_episode(paths, 3, [s for s, _, _ in AUTO_SCRIPT])
    result = vl.learn_voices(config, paths, embed=_fake_embed)
    assert result.auto.accepted and result.auto.candidate == 1.0
    # 6 reviewed + 5 auto each; with 11 samples the least typical one is dropped
    assert result.voices == {"lin_yuan": 10, "shi_zun": 10} and result.episodes == ["ep001", "ep002", "ep003"]


def test_auto_lines_wait_until_there_is_enough_to_measure(project):
    config, paths = project
    seed_memory(config, paths)
    _episode(paths, 1, SCRIPT)
    _episode(paths, 2, SCRIPT)
    _auto_episode(paths, 3, [s for s, _, _ in AUTO_SCRIPT])
    result = vl.learn_voices(config, paths, embed=_fake_embed)       # 12 reviewed lines < 30 needed
    assert not result.auto.accepted and "needs 30" in result.auto.reason
    assert result.voices == {"lin_yuan": 6, "shi_zun": 6}
