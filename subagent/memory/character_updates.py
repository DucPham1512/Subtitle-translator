"""Character updates from an episode (5.15c): one utility call reads the approved script and proposes what it
teaches about the characters in it: names, descriptions, aliases / titles, and the pronoun pairs actually used.

The model's answer is checked in code before anything becomes a proposal: only characters present in the episode,
evidence only from lines it may learn from (with that character in them), names and aliases written in a line that
addresses the character (it is the listener) or, for a name, in its own self-introduction, pronoun terms that occur
in the Vietnamese of a line with that speaker and listener. The Memory Manager then
applies the proposals (source `updater`) to unlocked entries and holds the ones on locked entries for review.
"""

from __future__ import annotations

import json
import logging
import re

from pydantic import BaseModel, Field

from subagent.config import Config, Paths
from subagent.llm import build_messages, load_prompt
from subagent.memory import briefings as bf
from subagent.memory.prefix import characters_block
from subagent.memory.store import MemoryStore, parse_aliases
from subagent.models import MemoryProposal, ReviewedLine

log = logging.getLogger(__name__)

TASK = "character_update"
# a speaker naming themself: 我是王五, 在下王五, 老夫王五 ...
SELF_INTRO = re.compile(r"(?:我是|我叫|我乃|吾乃|在下|老夫|本座|本王|贫道|小女子|小人)")


class CharacterChange(BaseModel):
    id: str = Field(description="id from the Present characters list")
    name_zh: str | None = Field(default=None, description="the name as written in Chinese, only when a line states it")
    name_vi: str | None = Field(default=None, description="its Hán-Việt reading")
    description: str | None = Field(default=None, description="the full updated description, or null if nothing new")
    aliases: list[str] = Field(default_factory=list, description="new titles or other names: 'zh (vi)'")
    evidence: list[str] = Field(default_factory=list, description="event ids of the lines that show it")


class PronounUse(BaseModel):
    speaker_id: str
    listener_id: str
    self_term: str
    address_term: str
    context: str = ""
    evidence: list[str] = Field(default_factory=list)


class CharacterUpdateResponse(BaseModel):
    characters: list[CharacterChange] = Field(default_factory=list)
    pronouns: list[PronounUse] = Field(default_factory=list)


def present_ids(lines: list[ReviewedLine]) -> list[str]:
    return sorted({cid for x in lines for cid in (x.speaker, x.listener) if cid})


def _present_block(store: MemoryStore, ids: list[str]) -> str:
    chars = {c.id: c for c in store.characters()}
    cands = {c.id: c for c in store.candidates()}
    rows = []
    for cid in ids:
        if cid in chars:
            c = chars[cid]
            kind = "locked" if c.locked else "unlocked"
            name_zh, name_vi, desc, aliases = c.name_zh, c.name_vi, c.description, c.aliases
        elif cid in cands:
            c2 = cands[cid]
            kind, name_zh, name_vi, desc, aliases = "candidate", c2.name_zh, c2.name_vi, c2.description, c2.aliases
        else:
            kind, name_zh, name_vi, desc, aliases = "new voice", None, None, None, []
        unnamed = not name_vi or name_vi == cid
        rows.append({"id": cid, "kind": kind, "name_zh": None if unnamed else name_zh,
                     "name_vi": None if unnamed else name_vi, "description": desc or "", "aliases": aliases})
    return json.dumps(rows, ensure_ascii=False, indent=1)


def _pairs_block(store: MemoryStore, ids: set[str]) -> str:
    pairs = [p for p in store.pronoun_pairs() if p.speaker_id in ids and p.listener_id in ids]
    if not pairs:
        return "(none)"
    return "\n".join(f"- {p.speaker_id} → {p.listener_id}: {p.self_term} / {p.address_term}"
                     + (f" (when: {p.context})" if p.context else "") for p in pairs)


def _script(lines: list[ReviewedLine]) -> str:
    rows = []
    for x in lines:
        who = f"{x.speaker or '?'} → {x.listener or '?'}" if x.line_type == "dialogue" else f"[{x.line_type}]"
        rows.append(f"{x.event_id} | {who}: {x.zh} | {x.vi}")
    return "\n".join(rows)


def propose(paths: Paths, config: Config, store: MemoryStore, episode_id: str, lines: list[ReviewedLine],
            llm: object, *, learnable: set[str] | None = None) -> list[MemoryProposal]:
    """The checked proposals of one episode. `lines`: its approved, non-deleted lines (all shown to the model as
    context); `learnable`: the event ids evidence may come from (default: every line)."""
    ids = present_ids(lines)
    if not ids:
        return []
    cap = config.memory.description_max_chars
    static = (load_prompt(paths, "character_update_system")
              .replace("{{description_max_chars}}", str(cap)))
    variable = (
        f"Episode: {episode_id}\n\n"
        f"Story so far:\n{bf.read_story(paths.memory).strip() or '(empty)'}\n\n"
        f"Present characters (everyone who speaks or is spoken to in this episode):\n"
        f"{_present_block(store, ids)}\n\n"
        f"Pronoun matrix between them:\n{_pairs_block(store, set(ids))}\n\n"
        f"Approved script of {episode_id} (event id | speaker → listener: Chinese | Vietnamese):\n{_script(lines)}\n"
    )
    messages = build_messages(static, characters_block(store), variable)
    resp: CharacterUpdateResponse = llm.call("utility", messages, CharacterUpdateResponse,  # type: ignore[attr-defined]
                                             task=TASK)
    return check(resp, store, lines, ids, learnable, config)


def check(resp: CharacterUpdateResponse, store: MemoryStore, lines: list[ReviewedLine], ids: list[str],
          learnable: set[str] | None, config: Config) -> list[MemoryProposal]:
    by_id = {x.event_id: x for x in lines}
    allowed = set(by_id) if learnable is None else set(by_id) & learnable
    chars = {c.id: c for c in store.characters()}
    cands = {c.id: c for c in store.candidates()}
    cap = config.memory.description_max_chars
    out: list[MemoryProposal] = []
    dropped: list[str] = []
    for ch in resp.characters:
        if ch.id not in ids:
            dropped.append(f"{ch.id}: not in this episode")
            continue
        evidence = [e for e in dict.fromkeys(ch.evidence) if e in allowed and ch.id in
                    (by_id[e].speaker, by_id[e].listener)]
        if not evidence:
            dropped.append(f"{ch.id}: no usable evidence")
            continue
        addressed = " ".join(by_id[e].zh for e in evidence if by_id[e].listener == ch.id)
        current = chars.get(ch.id) or cands.get(ch.id)
        payload: dict = {"id": ch.id}
        name_zh = (ch.name_zh or "").strip()
        name_vi = (ch.name_vi or "").strip()
        if name_zh and name_vi and name_vi != ch.id and (name_zh in addressed or _introduces(
                [by_id[e].zh for e in evidence if by_id[e].speaker == ch.id], name_zh)):
            if not current or (current.name_zh, current.name_vi) != (name_zh, name_vi):
                payload["name_zh"], payload["name_vi"] = name_zh, name_vi
        elif name_zh or name_vi:
            dropped.append(f"{ch.id}: name {name_zh or name_vi} not used to address or introduce it")
        desc = " ".join((ch.description or "").split())
        if desc and (not current or desc != (current.description or "")):
            payload["description"] = _clip(desc, cap)
        have = list(current.aliases) if current else []
        new = [a for a in parse_aliases(ch.aliases) if a not in have and _alias_zh(a)
               and _alias_zh(a) in addressed]
        if new:
            payload["aliases"] = (have + new)[:config.memory.aliases_max]
        if len(payload) > 1:
            out.append(MemoryProposal(kind="character", source="updater", payload=payload, evidence=evidence))
    pairs = {(p.speaker_id, p.listener_id, p.context): p for p in store.pronoun_pairs()}
    for pu in resp.pronouns:
        s, li = pu.speaker_id, pu.listener_id
        self_term, address_term = " ".join(pu.self_term.split()), " ".join(pu.address_term.split())
        context = " ".join(pu.context.split())
        if s not in ids or li not in ids or s == li or not self_term or not address_term:
            dropped.append(f"pronouns {s} → {li}: not two characters of this episode")
            continue
        evidence = [e for e in dict.fromkeys(pu.evidence) if e in allowed and by_id[e].speaker == s
                    and by_id[e].listener == li and (_has_word(by_id[e].vi, self_term)
                                                    or _has_word(by_id[e].vi, address_term))]
        if not evidence:
            dropped.append(f"pronouns {s} → {li}: terms not used in its evidence lines")
            continue
        old = pairs.get((s, li, context))
        if old and (old.self_term.lower(), old.address_term.lower()) == (self_term.lower(), address_term.lower()):
            continue
        out.append(MemoryProposal(kind="pronoun_pair", source="updater", evidence=evidence, payload={
            "speaker_id": s, "listener_id": li, "self_term": self_term, "address_term": address_term,
            "context": context}))
    if dropped:
        log.info("character updates: %d dropped by the checks: %s", len(dropped), "; ".join(dropped[:20]))
    return out


def _clip(text: str, cap: int) -> str:
    if len(text) <= cap:
        return text
    cut = text[:cap].rsplit(" ", 1)[0].rstrip(",;:")
    return cut + "…"


def _introduces(lines: list[str], name: str) -> bool:
    """One of the character's own lines names it: a self-reference followed closely by the name."""
    return any(SELF_INTRO.search(zh[max(0, i - 4):i]) for zh in lines for i in _positions(zh, name))


def _positions(text: str, sub: str) -> list[int]:
    return [m.start() for m in re.finditer(re.escape(sub), text)]


def _alias_zh(alias: str) -> str:
    """The Chinese part of 'zh (vi)'."""
    return alias.split("(", 1)[0].strip()


def _has_word(text: str, term: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text or "", re.IGNORECASE) is not None
