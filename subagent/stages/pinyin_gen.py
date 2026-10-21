"""Stage 7: deterministic pinyin from the corrected Chinese (5.9); LLM fallback only for polyphones."""

from __future__ import annotations

import json
import logging
import unicodedata
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from subagent.context import EpisodeContext
from subagent.kernel.models import PinyinLine, SubtitleEvent
from subagent.kernel.textutil import is_han
from subagent.kernel.util import read_jsonl, write_jsonl
from subagent.llm.client import build_messages, load_prompt
from subagent.memory.store import Character, GlossaryEntry, MemoryStore
from subagent.settings.config import Config

log = logging.getLogger(__name__)

PUNCT_MAP = {
    "，": ",", "。": ".", "！": "!", "？": "?", "：": ":", "；": ";", "、": ",", "“": "“", "”": "”",
    "‘": "‘", "’": "’", "（": "(", "）": ")", "《": "«", "》": "»", "…": "…", "—": "—",
    "·": "·", "～": "~", "「": "“", "」": "”", "『": "‘", "』": "’", "【": "[", "】": "]",
}
OPENING = {"“", "‘", "(", "«", "["}


@dataclass
class Token:
    text: str
    start: int
    syllables: list[str] = field(default_factory=list)   # aligned 1:1 with chars when `aligned`
    fixed: str | None = None                            # glossary pinyin, used verbatim
    punct: bool = False
    known_phrase: bool = False
    aligned: bool = False


class PinyinEngine:
    """Glossary-aware segmentation (jieba) + tone-mark pinyin (pypinyin)."""

    def __init__(self, glossary: list[GlossaryEntry], characters: list[Character], polyphones: list[str]):
        import jieba
        from pypinyin import load_phrases_dict

        jieba.setLogLevel(logging.WARNING)
        self.tokenizer = jieba.Tokenizer()
        self.fixed: dict[str, str] = {}
        phrases: dict[str, list[list[str]]] = {}
        for entry in glossary:
            self.tokenizer.add_word(entry.zh, freq=100000)
            if entry.pinyin:
                self.fixed[entry.zh] = entry.pinyin.strip()
                sylls = entry.pinyin.split()
                if len(sylls) == len(entry.zh):
                    phrases[entry.zh] = [[s.lower()] for s in sylls]
        for c in characters:
            self.tokenizer.add_word(c.name_zh, freq=100000)
        if phrases:
            load_phrases_dict(phrases)
        self.polyphones = set(polyphones)

    @classmethod
    def from_store(cls, store: MemoryStore, config: Config) -> PinyinEngine:
        return cls(store.glossary(), store.characters(), config.pinyin.polyphones)

    def tokens(self, zh: str) -> list[Token]:
        from pypinyin import Style, lazy_pinyin
        from pypinyin.constants import PHRASES_DICT

        out: list[Token] = []
        pos = 0
        for word in self.tokenizer.lcut(zh):
            start = zh.find(word, pos)
            pos = start + len(word)
            if not any(is_han(ch) or ch.isalnum() for ch in word):
                out.append(Token(text=word, start=start, punct=True))
                continue
            if word in self.fixed:
                out.append(Token(text=word, start=start, fixed=self.fixed[word], known_phrase=True))
                continue
            sylls = lazy_pinyin(word, style=Style.TONE, errors=lambda s: [s])
            aligned = all(is_han(ch) for ch in word) and len(sylls) == len(word)
            known = len(word) > 1 and word in PHRASES_DICT
            out.append(Token(text=word, start=start, syllables=sylls, aligned=aligned, known_phrase=known))
        return out

    def polyphone_positions(self, tokens: list[Token]) -> list[int]:
        """Char indices of high-risk polyphones that occur outside a known phrase."""
        positions = []
        for t in tokens:
            if t.punct or t.fixed is not None or t.known_phrase or not t.aligned:
                continue
            for i, ch in enumerate(t.text):
                if ch in self.polyphones:
                    positions.append(t.start + i)
        return positions

    @staticmethod
    def render(tokens: list[Token], overrides: dict[int, str] | None = None) -> str:
        overrides = overrides or {}
        parts: list[str] = []
        attach_next = False
        for t in tokens:
            if t.punct:
                mapped = "".join(PUNCT_MAP.get(ch, ch) for ch in t.text if not ch.isspace())
                if not mapped:
                    continue
                if mapped[0] in OPENING:
                    parts.append(mapped)
                    attach_next = True
                else:
                    if parts:
                        parts[-1] += mapped
                    else:
                        parts.append(mapped)
                continue
            if t.fixed is not None:
                text = t.fixed
            else:
                sylls = list(t.syllables)
                if t.aligned:
                    for i in range(len(sylls)):
                        if t.start + i in overrides:
                            sylls[i] = overrides[t.start + i]
                text = "".join(sylls)
            if attach_next and parts:
                parts[-1] += text
                attach_next = False
            else:
                parts.append(text)
        return unicodedata.normalize("NFC", " ".join(p for p in parts if p))

    def line(self, zh: str) -> tuple[str, list[int]]:
        tokens = self.tokens(zh)
        return self.render(tokens), self.polyphone_positions(tokens)


def heteronyms(ch: str) -> list[str]:
    from pypinyin import Style, pinyin

    return pinyin(ch, style=Style.TONE, heteronym=True)[0]


class PolyphoneChoice(BaseModel):
    event_id: str
    index: int = Field(description="character index in the line")
    pinyin: str = Field(description="chosen reading with tone mark, one of the candidates")


class PolyphoneResponse(BaseModel):
    choices: list[PolyphoneChoice] = Field(default_factory=list)


def resolve_polyphones(ctx: EpisodeContext, items: list[dict]) -> dict[tuple[str, int], str]:
    """One batched utility call per episode for the polyphones outside known phrases."""
    if not items:
        return {}
    static = load_prompt(ctx.paths, "polyphone_system")
    variable = "Polyphones to resolve:\n" + json.dumps(items, ensure_ascii=False, indent=0)
    resp: PolyphoneResponse = ctx.llm.call("utility", build_messages(static, "", variable), PolyphoneResponse, task="pinyin")  # type: ignore[assignment]
    allowed = {(it["event_id"], it["index"]): {c.lower() for c in it["candidates"]} for it in items}
    chosen: dict[tuple[str, int], str] = {}
    for c in resp.choices:
        reading = unicodedata.normalize("NFC", c.pinyin.strip().lower())
        if reading in allowed.get((c.event_id, c.index), set()):
            chosen[(c.event_id, c.index)] = reading
        else:
            log.info("pinyin: ignored reading %r for %s[%d]", c.pinyin, c.event_id, c.index)
    return chosen


def run(ctx: EpisodeContext) -> dict[str, int]:
    events = read_jsonl(ctx.artifact("events.jsonl"), SubtitleEvent)
    engine = PinyinEngine.from_store(MemoryStore(ctx.paths.memory_db), ctx.config)
    tokenized = {e.id: engine.tokens(e.zh) for e in events}
    items: list[dict] = []
    if ctx.config.pinyin.polyphone_fallback:
        for e in events:
            for idx in engine.polyphone_positions(tokenized[e.id]):
                cands = [unicodedata.normalize("NFC", h) for h in heteronyms(e.zh[idx])]
                if len(cands) > 1:
                    items.append({"event_id": e.id, "index": idx, "char": e.zh[idx], "zh": e.zh, "candidates": cands})
    chosen = resolve_polyphones(ctx, items)
    lines = []
    for e in events:
        overrides = {idx: reading for (eid, idx), reading in chosen.items() if eid == e.id}
        lines.append(PinyinLine(event_id=e.id, pinyin=engine.render(tokenized[e.id], overrides)))
    write_jsonl(ctx.artifact("pinyin.jsonl"), lines)
    return {"lines": len(lines), "polyphones_sent": len(items), "polyphones_resolved": len(chosen)}
