"""Memory bootstrap (5.17): seed characters, pronoun pairs, glossary and the voice bank before episode 1."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field, field_validator

from subagent.kernel.errors import SubagentError
from subagent.kernel.models import MemoryProposal, SubtitleEvent
from subagent.kernel.util import atomic_write_text, now_iso, read_jsonl
from subagent.llm.client import build_messages, load_prompt
from subagent.memory.manager import ApplyResult, MemoryManager
from subagent.settings.config import Config, Paths
from subagent.stages.voice import compute_centroids, pair_similarities, voice_clips

log = logging.getLogger(__name__)

_SLUG = re.compile(r"[^a-z0-9_]+")


def slugify(text: str) -> str:
    import unicodedata

    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    return _SLUG.sub("_", ascii_text).strip("_") or "character"


class SeedCharacter(BaseModel):
    id: str
    name_zh: str
    name_vi: str
    description: str = ""

    @field_validator("id")
    @classmethod
    def _slug(cls, v: str) -> str:
        return slugify(v)


class SeedPronoun(BaseModel):
    speaker_id: str
    listener_id: str
    self_term: str
    address_term: str
    context: str = ""


class SeedGlossary(BaseModel):
    zh: str
    vi: str
    pinyin: str | None = None
    type: str | None = None
    notes: str | None = None


class SeedResponse(BaseModel):
    characters: list[SeedCharacter] = Field(default_factory=list)
    pronoun_pairs: list[SeedPronoun] = Field(default_factory=list)
    glossary: list[SeedGlossary] = Field(default_factory=list)


class SeedVoice(BaseModel):
    character_id: str
    n_clips: int
    embedding: list[float]


class SeedConfusable(BaseModel):
    a: str
    b: str
    similarity: float


class SeedDraft(SeedResponse):
    generated_at: str = ""
    voices: list[SeedVoice] = Field(default_factory=list)
    confusable_pairs: list[SeedConfusable] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def seed_path(paths: Paths) -> Path:
    return paths.bootstrap / "seed_draft.json"


def load_seed(paths: Paths) -> SeedDraft:
    path = seed_path(paths)
    if not path.is_file():
        raise SubagentError("No seed draft yet; run `bootstrap` first", code="seed_missing")
    return SeedDraft.model_validate_json(path.read_text(encoding="utf-8"))


def save_seed(paths: Paths, draft: SeedDraft) -> None:
    atomic_write_text(seed_path(paths), draft.model_dump_json(indent=2))


# -- voices ----------------------------------------------------------------------------------------

# -- seed ------------------------------------------------------------------------------------------

def _episode1_lines(paths: Paths, limit: int = 150) -> list[str]:
    from subagent.workspace.episodes import Registry

    episodes = Registry(paths).load()   # sorted by number
    if not episodes:
        return []
    events = read_jsonl(paths.episode_dir(episodes[0].id) / "events.jsonl", SubtitleEvent)
    return [e.zh for e in events[:limit]]


def name_pinyin(zh: str) -> str:
    from pypinyin import Style, lazy_pinyin

    return " ".join(s.capitalize() for s in lazy_pinyin(zh, style=Style.TONE))


def generate_seed(config: Config, paths: Paths, llm, *, embed=None) -> SeedDraft:
    cast_file = paths.bootstrap / "cast.md"
    if not cast_file.is_file():
        raise SubagentError(f"Write the cast list and synopsis in {cast_file} first", code="cast_missing")
    cast = cast_file.read_text(encoding="utf-8")
    ep1 = _episode1_lines(paths)
    static = load_prompt(paths, "bootstrap_system")
    variable = f"Show: {config.show.name}\n\n# cast.md\n{cast}\n"
    if ep1:
        variable += "\n# Episode 1 subtitle lines (Chinese)\n" + "\n".join(ep1) + "\n"
    seed: SeedResponse = llm.call("utility", build_messages(static, "", variable), SeedResponse, task="bootstrap")
    draft = SeedDraft(**seed.model_dump(), generated_at=now_iso())

    known = {c.id for c in draft.characters}
    glossary_zh = {g.zh for g in draft.glossary}
    for c in draft.characters:   # names in the glossary: segmentation, pinyin and the glossary rule use them
        if c.name_zh not in glossary_zh:
            draft.glossary.append(SeedGlossary(zh=c.name_zh, vi=c.name_vi, pinyin=name_pinyin(c.name_zh), type="name"))
    for p in draft.pronoun_pairs:
        for cid in (p.speaker_id, p.listener_id):
            if cid not in known:
                draft.warnings.append(f"pronoun pair uses unknown character id '{cid}'")

    centroids: dict[str, tuple[np.ndarray, int]] = {}
    if voice_clips(paths):
        try:
            centroids = compute_centroids(config, paths, embed=embed)
        except SubagentError as exc:
            draft.warnings.append(f"voice bank skipped: {exc}")
    for cid, (emb, n) in sorted(centroids.items()):
        if cid not in known:
            draft.warnings.append(f"voice clips for unknown character id '{cid}'")
        draft.voices.append(SeedVoice(character_id=cid, n_clips=n, embedding=[float(x) for x in emb]))
    embs = {cid: emb for cid, (emb, _) in centroids.items()}
    draft.confusable_pairs = [SeedConfusable(a=a, b=b, similarity=s)
                              for (a, b), s in pair_similarities(embs, config.voice.confusable_similarity).items()]
    save_seed(paths, draft)
    return draft


def seed_proposals(draft: SeedDraft) -> list[MemoryProposal]:
    props = [MemoryProposal(kind="character", payload=c.model_dump(), source="bootstrap") for c in draft.characters]
    props += [MemoryProposal(kind="glossary", payload=g.model_dump(), source="bootstrap") for g in draft.glossary]
    props += [MemoryProposal(kind="pronoun_pair", payload=p.model_dump(), source="bootstrap")
              for p in draft.pronoun_pairs]
    return props


def approve_seed(config: Config, paths: Paths) -> ApplyResult:
    """Write the (edited) seed draft to memory, locked, in one commit."""
    draft = load_seed(paths)
    manager = MemoryManager(paths, config)
    manager.ensure_repo()
    with manager.locked():
        result = manager.apply(seed_proposals(draft), episode_id=None)
        known = manager.store.character_ids()
        voices = {v.character_id: (np.asarray(v.embedding, dtype=np.float32), v.n_clips)
                  for v in draft.voices if v.character_id in known}
        if voices:
            manager.write_voices(voices, source="bootstrap")
            manager.write_confusable_pairs({(p.a, p.b): p.similarity for p in draft.confusable_pairs
                                            if p.a in known and p.b in known})
        manager.commit(f"bootstrap: {result.writes} writes, {len(voices)} voices")
    return result


def update_voices(config: Config, paths: Paths, char_ids: set[str], *, embed=None) -> dict[str, int]:
    """Recompute only these characters' centroids and their pair similarities (rerunnable per character)."""
    manager = MemoryManager(paths, config)
    manager.ensure_repo()
    known = manager.store.character_ids()
    unknown = char_ids - known
    if unknown:
        raise SubagentError(f"Unknown character id(s): {', '.join(sorted(unknown))}", code="unknown_character")
    centroids = compute_centroids(config, paths, char_ids, embed=embed)
    missing = char_ids - set(centroids)
    if missing:
        raise SubagentError(f"No voice clips for: {', '.join(sorted(missing))}", code="clips_missing")
    with manager.locked():
        manager.write_voices(centroids, source="human")
        bank = manager.store.voice_bank()
        pairs = pair_similarities(bank, config.voice.confusable_similarity, only=char_ids)
        manager.write_confusable_pairs(pairs, involving=char_ids, source="human")
        manager.commit(f"voices: {', '.join(sorted(char_ids))}")
    return {cid: n for cid, (_, n) in centroids.items()}


def save_clip(config: Config, paths: Paths, char_id: str, source: Path, start_ms: int, end_ms: int) -> Path:
    """Cut a voice clip from an episode video into data/bootstrap/voices/<char_id>/ (16 kHz mono WAV)."""
    from subagent.infra.media import require_binary, run

    if end_ms <= start_ms:
        raise SubagentError("The clip end must be after its start", code="clip_invalid")
    folder = paths.bootstrap / "voices" / slugify(char_id)
    folder.mkdir(parents=True, exist_ok=True)
    out = folder / f"{source.stem}_{start_ms:08d}_{end_ms:08d}.wav"
    run([require_binary("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
         "-ss", f"{start_ms / 1000:.3f}", "-i", str(source), "-t", f"{(end_ms - start_ms) / 1000:.3f}",
         "-vn", "-ac", "1", "-ar", str(config.audio.sample_rate), "-c:a", "pcm_s16le", str(out)])
    return out
