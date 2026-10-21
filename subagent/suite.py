"""Benchmark suite (6.11e): five benchmarks scored against a frozen baseline (6.11d).

The baseline's reviewed episodes are the gold; a "system" is a folder with the same per-episode machine files
(`<system>/<episode>/events.jsonl`, `translations.jsonl`, ...): the baseline itself (the recorded output the
reviewer worked from) or a sandbox run of `bench run` (subagent/bench_run.py). Nothing here calls a model.

1. OCR / Chinese: raw OCR, after OCR correction, and with the script review's fixes accepted, against the
   approved Chinese with the baseline's answer key (`answer_key.json`) applied; lines matched by time.
2. Speaker / listener: the translator's choice and the voice match's first candidate against the approved
   speaker. Ids in `aliases.json` count as one character. Automatic ids (`npc_005_01`) are grouped: each is mapped
   one-to-one onto the gold id it shares most lines with, among gold ids that were not in memory when the episode
   ran (automatic characters, candidates, characters created in review), so the numbering never counts.
3. Character recognition: the lines marked On screen checked; boxes (IoU >= BOX_IOU), names, talking sprite.
4. Translation + evaluator: similarity to the approved Vietnamese (all lines, rewritten lines by cause), pronoun
   terms, and the evaluator's verdict on the kept attempt: catch rate on lines that differ from the gold, false
   alarms on lines that match it; signal "failed" (not passed) and "doubt" (failed or any criterion <= 3).
5. Script review: the review draft's pre-deleted and flagged lines against the reviewer's deletions; suggested
   OCR fixes against the gold Chinese.
"""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from subagent.kernel.models import (
    CastLine,
    EditRecord,
    Evaluation,
    LineTranslation,
    ReviewedLine,
    ScriptDecision,
    SpeakerCandidates,
    SubtitleEvent,
)
from subagent.kernel.util import append_jsonl, atomic_write_text, now_iso, read_jsonl
from subagent.ocr_benchmark import KEY_FILE, _norm, _overlap, score_episode
from subagent.settings.config import Config, Paths

FOLDER = "_suite"
BOX_IOU = 0.5
DOUBT_SCORE = 3
NOT_A_CHARACTER = "_none"
UNKNOWN = "?"                           # a box the reviewer left unrecognised on a checked line
REMOVAL_FLAGS = ("script_repeat", "script_noise", "script_unrelated", "script_other")   # the script review removed it


# -- loading -------------------------------------------------------------------------------------

@dataclass
class Gold:
    folder: Path
    manifest: dict
    aliases: dict[str, str]
    key: dict
    episodes: list[str]


def load_gold(folder: Path, episodes: list[str] | None = None) -> Gold:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    aliases_file = folder / "aliases.json"
    aliases = {a["id"]: a["same_as"] for a in json.loads(aliases_file.read_text(encoding="utf-8"))["aliases"]} \
        if aliases_file.is_file() else {}
    key_file = folder / KEY_FILE
    key = json.loads(key_file.read_text(encoding="utf-8")) if key_file.is_file() else {}
    key = {"corrections": key.get("corrections", {}), "excluded": key.get("excluded", {})}
    eps = [e for e in sorted(manifest["episodes"]) if episodes is None or e in episodes]
    return Gold(folder, manifest, aliases, key, eps)


def _approved(work: Path) -> list[ReviewedLine]:
    return [x for x in read_jsonl(work / "approved.jsonl", ReviewedLine) if x.approved or x.deleted]


def _events(work: Path, name: str = "events.jsonl") -> list[SubtitleEvent]:
    return read_jsonl(work / name, SubtitleEvent) if (work / name).is_file() else []


def align(gold: list[ReviewedLine], events: list[SubtitleEvent]) -> dict[str, str]:
    """Gold event id -> system event id: the same id when the system kept the baseline's events, else the event
    overlapping the line most in time (a rerun of OCR renumbers events)."""
    ids = {e.id: e for e in events}
    out = {}
    for x in gold:
        e = ids.get(x.event_id)
        if e is not None and e.start_ms < x.end_ms and x.start_ms < e.end_ms:
            out[x.event_id] = e.id
            continue
        best = max(events, key=lambda ev: _overlap(x.start_ms, x.end_ms, ev.start_ms, ev.end_ms), default=None)
        if best is not None and _overlap(x.start_ms, x.end_ms, best.start_ms, best.end_ms) > 0:
            out[x.event_id] = best.id
    return out


def characters_at(memory: Path, sha: str | None, cache: dict[str, set[str]] | None = None) -> set[str]:
    """Character ids in memory.db at a memory commit (read with git show; nothing is checked out)."""
    from subagent.infra.media import require_binary, run

    if not sha or not (memory / ".git").exists():
        return set()
    if cache is not None and sha in cache:
        return cache[sha]
    proc = run([require_binary("git"), "show", f"{sha}:memory.db"], cwd=memory, check=False)
    ids: set[str] = set()
    if proc.returncode == 0 and proc.stdout:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "memory.db"
            db.write_bytes(proc.stdout)
            conn = sqlite3.connect(db)
            try:
                ids = {r[0] for r in conn.execute("SELECT id FROM characters")}
            finally:
                conn.close()
    if cache is not None:
        cache[sha] = ids
    return ids


# -- small helpers -------------------------------------------------------------------------------

def _pct(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def _rate(n: int, d: int) -> dict:
    from subagent.audit import wilson

    r = wilson(d - n, d)
    return {"right": n, "of": d, "share": _pct(n, d), "low": round(1 - r.high, 4) if d else None,
            "high": round(1 - r.low, 4) if d else None}


def _vi(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.replace("\\N", " ").lower())).strip()


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _vi(a), _vi(b), autojunk=False).ratio()


def iou(a: list[float], b: list[float]) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def group_map(pairs: list[tuple[str | None, str | None]], mappable: set[str], targets: set[str]) -> dict[str, str]:
    """One-to-one map of system ids onto gold ids by shared lines (most shared first): automatic ids carry no
    meaning of their own, only which lines they group together."""
    counts = Counter((p, g) for p, g in pairs if p in mappable and g in targets)
    out: dict[str, str] = {}
    used: set[str] = set()
    for (p, g), _n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if p not in out and g not in used:
            out[p] = g
            used.add(g)
    return out


def _auto_pattern(config: Config) -> re.Pattern:
    return re.compile(rf"^{re.escape(config.voice.new_voice_prefix)}_\d{{3}}_\d{{2}}$")


# -- 1. OCR --------------------------------------------------------------------------------------

def score_ocr(gold: Gold, system: Path) -> dict:
    from subagent.ocr_benchmark import gold_lines

    levels = {"raw": [], "ocr_fix": [], "fixes_accepted": []}
    for ep in gold.episodes:
        lines = gold_lines(gold.folder / ep, gold.key)
        work = system / ep
        raw = _events(work, "events_raw.jsonl")
        fixed = _events(work)
        fixes = {d.event_id: d.zh_fix for d in _decisions(work) if d.action == "fix" and d.zh_fix}
        levels["raw"].append(score_episode(ep, lines, raw))
        levels["ocr_fix"].append(score_episode(ep, lines, [e.model_copy(update={"zh_raw": e.zh}) for e in fixed]))
        levels["fixes_accepted"].append(score_episode(
            ep, lines, [e.model_copy(update={"zh_raw": fixes.get(e.id, e.zh)}) for e in fixed]))
    out = {}
    for name, scores in levels.items():
        t = {k: sum(getattr(s, k) for s in scores) for k in ("lines", "exact", "chars", "char_errors", "missed",
                                                               "events", "junk")}
        out[name] = {**t, "line_accuracy": _pct(t["exact"], t["lines"]), "cer": _pct(t["char_errors"], t["chars"]),
                     "per_episode": {s.episode_id: {"accuracy": round(s.accuracy, 4), "cer": round(s.cer, 4),
                                                    "lines": s.lines} for s in scores},
                     "wrong": [w | {"episode": s.episode_id} for s in scores for w in s.wrong]}
    out["key"] = {k: len(v) for k, v in gold.key.items()}
    return out


def _decisions(work: Path) -> list[ScriptDecision]:
    return read_jsonl(work / "script_review.jsonl", ScriptDecision) if (work / "script_review.jsonl").is_file() else []


# -- 2. speaker / listener -----------------------------------------------------------------------

@dataclass
class SpeakerRow:
    episode: str
    event_id: str
    gold: str | None
    gold_listener: str | None
    category: str                     # known (in memory when the episode ran) | new | nobody
    listener_new: bool
    voice: str | None
    voice_status: str
    speaker: str | None
    listener: str | None


def speaker_rows(config: Config, paths: Paths, gold: Gold, system: Path) -> list[SpeakerRow]:
    al = gold.aliases.get
    cache: dict[str, set[str]] = {}
    rows = []
    for ep in gold.episodes:
        known = {al(c, c) for c in characters_at(paths.memory, gold.manifest["episodes"][ep].get("memory_at_run"),
                                                 cache)}
        lines = [x for x in _approved(gold.folder / ep) if not x.deleted]
        work = system / ep
        m = align(lines, _events(work))
        tr = {t.event_id: t for t in read_jsonl(work / "translations.jsonl", LineTranslation)}
        sp = {s.event_id: s for s in read_jsonl(work / "speakers.jsonl", SpeakerCandidates)} \
            if (work / "speakers.jsonl").is_file() else {}
        for x in lines:
            sid = m.get(x.event_id)
            t, s = tr.get(sid or ""), sp.get(sid or "")
            g = al(x.speaker, x.speaker) if x.speaker else None
            cat = "nobody" if g is None else ("known" if g in known else "new")
            voice = s.candidates[0][0] if s is not None and s.candidates else None
            rows.append(SpeakerRow(
                ep, x.event_id, g, al(x.listener, x.listener) if x.listener else None, cat,
                bool(x.listener) and al(x.listener, x.listener) not in known,
                al(voice, voice) if voice else None, s.status if s is not None else "missing",
                al(t.speaker, t.speaker) if t is not None and t.speaker else None,
                al(t.listener, t.listener) if t is not None and t.listener else None))
    return rows


def score_speakers(config: Config, paths: Paths, gold: Gold, system: Path) -> dict:
    rows = speaker_rows(config, paths, gold, system)
    auto = _auto_pattern(config)
    def mapping(pred: str) -> dict[str, str]:
        # only lines whose gold character was not in memory when the episode ran may pair an automatic id with it
        pairs = [(getattr(r, pred), r.gold) for r in rows if r.category == "new"]
        if pred == "speaker":
            pairs += [(r.listener, r.gold_listener) for r in rows if r.listener_new]
        ids = {p for p, _ in pairs if p and auto.match(p)}
        return group_map(pairs, ids, {g for _, g in pairs if g})

    tmap, vmap = mapping("speaker"), mapping("voice")

    def ok(pred: str | None, want: str | None, mp: dict[str, str]) -> bool:
        return (mp.get(pred, pred) if pred else None) == want

    out: dict = {"lines": len(rows), "grouped": {"translator": tmap, "voice": vmap}}
    for cat in ("all", "known", "new", "nobody"):
        sel = [r for r in rows if cat == "all" or r.category == cat]
        out[f"speaker_{cat}"] = _rate(sum(ok(r.speaker, r.gold, tmap) for r in sel), len(sel))
    lis = [r for r in rows if r.gold is not None]
    out["listener"] = _rate(sum(ok(r.listener, r.gold_listener, tmap) for r in lis), len(lis))
    voiced = [r for r in rows if r.voice_status not in ("too_short", "missing", "unknown")]
    out["voice_top1"] = _rate(sum(ok(r.voice, r.gold, vmap) for r in voiced), len(voiced))
    out["voice_by_status"] = {}
    for status in sorted({r.voice_status for r in rows}):
        sel = [r for r in rows if r.voice_status == status]
        out["voice_by_status"][status] = {"voice": _rate(sum(ok(r.voice, r.gold, vmap) for r in sel), len(sel)),
                                          "translator": _rate(sum(ok(r.speaker, r.gold, tmap) for r in sel), len(sel))}
    changed = [r for r in rows if r.voice_status in ("fixed", "new_voice") and r.speaker != r.voice]
    out["translator_overrode_sure_voice"] = {
        "lines": len(changed), "translator_right": sum(ok(r.speaker, r.gold, tmap) for r in changed),
        "voice_right": sum(ok(r.voice, r.gold, vmap) for r in changed)}
    out["per_episode"] = {ep: _rate(sum(ok(r.speaker, r.gold, tmap) for r in rows if r.episode == ep),
                                    sum(r.episode == ep for r in rows)) for ep in gold.episodes}
    out["wrong"] = [{"event_id": r.event_id, "gold": r.gold, "got": tmap.get(r.speaker, r.speaker) if r.speaker
                     else None, "voice": r.voice, "status": r.voice_status} for r in rows
                    if not ok(r.speaker, r.gold, tmap)]
    return out


# -- 3. character recognition --------------------------------------------------------------------

def gold_boxes(line: ReviewedLine, cast: CastLine) -> tuple[list[tuple[list[float], str]], list[float] | None]:
    """The checked line's boxes as the reviewer left them: (box, character | UNKNOWN | NOT_A_CHARACTER), and the
    talking box (None: nobody on screen talks). Mirrors sprite_learning.apply_review_edits."""
    from subagent.cast.card import shown_talking_box

    boxes = []
    for k, d in enumerate(cast.detections):
        label = line.cast_labels.get(str(k)) or d.character or UNKNOWN
        boxes.append([line.cast_boxes.get(str(k), d.box), label])
    for a in line.cast_added:
        boxes.append([a.box, a.character or UNKNOWN])
    talking = shown_talking_box(line, cast)
    if line.cast_talking and line.cast_talking != "none" and line.speaker and talking is not None:
        pos = int(line.cast_talking[1:]) + len(cast.detections) if line.cast_talking.startswith("a") \
            else int(line.cast_talking)
        if pos < len(boxes) and not line.cast_labels.get(str(pos)) and not (
                pos >= len(cast.detections) and line.cast_added[pos - len(cast.detections)].character):
            boxes[pos][1] = line.speaker               # the reviewer saw this box talk: it is the speaker
    return [(b, lab) for b, lab in boxes], talking


def _match(gold: list[list[float]], pred: list[list[float]]) -> dict[int, int]:
    pairs = sorted(((iou(g, p), i, j) for i, g in enumerate(gold) for j, p in enumerate(pred)), reverse=True)
    out: dict[int, int] = {}
    used: set[int] = set()
    for v, i, j in pairs:
        if v < BOX_IOU:
            break
        if i not in out and j not in used:
            out[i] = j
            used.add(j)
    return out


def score_cast(gold: Gold, system: Path) -> dict:
    al = gold.aliases.get
    c = Counter()
    for ep in gold.episodes:
        checked = [x for x in _approved(gold.folder / ep) if x.cast_checked and not x.deleted]
        if not checked or not (system / ep / "cast.jsonl").is_file():
            continue
        recorded = {ln.event_id: ln for ln in read_jsonl(gold.folder / ep / "cast.jsonl", CastLine)}
        m = align(checked, _events(system / ep))
        pred_lines = {ln.event_id: ln for ln in read_jsonl(system / ep / "cast.jsonl", CastLine)}
        for x in checked:
            if x.event_id not in recorded:
                continue
            c["lines"] += 1
            boxes, talking = gold_boxes(x, recorded[x.event_id])
            pred = pred_lines.get(m.get(x.event_id, ""), CastLine(event_id=x.event_id))
            real = [(b, al(lab, lab)) for b, lab in boxes if lab != NOT_A_CHARACTER]
            hit = _match([b for b, _ in real], [d.box for d in pred.detections])
            c["gold_boxes"] += len(real)
            c["found"] += len(hit)
            c["pred_boxes"] += len(pred.detections)
            for i, (_b, lab) in enumerate(real):
                if i not in hit:
                    continue
                got = pred.detections[hit[i]].character
                got = al(got, got) if got else None
                if lab == UNKNOWN:
                    c["unknown_boxes"] += 1
                    c["unknown_named"] += got is not None
                else:
                    c["named_boxes"] += 1
                    c["named_right" if got == lab else ("named_unrecognised" if got is None else "named_wrong")] += 1
            want_talk = talking
            got_talk = pred.detections[pred.talking].box if pred.talking is not None else None
            if want_talk is None:
                c["no_talker_lines"] += 1
                c["no_talker_right"] += got_talk is None
            else:
                c["talker_lines"] += 1
                c["talker_found"] += got_talk is not None and iou(want_talk, got_talk) >= BOX_IOU
                if x.speaker and got_talk is not None:
                    who = pred.detections[pred.talking].character
                    c["talker_named_speaker"] += (al(who, who) if who else None) == al(x.speaker, x.speaker)
    return {"lines": c["lines"],
            "box_recall": _rate(c["found"], c["gold_boxes"]),
            "box_precision": _rate(c["found"], c["pred_boxes"]),
            "names": _rate(c["named_right"], c["named_boxes"]),
            "names_unrecognised": c["named_unrecognised"], "names_wrong": c["named_wrong"],
            "unknown_boxes_named": {"named": c["unknown_named"], "of": c["unknown_boxes"]},
            "talker": _rate(c["talker_found"], c["talker_lines"]),
            "talker_is_speaker": _rate(c["talker_named_speaker"], c["talker_lines"]),
            "no_talker": _rate(c["no_talker_right"], c["no_talker_lines"])}


# -- 4. translation + evaluator ------------------------------------------------------------------

def _kept_evaluation(evals: list[Evaluation]) -> Evaluation | None:
    from subagent.translation.translate import rank_attempt

    return max(evals, key=rank_attempt) if evals else None


def score_translation(config: Config, gold: Gold, system: Path, speaker_ok: dict[str, bool] | None = None) -> dict:
    from subagent.kernel.textutil import found_terms

    terms = config.translate.pronoun_terms
    c = Counter()
    sims: dict[str, list[float]] = {"all": [], "rewritten": [], "speaker": [], "zh": [], "pure": []}
    ev_counts = Counter()
    for ep in gold.episodes:
        lines = [x for x in _approved(gold.folder / ep) if not x.deleted and x.vi.strip()]
        edits: dict[str, set[str]] = {}
        for e in read_jsonl(gold.folder / ep / "edits.jsonl", EditRecord):
            edits.setdefault(e.event_id, set()).add(e.field)
        work = system / ep
        m = align(lines, _events(work))
        tr = {t.event_id: t for t in read_jsonl(work / "translations.jsonl", LineTranslation)}
        evals: dict[str, list[Evaluation]] = {}
        for e in read_jsonl(work / "evaluations.jsonl", Evaluation) if (work / "evaluations.jsonl").is_file() else []:
            evals.setdefault(e.event_id, []).append(e)
        for x in lines:
            sid = m.get(x.event_id, "")
            t = tr.get(sid)
            got = t.vi if t is not None else ""
            sim = similarity(got, x.vi)
            same = _vi(got) == _vi(x.vi)
            c["lines"] += 1
            c["exact"] += same
            sims["all"].append(sim)
            fields = edits.get(x.event_id, set())
            if "vi" in fields:
                cause = "speaker" if fields & {"speaker", "listener"} else ("zh" if "zh" in fields else "pure")
                sims["rewritten"].append(sim)
                sims[cause].append(sim)
            want, have = set(found_terms(x.vi, terms)), set(found_terms(got, terms))
            if want or have:
                c["pronoun_lines"] += 1
                c["pronoun_same"] += want == have
            ev = _kept_evaluation(evals.get(sid, []))
            if ev is None:
                continue
            failed = not ev.passed
            doubt = failed or bool(ev.rule_failures) or any(v <= DOUBT_SCORE for v in ev.scores.values())
            group = "differs" if not same else "matches"
            ev_counts[f"{group}"] += 1
            ev_counts[f"{group}_failed"] += failed
            ev_counts[f"{group}_doubt"] += doubt
            if speaker_ok is not None and x.event_id in speaker_ok and "speaker" in ev.scores:
                wrong = not speaker_ok[x.event_id]
                k = "speaker_wrong" if wrong else "speaker_right"
                ev_counts[k] += 1
                ev_counts[f"{k}_flagged"] += ev.scores["speaker"] < config.evaluate.min_score
                ev_counts[f"{k}_doubt"] += ev.scores["speaker"] <= DOUBT_SCORE

    def mean(v: list[float]) -> float | None:
        return round(sum(v) / len(v), 4) if v else None

    return {"lines": c["lines"], "exact": _rate(c["exact"], c["lines"]),
            "similarity": {k: {"mean": mean(v), "lines": len(v)} for k, v in sims.items()},
            "pronouns_same": _rate(c["pronoun_same"], c["pronoun_lines"]),
            "evaluator": {
                "catch_failed": _rate(ev_counts["differs_failed"], ev_counts["differs"]),
                "catch_doubt": _rate(ev_counts["differs_doubt"], ev_counts["differs"]),
                "false_alarm_failed": _rate(ev_counts["matches_failed"], ev_counts["matches"]),
                "false_alarm_doubt": _rate(ev_counts["matches_doubt"], ev_counts["matches"]),
                "speaker_catch_failed": _rate(ev_counts["speaker_wrong_flagged"], ev_counts["speaker_wrong"]),
                "speaker_catch_doubt": _rate(ev_counts["speaker_wrong_doubt"], ev_counts["speaker_wrong"]),
                "speaker_false_alarm_failed": _rate(ev_counts["speaker_right_flagged"], ev_counts["speaker_right"]),
                "speaker_false_alarm_doubt": _rate(ev_counts["speaker_right_doubt"], ev_counts["speaker_right"])}}


# -- 5. script review ----------------------------------------------------------------------------

def score_script_review(config: Config, gold: Gold, system: Path) -> dict:
    from subagent.ocr_benchmark import gold_lines
    from subagent.review.review import original_draft

    rc = config.review
    c = Counter()
    by_source = Counter()
    by_source_right = Counter()
    for ep in gold.episodes:
        work = system / ep
        lines = _approved(gold.folder / ep)
        draft = {x.event_id: x for x in original_draft(work, rc.predelete_fragments, rc.noise_max_han)}
        m = align(lines, _events(work))
        zh_gold = {x.event_id: x.zh for x in gold_lines(gold.folder / ep, gold.key)}
        events = {e.id: e for e in _events(work)}
        decisions = {d.event_id: d for d in _decisions(work)}
        for x in lines:
            d = draft.get(m.get(x.event_id, ""))
            if d is None:
                continue
            c["lines"] += 1
            c["gold_deleted"] += x.deleted
            if d.deleted:
                source = next((f for f in d.flags if f in REMOVAL_FLAGS), "fragment")
                c["predeleted"] += 1
                c["predeleted_right"] += x.deleted
                by_source[source] += 1
                by_source_right[source] += x.deleted
            elif "script_suspect" in d.flags:
                c["flagged"] += 1
                c["flagged_deleted"] += x.deleted
                ev = events.get(d.event_id)
                c["flagged_zh_wrong"] += (not x.deleted and ev is not None and x.event_id in zh_gold
                                          and _norm(ev.zh) != _norm(zh_gold[x.event_id]))
            elif x.deleted:
                c["missed"] += 1
            dec = decisions.get(d.event_id)
            if dec is not None and dec.action == "fix" and dec.zh_fix and x.event_id in zh_gold:
                want = _norm(zh_gold[x.event_id])
                was = _norm(events[d.event_id].zh) if d.event_id in events else ""
                c["fixes"] += 1
                if _norm(dec.zh_fix) == want:
                    c["fixes_right"] += 1
                elif was == want:
                    c["fixes_harmful"] += 1
    return {"lines": c["lines"], "gold_deleted": c["gold_deleted"],
            "predelete_precision": _rate(c["predeleted_right"], c["predeleted"]),
            "predelete_recall": _rate(c["predeleted_right"], c["gold_deleted"]),
            "predeleted_by_source": {s: {"lines": n, "deleted_by_reviewer": by_source_right[s]}
                                     for s, n in sorted(by_source.items())},
            "flagged": {"lines": c["flagged"], "deleted_by_reviewer": c["flagged_deleted"],
                        "chinese_wrong": c["flagged_zh_wrong"]},
            "missed_deletions": c["missed"],
            "fixes": {"suggested": c["fixes"], "right": c["fixes_right"], "harmful": c["fixes_harmful"]}}


# -- whole suite ---------------------------------------------------------------------------------

@dataclass
class SuiteResult:
    label: str
    system: str
    baseline: str
    started_at: str
    episodes: list[str]
    ocr: dict = field(default_factory=dict)
    speakers: dict = field(default_factory=dict)
    cast: dict = field(default_factory=dict)
    translation: dict = field(default_factory=dict)
    script_review: dict = field(default_factory=dict)
    run: dict = field(default_factory=dict)          # what the harness ran (bench_run), empty for recorded output


def score(config: Config, paths: Paths, gold: Gold, system: Path, *, label: str = "recorded",
          run: dict | None = None) -> SuiteResult:
    r = SuiteResult(label, str(system), str(gold.folder), now_iso(), gold.episodes, run=run or {})
    r.ocr = score_ocr(gold, system)
    r.speakers = score_speakers(config, paths, gold, system)
    wrong = {w["event_id"] for w in r.speakers["wrong"]}
    speaker_ok = {row.event_id: row.event_id not in wrong
                  for row in speaker_rows(config, paths, gold, system) if row.gold is not None}
    r.cast = score_cast(gold, system)
    r.translation = score_translation(config, gold, system, speaker_ok)
    r.script_review = score_script_review(config, gold, system)
    return r


def save(paths: Paths, r: SuiteResult, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    atomic_write_text(folder / "report.md", render(r))
    atomic_write_text(folder / "summary.json", json.dumps(asdict(r), ensure_ascii=False, indent=1))
    append_jsonl(paths.work / FOLDER / "history.jsonl", {"label": r.label, "at": r.started_at, "folder": str(folder),
                                                         "episodes": r.episodes, **headline(r)})
    return folder


def headline(r: SuiteResult) -> dict:
    """The few numbers a run is compared by (history.jsonl)."""
    return {
        "ocr_raw": r.ocr["raw"]["line_accuracy"], "ocr_fixed": r.ocr["ocr_fix"]["line_accuracy"],
        "ocr_cer": r.ocr["raw"]["cer"], "speaker": r.speakers["speaker_all"]["share"],
        "speaker_known": r.speakers["speaker_known"]["share"], "speaker_new": r.speakers["speaker_new"]["share"],
        "listener": r.speakers["listener"]["share"], "voice_top1": r.speakers["voice_top1"]["share"],
        "cast_names": r.cast["names"]["share"], "talker": r.cast["talker"]["share"],
        "vi_similarity": r.translation["similarity"]["all"]["mean"],
        "evaluator_catch": r.translation["evaluator"]["catch_failed"]["share"],
        "evaluator_false_alarm": r.translation["evaluator"]["false_alarm_failed"]["share"],
        "predelete_precision": r.script_review["predelete_precision"]["share"],
        "cost": r.run.get("cost")}


def _r(d: dict) -> str:
    if not d or not d.get("of"):
        return "n/a"
    return f"{d['share']:.1%} ({d['right']}/{d['of']}; 95%: {d['low']:.0%}–{d['high']:.0%})"


def render(r: SuiteResult) -> str:
    o, s, c, t, sr = r.ocr, r.speakers, r.cast, r.translation, r.script_review
    ev = t["evaluator"]
    out = [f"# Benchmark suite: {r.label}", "",
           f"System: `{r.system}` · gold: `{r.baseline}` · {len(r.episodes)} episodes · {r.started_at}", ""]
    if r.run:
        out += [f"Run: mode {r.run.get('mode')}, from stage {r.run.get('from_stage')}, "
                f"cost ${r.run.get('cost', 0):.4f}", ""]
    out += ["## 1. OCR / Chinese", "",
            f"Answer key: {o['key'].get('corrections', 0)} corrections, {o['key'].get('excluded', 0)} excluded. The reviewer "
            "corrected the Chinese the pipeline gave them, so the levels after raw OCR lean towards the recorded "
            "output; compare runs with each other.", "",
            "| Level | Lines right | CER | Missed | Junk events |", "|---|---|---|---|---|"]
    for name in ("raw", "ocr_fix", "fixes_accepted"):
        x = o[name]
        out.append(f"| {name} | {x['line_accuracy']:.1%} ({x['exact']}/{x['lines']}) | {x['cer']:.2%} | "
                   f"{x['missed']} | {x['junk']} / {x['events']} |")
    out += ["", "## 2. Speaker / listener", "",
            f"- Translator speaker, all lines: {_r(s['speaker_all'])}",
            f"  - known characters (in memory when the episode ran): {_r(s['speaker_known'])}",
            f"  - new (automatic ids, candidates, created in review; grouped): {_r(s['speaker_new'])}",
            f"  - nobody (gold blank): {_r(s['speaker_nobody'])}",
            f"- Listener (lines with a speaker): {_r(s['listener'])}",
            f"- Voice match first candidate (lines with a usable voice): {_r(s['voice_top1'])}",
            f"- Translator overrode a sure voice: {s['translator_overrode_sure_voice']['lines']} lines, translator "
            f"right {s['translator_overrode_sure_voice']['translator_right']}, voice right "
            f"{s['translator_overrode_sure_voice']['voice_right']}", "",
            "| Voice status | Voice right | Translator right |", "|---|---|---|"]
    for status, v in s["voice_by_status"].items():
        out.append(f"| {status} | {_r(v['voice'])} | {_r(v['translator'])} |")
    out += ["", "## 3. Character recognition (On screen checked lines)", "",
            f"{c['lines']} lines.", "",
            f"- Boxes found (recall): {_r(c['box_recall'])}",
            f"- Boxes that are characters (precision): {_r(c['box_precision'])}",
            f"- Named right: {_r(c['names'])}; unrecognised {c['names_unrecognised']}, wrong name {c['names_wrong']}",
            f"- Boxes left unrecognised by the reviewer that the system named: {c['unknown_boxes_named']['named']} "
            f"of {c['unknown_boxes_named']['of']}",
            f"- Talking sprite found: {_r(c['talker'])}; it names the speaker: {_r(c['talker_is_speaker'])}",
            f"- Nobody talking on screen, system agrees: {_r(c['no_talker'])}", "",
            "## 4. Translation + evaluator", "",
            f"- Same as the approved Vietnamese: {_r(t['exact'])}",
            "- Similarity to the approved Vietnamese: " + ", ".join(
                f"{k} {v['mean']:.3f} ({v['lines']})" for k, v in t["similarity"].items() if v["mean"] is not None),
            f"- Pronoun terms the same: {_r(t['pronouns_same'])}", "",
            "| Evaluator | Catch rate (line differs from gold) | False alarms (line matches gold) |", "|---|---|---|",
            f"| failed | {_r(ev['catch_failed'])} | {_r(ev['false_alarm_failed'])} |",
            f"| doubt (failed or a score <= {DOUBT_SCORE}) | {_r(ev['catch_doubt'])} | {_r(ev['false_alarm_doubt'])} |",
            f"| speaker score failed | {_r(ev['speaker_catch_failed'])} | {_r(ev['speaker_false_alarm_failed'])} |",
            f"| speaker score <= {DOUBT_SCORE} | {_r(ev['speaker_catch_doubt'])} | "
            f"{_r(ev['speaker_false_alarm_doubt'])} |", "",
            "## 5. Script review", "",
            f"{sr['lines']} lines, {sr['gold_deleted']} deleted by the reviewer.", "",
            f"- Pre-deleted lines the reviewer kept deleted (precision): {_r(sr['predelete_precision'])}",
            f"- Reviewer deletions pre-deleted (recall): {_r(sr['predelete_recall'])}",
            "- By source: " + ", ".join(f"{k} {v['deleted_by_reviewer']}/{v['lines']}"
                                        for k, v in sr["predeleted_by_source"].items()),
            f"- Flagged lines: {sr['flagged']['lines']}, deleted by the reviewer {sr['flagged']['deleted_by_reviewer']}, "
            f"Chinese wrong {sr['flagged']['chinese_wrong']}",
            f"- Deletions neither pre-deleted nor flagged: {sr['missed_deletions']}",
            f"- OCR fixes suggested: {sr['fixes']['suggested']}, right {sr['fixes']['right']}, harmful "
            f"{sr['fixes']['harmful']}", "",
            "## Per episode", "", "| Episode | OCR raw | Speaker |", "|---|---|---|"]
    for ep in r.episodes:
        oe = o["raw"]["per_episode"].get(ep, {})
        se = s["per_episode"].get(ep, {})
        out.append(f"| {ep} | {oe.get('accuracy', 0):.1%} | {_r(se)} |")
    out += ["", "## Wrong speakers", "", "| Line | Gold | System | Voice (status) |", "|---|---|---|---|"]
    for w in s["wrong"]:
        out.append(f"| {w['event_id']} | {w['gold'] or '—'} | {w['got'] or '—'} | {w['voice'] or '—'} ({w['status']}) |")
    return "\n".join(out) + "\n"
