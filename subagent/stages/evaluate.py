"""Evaluator (5.12): free rule checks in code first, then an LLM rubric from a different model family."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache

from pydantic import BaseModel, Field, field_validator

from subagent.kernel.models import Evaluation, LineTranslation, SpeakerCandidates, SubtitleEvent
from subagent.kernel.textutil import (
    balanced_wrap,
    contains_term,
    found_terms,
    split_explicit_lines,
    visible_chars,
)
from subagent.llm import LLMClient, build_messages
from subagent.memory.store import GlossaryEntry, MemoryStore, PronounPair
from subagent.settings.config import Config

# rule failure code -> flag kept on the line when the retry cap is reached (NFR-Q1, NFR-Q2)
RULE_FLAGS = {
    "empty": "missing_translation",
    "missing": "missing_translation",
    "line_length": "line_too_long",
    "line_count": "line_too_long",
    "cps": "cps_exceeded",
    "glossary": "glossary_mismatch",
    "pronoun": "pronoun_mismatch",
    "speaker_unknown": "speaker_invalid",
    "speaker_not_candidate": "speaker_invalid",
    "listener_unknown": "speaker_invalid",
}


@dataclass
class RuleFailure:
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


@dataclass
class RuleContext:
    config: Config
    store: MemoryStore
    character_ids: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.character_ids = self.character_ids or self.store.character_ids()
        self._glossary = self.store.glossary()
        self._pairs: dict[tuple[str, str], list[PronounPair]] = {}
        for p in self.store.pronoun_pairs():
            self._pairs.setdefault((p.speaker_id, p.listener_id), []).append(p)
        self._glossary_in = lru_cache(maxsize=4096)(self._find_glossary)
        self._tokenizer = _word_tokenizer(self._glossary)

    def _boundaries(self, zh: str) -> set[int]:
        """Positions between words (jieba, glossary terms of 2+ characters kept whole). HMM joins runs of unknown
        characters into one word, so the show's coinages count as words before they reach the glossary (降鱼钓法,
        何罗鱼: 鱼 is not a word there; 2026-10-10: wrong 鱼 fires 16 -> 1 over 16 episodes)."""
        cuts, pos = {0}, 0
        for word in self._tokenizer.cut(zh, HMM=True):
            pos += len(word)
            cuts.add(pos)
        return cuts

    def _find_glossary(self, zh: str) -> tuple[GlossaryEntry, ...]:
        """Glossary terms in the line, as whole words: a term that starts or ends inside a longer word does not
        count (鱼 is not in 钓鱼 "to fish" or 鱼钩 "fish hook"; 2026-10-10: forcing "cá" there broke 35 lines)."""
        found: list[GlossaryEntry] = []
        covered = [False] * len(zh)
        cuts = self._boundaries(zh)
        for entry in self._glossary:   # longest first
            start = zh.find(entry.zh)
            while start != -1:
                end = start + len(entry.zh)
                if start in cuts and end in cuts and not any(covered[start:end]):
                    covered[start:end] = [True] * (end - start)
                    if entry not in found:
                        found.append(entry)
                start = zh.find(entry.zh, start + 1)
        return tuple(found)

    def glossary_in(self, zh: str) -> list[GlossaryEntry]:
        return list(self._glossary_in(zh))

    def pronoun_variants(self, speaker: str, listener: str) -> list[PronounPair]:
        return self._pairs.get((speaker, listener), [])


def _word_tokenizer(glossary: list[GlossaryEntry]):
    """A jieba tokenizer that keeps multi-character glossary terms whole. Single characters are not boosted, so
    the words they are part of (钓鱼) stay whole. Loaded here, not on first use (the review screen builds the
    rule context in a worker)."""
    import logging

    import jieba

    jieba.setLogLevel(logging.WARNING)
    tok = jieba.Tokenizer()
    tok.initialize()
    for entry in glossary:
        if len(entry.zh) >= 2:
            tok.add_word(entry.zh, freq=100000)
    return tok


def wrap_lines(vi: str, max_chars: int) -> list[str]:
    explicit = split_explicit_lines(vi)
    if len(explicit) > 1:
        return explicit
    return balanced_wrap(vi, max_chars)


def max_chars_for(event: SubtitleEvent, config: Config) -> int:
    cfg = config.translate
    by_cps = int(cfg.max_cps * max(event.duration_ms, 1) / 1000)
    return max(1, min(by_cps, cfg.max_line_chars * cfg.max_lines_per_event))


def rule_checks(line: LineTranslation, event: SubtitleEvent, cands: SpeakerCandidates | None,
                rc: RuleContext) -> tuple[list[RuleFailure], list[str]]:
    """Returns (failures, warnings). Failures send the line back to the translator."""
    cfg = rc.config.translate
    failures: list[RuleFailure] = []
    warnings: list[str] = []
    vi = line.vi.strip()
    if not vi:
        return [RuleFailure("empty", "translation is empty")], warnings

    lines = wrap_lines(vi, cfg.max_line_chars)
    long_lines = [ln for ln in lines if len(ln) > cfg.max_line_chars]
    if long_lines:
        failures.append(RuleFailure("line_length", f"a line has {len(long_lines[0])} characters; max {cfg.max_line_chars}"))
    if len(lines) > cfg.max_lines_per_event:
        failures.append(RuleFailure("line_count", f"needs {len(lines)} lines; max {cfg.max_lines_per_event}"))
    seconds = max(event.duration_ms, 1) / 1000
    cps = visible_chars(vi) / seconds
    if cps > cfg.max_cps:
        failures.append(RuleFailure(
            "cps", f"{cps:.1f} characters/second; max {cfg.max_cps:g} (shorten to ≤ {max_chars_for(event, rc.config)} characters)"))

    for entry in rc.glossary_in(event.zh):
        if not contains_term(vi, entry.vi):
            failures.append(RuleFailure("glossary", f"{entry.zh} must be translated as “{entry.vi}”"))

    if line.speaker and line.speaker not in rc.character_ids:
        failures.append(RuleFailure("speaker_unknown", f"speaker '{line.speaker}' is not a known character id"))
    if line.listener and line.listener not in rc.character_ids:
        failures.append(RuleFailure("listener_unknown", f"listener '{line.listener}' is not a known character id"))
    if cands and cands.status in ("confusable", "disputed") and cands.candidates and line.line_type == "dialogue":
        allowed = [c for c, _ in cands.candidates]
        # a disputed line may also have no speaker: neither the voice nor the picture fits (e.g. an NPC)
        if line.speaker not in allowed and not (cands.status == "disputed" and line.speaker is None):
            failures.append(RuleFailure("speaker_not_candidate", f"speaker must be one of {', '.join(allowed)}"))
    if cands and cands.status in ("fixed", "new_voice") and cands.candidates and line.speaker != cands.candidates[0][0]:
        warnings.append(f"voice match says {cands.candidates[0][0]}; translator chose {line.speaker}")

    if line.line_type == "dialogue" and line.speaker and line.listener:
        variants = rc.pronoun_variants(line.speaker, line.listener)
        if variants:
            allowed_terms = {t for v in variants for t in (v.self_term, v.address_term)}
            used = found_terms(vi, cfg.pronoun_terms)
            conflicting = [t for t in used if not any(t.lower() == a.lower() or contains_term(a, t) for a in allowed_terms)]
            expected = " / ".join(f"{v.self_term}–{v.address_term}" for v in variants)
            if conflicting and not any(contains_term(vi, a) for a in allowed_terms):
                failures.append(RuleFailure(
                    "pronoun", f"{line.speaker} → {line.listener} uses {expected}; found {', '.join(conflicting)}"))
            elif conflicting:
                warnings.append(f"pronoun terms {', '.join(conflicting)} besides {expected}")
    return failures, warnings


# -- LLM rubric ------------------------------------------------------------------------------------

class RubricLine(BaseModel):
    event_id: str
    scores: dict[str, int] = Field(description="criterion -> score 1..5")
    feedback: str = Field(default="", description="what to fix; empty when all scores are high")
    suggestion: str = Field(default="", description="your corrected Vietnamese line when any score is below 4; "
                                                    "empty otherwise")

    @field_validator("scores")
    @classmethod
    def _clamp(cls, v: dict[str, int]) -> dict[str, int]:
        return {k: max(1, min(5, int(s))) for k, s in v.items()}


class RubricResponse(BaseModel):
    lines: list[RubricLine] = Field(default_factory=list)


def rubric_payload(items: list[tuple[SubtitleEvent, LineTranslation, SpeakerCandidates | None]],
                   context: list[dict], identify: bool = True) -> str:
    """`identify` off (5.11a): no speaker, listener or voice fields."""
    rows = []
    for event, line, cands in items:
        who = {"speaker": line.speaker, "listener": line.listener} if identify else {}
        voice = {"voice_candidates": [c for c, _ in cands.candidates] if cands else [],
                 "voice_status": cands.status if cands else "unknown"} if identify else {}
        rows.append({
            "event_id": event.id, "zh": event.zh, "line_type": line.line_type, **who, "vi": line.vi, **voice,
            **({"translator_notes": line.notes} if line.notes else {}),
        })
    return (
        "Scene context (read-only):\n" + json.dumps(context, ensure_ascii=False, indent=0)
        + "\n\nLines to evaluate:\n" + json.dumps(rows, ensure_ascii=False, indent=0)
    )


def llm_rubric(llm: LLMClient, static_prompt: str, prefix: str,
               items: list[tuple[SubtitleEvent, LineTranslation, SpeakerCandidates | None]],
               context: list[dict], identify: bool = True) -> dict[str, RubricLine]:
    if not items:
        return {}
    messages = build_messages(static_prompt, prefix, rubric_payload(items, context, identify))
    resp: RubricResponse = llm.call("evaluator", messages, RubricResponse, task="evaluate")  # type: ignore[assignment]
    wanted = {e.id for e, _, _ in items}
    return {r.event_id: r for r in resp.lines if r.event_id in wanted}


def judge(event_id: str, attempt: int, failures: list[RuleFailure], warnings: list[str],
          rubric: RubricLine | None, config: Config, evaluated: bool) -> Evaluation:
    min_score = config.evaluate.min_score
    # no speaker criterion while character identification is off (5.11a)
    criteria = [c for c in config.evaluate.criteria if c != "speaker" or config.show.character_identification]
    scores = {k: v for k, v in (rubric.scores if rubric else {}).items() if k in criteria}
    low = [k for k, v in scores.items() if v < min_score]
    passed = not failures and not low
    parts = [str(f) for f in failures]
    if rubric and rubric.feedback and (low or failures):
        parts.append(rubric.feedback)
    elif rubric and rubric.feedback:
        parts.append(f"(passed) {rubric.feedback}")
    if low:
        parts.append("low scores: " + ", ".join(f"{k}={scores[k]}" for k in low))
    if not failures and evaluated and rubric is None:
        parts.append("not evaluated: the evaluator returned no score for this line")
    parts += [f"warning: {w}" for w in warnings]
    # kept on a passing line too (a score of 3 passes but still gets a suggestion): the reviewer sees it (6.4);
    # only failed lines are sent back to the translator
    suggestion = rubric.suggestion.strip() if rubric else ""
    if suggestion:
        parts.append(f"suggested: {suggestion}")
    return Evaluation(event_id=event_id, attempt=attempt, passed=passed, scores=scores, feedback="\n".join(parts),
                      rule_failures=[f.code for f in failures], suggestion=suggestion)
