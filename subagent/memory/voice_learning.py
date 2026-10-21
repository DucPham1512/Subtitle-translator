"""Learn character voices from reviewed episodes.

Every line a person approved with a speaker is a labelled voice sample. Their audio (cut from the source
video), together with the manual bootstrap clips, gives each character a voice-bank centroid. The bank is
written through the Memory Manager; `evaluate` measures accuracy episode by episode without writing anything.

Auto-mode episodes have no person behind their speakers, and their speakers mostly come from voice match
itself, so learning from them can reinforce its own mistakes. They contribute only lines where every
independent signal agrees (`auto_clips`), and only when leave-one-episode-out accuracy on human-reviewed
lines does not get worse with them (`auto_gate`).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from subagent.config import Config, Paths
from subagent.episodes import Registry
from subagent.kernel.models import Episode, ReviewedLine
from subagent.kernel.util import read_jsonl
from subagent.memory.evidence import is_auto_episode, trusted_auto_lines, usable_line
from subagent.memory.store import MemoryStore

log = logging.getLogger(__name__)


@dataclass
class Clip:
    episode_id: str
    event_id: str
    speaker: str
    start_ms: int
    end_ms: int


@dataclass
class AutoGate:
    offered: int = 0                   # auto-mode lines that passed the filter
    test_lines: int = 0                # human-reviewed lines the measurement used
    baseline: float = 0.0              # top-1 accuracy without the auto lines
    candidate: float = 0.0             # top-1 accuracy with them
    accepted: bool = False
    reason: str = ""


@dataclass
class LearnResult:
    voices: dict[str, int] = field(default_factory=dict)          # character -> samples used
    skipped: dict[str, int] = field(default_factory=dict)         # character -> samples (too few to learn)
    confusable: dict[tuple[str, str], float] = field(default_factory=dict)
    lines_used: int = 0
    episodes: list[str] = field(default_factory=list)
    auto: AutoGate | None = None       # None: no auto-mode lines were offered


def reviewed_clips(paths: Paths, config: Config, known: set[str], episodes: set[str] | None = None) -> list[Clip]:
    """Lines a person approved (human-mode episodes only) with a known speaker, long enough to carry a voice."""
    clips: list[Clip] = []
    for ep in Registry(paths).load():
        if (episodes is not None and ep.id not in episodes) or is_auto_episode(paths, ep.id):
            continue
        for x in read_jsonl(paths.episode_dir(ep.id) / "approved.jsonl", ReviewedLine):
            if usable_line(x, config, known):
                clips.append(Clip(ep.id, x.event_id, x.speaker, x.start_ms, x.end_ms))
    return clips


def auto_clips(paths: Paths, config: Config, known: set[str]) -> list[Clip]:
    """Auto-mode lines where voice and translator agree clearly and nothing else looks off.

    Voice match was "fixed" well above its own thresholds, the translator kept that speaker, the evaluator
    passed the line on the first attempt, and the line carries no flag except harmless ones (reading speed).
    The translator's speaker_conf is not used: it copies the voice score, so it is not a second opinion.
    """
    clips: list[Clip] = []
    for ep in Registry(paths).load():
        if is_auto_episode(paths, ep.id):
            clips += [Clip(ep.id, x.event_id, x.speaker, x.start_ms, x.end_ms)
                      for x in trusted_auto_lines(paths, config, ep.id, known)]
    return clips


def _samples(manual: dict[str, list[np.ndarray]], clips: list[Clip],
             embs: dict[tuple[str, str], np.ndarray]) -> dict[str, list[np.ndarray]]:
    samples: dict[str, list[np.ndarray]] = defaultdict(list, {k: list(v) for k, v in manual.items()})
    for c in clips:
        if (c.episode_id, c.event_id) in embs:
            samples[c.speaker].append(embs[(c.episode_id, c.event_id)])
    return samples


def _leave_one_out(human: list[Clip], extra: list[Clip], embs: dict[tuple[str, str], np.ndarray],
                   manual: dict[str, list[np.ndarray]], config: Config) -> tuple[int, int]:
    """Top-1 hits on human-reviewed lines, each episode tested with a bank learned without it (+ extra)."""
    from subagent.stages.voice import score_embedding

    right = total = 0
    for ep in sorted({c.episode_id for c in human}):
        train = [c for c in human if c.episode_id != ep] + extra
        bank = {c: v for c, (v, _) in build_centroids(_samples(manual, train, embs), config).items()}
        for c in human:
            e = embs.get((c.episode_id, c.event_id))
            if c.episode_id != ep or e is None:
                continue
            total += 1
            right += bool(bank) and score_embedding(e, bank)[0][0] == c.speaker
    return right, total


def auto_gate(human: list[Clip], auto: list[Clip], embs: dict[tuple[str, str], np.ndarray],
              manual: dict[str, list[np.ndarray]], config: Config) -> AutoGate:
    """Accept the auto lines only if speaker accuracy on human-reviewed lines does not get worse with them."""
    gate = AutoGate(offered=sum((c.episode_id, c.event_id) in embs for c in auto))
    base_right, total = _leave_one_out(human, [], embs, manual, config)
    cand_right, _ = _leave_one_out(human, auto, embs, manual, config)
    gate.test_lines = total
    if total:
        gate.baseline, gate.candidate = base_right / total, cand_right / total
    if total < config.voice.learn_auto_min_test_lines:
        gate.reason = (f"only {total} human-reviewed lines to measure with "
                       f"(needs {config.voice.learn_auto_min_test_lines})")
    elif gate.candidate < gate.baseline - config.voice.learn_auto_max_drop:
        gate.reason = f"accuracy would drop from {gate.baseline:.0%} to {gate.candidate:.0%}"
    else:
        gate.accepted = True
        gate.reason = f"accuracy {gate.baseline:.0%} -> {gate.candidate:.0%}"
    return gate


def episode_samples(paths: Paths, config: Config, episode: Episode) -> np.ndarray:
    """The episode's audio as 16 kHz mono: the stage's audio.wav when it still exists, else cut from the video."""
    from subagent.stages.voice import load_audio_any, load_wav

    wav = paths.episode_dir(episode.id) / "audio.wav"
    if wav.is_file():
        samples, sr = load_wav(wav)
        if sr == config.audio.sample_rate and len(samples):
            return samples
    return load_audio_any(Path(episode.source_path), config.audio.sample_rate)


def embed_clips(paths: Paths, config: Config, clips: list[Clip], embed) -> dict[tuple[str, str], np.ndarray]:
    """One embedding per clip; each episode's audio is loaded once. Missing videos are skipped with a warning."""
    sr = config.audio.sample_rate
    trim = config.voice.learn_trim_ms
    registry = Registry(paths)
    out: dict[tuple[str, str], np.ndarray] = {}
    by_episode: dict[str, list[Clip]] = defaultdict(list)
    for c in clips:
        by_episode[c.episode_id].append(c)
    for ep_id, items in by_episode.items():
        episode = registry.get(ep_id)
        if not Path(episode.source_path).is_file() and not (paths.episode_dir(ep_id) / "audio.wav").is_file():
            log.warning("voices: %s skipped, its video is missing (%s)", ep_id, episode.source_path)
            continue
        samples = episode_samples(paths, config, episode)
        for c in items:
            a = int((c.start_ms + trim) * sr / 1000)
            b = int((c.end_ms - trim) * sr / 1000)
            if b - a >= sr * config.audio.min_event_ms / 1000:
                out[(ep_id, c.event_id)] = embed(samples[a:b])
    return out


def manual_clip_embeddings(paths: Paths, config: Config, known: set[str], embed) -> dict[str, list[np.ndarray]]:
    from subagent.stages.voice import load_audio_any, voice_clips

    out: dict[str, list[np.ndarray]] = defaultdict(list)
    for char, files in voice_clips(paths).items():
        if char in known:
            out[char] += [embed(load_audio_any(f, config.audio.sample_rate)) for f in files]
    return out


def _normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return (v / n).astype(np.float32) if n else v.astype(np.float32)


def build_centroids(samples: dict[str, list[np.ndarray]], config: Config) -> dict[str, tuple[np.ndarray, int]]:
    """Mean voice per character; with enough samples, the least typical share (likely mislabels) is dropped."""
    out: dict[str, tuple[np.ndarray, int]] = {}
    for char, embs in samples.items():
        if len(embs) < config.voice.learn_min_clips:
            continue
        m = np.stack([_normalize(e) for e in embs])
        centroid = _normalize(m.mean(axis=0))
        drop = int(len(m) * config.voice.learn_outlier_share) if len(m) >= 10 else 0
        if drop:
            keep = np.argsort(m @ centroid)[drop:]
            m = m[keep]
            centroid = _normalize(m.mean(axis=0))
        out[char] = (centroid, len(m))
    return out


def learn_voices(config: Config, paths: Paths, embed=None, *, commit: bool = True) -> LearnResult:
    """Rebuild the voice bank from every reviewed episode plus the manual clips, then commit it to memory."""
    from subagent.memory.manager import MemoryManager
    from subagent.stages.voice import get_embedder, pair_similarities

    manager = MemoryManager(paths, config)
    manager.ensure_repo()
    known = manager.store.character_ids() - {c.id for c in manager.store.characters() if c.generic}
    embed = embed or get_embedder(config, paths).embed
    human = reviewed_clips(paths, config, known)
    auto = auto_clips(paths, config, known) if config.voice.learn_from_auto else []
    embs = embed_clips(paths, config, human + auto, embed)
    manual = manual_clip_embeddings(paths, config, known, embed)
    gate = auto_gate(human, auto, embs, manual, config) if auto else None
    if gate:
        log.info("voices: %d auto-mode lines %s: %s", gate.offered, "used" if gate.accepted else "not used",
                 gate.reason)
    clips = human + auto if gate and gate.accepted else human
    samples = _samples(manual, clips, embs)
    centroids = build_centroids(samples, config)
    result = LearnResult(
        voices={c: n for c, (_, n) in centroids.items()},
        skipped={c: len(v) for c, v in samples.items() if c not in centroids},
        lines_used=sum((c.episode_id, c.event_id) in embs for c in clips),
        episodes=sorted({c.episode_id for c in clips}), auto=gate,
    )
    if not centroids:
        return result
    bank = {c: v for c, (v, _) in centroids.items()}
    result.confusable = pair_similarities(bank, config.voice.confusable_similarity)
    with manager.locked():
        manager.write_voices(centroids, source="human")
        manager.write_confusable_pairs(result.confusable, involving=set(centroids), source="human")
        if commit:
            auto_note = ""
            if gate:
                auto_note = (f"; {gate.offered} auto-mode lines {'used' if gate.accepted else 'not used'}, "
                             f"{gate.reason}")
            manager.commit(f"voices learned from {result.lines_used} lines ({len(centroids)} characters{auto_note})")
    return result


# -- evaluation ------------------------------------------------------------------------------------

@dataclass
class EvalReport:
    lines: int = 0
    top1: int = 0
    top3: int = 0
    by_episode: dict[str, tuple[int, int]] = field(default_factory=dict)      # episode -> (correct, total)
    statuses: dict[str, tuple[int, int]] = field(default_factory=dict)        # status -> (correct, total)
    sweep: list[tuple[float, float, float, float]] = field(default_factory=list)   # accept, margin, precision, coverage


def evaluate(config: Config, paths: Paths, embed=None) -> EvalReport:
    """Leave one episode out: learn from the other reviewed episodes (+ manual clips), test on this one."""
    from subagent.stages.voice import classify, get_embedder, score_embedding

    known = MemoryStore(paths.memory_db).character_ids()
    embed = embed or get_embedder(config, paths).embed
    clips = reviewed_clips(paths, config, known)
    embs = embed_clips(paths, config, clips, embed)
    manual = manual_clip_embeddings(paths, config, known, embed)
    report = EvalReport()
    scored: list[tuple[str, list[tuple[str, float]]]] = []
    for ep in sorted({c.episode_id for c in clips}):
        samples: dict[str, list[np.ndarray]] = defaultdict(list, {k: list(v) for k, v in manual.items()})
        for c in clips:
            if c.episode_id != ep and (c.episode_id, c.event_id) in embs:
                samples[c.speaker].append(embs[(c.episode_id, c.event_id)])
        bank = {c: v for c, (v, _) in build_centroids(samples, config).items()}
        if not bank:
            continue
        right = total = 0
        for c in clips:
            e = embs.get((c.episode_id, c.event_id))
            if c.episode_id != ep or e is None:
                continue
            scores = score_embedding(e, bank)
            scored.append((c.speaker, scores))
            total += 1
            right += scores[0][0] == c.speaker
            report.top3 += c.speaker in [s for s, _ in scores[:3]]
            status = classify(c.event_id, scores, config.voice, set()).status
            ok, n = report.statuses.get(status, (0, 0))
            report.statuses[status] = (ok + (scores[0][0] == c.speaker), n + 1)
        report.by_episode[ep] = (right, total)
        report.top1 += right
        report.lines += total
    for accept in (0.3, 0.4, 0.5, 0.55, 0.6, 0.7):
        for margin in (0.02, 0.05, 0.08, 0.12):
            fixed = [(sp, sc) for sp, sc in scored if sc and sc[0][1] >= accept
                     and sc[0][1] - (sc[1][1] if len(sc) > 1 else -1.0) >= margin]
            if fixed:
                precision = sum(sc[0][0] == sp for sp, sc in fixed) / len(fixed)
                report.sweep.append((accept, margin, precision, len(fixed) / max(1, len(scored))))
    return report
