"""Audit (6.11): measure accuracy on finished episodes by checking a small sample instead of every line.

Per episode, a reproducible random sample is drawn from the final script (flagged and unflagged lines in
proportion, at least `audit.min_per_stratum` of each when available), plus up to `audit.max_disagreements`
lines where independent signals disagree about the speaker (voice match, talking sprite, final speaker).
The reviewer marks each sampled line ✓ / ✗ / n/a per aspect (speaker, OCR, translation, pronouns). Marks are
measurement only: they change no output and teach no memory.

The report estimates each aspect's accuracy over all lines of the audited episodes (stratified by episode and
flagged/unflagged, weighted by line counts) with a 95% range, the error rates of flagged vs unflagged lines,
the error rate on disagreement lines (counted separately: they are not random), and a per-episode trend.
Series-neutral: nothing here depends on the show.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from subagent.kernel.models import (
    AUDIT_ASPECTS,
    AuditMark,
    AuditSample,
    CastLine,
    ReviewedLine,
    SpeakerCandidates,
)
from subagent.kernel.util import atomic_write_text, read_jsonl, write_jsonl
from subagent.settings.config import Config, Paths

NO_ID_YET = "_new"      # correct speaker: a character appearing for the first time, with no id (blank is right)
SAMPLE_FILE = "audit_sample.jsonl"
MARKS_FILE = "audit_marks.jsonl"
Z95 = 1.96


def auditable_lines(work: Path) -> list[ReviewedLine]:
    """The final script: approved, non-deleted lines (what the viewer sees)."""
    return [x for x in read_jsonl(work / "approved.jsonl", ReviewedLine) if not x.deleted]


def is_flagged(line: ReviewedLine, ignore: list[str] | tuple[str, ...] = ()) -> bool:
    """Flagged for something that could be wrong (flags in `audit.ignore_flags`, e.g. reading speed, do not count)."""
    return any(f not in ignore for f in line.flags)


def disagreements(work: Path, lines: list[ReviewedLine]) -> dict[str, list[str]]:
    """Lines where the voice match, the talking sprite and the final speaker do not all agree."""
    voices = {s.event_id: s for s in read_jsonl(work / "speakers.jsonl", SpeakerCandidates)}
    cast = {c.event_id: c for c in read_jsonl(work / "cast.jsonl", CastLine)}
    out: dict[str, list[str]] = {}
    for x in lines:
        if x.line_type != "dialogue":
            continue
        reasons = []
        v = voices.get(x.event_id)
        voice = v.candidates[0][0] if v and v.status in ("fixed", "new_voice") and v.candidates else None
        c = cast.get(x.event_id)
        talker = c.talker().character if c is not None and c.talker() is not None else None
        if voice and voice != x.speaker:
            reasons.append(f"voice: {voice}")
        if talker and talker != x.speaker:
            reasons.append(f"talking on screen: {talker}")
        if reasons:
            out[x.event_id] = reasons
    return out


def _rng(episode_id: str) -> random.Random:
    return random.Random(int(hashlib.sha256(f"audit:{episode_id}".encode()).hexdigest()[:12], 16))


def auditable(config: Config, paths: Paths, episode_id: str) -> bool:
    """Auto-mode episodes; human-reviewed ones only with `audit.include_human` (their output is the reviewer's
    corrected script, and their edits.jsonl already records every machine error exactly)."""
    from subagent.workspace.state import load_state

    mode = load_state(paths.episode_dir(episode_id), episode_id).mode
    return mode == "auto" or config.audit.include_human


def draw_sample(config: Config, paths: Paths, episode_id: str) -> list[AuditSample]:
    """A reproducible sample for one finished episode (same episode, same sample)."""
    cfg = config.audit
    work = paths.episode_dir(episode_id)
    if not auditable(config, paths, episode_id):
        return []
    lines = auditable_lines(work)
    if not lines:
        return []
    rng = _rng(episode_id)
    flagged = [x for x in lines if is_flagged(x, cfg.ignore_flags)]
    plain = [x for x in lines if not is_flagged(x, cfg.ignore_flags)]
    n = min(cfg.sample_size, len(lines))
    n_flag = round(n * len(flagged) / len(lines))
    n_flag = max(n_flag, min(cfg.min_per_stratum, len(flagged)))
    n_plain = max(n - n_flag, min(cfg.min_per_stratum, len(plain)))
    n_flag, n_plain = min(n_flag, len(flagged)), min(n_plain, len(plain))
    picked = {x.event_id: True for x in rng.sample(flagged, n_flag)}
    picked.update({x.event_id: False for x in rng.sample(plain, n_plain)})
    disagree = disagreements(work, lines)
    samples = [AuditSample(event_id=e, kind="random", flagged=f, disagreement=disagree.get(e, []))
               for e, f in picked.items()]
    extra = [e for e in disagree if e not in picked]
    rng.shuffle(extra)
    by_id = {x.event_id: x for x in lines}
    samples += [AuditSample(event_id=e, kind="disagreement", flagged=is_flagged(by_id[e], cfg.ignore_flags),
                            disagreement=disagree[e])
                for e in extra[: cfg.max_disagreements]]
    order = {x.event_id: i for i, x in enumerate(sorted(lines, key=lambda x: (x.start_ms, x.event_id)))}
    samples.sort(key=lambda s: order[s.event_id])
    write_jsonl(work / SAMPLE_FILE, samples)
    return samples


def load_sample(work: Path) -> list[AuditSample]:
    return read_jsonl(work / SAMPLE_FILE, AuditSample)


def load_marks(work: Path) -> dict[str, AuditMark]:
    return {m.event_id: m for m in read_jsonl(work / MARKS_FILE, AuditMark)}


def gold_speakers(work: Path) -> dict[str, str | None]:
    """Reference speakers from the audit: ✓ lines keep the speaker they had when marked, ✗ lines the correct
    speaker the auditor picked (✗ without an answer and n/a lines are left out)."""
    marks = load_marks(work)
    if not marks:
        return {}
    current = {x.event_id: x.speaker for x in auditable_lines(work)}
    gold: dict[str, str | None] = {}
    for e, m in marks.items():
        if m.speaker is True:
            gold[e] = m.speaker_value if m.speaker_value is not None else current.get(e)
        elif m.speaker is False and m.correct_speaker:
            gold[e] = None if m.correct_speaker == NO_ID_YET else m.correct_speaker
    return gold


def missing_answers(work: Path) -> int:
    """Wrong-speaker marks without the correct speaker (the benchmark cannot use them)."""
    return sum(1 for m in load_marks(work).values() if m.speaker is False and not m.correct_speaker)


def save_marks(work: Path, marks: dict[str, AuditMark]) -> None:
    write_jsonl(work / MARKS_FILE, [m for _, m in sorted(marks.items()) if m.marked()])


# -- statistics ------------------------------------------------------------------------------------

@dataclass
class Rate:
    errors: float = 0.0               # estimated error rate (0..1)
    low: float = 0.0                  # 95% range of the error rate
    high: float = 0.0
    checked: int = 0                  # marked lines behind the estimate

    @property
    def accuracy(self) -> float:
        return 1.0 - self.errors


def wilson(errors: int, n: int) -> Rate:
    if n == 0:
        return Rate()
    p = errors / n
    denom = 1 + Z95 ** 2 / n
    centre = (p + Z95 ** 2 / (2 * n)) / denom
    half = Z95 * math.sqrt(p * (1 - p) / n + Z95 ** 2 / (4 * n * n)) / denom
    return Rate(p, max(0.0, centre - half), min(1.0, centre + half), n)


def stratified(cells: list[tuple[int, int, int]]) -> Rate:
    """cells: (lines in the stratum, marked, errors). Error rate over all lines of the covered strata, with a
    normal-approximation 95% range (each stratum's rate smoothed so a clean sample still has some spread)."""
    cells = [c for c in cells if c[1] > 0]
    total = sum(c[0] for c in cells)
    if not total:
        return Rate()
    est = sum(N * x / n for N, n, x in cells) / total
    var = sum((N / total) ** 2 * ((x + 0.5) / (n + 1)) * (1 - (x + 0.5) / (n + 1)) / n for N, n, x in cells)
    half = Z95 * math.sqrt(var)
    return Rate(est, max(0.0, est - half), min(1.0, est + half), sum(c[1] for c in cells))


@dataclass
class EpisodeAudit:
    episode_id: str
    mode: str
    lines: int
    sampled: int
    marked: int
    any_error: Rate = field(default_factory=Rate)


@dataclass
class AuditReport:
    episodes: list[EpisodeAudit] = field(default_factory=list)
    aspects: dict[str, Rate] = field(default_factory=dict)
    flagged: Rate = field(default_factory=Rate)
    unflagged: Rate = field(default_factory=Rate)
    disagreement: Rate = field(default_factory=Rate)


def build_report(config: Config, paths: Paths, episode_ids: list[str]) -> AuditReport:
    from subagent.workspace.state import load_state

    report = AuditReport()
    cells: dict[str, list[tuple[int, int, int]]] = {a: [] for a in AUDIT_ASPECTS}
    flag_tot = {True: [0, 0], False: [0, 0]}
    dis = [0, 0]
    for ep in episode_ids:
        work = paths.episode_dir(ep)
        sample = load_sample(work)
        if not sample or not auditable(config, paths, ep):
            continue
        marks = load_marks(work)
        lines = auditable_lines(work)
        ignore = config.audit.ignore_flags
        sizes = {True: sum(is_flagged(x, ignore) for x in lines), False: sum(not is_flagged(x, ignore) for x in lines)}
        mode = load_state(work, ep).mode or "-"
        any_err = [0, 0]
        for aspect in AUDIT_ASPECTS:
            for stratum in (True, False):
                vals = [getattr(marks[s.event_id], aspect) for s in sample
                        if s.kind == "random" and s.flagged == stratum and s.event_id in marks]
                vals = [v for v in vals if v is not None]
                cells[aspect].append((sizes[stratum], len(vals), sum(not v for v in vals)))
        for s in sample:
            m = marks.get(s.event_id)
            if m is None or not m.marked():
                continue
            wrong = m.any_wrong()
            if s.kind == "random":
                any_err[0] += wrong
                any_err[1] += 1
                flag_tot[s.flagged][0] += wrong
                flag_tot[s.flagged][1] += 1
            else:
                dis[0] += wrong
                dis[1] += 1
        report.episodes.append(EpisodeAudit(ep, mode, len(lines), len(sample),
                                            sum(1 for s in sample if s.event_id in marks and marks[s.event_id].marked()),
                                            wilson(*any_err)))
    report.aspects = {a: stratified(c) for a, c in cells.items()}
    report.flagged = wilson(*flag_tot[True])
    report.unflagged = wilson(*flag_tot[False])
    report.disagreement = wilson(*dis)
    return report


def _pct(r: Rate, accuracy: bool = True) -> str:
    if not r.checked:
        return "n/a"
    if accuracy:
        return f"{(1 - r.errors) * 100:.0f}% (95%: {(1 - r.high) * 100:.0f}–{(1 - r.low) * 100:.0f}%, {r.checked} checked)"
    return f"{r.errors * 100:.0f}% (95%: {r.low * 100:.0f}–{r.high * 100:.0f}%, {r.checked} checked)"


def render_report(r: AuditReport) -> str:
    out = ["# Audit report", "", "## Accuracy over all lines of the audited episodes", "",
           "Estimated from the random sample, weighted by episode size and flagged / unflagged lines.", ""]
    names = {"speaker": "Speaker", "ocr": "OCR (Chinese text)", "translation": "Translation (meaning)",
             "pronouns": "Pronouns (xưng hô)"}
    for a in AUDIT_ASPECTS:
        out.append(f"- {names[a]}: {_pct(r.aspects.get(a, Rate()))}")
    out += ["", "## Where the errors are", "",
            f"- Flagged lines, any error: {_pct(r.flagged, False)}",
            f"- Unflagged lines, any error: {_pct(r.unflagged, False)}",
            f"- Lines where voice / picture / speaker disagree, any error: {_pct(r.disagreement, False)}",
            "", "## Per episode", "", "| episode | mode | lines | sampled | marked | any error (random sample) |",
            "|---|---|---|---|---|---|"]
    for e in r.episodes:
        out.append(f"| {e.episode_id} | {e.mode} | {e.lines} | {e.sampled} | {e.marked} | {_pct(e.any_error, False)} |")
    return "\n".join(out) + "\n"


def write_report(config: Config, paths: Paths, episode_ids: list[str]) -> tuple[AuditReport, Path]:
    r = build_report(config, paths, episode_ids)
    folder = paths.work / "_audit"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "report.md"
    atomic_write_text(path, render_report(r))
    summary = {"aspects": {a: vars(v) for a, v in r.aspects.items()}, "flagged": vars(r.flagged),
               "unflagged": vars(r.unflagged), "disagreement": vars(r.disagreement),
               "episodes": [{**{k: v for k, v in vars(e).items() if k != "any_error"},
                             "any_error": vars(e.any_error)} for e in r.episodes]}
    atomic_write_text(folder / "summary.json", json.dumps(summary, indent=1))
    return r, path
