"""Memory commands: bootstrap, dreaming, voice and sprite learning (5.17, 5.18, 5.8a, 5.8b)."""

from __future__ import annotations

import json
import logging

from subagent.cli.common import (  # noqa: F401
    ON_EXISTS_CHOICES,
    _ask,
    _interactive,
    _output_exists,
    _resolve_on_exists,
    build_pipeline,
)

log = logging.getLogger("subagent")


def cmd_bootstrap(args, config, paths, progress) -> int:
    from subagent.joblock import job_lock
    from subagent.llm import LLMClient
    from subagent.memory import bootstrap

    with job_lock(paths, "bootstrap"):
        if args.approve:
            progress.emit("bootstrap", "start", message="writing the seed to memory")
            result = bootstrap.approve_seed(config, paths)
            progress.emit("bootstrap", "done", message=f"{result.writes} writes")
            print(f"memory seeded: {result.writes} writes, {len(result.rejected)} rejected")
            for key, reason in result.rejected:
                print(f"  rejected {key}: {reason}")
            return 0
        if args.voices:
            progress.emit("bootstrap", "start", message="recomputing voices")
            counts = bootstrap.update_voices(config, paths, set(args.voices))
            progress.emit("bootstrap", "done", message=json.dumps(counts))
            print(f"voices updated: {counts}")
            return 0
        progress.emit("bootstrap", "start", message="drafting the seed")
        llm = LLMClient(config, paths, cost_path=paths.work / "_bootstrap" / "cost.jsonl", use_cache=not args.no_cache,
                        on_cost=progress.set_cost)
        draft = bootstrap.generate_seed(config, paths, llm)
        progress.emit("bootstrap", "done", message=f"{len(draft.characters)} characters")
        print(f"seed draft written to {bootstrap.seed_path(paths)}: {len(draft.characters)} characters, "
              f"{len(draft.pronoun_pairs)} pronoun pairs, {len(draft.glossary)} glossary terms, "
              f"{len(draft.voices)} voices, {len(draft.confusable_pairs)} confusable pairs")
        for w in draft.warnings:
            print(f"  warning: {w}")
        print("Review it (app Bootstrap screen, or edit the JSON), then run: python -m subagent bootstrap --approve")
        return 0


def cmd_dream(args, config, paths, progress) -> int:
    from subagent.joblock import job_lock
    from subagent.llm import LLMClient
    from subagent.memory import dreaming

    with job_lock(paths, "dream"):
        progress.emit("dream", "start")
        llm = LLMClient(config, paths, cost_path=paths.work / "_dream" / "cost.jsonl", use_cache=not args.no_cache,
                        on_cost=progress.set_cost)
        out = dreaming.dream(config, paths, llm)
        progress.emit("dream", "done", message=f"{len(out.items)} proposals")
        print(f"{len(out.items)} proposals written to data/memory/dream_proposals.json")
        if out.inputs.get("previously_rejected"):
            print(f"  ({out.inputs['previously_rejected']} proposals you rejected before were left out)")
        for item in out.items:
            mark = "locked, preselected reject" if item.touches_locked else "preselected accept"
            print(f"  [{item.id}] {item.proposal.kind} {item.key} ({mark}) {item.reason}")
        if args.auto_apply:
            result = dreaming.apply_dream(config, paths, auto=True)
            print(f"auto-applied: {result.writes} writes, {len(result.rejected)} rejected, "
                  f"{len(result.conflicts)} conflicts")
    return 0


def cmd_voices(args, config, paths, progress) -> int:
    from subagent.joblock import job_lock
    from subagent.memory import voice_learning as vl

    with job_lock(paths, "voices"):
        if args.action == "evaluate":
            progress.emit("voices", "start", message="leave-one-episode-out evaluation")
            r = vl.evaluate(config, paths)
            progress.emit("voices", "done")
            if not r.lines:
                print("Nothing to evaluate: needs at least two reviewed episodes with speakers.")
                return 1
            print(f"reviewed lines tested: {r.lines}")
            print(f"best voice = your speaker: {r.top1} ({r.top1 / r.lines:.0%}) | in top 3: {r.top3} ({r.top3 / r.lines:.0%})")
            for ep, (ok, n) in sorted(r.by_episode.items()):
                print(f"  {ep}: {ok}/{n} ({ok / max(1, n):.0%})")
            print("with the current thresholds (status: correct / lines):")
            for status, (ok, n) in sorted(r.statuses.items()):
                print(f"  {status:<11} {ok}/{n}")
            print("threshold sweep (accept_score, min_margin -> precision of 'fixed', share of lines fixed):")
            for accept, margin, prec, cov in r.sweep:
                print(f"  accept {accept:.2f} margin {margin:.2f} -> precision {prec:.0%}, coverage {cov:.0%}")
            return 0
        progress.emit("voices", "start", message="learning voices from reviewed episodes")
        r = vl.learn_voices(config, paths)
        progress.emit("voices", "done", message=f"{len(r.voices)} voices")
        print(f"voices learned from {r.lines_used} reviewed lines in {', '.join(r.episodes) or 'no episodes'}:")
        for char, n in sorted(r.voices.items(), key=lambda kv: -kv[1]):
            print(f"  {char:<16} {n} samples")
        for char, n in sorted(r.skipped.items()):
            print(f"  {char:<16} not learned ({n} samples, needs {config.voice.learn_min_clips})")
        for (a, b), sim in sorted(r.confusable.items(), key=lambda kv: -kv[1]):
            print(f"  confusable: {a} ~ {b} ({sim:.2f})")
        if r.auto:
            print(f"auto-mode lines: {r.auto.offered} passed the filter, "
                  f"{'used' if r.auto.accepted else 'not used'} ({r.auto.reason})")
        return 0


def cmd_sprites(args, config, paths, progress) -> int:
    if not config.cast.enabled:
        print("cast.enabled is false in config.yaml: nothing to learn.")
        return 1
    pipe = build_pipeline(config, paths, progress=progress)
    for ep, counts in pipe.learn_sprites_backfill():
        print(f"{ep}: " + (", ".join(f"{k}={v}" for k, v in counts.items()) or "already learned"))
    return 0


# -- parsers --


def add_bootstrap(sub, common) -> None:
    p = sub.add_parser("bootstrap", parents=[common], help="generate or approve the memory seed")
    p.add_argument("--approve", action="store_true", help="write the (edited) seed draft to memory")
    p.add_argument("--voices", nargs="+", metavar="CHAR_ID", help="recompute only these characters' voices")
    p.add_argument("--no-cache", action="store_true")
    p.set_defaults(func=cmd_bootstrap)


def add_dream(sub, common) -> None:
    p = sub.add_parser("dream", parents=[common], help="offline memory consolidation")
    p.add_argument("--auto-apply", action="store_true", help="apply proposals that touch no locked entry")
    p.add_argument("--no-cache", action="store_true")
    p.set_defaults(func=cmd_dream)


def add_voices(sub, common) -> None:
    p = sub.add_parser("voices", parents=[common], help="learn voices from reviewed episodes, or evaluate them")
    p.add_argument("action", choices=["learn", "evaluate"])
    p.set_defaults(func=cmd_voices)


def add_sprites(sub, common) -> None:
    p = sub.add_parser("sprites", parents=[common],
                       help="teach the sprite bank from finished episodes (runs the cast stage where missing)")
    p.add_argument("action", choices=["learn"])
    p.set_defaults(func=cmd_sprites)


PARSERS = {"bootstrap": add_bootstrap, "dream": add_dream, "voices": add_voices, "sprites": add_sprites}
