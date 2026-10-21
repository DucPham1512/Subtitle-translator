"""Stage 9: translate each scene window and infer speaker/listener (5.11), with the evaluator loop (5.12)."""

from __future__ import annotations

import json
import logging
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from subagent.kernel.errors import SubagentError
from subagent.kernel.models import (
    CastLine,
    Evaluation,
    LineTranslation,
    LineType,
    MemoryProposal,
    SpeakerCandidates,
    SubtitleEvent,
    Window,
)
from subagent.kernel.util import atomic_write_text, read_json, read_jsonl, write_jsonl
from subagent.llm.client import build_messages, load_prompt
from subagent.memory.prefix import (
    corrections_block,
    evaluator_prefix,
    new_voices_block,
    reviewer_corrections,
    translator_prefix,
)
from subagent.memory.store import MemoryStore
from subagent.settings.config import Config
from subagent.stages.evaluate import (
    RULE_FLAGS,
    RuleContext,
    judge,
    llm_rubric,
    max_chars_for,
    rule_checks,
)
from subagent.workspace.context import EpisodeContext

log = logging.getLogger(__name__)


class ProposalDraft(BaseModel):
    kind: Literal["glossary", "pronoun_pair", "character"]
    payload: dict
    evidence: list[str] = Field(default_factory=list, description="event ids supporting the proposal")


class TranslatedLine(BaseModel):
    event_id: str
    speaker: str | None = None
    listener: str | None = None
    speaker_conf: float = 0.5
    line_type: LineType = "dialogue"
    vi: str
    notes: str = ""
    proposals: list[ProposalDraft] = Field(default_factory=list)

    @field_validator("speaker_conf")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    @field_validator("speaker", "listener")
    @classmethod
    def _empty_none(cls, v: str | None) -> str | None:
        return v.strip() or None if isinstance(v, str) and v.strip().lower() not in ("", "null", "none") else None


class TranslatorResponse(BaseModel):
    lines: list[TranslatedLine]


# -- prompt pieces ---------------------------------------------------------------------------------

_REGISTER_BLOCK = re.compile(r"<!-- register:(?P<name>[\w-]+) -->\n(?P<body>.*?)<!-- /register -->\n?", re.S)
# parts of the translator / evaluator prompts for one character identification mode (5.11a): `identify` (on)
# or `default_pair` (off); the markers' lines are removed, so the on-mode prompt is unchanged
_MODE_BLOCK = re.compile(r"<!-- if:(?P<name>\w+) -->\n(?P<body>.*?)<!-- /if -->\n?", re.S)
MODES = ("identify", "default_pair")


def mode_prompt(prompt: str, config: Config) -> str:
    """Keep the blocks of the series' character identification mode; fill in the default pronoun pair."""
    mode = "identify" if config.show.character_identification else "default_pair"

    def keep(m: re.Match) -> str:
        if m.group("name") not in MODES:
            raise SubagentError(f"Unknown prompt block 'if:{m.group('name')}' (known: {', '.join(MODES)})",
                                code="config_invalid")
        return m.group("body") if m.group("name") == mode else ""
    text = _MODE_BLOCK.sub(keep, prompt)
    return text.replace("{{self_term}}", config.show.self_term).replace("{{address_term}}", config.show.address_term)


def translator_static(prompt: str, register: str, config: Config, body: str | None = None) -> str:
    """The register (translation style) selected by show.genre_register in place of `{{register}}`
    (`body`: its text from prompts/registers/<id>.md); a prompt with inline register blocks keeps only the
    selected one. Limits are filled from config."""
    if "{{register}}" in prompt:
        if body is None:
            raise SubagentError(f"No translation style '{register}' in prompts/registers/", code="config_invalid")
        prompt = prompt.replace("{{register}}", body)
    blocks = {m.group("name"): m.group("body") for m in _REGISTER_BLOCK.finditer(prompt)}
    if blocks and register not in blocks:
        raise SubagentError(f"No register block '{register}' in prompts/translator_system.md "
                            f"(available: {', '.join(blocks)})", code="config_invalid")
    text = mode_prompt(_REGISTER_BLOCK.sub(lambda m: m.group("body") if m.group("name") == register else "", prompt),
                       config)
    return (text.replace("{{max_line_chars}}", str(config.translate.max_line_chars))
                .replace("{{max_lines_per_event}}", str(config.translate.max_lines_per_event))
                .replace("{{new_voice_prefix}}", config.voice.new_voice_prefix))


# voice statuses whose speaker the picture may not change (translate.picture_evidence: tiebreak)
PICTURE_SILENT = ("fixed", "new_voice")


def line_input(event: SubtitleEvent, cands: SpeakerCandidates | None, ctx: EpisodeContext,
               cast: CastLine | None = None) -> dict:
    row: dict = {
        "event_id": event.id,
        "zh": event.zh,
        "duration_s": round(event.duration_ms / 1000, 2),
        "max_vi_chars": max_chars_for(event, ctx.config),
        "speaker_status": cands.status if cands else "unknown",
        "speaker_candidates": [[c, round(s, 2)] for c, s in (cands.candidates if cands else [])],
    }
    if event.suspect:
        row["non_dialogue_suspect"] = True
    if not ctx.config.show.character_identification:      # no speakers: the default pronoun pair (5.11a)
        del row["speaker_status"], row["speaker_candidates"]
        return row
    mode = ctx.config.translate.picture_evidence
    if mode == "tiebreak" and row["speaker_status"] in PICTURE_SILENT:
        cast = None                     # a sure voice is never changed by the picture: do not show it
    if cast is not None and cast.detections and mode != "off":
        row["on_screen"] = cast.on_screen()
        unrecognised = sum(d.character is None for d in cast.detections)
        if unrecognised:
            row["unrecognised_on_screen"] = unrecognised
        talker = cast.talker()
        if talker is not None:
            row["talking"] = talker.character or "unrecognised"
    return row


def picture_veto(speakers: dict[str, SpeakerCandidates], cast: dict[str, CastLine], mode: str,
                 ) -> dict[str, SpeakerCandidates]:
    """The talking character on screen disputes the voice match (5.11).

    A line whose voice match is sure (`fixed` / `new_voice`) or unsure (`confusable`) becomes `disputed` when
    the clearly talking character on screen is someone else: a recognised different character, or (mode
    "any") someone not recognised. Its candidates are the voice's, plus the talking character when recognised;
    the translator chooses among them or leaves the speaker empty. Without a talking character nothing changes.
    """
    if mode == "off":
        return speakers
    out = dict(speakers)
    for eid, s in speakers.items():
        c = cast.get(eid)
        talker = c.talker() if c is not None else None
        if talker is None or s.status not in ("fixed", "new_voice", "confusable") or not s.candidates:
            continue
        voice_ids = [cid for cid, _ in s.candidates]
        if talker.character:
            if talker.character == voice_ids[0] or (s.status == "confusable" and talker.character in voice_ids):
                continue        # the picture agrees with the voice
            extra = [] if talker.character in voice_ids else [(talker.character, round(talker.similarity, 4))]
        elif mode == "any" and s.status != "confusable":
            extra = []
        else:
            continue
        out[eid] = s.model_copy(update={"status": "disputed", "candidates": list(s.candidates) + extra})
    return out


def context_row(event: SubtitleEvent, line: LineTranslation | None) -> dict:
    row: dict = {"event_id": event.id, "zh": event.zh}
    if line is not None:
        row.update({"speaker": line.speaker, "listener": line.listener, "line_type": line.line_type, "vi": line.vi})
    return row


def translator_payload(lines: list[dict], context: list[dict], feedback: list[dict] | None) -> str:
    text = "Previous context (read-only, already translated):\n" + json.dumps(context, ensure_ascii=False, indent=0)
    text += "\n\nLines to translate:\n" + json.dumps(lines, ensure_ascii=False, indent=0)
    if feedback:
        text += ("\n\nThese lines failed evaluation. Fix them using the feedback:\n"
                 + json.dumps(feedback, ensure_ascii=False, indent=0))
    return text


def to_translation(t: TranslatedLine, attempt: int, identify: bool = True) -> LineTranslation:
    speaker, listener = (t.speaker, t.listener) if t.line_type == "dialogue" and identify else (None, None)
    proposals = [
        MemoryProposal(kind=p.kind, payload=p.payload, source="translator", evidence=p.evidence or [t.event_id])
        for p in t.proposals
    ]
    return LineTranslation(event_id=t.event_id, speaker=speaker, listener=listener, speaker_conf=t.speaker_conf,
                           line_type=t.line_type, vi=t.vi.strip(), attempts=attempt, proposals=proposals,
                           notes=t.notes)


def rank_attempt(ev: Evaluation) -> tuple:
    return (ev.passed, not ev.rule_failures, sum(ev.scores.values()), -ev.attempt)


# -- window loop -----------------------------------------------------------------------------------

class WindowTranslator:
    def __init__(self, ctx: EpisodeContext, events: dict[str, SubtitleEvent], speakers: dict[str, SpeakerCandidates]):
        self.ctx = ctx
        self.events = events
        self.speakers = speakers
        from subagent.memory.characters import load_new_voices

        store = MemoryStore(ctx.paths.memory_db)
        self.identify = ctx.config.show.character_identification
        voices = load_new_voices(ctx.work) if self.identify else []
        self.rules = RuleContext(ctx.config, store, store.character_ids() | {v.id for v in voices})
        from subagent.settings.registers import load_register

        style = load_register(ctx.paths.root, ctx.config.show.genre_register)
        self.t_static = translator_static(load_prompt(ctx.paths, "translator_system"), ctx.config.show.genre_register,
                                          ctx.config, style.body if style else None)
        self.e_static = mode_prompt(load_prompt(ctx.paths, "evaluator_system"), ctx.config)
        # memory prefixes: built once per episode, byte-identical across calls (prefix caching)
        corrections = corrections_block(reviewer_corrections(ctx.paths, ctx.config.memory.correction_examples))
        episode = new_voices_block(voices, store, {e.id: e.start_ms for e in events.values()}) if self.identify \
            else ""
        self.t_prefix = translator_prefix(store, ctx.paths.memory, corrections, episode, pronouns=self.identify)
        self.e_prefix = evaluator_prefix(store, ctx.paths.memory, corrections, episode, pronouns=self.identify)
        self.soft_codes = set() if ctx.config.translate.retry_on_cps else {"cps"}
        atomic_write_text(ctx.artifact("memory_prefix.md"), self.t_prefix)
        self.cast = {c.event_id: c for c in read_jsonl(ctx.artifact("cast.jsonl"), CastLine)} if self.identify \
            else {}
        self.speakers = picture_veto(speakers, self.cast, ctx.config.translate.picture_veto)
        self.done: dict[str, LineTranslation] = {}
        self.evaluations: list[Evaluation] = []

    def _translate(self, ids: list[str], context: list[dict], feedback: list[dict] | None) -> dict[str, TranslatedLine]:
        lines = [line_input(self.events[i], self.speakers.get(i), self.ctx, self.cast.get(i)) for i in ids]
        messages = build_messages(self.t_static, self.t_prefix, translator_payload(lines, context, feedback))
        resp: TranslatorResponse = self.ctx.llm.call("translator", messages, TranslatorResponse, task="translate")  # type: ignore[assignment]
        wanted = set(ids)
        return {t.event_id: t for t in resp.lines if t.event_id in wanted}

    def run_window(self, window: Window) -> None:
        """Translate a window, then retry only the failed lines (with their history and the evaluator's
        suggestion) up to `translate.max_retries`; each line keeps its best attempt."""
        cfg = self.ctx.config
        base_context = [context_row(self.events[i], self.done.get(i)) for i in window.context_ids if i in self.events]
        attempts: dict[str, list[tuple[LineTranslation, Evaluation]]] = {i: [] for i in window.event_ids}
        pending = list(window.event_ids)
        feedback: list[dict] | None = None
        for attempt in range(1, cfg.translate.max_retries + 2):
            if attempt == 1:
                context = base_context
            else:  # only failed lines are resent; the rest of the window is context
                context = base_context + [
                    context_row(self.events[i], _best(attempts[i])[0] if attempts[i] else None)
                    for i in window.event_ids if i not in pending
                ]
            got = self._translate(pending, context, feedback)
            checked = self._check_lines(pending, got, attempts, attempt)
            to_rubric = [(self.events[eid], line, self.speakers.get(eid))
                         for eid, line, hard, _, _, repeat in checked if line is not None and not hard and not repeat]
            scene = [context_row(self.events[i], None) for i in window.event_ids]
            rubric = llm_rubric(self.ctx.llm, self.e_static, self.e_prefix, to_rubric, scene, self.identify)
            pending, feedback = self._judge_lines(checked, rubric, attempts, attempt)
            if not pending:
                break

        for eid in window.event_ids:
            self.done[eid] = self._finalize(eid, attempts[eid])

    def _check_lines(self, pending: list[str], got: dict[str, TranslatedLine],
                     attempts: dict[str, list[tuple[LineTranslation, Evaluation]]], attempt: int,
                     ) -> list[tuple[str, LineTranslation | None, list, list, list, Evaluation | None]]:
        """Per pending line: (event id, translation or None when missing, hard rule failures, soft ones, warnings,
        the verdict of an identical earlier answer)."""
        checked: list[tuple[str, LineTranslation | None, list, list, list, Evaluation | None]] = []
        for eid in pending:
            t = got.get(eid)
            if t is None:
                checked.append((eid, None, [], [], [], None))
                continue
            line = to_translation(t, attempt, self.identify)
            repeat = next((ev for old, ev in attempts[eid] if _same(old, line)), None)
            failures, warnings = rule_checks(line, self.events[eid], self.speakers.get(eid), self.rules)
            hard = [f for f in failures if f.code not in self.soft_codes]
            soft = [f for f in failures if f.code in self.soft_codes]
            checked.append((eid, line, hard, soft, warnings, repeat))
        return checked

    def _judge_lines(self, checked: list, rubric: dict, attempts: dict[str, list[tuple[LineTranslation, Evaluation]]],
                     attempt: int) -> tuple[list[str], list[dict]]:
        """Record each line's evaluation; returns the lines to retry and the feedback the translator gets."""
        cfg = self.ctx.config
        next_pending, feedback = [], []
        for eid, line, hard, soft, warnings, repeat in checked:
            if line is None:
                ev = Evaluation(event_id=eid, attempt=attempt, passed=False, rule_failures=["missing"],
                                feedback="[missing] the translator returned no line for this event")
                line = LineTranslation(event_id=eid, speaker=None, listener=None, speaker_conf=0.0, vi="",
                                       attempts=attempt)
            elif repeat is not None:
                # the same answer again: re-judging it would give the same verdict, so stop retrying this line
                ev = repeat.model_copy(update={"attempt": attempt})
                self.evaluations.append(ev)
                attempts[eid].append((line, ev))
                continue
            else:
                ev = judge(eid, attempt, hard, warnings + [str(f) for f in soft], rubric.get(eid), cfg,
                           evaluated=not hard)
                ev.soft_failures = [f.code for f in soft]
            self.evaluations.append(ev)
            attempts[eid].append((line, ev))
            if not ev.passed:
                next_pending.append(eid)
                feedback.append({
                    "event_id": eid,
                    "earlier_attempts": [{"vi": old.vi, "speaker": old.speaker, "listener": old.listener,
                                          "feedback": old_ev.feedback} for old, old_ev in attempts[eid]],
                    "evaluator_suggestion": ev.suggestion,
                })
        return next_pending, feedback

    def _finalize(self, eid: str, tries: list[tuple[LineTranslation, Evaluation]]) -> LineTranslation:
        line, ev = _best(tries)
        line = line.model_copy(deep=True)
        line.attempts = len(tries)
        flags: list[str] = []
        if not ev.passed:
            flags.append("retry_cap")
            flags += [RULE_FLAGS[c] for c in ev.rule_failures if c in RULE_FLAGS]
        flags += [RULE_FLAGS[c] for c in ev.soft_failures if c in RULE_FLAGS]
        if "not evaluated" in ev.feedback:
            flags.append("not_evaluated")
        cands = self.speakers.get(eid)
        if cands and cands.status == "fixed" and cands.candidates and line.speaker and line.speaker != cands.candidates[0][0]:
            flags.append("speaker_override")
        if self.identify and line.line_type == "dialogue" and \
                line.speaker_conf < self.ctx.config.sprite.trigger_conf_below:
            flags.append("low_speaker_conf")
        line.flags = list(dict.fromkeys(line.flags + flags))
        return line


def _same(a: LineTranslation, b: LineTranslation) -> bool:
    return (a.vi.strip(), a.speaker, a.listener, a.line_type) == (b.vi.strip(), b.speaker, b.listener, b.line_type)


def _best(tries: list[tuple[LineTranslation, Evaluation]]) -> tuple[LineTranslation, Evaluation]:
    return max(tries, key=lambda pair: rank_attempt(pair[1]))


def run(ctx: EpisodeContext) -> dict[str, int]:
    events = {e.id: e for e in read_jsonl(ctx.artifact("events.jsonl"), SubtitleEvent)}
    speakers = {s.event_id: s for s in read_jsonl(ctx.artifact("speakers.jsonl"), SpeakerCandidates)} \
        if ctx.config.show.character_identification else {}     # off: an older run's file is not read (5.11a)
    windows = [Window.model_validate(w) for w in read_json(ctx.artifact("windows.json"), [])]
    translator = WindowTranslator(ctx, events, speakers)
    for i, window in enumerate(windows, 1):
        translator.run_window(window)
        ctx.progress.emit("translate", "progress", done=i, total=len(windows))
    order = [e for w in windows for e in w.event_ids]
    results = [translator.done[e] for e in order]
    write_jsonl(ctx.artifact("translations.jsonl"), results)
    write_jsonl(ctx.artifact("evaluations.jsonl"), translator.evaluations)
    first = [ev for ev in translator.evaluations if ev.attempt == 1]
    return {
        "lines": len(results),
        "first_pass": sum(ev.passed for ev in first),
        "retried": sum(1 for r in results if r.attempts > 1),
        "retry_cap": sum("retry_cap" in r.flags for r in results),
        "low_speaker_conf": sum("low_speaker_conf" in r.flags for r in results),
    }
