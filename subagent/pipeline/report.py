"""Per-episode metrics, report.md and episode status (5.20)."""

from __future__ import annotations

import logging
from collections import Counter
from pathlib import Path

from subagent.kernel import (
    CostRecord,
    EditRecord,
    Episode,
    Evaluation,
    LineTranslation,
    ReviewedLine,
    SpeakerCandidates,
    SubtitleEvent,
    atomic_write_text,
    now_iso,
    read_json,
    read_jsonl,
)
from subagent.llm import record_cost
from subagent.pipeline.stages import STAGE_NAMES
from subagent.settings import Paths
from subagent.workspace import EpisodeContext, load_state

log = logging.getLogger(__name__)


# -- report / status -------------------------------------------------------------------------------

def collect_metrics(work: Path, episode_id: str, prices: dict | None = None) -> dict:
    state = load_state(work, episode_id)
    costs = read_jsonl(work / "cost.jsonl", CostRecord)
    speakers = read_jsonl(work / "speakers.jsonl", SpeakerCandidates)
    evaluations = read_jsonl(work / "evaluations.jsonl", Evaluation)
    translations = read_jsonl(work / "translations.jsonl", LineTranslation)
    events = read_jsonl(work / "events.jsonl", SubtitleEvent) or read_jsonl(work / "events_raw.jsonl", SubtitleEvent)
    approved = read_jsonl(work / "approved.jsonl", ReviewedLine)
    edits = read_jsonl(work / "edits.jsonl", EditRecord)
    sprite = read_json(work / "sprite.json", []) or []

    prices = prices or {}
    by_role: dict[str, dict[str, float]] = {}
    by_task: dict[str, dict[str, float]] = {}
    unpriced: set[str] = set()
    cost_total = 0.0
    def tally(table: dict[str, dict[str, float]], key: str, c: CostRecord, cost: float) -> None:
        r = table.setdefault(key, {"calls": 0, "cost": 0.0, "prompt": 0, "cache_hit": 0, "completion": 0,
                                   "disk_cache_hits": 0})
        r["calls"] += 1
        r["cost"] += cost
        r["prompt"] += c.prompt_tokens
        r["cache_hit"] += c.cache_hit_tokens
        r["completion"] += c.completion_tokens
        r["disk_cache_hits"] += int(c.cached_response)

    for c in costs:
        cost = record_cost(c, prices)
        if cost is None:
            unpriced.add(c.model)
            cost = 0.0
        cost_total += cost
        tally(by_role, c.role, c, cost)
        tally(by_task, c.task or c.role, c, cost)   # calls recorded before agents were tagged show their role
    prompt_total = sum(c.prompt_tokens for c in costs)
    first = [e for e in evaluations if e.attempt == 1]
    flags: Counter[str] = Counter()
    for e in events:
        flags.update(e.flags)
    for t in translations:
        flags.update(t.flags)
    return {
        "state": state,
        "cost_total": cost_total,
        "unpriced_models": sorted(unpriced),
        "cost_by_role": by_role,
        "cost_by_task": by_task,
        "cache_hit_share": (sum(c.cache_hit_tokens for c in costs) / prompt_total) if prompt_total else 0.0,
        "voice_status": Counter(s.status for s in speakers),
        "events": len(events),
        "first_pass_rate": (sum(e.passed for e in first) / len(first)) if first else None,
        "retry_rate": (sum(1 for t in translations if t.attempts > 1) / len(translations)) if translations else None,
        "flags": flags,
        "sprite_triggered": len(sprite),
        "sprite_resolved": sum(1 for s in sprite if s.get("result") == "resolved"),
        "edit_rate": (len({e.event_id for e in edits}) / len(approved)) if approved else None,
        "edits": len(edits),
    }


# Agents (LLM tasks) as named in reports; calls recorded before tasks existed show their role instead.
AGENT_NAMES = {"translate": "Translator", "evaluate": "Evaluator", "script_review": "Script reviewer",
               "ocr_fix": "OCR correction", "pinyin": "Pinyin (polyphones)", "briefing": "Memory briefing",
               "bootstrap": "Bootstrap", "dreaming": "Dreaming"}


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v * 100:.1f}%"


def write_report(ctx: EpisodeContext) -> Path:
    m = collect_metrics(ctx.work, ctx.episode.id, ctx.config.llm.prices)
    state = m["state"]
    lines = [f"# Report {ctx.episode.id}", "", f"Source: `{ctx.episode.source_path}`",
             f"Generated: {now_iso()}", f"Mode: {state.mode or '-'}", "", "## Stage timings", "",
             "| stage | status | seconds | counts |", "|---|---|---|---|"]
    for name in STAGE_NAMES:
        st = state.stages.get(name)
        if st:
            lines.append(f"| {name} | {st.status} | {st.duration_s:.1f} | {counts_text(st.counts)} |")
    lines += ["", "## Cost", "", f"Total: ${m['cost_total']:.4f} (budget ${ctx.config.budget.max_cost_per_episode:.2f})",
              f"Provider cache-hit share of input tokens: {_pct(m['cache_hit_share'])}", ""]
    if m["unpriced_models"]:
        lines += [f"**Incomplete:** no price configured for {', '.join(m['unpriced_models'])}; their calls are not "
                  "included above. Add them under `llm.prices` in config.yaml (USD per 1M tokens); past calls are "
                  "then priced from their recorded tokens.", ""]
    lines += [
              "| role | calls | disk-cache hits | prompt tokens | cache-hit tokens | completion tokens | cost |",
              "|---|---|---|---|---|---|---|"]
    for role, r in sorted(m["cost_by_role"].items()):
        lines.append(f"| {role} | {int(r['calls'])} | {int(r['disk_cache_hits'])} | {int(r['prompt'])} | "
                     f"{int(r['cache_hit'])} | {int(r['completion'])} | ${r['cost']:.4f} |")
    lines += ["", "### Cost by agent", "",
              "| agent | calls | disk-cache hits | prompt tokens | completion tokens | cost |", "|---|---|---|---|---|---|"]
    for task, r in sorted(m["cost_by_task"].items(), key=lambda kv: -kv[1]["cost"]):
        lines.append(f"| {AGENT_NAMES.get(task, task)} | {int(r['calls'])} | {int(r['disk_cache_hits'])} | "
                     f"{int(r['prompt'])} | {int(r['completion'])} | ${r['cost']:.4f} |")
    total_voice = sum(m["voice_status"].values())
    lines += ["", "## Voice match", ""]
    for status in ("fixed", "confusable", "unknown", "too_short", "new_voice"):
        n = m["voice_status"].get(status, 0)
        lines.append(f"- {status}: {n} ({_pct(n / total_voice if total_voice else None)})")
    lines += ["", "## Quality", "",
              f"- Events: {m['events']}",
              f"- Evaluator pass rate on first attempt: {_pct(m['first_pass_rate'])}",
              f"- Retry rate: {_pct(m['retry_rate'])}",
              f"- Sprite check: triggered {m['sprite_triggered']}, resolved {m['sprite_resolved']}",
              f"- Human edit rate: {_pct(m['edit_rate'])} ({m['edits']} field edits)",
              f"- Non-dialogue suspects: {m['flags'].get('non_dialogue_suspect', 0)}",
              "", "## Flags", ""]
    for flag, n in m["flags"].most_common():
        lines.append(f"- {flag}: {n}")
    flagged = [t for t in read_jsonl(ctx.artifact("translations.jsonl"), LineTranslation) if t.flags]
    if flagged:
        lines += ["", "## Flagged lines", ""]
        for t in flagged:
            lines.append(f"- `{t.event_id}` [{', '.join(t.flags)}] {t.vi}")
    path = ctx.artifact("report.md")
    atomic_write_text(path, "\n".join(lines) + "\n")
    return path


def episode_status(paths: Paths, episode: Episode, prices: dict | None = None) -> dict:
    work = paths.episode_dir(episode.id)
    m = collect_metrics(work, episode.id, prices)
    stages = {name: (m["state"].stages[name].status if name in m["state"].stages else "pending")
              for name in STAGE_NAMES if name != "report"}
    return {
        "id": episode.id, "number": episode.number, "status": episode.status, "source": episode.source_path,
        "output": episode.output_path, "stages": stages, "cost": round(m["cost_total"], 4),
        "cost_complete": not m["unpriced_models"], "unpriced_models": m["unpriced_models"],
        "cost_by_agent": {task: round(r["cost"], 6) for task, r in m["cost_by_task"].items()},
        "flags": dict(m["flags"]), "flag_total": sum(m["flags"].values()),
    }


def counts_text(counts: dict[str, int]) -> str:
    return ", ".join(f"{k}={v}" for k, v in counts.items())
