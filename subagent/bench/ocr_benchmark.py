"""OCR benchmark (6.11c): raw OCR text scored against the Chinese of human-reviewed episodes.

The reviewer's approved Chinese is the answer key. A run regenerates the subtitle bands and reruns OCR and
event building in a sandbox (`<work>/_ocr_benchmark/<timestamp>-<label>/`) with today's code and config; no LLM
is called, nothing real is touched. `existing=True` scores the OCR already on disk instead (instant; that is
what the episodes were translated from).

Lines are matched by time: each approved, non-deleted line takes the event overlapping it most. Scores:
- line accuracy: share of lines whose raw OCR text equals the approved text (punctuation and spaces ignored);
- character error rate: edit distance over approved characters (a missed line counts all its characters);
- junk events: events that overlap no approved line for at least half their time (on-screen props, numbers,
  fragments: what the reviewer deleted or the script review had to remove).

Answer key: the approved Chinese is not always what is on screen (about 7% of lines kept OCR errors; some were
changed on purpose). `<work>/_ocr_benchmark/answer_key.json` corrects them ("corrections": event id -> on-screen
text) and leaves out lines that cannot be checked ("excluded": event id -> reason). Traditional and simplified
variants of a character count as equal (VARIANTS).
"""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from subagent.kernel.models import ReviewedLine, SubtitleEvent
from subagent.kernel.textutil import edit_distance, keep_cjk, normalize_zh
from subagent.kernel.util import append_jsonl, atomic_write_text, now_iso, read_jsonl
from subagent.settings.config import Config, Paths
from subagent.workspace.state import load_state

STAGES = ("ingest", "ocr", "events")
KEY_FILE = "answer_key.json"
# the OCR model returns some characters in their traditional form; scoring treats them as the same character
VARIANTS = str.maketrans("別爭沒將脫掙靜眞黃屆戸個說這們麼會來對時見淨溫題決懶臥", "别争没将脱挣静真黄届户个说这们么会来对时见净温题决懒卧")
FOLDER = "_ocr_benchmark"
KEEP = ("events_raw.jsonl", "ocr_raw.jsonl", "ocr_samples", "video.json")   # the rest of a sandbox is deleted


@dataclass
class EpisodeOcrScore:
    episode_id: str
    lines: int = 0
    exact: int = 0
    chars: int = 0
    char_errors: int = 0
    missed: int = 0
    events: int = 0
    junk: int = 0
    wrong: list[dict] = field(default_factory=list)       # {event_id, gold, got}

    @property
    def accuracy(self) -> float:
        return self.exact / self.lines if self.lines else 0.0

    @property
    def cer(self) -> float:
        return self.char_errors / self.chars if self.chars else 0.0


@dataclass
class OcrBenchResult:
    label: str
    started_at: str
    folder: str
    existing: bool
    episodes: list[EpisodeOcrScore] = field(default_factory=list)
    key: dict = field(default_factory=dict)            # answer key size: corrections, excluded

    def total(self) -> EpisodeOcrScore:
        t = EpisodeOcrScore("all")
        for e in self.episodes:
            for k in ("lines", "exact", "chars", "char_errors", "missed", "events", "junk"):
                setattr(t, k, getattr(t, k) + getattr(e, k))
        return t


def remap_ids(old: dict[str, tuple[int, int]], new_events: list[SubtitleEvent]) -> dict[str, str]:
    """Old event id -> the new event overlapping its time most (events are renumbered when OCR runs again)."""
    out = {}
    for eid, (start, end) in old.items():
        best = max(new_events, key=lambda e: _overlap(start, end, e.start_ms, e.end_ms), default=None)
        if best is not None and _overlap(start, end, best.start_ms, best.end_ms) > 0:
            out[eid] = best.id
    return out


def remap_key(paths: Paths, archive: Path) -> tuple[dict, list[str]]:
    """Move the answer key in `archive` (answer_key.json + each episode's old events.jsonl, as archived before a
    re-run) onto today's event ids, and save it as the current key. Returns the key and the ids that found no
    new event (left out).

    Several old events can land on one new line (fragments merged by the new OCR). An exclusion moves only when
    the old excluded events together cover at least half of the new line: one about a fragment ("the sampled
    frame shows the previous line") says nothing about the whole line. Corrections that disagree keep the one
    whose old event overlaps the new line most. Both are listed in the key's `remapped` note."""
    key = json.loads((archive / KEY_FILE).read_text(encoding="utf-8"))
    lost: list[str] = []
    mapping: dict[str, str] = {}
    old_span: dict[str, tuple[int, int]] = {}
    new_span: dict[str, tuple[int, int]] = {}
    episodes = {eid.split(":")[0] for part in ("corrections", "excluded") for eid in key.get(part, {})}
    for ep in sorted(episodes):
        old = {e.id: (e.start_ms, e.end_ms) for e in read_jsonl(archive / ep / "events.jsonl", SubtitleEvent)}
        events = read_jsonl(paths.episode_dir(ep) / "events.jsonl", SubtitleEvent)
        old_span.update(old)
        new_span.update({e.id: (e.start_ms, e.end_ms) for e in events})
        mapping.update(remap_ids(old, events))
    new = {k: v for k, v in key.items() if k not in ("corrections", "excluded", "remapped")}
    dropped: list[str] = []
    conflicts: list[str] = []
    best: dict[str, int] = {}
    new["corrections"] = {}
    for eid, value in key.get("corrections", {}).items():
        if eid not in mapping:
            lost.append(eid)
            continue
        target = mapping[eid]
        overlap = _overlap(*old_span[eid], *new_span[target])
        if target in new["corrections"] and new["corrections"][target] != value:
            conflicts.append(eid)
            if overlap <= best[target]:
                continue
        new["corrections"][target] = value
        best[target] = max(best.get(target, 0), overlap)
    groups: dict[str, list[str]] = {}
    for eid in key.get("excluded", {}):
        if eid in mapping:
            groups.setdefault(mapping[eid], []).append(eid)
        else:
            lost.append(eid)
    new["excluded"] = {}
    for target, eids in groups.items():
        start, end = new_span[target]
        covered = _covered(start, end, [old_span[e] for e in eids])
        if covered * 2 >= max(1, end - start):
            new["excluded"][target] = key["excluded"][eids[0]]
        else:
            dropped.extend(eids)
    new["remapped"] = {"from": str(archive), "at": now_iso(), "lost": lost,
                       "exclusions_dropped": dropped, "conflicting_corrections": conflicts}
    out = paths.work / FOLDER / KEY_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(out, json.dumps(new, ensure_ascii=False, indent=1))
    return new, lost


def _covered(start: int, end: int, spans: list[tuple[int, int]]) -> int:
    """Milliseconds of [start, end) covered by the union of spans."""
    total, reach = 0, start
    for a, b in sorted(spans):
        a, b = max(a, reach), min(b, end)
        if b > a:
            total += b - a
            reach = b
    return total


def load_key(paths: Paths) -> dict:
    path = paths.work / FOLDER / KEY_FILE
    if not path.is_file():
        return {"corrections": {}, "excluded": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"corrections": data.get("corrections", {}), "excluded": data.get("excluded", {})}


def gold_lines(work: Path, key: dict | None = None) -> list[ReviewedLine]:
    """Approved, non-deleted lines, with the answer key's corrections applied and its exclusions left out."""
    key = key or {"corrections": {}, "excluded": {}}
    out = []
    for x in read_jsonl(work / "approved.jsonl", ReviewedLine):
        if not x.approved or x.deleted or x.event_id in key["excluded"]:
            continue
        if x.event_id in key["corrections"]:
            x = x.model_copy(update={"zh": key["corrections"][x.event_id]})
        out.append(x)
    return out


def ocr_episodes(paths: Paths) -> list[str]:
    """Human-reviewed, finished episodes: their approved Chinese was checked by a person."""
    from subagent.workspace.episodes import Registry

    out = []
    for ep in sorted(Registry(paths).load(), key=lambda e: e.number):
        work = paths.episode_dir(ep.id)
        if (work / "approved.jsonl").is_file() and load_state(work, ep.id).mode == "human":
            out.append(ep.id)
    return out


def _norm(text: str) -> str:
    """Comparison form, filtered like OCR output (5.4) so punctuation never counts."""
    return keep_cjk(normalize_zh(text)).translate(VARIANTS)


def _overlap(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0))


def score_episode(episode_id: str, gold: list[ReviewedLine], events: list[SubtitleEvent]) -> EpisodeOcrScore:
    s = EpisodeOcrScore(episode_id, events=len(events))
    for g in gold:
        want = _norm(g.zh)
        if not want:
            continue
        s.lines += 1
        s.chars += len(want)
        best = max(events, key=lambda e: _overlap(g.start_ms, g.end_ms, e.start_ms, e.end_ms), default=None)
        if best is None or _overlap(g.start_ms, g.end_ms, best.start_ms, best.end_ms) == 0:
            s.missed += 1
            s.char_errors += len(want)
            s.wrong.append({"event_id": g.event_id, "gold": g.zh, "got": None})
            continue
        got = _norm(best.zh_raw)
        if got == want:
            s.exact += 1
        else:
            s.char_errors += edit_distance(got, want)
            s.wrong.append({"event_id": g.event_id, "gold": g.zh, "got": best.zh_raw})
    for e in events:
        covered = max((_overlap(e.start_ms, e.end_ms, g.start_ms, g.end_ms) for g in gold), default=0)
        if covered * 2 < max(1, e.end_ms - e.start_ms):
            s.junk += 1
    return s


def _existing_events(work: Path) -> list[SubtitleEvent]:
    name = "events_raw.jsonl" if (work / "events_raw.jsonl").is_file() else "events.jsonl"
    return read_jsonl(work / name, SubtitleEvent)


def run_ocr_benchmark(config: Config, paths: Paths, episode_ids: list[str] | None = None, *, label: str = "",
                      existing: bool = False, progress=None, stage_runner=None) -> OcrBenchResult:
    """stage_runner(name, ctx) runs one stage (tests inject fakes); default: the real stage modules."""
    from subagent.bench.benchmark import _sandbox_paths
    from subagent.pipeline import run_stage
    from subagent.workspace.context import EpisodeContext
    from subagent.workspace.episodes import Registry

    episode_ids = episode_ids or ocr_episodes(paths)
    stamp = now_iso().replace(":", "").replace("-", "")[:15]
    folder = paths.work / FOLDER / f"{stamp}-{label or ('existing' if existing else 'run')}"
    result = OcrBenchResult(label=label or ("existing" if existing else "run"), started_at=now_iso(),
                            folder=str(folder), existing=existing)
    cfg, sandbox = _sandbox_paths(config, paths, folder)
    registry = Registry(paths)
    run = stage_runner or run_stage
    key = load_key(paths)
    result.key = {k: len(v) for k, v in key.items()}
    for n, ep_id in enumerate(episode_ids, 1):
        gold = gold_lines(paths.episode_dir(ep_id), key)
        if not gold:
            continue
        if progress:
            progress.emit("ocr_benchmark", "progress", done=n - 1, total=len(episode_ids), message=ep_id)
        if existing:
            events = _existing_events(paths.episode_dir(ep_id))
        else:
            ctx = EpisodeContext(cfg, sandbox, registry.get(ep_id))
            ctx.work.mkdir(parents=True, exist_ok=True)
            for stage in STAGES:
                run(stage, ctx)
            events = read_jsonl(ctx.work / "events_raw.jsonl", SubtitleEvent)
            for p in ctx.work.iterdir():                      # bands are large; keep only the small results
                if p.name not in KEEP:
                    shutil.rmtree(p) if p.is_dir() else p.unlink()
        result.episodes.append(score_episode(ep_id, gold, events))
    folder.mkdir(parents=True, exist_ok=True)
    atomic_write_text(folder / "report.md", render(result))
    total = result.total()
    summary = {"label": result.label, "started_at": result.started_at, "existing": existing,
               "episodes": [e.episode_id for e in result.episodes], "lines": total.lines,
               "line_accuracy": round(total.accuracy, 4), "cer": round(total.cer, 4), "missed": total.missed,
               "junk_events": total.junk, "events": total.events}
    atomic_write_text(folder / "summary.json", json.dumps(
        {**summary, "per_episode": [asdict(e) for e in result.episodes]}, ensure_ascii=False, indent=1))
    append_jsonl(paths.work / FOLDER / "history.jsonl", summary)
    return result


def render(r: OcrBenchResult) -> str:
    t = r.total()
    out = [f"# OCR benchmark: {r.label}", "",
           f"{'OCR already on disk' if r.existing else 'Fresh OCR in a sandbox'}, {len(r.episodes)} human-reviewed "
           f"episodes, {t.lines} approved lines ({t.chars} characters).",
           (f"Answer key: {r.key.get('corrections', 0)} lines corrected to the on-screen text, "
            f"{r.key.get('excluded', 0)} left out." if r.key.get("corrections") or r.key.get("excluded")
            else "No answer key: scored against the approved Chinese as it is."), "",
           f"- Line accuracy: **{t.accuracy:.1%}** ({t.exact}/{t.lines})",
           f"- Character error rate: **{t.cer:.2%}** ({t.char_errors} errors)",
           f"- Missed lines (no OCR event): {t.missed}",
           f"- Junk events (no approved line under them): **{t.junk}** of {t.events}", "",
           "| Episode | Lines | Accuracy | CER | Missed | Junk / events |", "|---|---|---|---|---|---|"]
    for e in r.episodes:
        out.append(f"| {e.episode_id} | {e.lines} | {e.accuracy:.1%} | {e.cer:.2%} | {e.missed} | {e.junk} / {e.events} |")
    out += ["", "## Wrong lines", "", "| Line | Approved | OCR |", "|---|---|---|"]
    for e in r.episodes:
        for w in e.wrong:
            out.append(f"| {w['event_id']} | {w['gold']} | {w['got'] if w['got'] is not None else '(missed)'} |")
    return "\n".join(out) + "\n"
