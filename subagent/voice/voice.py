"""Stage 6: voice match (5.8). Subtitle events segment the audio, so no diarization model is used."""

from __future__ import annotations

import itertools
import logging
import wave
from collections import Counter
from pathlib import Path

import numpy as np

from subagent.infra import torch_device
from subagent.kernel import (
    MediaError,
    ModelUnavailableError,
    NewVoice,
    SpeakerCandidates,
    SubtitleEvent,
    read_jsonl,
    write_jsonl,
)
from subagent.memory import MemoryStore
from subagent.settings import Config, Paths, VoiceConfig
from subagent.workspace import EpisodeContext

log = logging.getLogger(__name__)

_EMBEDDER: Embedder | None = None


# -- audio I/O -------------------------------------------------------------------------------------

def load_wav(path: Path) -> tuple[np.ndarray, int]:
    """16-bit PCM WAV → float32 mono samples in [-1, 1]."""
    with wave.open(str(path), "rb") as w:
        sr, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        data = w.readframes(w.getnframes())
    if width != 2:
        raise MediaError(f"{path.name}: expected 16-bit PCM WAV")
    samples = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, sr


def load_audio_any(path: Path, sample_rate: int) -> np.ndarray:
    """Any audio file → float32 mono at `sample_rate` (ffmpeg); plain WAVs at the right rate need no ffmpeg."""
    if path.suffix.lower() == ".wav":
        try:
            samples, sr = load_wav(path)
            if sr == sample_rate:
                return samples
        except (MediaError, wave.Error, EOFError):
            pass
    from subagent.infra import require_binary, run

    proc = run([require_binary("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path),
                "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", "-"])
    return np.frombuffer(proc.stdout, dtype="<i2").astype(np.float32) / 32768.0


def slice_audio(samples: np.ndarray, sr: int, start_ms: int, end_ms: int, pad_ms: int) -> np.ndarray:
    a = max(0, int((start_ms - pad_ms) * sr / 1000))
    b = min(len(samples), int((end_ms + pad_ms) * sr / 1000))
    return samples[a:b] if b > a else samples[:0]


def l2_normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return (v / n).astype(np.float32) if n else v.astype(np.float32)


# -- embedding model -------------------------------------------------------------------------------

class Embedder:
    """SpeechBrain ECAPA speaker embeddings; GPU when available, CPU otherwise."""

    def __init__(self, config: Config, paths: Paths):
        try:
            import torch

            try:
                from speechbrain.inference.speaker import EncoderClassifier
            except ImportError:
                from speechbrain.pretrained import EncoderClassifier  # type: ignore[no-redef]
        except ImportError as exc:
            raise ModelUnavailableError(
                "Voice match needs speechbrain + torch. See README for the CUDA install command."
            ) from exc
        self._torch = torch
        self.device = torch_device(config)
        kwargs: dict = {
            "source": config.voice.model,
            "savedir": str(paths.models_cache / config.voice.model.replace("/", "--")),
            "run_opts": {"device": self.device},
        }
        try:  # copy instead of symlinks: symlinks need admin rights on Windows (NFR-PT4)
            from speechbrain.utils.fetching import LocalStrategy

            kwargs["local_strategy"] = LocalStrategy.COPY
        except ImportError:
            pass
        self.model = EncoderClassifier.from_hparams(**kwargs)
        self.model.eval()
        log.info("voice: ECAPA loaded on %s", self.device)

    def embed(self, samples: np.ndarray) -> np.ndarray:
        with self._torch.no_grad():
            wav = self._torch.from_numpy(np.ascontiguousarray(samples, dtype=np.float32)).unsqueeze(0).to(self.device)
            emb = self.model.encode_batch(wav).squeeze().detach().cpu().numpy()
        return l2_normalize(emb)


def get_embedder(config: Config, paths: Paths) -> Embedder:
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = Embedder(config, paths)
    return _EMBEDDER


# -- classification --------------------------------------------------------------------------------

def score_embedding(emb: np.ndarray, bank: dict[str, np.ndarray]) -> list[tuple[str, float]]:
    scores = [(cid, float(np.dot(emb, l2_normalize(c)))) for cid, c in bank.items()]
    return sorted(scores, key=lambda s: (-s[1], s[0]))


def classify(event_id: str, scores: list[tuple[str, float]], cfg: VoiceConfig,
             confusable: set[tuple[str, str]]) -> SpeakerCandidates:
    top = [(cid, round(s, 4)) for cid, s in scores[: cfg.top_k]]
    if not top or top[0][1] < cfg.unknown_below:
        return SpeakerCandidates(event_id=event_id, candidates=top, status="unknown")
    top1 = top[0][1]
    margin = top1 - (top[1][1] if len(top) > 1 else -1.0)
    pair = tuple(sorted((top[0][0], top[1][0]))) if len(top) > 1 else None
    if top1 >= cfg.accept_score and margin >= cfg.min_margin and pair not in confusable:
        return SpeakerCandidates(event_id=event_id, candidates=top, status="fixed")
    return SpeakerCandidates(event_id=event_id, candidates=top, status="confusable")


def group_voices(embs: list[np.ndarray], similarity: float) -> list[list[int]]:
    """Group clips that sound alike: repeatedly merge the two groups with the most similar mean voice while
    that similarity is ≥ `similarity`; then drop members that sit below it. Deterministic; NumPy only."""
    groups = [[i] for i in range(len(embs))]
    sums = [l2_normalize(e).astype(np.float64) for e in embs]
    while len(groups) > 1:
        cent = np.stack([s / (np.linalg.norm(s) or 1.0) for s in sums])
        sims = cent @ cent.T
        np.fill_diagonal(sims, -2.0)
        i, j = np.unravel_index(int(np.argmax(sims)), sims.shape)
        if sims[i, j] < similarity:
            break
        i, j = min(i, j), max(i, j)
        groups[i] += groups.pop(j)
        sums[i] = sums[i] + sums.pop(j)
    out = []
    for g, s in zip(groups, sums, strict=True):
        c = s / (np.linalg.norm(s) or 1.0)
        out.append(sorted(m for m in g if float(np.dot(l2_normalize(embs[m]), c)) >= similarity))
    return out


def find_new_voices(results: list[SpeakerCandidates], embs: dict[str, np.ndarray], bank: dict[str, np.ndarray],
                    cfg: VoiceConfig, episode_number: int, returning: list | None = None,
                    ) -> tuple[list[SpeakerCandidates], list[NewVoice]]:
    """Lines that match no known character well, grouped by voice. A group large enough whose average voice
    is not close to any known character becomes a new voice; its lines get status `new_voice`.

    `returning`: candidates from earlier episodes (5.15b, `store.Candidate` with a voice). A line that sounds like
    one (≥ `accept_score` and `min_margin` above its best known character), or a group whose average voice does
    (≥ `new_voice_similarity`), keeps the candidate's id instead of getting a new one.
    """
    from subagent.memory import new_voice_id

    back_bank = {c.id: c.embedding for c in returning or [] if c.embedding is not None}
    cand = [r for r in results if r.event_id in embs and r.status in ("unknown", "confusable")
            and (not r.candidates or r.candidates[0][1] < cfg.new_voice_below)]
    back: dict[str, list[tuple[SpeakerCandidates, float]]] = {}
    rest = []
    for r in cand:
        best = score_embedding(embs[r.event_id], back_bank)[0] if back_bank else None
        known = r.candidates[0][1] if r.candidates else -1.0
        if best and best[1] >= cfg.accept_score and best[1] - known >= cfg.min_margin:
            back.setdefault(best[0], []).append((r, best[1]))
        else:
            rest.append(r)
    groups = [g for g in group_voices([embs[r.event_id] for r in rest], cfg.new_voice_similarity)
              if len(g) >= cfg.new_voice_min_lines]
    voices: list[NewVoice] = []
    updated: dict[str, SpeakerCandidates] = {}
    for g in sorted(groups, key=min):
        members = [l2_normalize(embs[rest[i].event_id]) for i in g]
        centroid = l2_normalize(np.mean(members, axis=0))
        closest = score_embedding(centroid, bank)[0] if bank else (None, 0.0)
        if closest[1] >= cfg.new_voice_known_max:
            continue                       # as a whole, the group sounds like that known character
        again = score_embedding(centroid, back_bank)[0] if back_bank else None
        if again and again[1] >= cfg.new_voice_similarity:
            vec = l2_normalize(back_bank[again[0]])
            back.setdefault(again[0], []).extend((rest[i], float(np.dot(m, vec))) for i, m in zip(g, members, strict=True))
            continue
        vid = new_voice_id(cfg.new_voice_prefix, episode_number, len(voices) + 1)
        sims = [float(np.dot(m, centroid)) for m in members]
        voices.append(NewVoice(id=vid, event_ids=[rest[i].event_id for i in g], cohesion=round(float(np.mean(sims)), 4),
                               closest_known=closest[0], closest_score=round(float(closest[1]), 4)))
        for i, s in zip(g, sims, strict=True):
            r = rest[i]
            updated[r.event_id] = SpeakerCandidates(
                event_id=r.event_id, candidates=[(vid, round(s, 4))] + r.candidates[: cfg.top_k - 1], status="new_voice")
    by_id = {c.id: c for c in returning or []}
    for cid, lines in sorted(back.items()):
        lines.sort(key=lambda x: x[0].event_id)
        c = by_id[cid]
        voices.append(NewVoice(id=cid, event_ids=[r.event_id for r, _ in lines],
                               cohesion=round(float(np.mean([s for _, s in lines])), 4),
                               returning_from=c.first_episode, name_vi=c.name_vi if c.name_vi != cid else None))
        for r, s in lines:
            updated[r.event_id] = SpeakerCandidates(
                event_id=r.event_id, candidates=[(cid, round(s, 4))] + r.candidates[: cfg.top_k - 1], status="new_voice")
    return [updated.get(r.event_id, r) for r in results], voices


def save_line_voices(path: Path, embs: dict[str, np.ndarray]) -> None:
    """Every matched line's voice (voice_embeddings.npz): a candidate's voice is built from it at finish."""
    ids = sorted(embs)
    tmp = path.with_suffix(".tmp.npz")
    np.savez(tmp, ids=np.array(ids), embs=np.stack([embs[i] for i in ids]).astype(np.float32) if ids
             else np.zeros((0, 0), np.float32))
    tmp.replace(path)


def match_events(events: list[SubtitleEvent], samples: np.ndarray, sr: int, bank: dict[str, np.ndarray],
                 confusable: set[tuple[str, str]], config: Config, embed,
                 embeddings: dict[str, np.ndarray] | None = None) -> list[SpeakerCandidates]:
    cfg, out = config.voice, []
    for e in events:
        if e.duration_ms < config.audio.min_event_ms:
            out.append(SpeakerCandidates(event_id=e.id, status="too_short"))
        elif e.suspect or not bank:
            out.append(SpeakerCandidates(event_id=e.id, status="unknown"))
        else:
            clip = slice_audio(samples, sr, e.start_ms, e.end_ms, config.audio.pad_ms)
            if len(clip) < sr * config.audio.min_event_ms / 1000:
                out.append(SpeakerCandidates(event_id=e.id, status="too_short"))
                continue
            emb = embed(clip)
            if embeddings is not None:
                embeddings[e.id] = emb
            out.append(classify(e.id, score_embedding(emb, bank), cfg, confusable))
    return out


def run(ctx: EpisodeContext, embed=None) -> dict[str, int]:
    events = read_jsonl(ctx.artifact("events.jsonl"), SubtitleEvent)
    store = MemoryStore(ctx.paths.memory_db)
    skip = store.unmatchable_ids()      # archived one-offs (their AI voice is often reused) and generic characters
    bank = {k: v for k, v in store.voice_bank().items() if k not in skip}
    confusable = set(store.confusable_pairs())
    samples, sr = load_wav(ctx.artifact("audio.wav"))
    if bank and embed is None:
        embed = get_embedder(ctx.config, ctx.paths).embed
    elif not bank:
        log.info("voice: voice bank is empty; every event is 'unknown'")
    from subagent.memory import save_new_voices

    results: list[SpeakerCandidates] = []
    embs: dict[str, np.ndarray] = {}
    for i, e in enumerate(events, 1):
        results.extend(match_events([e], samples, sr, bank, confusable, ctx.config, embed, embs))
        ctx.progress.emit("voice", "progress", done=i, total=len(events))
    voices: list[NewVoice] = []
    returning = (store.returning_candidates(ctx.episode.number, ctx.config.memory.probation_window)
                 if ctx.config.memory.probation else [])
    if ctx.config.voice.new_voices and bank:       # with an empty bank every voice would be "new"
        results, voices = find_new_voices(results, embs, bank, ctx.config.voice, ctx.episode.number, returning)
    for v in voices:
        if v.returning_from:
            log.info("voice: candidate %s (first heard in %s) is back on %d lines", v.id, v.returning_from,
                     len(v.event_ids))
        else:
            log.info("voice: new voice %s on %d lines (closest known: %s %.2f)", v.id, len(v.event_ids),
                     v.closest_known, v.closest_score)
    save_line_voices(ctx.artifact("voice_embeddings.npz"), embs)
    save_new_voices(ctx.work, voices)               # before speakers.jsonl, the stage's output
    write_jsonl(ctx.artifact("speakers.jsonl"), results)
    counts = Counter(r.status for r in results)
    out = {s: counts.get(s, 0) for s in ("fixed", "confusable", "unknown", "too_short", "new_voice")}
    out["new_voices"] = sum(1 for v in voices if not v.returning_from)
    out["returning_candidates"] = sum(1 for v in voices if v.returning_from)
    return out


# -- bootstrap clips and centroids (5.17) -------------------------------------------------------

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".opus", ".aac"}


def voice_clips(paths: Paths) -> dict[str, list[Path]]:
    root = paths.bootstrap / "voices"
    if not root.is_dir():
        return {}
    out = {}
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        clips = sorted(f for f in d.iterdir() if f.suffix.lower() in AUDIO_EXTS)
        if clips:
            out[d.name] = clips
    return out


def compute_centroids(config: Config, paths: Paths, char_ids: set[str] | None = None,
                      embed=None) -> dict[str, tuple[np.ndarray, int]]:
    clips = {c: fs for c, fs in voice_clips(paths).items() if char_ids is None or c in char_ids}
    if not clips:
        return {}
    embed = embed or get_embedder(config, paths).embed
    out = {}
    for char_id, files in clips.items():
        embs = [embed(load_audio_any(f, config.audio.sample_rate)) for f in files]
        out[char_id] = (l2_normalize(np.mean(np.stack(embs), axis=0)), len(files))
    return out


def pair_similarities(centroids: dict[str, np.ndarray], threshold: float,
                      only: set[str] | None = None) -> dict[tuple[str, str], float]:
    pairs = {}
    for a, b in itertools.combinations(sorted(centroids), 2):
        if only is not None and a not in only and b not in only:
            continue
        sim = float(np.dot(centroids[a], centroids[b]))
        if sim >= threshold:
            pairs[(a, b)] = round(sim, 4)
    return pairs


def all_similarities(centroids: dict[str, np.ndarray]) -> dict[tuple[str, str], float]:
    return pair_similarities(centroids, threshold=-2.0)
