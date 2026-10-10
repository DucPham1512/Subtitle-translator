"""Memory prefix for prompts: built once per episode, byte-identical across calls (5.1 caching rule)."""

from __future__ import annotations

from pathlib import Path

from subagent.memory import briefings as bf
from subagent.memory.store import MemoryStore


def characters_block(store: MemoryStore) -> str:
    chars = store.characters(active_only=True)
    if not chars:
        return "## Characters\n(none yet)\n"
    lines = ["## Characters", "id | Chinese | Vietnamese (Hán-Việt) | description"]
    for c in chars:
        desc = (c.description or "").replace("\n", " ")
        if c.generic:
            desc = (desc + " " if desc else "") + "(generic: stands for many individuals; not identified by voice)"
        if c.aliases:
            desc = (desc + " " if desc else "") + f"(called: {'; '.join(c.aliases)})"
        lines.append(f"{c.id} | {c.name_zh} | {c.name_vi} | {desc}")
    return "\n".join(lines) + "\n"


def glossary_block(store: MemoryStore) -> str:
    entries = sorted(store.glossary(), key=lambda e: e.zh)
    if not entries:
        return "## Glossary\n(empty)\n"
    lines = ["## Glossary (use these translations exactly)"]
    for e in entries:
        extra = f" ({e.pinyin})" if e.pinyin else ""
        kind = f" [{e.type}]" if e.type else ""
        notes = f" — {e.notes}" if e.notes else ""
        lines.append(f"- {e.zh}{extra} → {e.vi}{kind}{notes}")
    return "\n".join(lines) + "\n"


def glossary_zh_block(store: MemoryStore) -> str:
    terms = sorted({e.zh for e in store.glossary()} | {c.name_zh for c in store.characters()})
    if not terms:
        return "## Known terms\n(none yet)\n"
    return "## Known terms (names and glossary, Chinese)\n" + "、".join(terms) + "\n"


def pronoun_block(store: MemoryStore) -> str:
    archived = {c.id for c in store.characters() if c.archived}
    pairs = [p for p in store.pronoun_pairs() if p.speaker_id not in archived and p.listener_id not in archived]
    if not pairs:
        return "## Pronoun matrix\n(empty)\n"
    lines = ["## Pronoun matrix (speaker → listener: self term / address term)"]
    for p in pairs:
        ctx = f" (when: {p.context})" if p.context else ""
        lines.append(f"- {p.speaker_id} → {p.listener_id}: {p.self_term} / {p.address_term}{ctx}")
    return "\n".join(lines) + "\n"


def story_block(memory_dir: Path) -> str:
    story = bf.read_story(memory_dir).strip()
    return "## Story so far\n" + (story or "(this is the start of the series)") + "\n"


def style_block(memory_dir: Path) -> str:
    rules = bf.read_style_rules(memory_dir)
    if not rules:
        return "## Style rules\n(none yet)\n"
    lines = ["## Style rules"]
    for r in rules:
        lines.append(f"- {r.rule}" + (f" Example: {r.example}" if r.example else ""))
    return "\n".join(lines) + "\n"


def reviewer_corrections(paths, limit: int) -> list[tuple[str, str, str]]:
    """(zh, machine vi, reviewer vi) from the latest finished reviews, newest episodes first, deduplicated."""
    from subagent.episodes import Registry
    from subagent.models import EditRecord, ReviewedLine
    from subagent.util import read_jsonl

    out: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for ep in reversed(Registry(paths).load()):
        work = paths.episode_dir(ep.id)
        lines = {x.event_id: x for x in read_jsonl(work / "approved.jsonl", ReviewedLine)}
        for e in read_jsonl(work / "edits.jsonl", EditRecord):
            line = lines.get(e.event_id)
            if e.field != "vi" or not e.before or not e.after or line is None or line.deleted:
                continue
            key = (e.before.strip(), e.after.strip())
            if key in seen:
                continue
            seen.add(key)
            out.append((line.zh, key[0], key[1]))
            if len(out) >= limit:
                return out
    return out


def corrections_block(corrections: list[tuple[str, str, str]]) -> str:
    if not corrections:
        return ""
    lines = ["## Reviewer corrections",
             "The human reviewer changed earlier machine translations like this. Follow the same preferences."]
    for zh, before, after in corrections:
        lines.append(f"- {zh}: “{before}” → “{after}”")
    return "\n".join(lines) + "\n"


def new_voices_block(voices: list, store: MemoryStore, first_ms: dict[str, int]) -> str:
    """This episode's new voices (fixed for the whole episode, so the prefix stays byte-identical)."""
    if not voices:
        return ""
    lines = ["## New voices in this episode",
             "Voices that match no known character, each heard on several lines. Use the id as speaker or listener."]
    cands = {c.id: c for c in store.candidates()}
    for v in voices:
        t = min((first_ms.get(e, 0) for e in v.event_ids), default=0) // 1000
        back = ""
        if getattr(v, "returning_from", None):
            back = f"; also heard in {v.returning_from}" + (f" (named {v.name_vi})" if v.name_vi else "")
            cand = cands.get(v.id)
            if cand is not None and cand.description:
                back += f"; {' '.join(cand.description.split())}"
            if cand is not None and cand.aliases:
                back += f" (called: {'; '.join(cand.aliases)})"
        lines.append(f"- {v.id}: {len(v.event_ids)} lines, first at {t // 60:02d}:{t % 60:02d}{back}")
    voiced = set(store.voice_bank())
    silent = [f"{c.id} ({c.name_vi})" for c in store.characters(active_only=True) if c.id not in voiced and not c.generic]
    if silent:
        lines.append("Known characters without a voice sample yet (a new voice may be one of them): "
                     + ", ".join(silent))
    return "\n".join(lines) + "\n"


def translator_prefix(store: MemoryStore, memory_dir: Path, corrections: str = "", episode: str = "") -> str:
    parts = [characters_block(store), glossary_block(store), pronoun_block(store), story_block(memory_dir),
             style_block(memory_dir), corrections, episode]
    return "# Series memory\n\n" + "\n".join(p for p in parts if p)


def evaluator_prefix(store: MemoryStore, memory_dir: Path | None = None, corrections: str = "",
                     episode: str = "") -> str:
    parts = [characters_block(store), glossary_block(store), pronoun_block(store),
             style_block(memory_dir) if memory_dir else "", corrections, episode]
    return "# Series memory\n\n" + "\n".join(p for p in parts if p)


def ocr_fix_prefix(store: MemoryStore) -> str:
    return "# Series memory\n\n" + glossary_zh_block(store)
