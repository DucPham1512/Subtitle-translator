"""Dreaming (5.18): offline consolidation between episodes. Produces proposals only; never writes directly."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from subagent.episodes import Registry
from subagent.kernel.models import EditRecord, MemoryProposal, ReviewedLine
from subagent.kernel.textutil import contains_term
from subagent.kernel.util import hash_path, now_iso, read_json, read_jsonl, sha256_json
from subagent.llm import build_messages, load_prompt
from subagent.memory import briefings as bf
from subagent.memory.briefing_gen import compress_story
from subagent.memory.manager import ApplyResult, MemoryManager
from subagent.memory.prefix import characters_block, glossary_block, pronoun_block, style_block
from subagent.memory.store import MemoryStore, row_key
from subagent.settings.config import Config, Paths

log = logging.getLogger(__name__)

STORY_COMPRESS_AT = 0.9   # compress story_so_far.md when it reaches this share of its word cap


class DreamGlossary(BaseModel):
    zh: str
    vi: str
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)


class DreamPronoun(BaseModel):
    speaker_id: str
    listener_id: str
    self_term: str
    address_term: str
    context: str = ""
    since_episode: str | None = None
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)


class DreamStyleRule(BaseModel):
    rule: str
    example: str = ""
    action: Literal["add", "remove", "use"] = "add"
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)


class DreamResponse(BaseModel):
    glossary: list[DreamGlossary] = Field(default_factory=list)
    pronoun_pairs: list[DreamPronoun] = Field(default_factory=list)
    style_rules: list[DreamStyleRule] = Field(default_factory=list)


class DreamItem(BaseModel):
    id: str
    proposal: MemoryProposal
    table: str
    key: str
    before: dict | None = None
    touches_locked: bool = False
    preselected: Literal["accept", "reject"] = "accept"
    reason: str = ""


class DreamOutput(BaseModel):
    generated_at: str
    items: list[DreamItem] = Field(default_factory=list)
    inputs: dict = Field(default_factory=dict)


# -- inputs ----------------------------------------------------------------------------------------

def done_episodes(paths: Paths) -> list[str]:
    return [e.id for e in Registry(paths).load() if (paths.episode_dir(e.id) / "approved.jsonl").is_file()]


def new_edits(paths: Paths, state: dict) -> tuple[dict[str, list[EditRecord]], dict[str, str]]:
    """Edits of episodes whose edits.jsonl changed since the last dream."""
    seen: dict[str, str] = state.get("edits_seen", {})
    edits, hashes = {}, {}
    for ep in done_episodes(paths):
        path = paths.episode_dir(ep) / "edits.jsonl"
        if not path.is_file():
            continue
        h = hash_path(path)
        hashes[ep] = h
        if seen.get(ep) != h:
            records = read_jsonl(path, EditRecord)
            if records:
                edits[ep] = records
    return edits, hashes


def approved_lines(paths: Paths, limit: int) -> list[ReviewedLine]:
    lines: list[ReviewedLine] = []
    for ep in reversed(done_episodes(paths)):   # newest first, then trimmed to the limit
        lines.extend(x for x in read_jsonl(paths.episode_dir(ep) / "approved.jsonl", ReviewedLine) if not x.deleted)
        if len(lines) >= limit:
            break
    return lines[:limit]


def glossary_usage(store: MemoryStore, lines: list[ReviewedLine]) -> list[dict]:
    """Glossary terms whose approved translations do not always use the glossary form."""
    report = []
    for entry in store.glossary():
        with_zh = [ln for ln in lines if entry.zh in ln.zh]
        missing = [ln for ln in with_zh if not contains_term(ln.vi, entry.vi)]
        if missing:
            report.append({"zh": entry.zh, "vi": entry.vi, "locked": entry.locked, "lines_with_term": len(with_zh),
                           "lines_not_using_vi": [{"event_id": ln.event_id, "zh": ln.zh, "vi": ln.vi}
                                                  for ln in missing[:8]]})
    return report


# -- run -------------------------------------------------------------------------------------------

# -- rejected proposals ------------------------------------------------------------------------------

REJECTIONS_SHOWN_TO_MODEL = 60


def signature(p: MemoryProposal) -> str | None:
    """What a proposal says, independent of wording that varies between runs (evidence, since_episode, reason).
    Story compressions are never remembered: a later one is a different text."""
    pl = p.payload
    if p.kind == "glossary":
        return f"glossary|{pl.get('zh', '').strip()}|{pl.get('vi', '').strip().lower()}"
    if p.kind == "pronoun_pair":
        return (f"pronoun_pair|{pl.get('speaker_id')}|{pl.get('listener_id')}|{(pl.get('context') or '').strip()}|"
                f"{pl.get('self_term', '').strip().lower()}|{pl.get('address_term', '').strip().lower()}")
    if p.kind == "style_rule":
        return f"style_rule|{pl.get('action', 'add')}|{' '.join(str(pl.get('rule', '')).lower().split())}"
    return None


def load_rejections(paths: Paths) -> list[dict]:
    return read_json(paths.memory / "dream_rejections.json", []) or []


def describe(p: MemoryProposal) -> str:
    pl = p.payload
    if p.kind == "glossary":
        return f"glossary {pl.get('zh')} → {pl.get('vi')}"
    if p.kind == "pronoun_pair":
        ctx = f" ({pl.get('context')})" if pl.get("context") else ""
        return f"pronouns {pl.get('speaker_id')} → {pl.get('listener_id')}{ctx}: {pl.get('self_term')} / {pl.get('address_term')}"
    return f"style rule ({pl.get('action', 'add')}): {pl.get('rule')}"


def forget_rejections(config: Config, paths: Paths) -> int:
    """Clear the rejected list (the reviewer changed their mind); returns how many were forgotten."""
    manager = MemoryManager(paths, config)
    n = len(load_rejections(paths))
    with manager.locked():
        manager.write_aux("dream_rejections.json", None)
        manager.commit(f"dream: forgot {n} rejected proposals")
    return n


def dream(config: Config, paths: Paths, llm) -> DreamOutput:
    manager = MemoryManager(paths, config)
    manager.ensure_repo()
    store = manager.store
    state = read_json(paths.memory / "dream_state.json", {}) or {}
    edits, edit_hashes = new_edits(paths, state)
    lines = approved_lines(paths, config.memory.dream_max_lines)
    corrections = [json.loads(x) for x in (paths.memory / "speaker_corrections.jsonl").read_text(encoding="utf-8").splitlines()
                   if x.strip()] if (paths.memory / "speaker_corrections.jsonl").is_file() else []
    corrections = [c for c in corrections if c.get("ts", "") > state.get("last_dream_at", "")]

    items: list[DreamItem] = []
    if lines or edits:
        by_id = {ln.event_id: ln for ln in lines}
        edit_rows = [{"edit_id": e.edit_id, "field": e.field, "before": e.before, "after": e.after,
                      "zh": by_id[e.event_id].zh if e.event_id in by_id else None}
                     for recs in edits.values() for e in recs]
        static = load_prompt(paths, "dreaming_system").replace("{{style_rules_max}}", str(config.memory.style_rules_max))
        prefix = "# Series memory\n\n" + "\n".join([characters_block(store), glossary_block(store), pronoun_block(store),
                                                    style_block(paths.memory)])
        rejected_text = "\n".join(f"- {r['description']}" for r in load_rejections(paths)[-REJECTIONS_SHOWN_TO_MODEL:])
        variable = (
            "Proposals the reviewer rejected before (never propose these again, not even reworded):\n"
            + (rejected_text or "(none)") + "\n\n"
            + "Glossary terms not used consistently:\n" + json.dumps(glossary_usage(store, lines), ensure_ascii=False, indent=0)
            + "\n\nHuman edits since the last dream:\n" + json.dumps(edit_rows, ensure_ascii=False, indent=0)
            + "\n\nSpeaker corrections since the last dream:\n" + json.dumps(corrections, ensure_ascii=False, indent=0)
            + "\n\nApproved lines (event_id | speaker → listener | zh | vi):\n"
            + "\n".join(f"{ln.event_id} | {ln.speaker or '-'} → {ln.listener or '-'} | {ln.zh} | {ln.vi}" for ln in lines)
        )
        resp: DreamResponse = llm.call("utility", build_messages(static, prefix, variable), DreamResponse, task="dreaming")
        items += _items_from_response(store, resp, paths.memory)

    story = bf.read_story(paths.memory)
    cap = config.memory.story_so_far_max_words
    if story and bf.word_count(story) >= STORY_COMPRESS_AT * cap:
        compressed = compress_story(paths, story, int(cap * 0.7), llm)
        items.append(_item(store, MemoryProposal(kind="briefing", source="dreaming",
                                                 payload={"file": "story_so_far.md", "content": compressed}),
                           "briefings", "story_so_far.md", None, False, "story_so_far.md is near its word cap"))

    rejected = {r["signature"] for r in load_rejections(paths)}
    kept = [i for i in items if signature(i.proposal) not in rejected]
    out = DreamOutput(generated_at=now_iso(), items=kept, inputs={
        "episodes": done_episodes(paths), "edit_hashes": edit_hashes, "lines": len(lines),
        "edits": sum(len(v) for v in edits.values()), "speaker_corrections": len(corrections),
        "previously_rejected": len(items) - len(kept)})
    manager.write_aux("dream_proposals.json", out.model_dump(mode="json"))
    return out


def _item(store: MemoryStore, p: MemoryProposal, table: str, key: str, before: dict | None, locked: bool,
          reason: str) -> DreamItem:
    return DreamItem(id=sha256_json([p.kind, p.payload])[:12], proposal=p, table=table, key=key, before=before,
                     touches_locked=locked, preselected="reject" if locked else "accept", reason=reason)


# "Dịch 白条 thành 'cá trắng'." is a term translation: it belongs in the (enforced) glossary, not the style rules.
_TERM_RULE = re.compile(r"^\s*(?:Dịch|Translate)\s+(?P<zh>\S+)\s+(?:thành|as)\s+['\"“‘](?P<vi>[^'\"”’]+)['\"”’]\s*\.?\s*$",
                        re.IGNORECASE)


def _rule_key(text: str) -> str:
    return " ".join(text.lower().split()).rstrip(".")


def _items_from_response(store: MemoryStore, resp: DreamResponse, memory_dir: Path | None = None) -> list[DreamItem]:
    items: list[DreamItem] = []
    glossary = [DreamGlossary(zh=g.zh, vi=g.vi, reason=g.reason, evidence=g.evidence) for g in resp.glossary]
    rules = []
    for r in resp.style_rules:
        m = _TERM_RULE.match(r.rule)
        if m and r.action != "remove":
            glossary.append(DreamGlossary(zh=m.group("zh"), vi=m.group("vi").strip(), reason=r.reason,
                                          evidence=r.evidence))
        else:
            rules.append(r)
    seen_terms: set[tuple[str, str]] = set()
    for g in glossary:
        if (g.zh, g.vi.lower()) in seen_terms:
            continue
        seen_terms.add((g.zh, g.vi.lower()))
        before = store.get_row("glossary", g.zh)
        if before and before.get("vi", "").lower() == g.vi.lower():
            continue
        p = MemoryProposal(kind="glossary", source="dreaming", payload={"zh": g.zh, "vi": g.vi}, evidence=g.evidence)
        items.append(_item(store, p, "glossary", g.zh, before, bool(before and before.get("locked")), g.reason))
    for pp in resp.pronoun_pairs:
        payload = pp.model_dump(exclude={"reason", "evidence"})
        key = row_key("pronoun_pairs", payload)
        before = store.get_row("pronoun_pairs", key)
        if before and before.get("self_term") == pp.self_term and before.get("address_term") == pp.address_term:
            continue
        p = MemoryProposal(kind="pronoun_pair", source="dreaming", payload=payload, evidence=pp.evidence)
        items.append(_item(store, p, "pronoun_pairs", key, before, bool(before and before.get("locked")), pp.reason))
    existing = {_rule_key(x.rule) for x in bf.read_style_rules(memory_dir)} if memory_dir else set()
    for r in rules:
        present = _rule_key(r.rule) in existing
        if present and r.action in ("add", "use"):
            continue          # you already have this rule: nothing to decide
        if not present and r.action == "remove":
            continue          # nothing to remove
        p = MemoryProposal(kind="style_rule", source="dreaming",
                           payload={"rule": r.rule, "example": r.example, "action": r.action}, evidence=r.evidence)
        items.append(_item(store, p, "style_rules", r.rule[:80], None, False, r.reason))
    return items


def load_proposals(paths: Paths) -> DreamOutput | None:
    data = read_json(paths.memory / "dream_proposals.json")
    return DreamOutput.model_validate(data) if data else None


def apply_dream(config: Config, paths: Paths, accepted_ids: set[str] | None = None, *,
                auto: bool = False) -> ApplyResult:
    """Apply accepted proposals in one commit.

    auto: only proposals that touch no locked entry. A proposal on a locked entry that the user explicitly
    accepted in the app is applied as a human decision.
    """
    out = load_proposals(paths)
    manager = MemoryManager(paths, config)
    if out is None:
        return ApplyResult()
    chosen = []
    rejected_now: list[dict] = []
    for item in out.items:
        if auto:
            if item.touches_locked:
                continue      # skipped by the auto rule, not rejected by a person: may come back
        elif accepted_ids is None or item.id not in accepted_ids:
            sig = signature(item.proposal)
            if sig:
                rejected_now.append({"signature": sig, "description": describe(item.proposal),
                                     "rejected_at": now_iso()})
            continue
        p = item.proposal.model_copy(deep=True)
        if item.touches_locked:
            p.source = "human"
        chosen.append(p)
    with manager.locked():
        result = manager.apply(chosen)
        state = read_json(paths.memory / "dream_state.json", {}) or {}
        state["last_dream_at"] = out.generated_at
        state["edits_seen"] = {**state.get("edits_seen", {}), **out.inputs.get("edit_hashes", {})}
        manager.write_aux("dream_state.json", state)
        if rejected_now:
            known = load_rejections(paths)
            seen = {r["signature"] for r in known}
            manager.write_aux("dream_rejections.json", known + [r for r in rejected_now if r["signature"] not in seen])
        manager.write_aux("dream_proposals.json", None)
        manager.commit(f"dream: {result.writes} writes, {len(rejected_now)} rejected")
    return result
