"""CLI entry point: python -m subagent <command> (5.20)."""

from __future__ import annotations

import argparse
import contextlib
import json
import logging
import os
import sys
from pathlib import Path

from subagent.config import Config, Paths, load_config
from subagent.errors import SubagentError
from subagent.progress import Progress

log = logging.getLogger("subagent")


def _setup_logging(verbose: bool) -> None:
    # Logs go to stderr so `--progress json` keeps stdout machine-readable.
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger("subagent")
    root.handlers[:] = [handler]
    root.setLevel(logging.DEBUG if verbose else logging.INFO)


def _interactive() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _ask(prompt: str, choices: dict[str, str]) -> str:
    while True:
        answer = input(prompt).strip().lower()
        if answer in choices:
            return choices[answer]


def _resolve_on_exists(config: Config, paths: Paths, ep_ref: str, arg: str | None) -> str:
    """CLI: --on-exists wins; otherwise config; `ask` prompts on a terminal and fails when non-interactive."""
    from subagent.delivery import target_path
    from subagent.episodes import Registry

    choice = (arg or config.output.on_exists).replace("-", "_")
    if choice != "ask":
        return choice
    if not _interactive():
        return "fail"
    try:
        target = target_path(config, Path(Registry(paths).resolve(ep_ref).source_path))
    except SubagentError:
        return "fail"   # the pipeline reports the missing output folder
    if not target.exists():
        return "fail"
    return _ask(f"{target} already exists. [o]verwrite, [k]eep both, [c]ancel? ",
                {"o": "overwrite", "k": "keep_both", "c": "fail"})


# -- commands --------------------------------------------------------------------------------------

def cmd_add(args, config: Config, paths: Paths, progress: Progress) -> int:
    from subagent.episodes import Registry

    registry = Registry(paths)
    candidates = registry.prepare_add([Path(p) for p in args.paths], config, recursive=args.recursive)
    if not candidates:
        print("No video files found.")
        return 1
    if args.number is not None:
        usable = [c for c in candidates if not c.problem]
        if len(usable) != 1:
            print("--number works with exactly one file.")
            return 1
        usable[0].number = args.number
    print(f"{'file':60} {'episode':>8}  note")
    for c in candidates:
        note = {"duplicate": f"duplicate of {c.duplicate_of}, skipped",
                "no_video_stream": f"no video stream, skipped ({c.problem_detail})"}.get(c.problem or "", "")
        if not c.problem and c.number is None:
            note = "no episode number detected"
        print(f"{Path(c.path).name[:60]:60} {c.number if c.number is not None else '-':>8}  {note}")
    errors = registry.validate_numbers(candidates)
    if errors:
        print("\nCannot register:\n  " + "\n  ".join(errors))
        print("Rename the files, or add one file at a time with --number N.")
        return 1
    usable = [c for c in candidates if not c.problem]
    if not usable:
        return 1
    if not args.yes:
        if not _interactive():
            print("Confirm with --yes when not running in a terminal.")
            return 1
        if _ask("Register these episodes? [y/n] ", {"y": "y", "n": "n"}) != "y":
            return 1
    for ep in registry.register(usable):
        print(f"registered {ep.id}: {ep.source_path}")
    return 0


def cmd_relink(args, config: Config, paths: Paths, progress: Progress) -> int:
    from subagent.episodes import Registry
    from subagent.state import state_path

    registry = Registry(paths)
    ep, matches = registry.relink(registry.resolve(args.episode).id, Path(args.path))
    if matches:
        print(f"{ep.id} relinked to {ep.source_path}")
        return 0
    print(f"Warning: {Path(args.path).name} does not match the fingerprint of the original video; it may be a "
          "different file and existing results may not line up.")
    choice = "rerun" if args.rerun else "keep" if args.keep else None
    if choice is None:
        choice = _ask("[k]eep results or [r]erun from the start? ", {"k": "keep", "r": "rerun"}) if _interactive() else "keep"
    if choice == "rerun":
        state_path(paths.episode_dir(ep.id)).unlink(missing_ok=True)
        print("Results will be regenerated on the next run.")
    return 0


def cmd_calibrate(args, config, paths, progress) -> int:
    from subagent.pipeline import Pipeline

    if args.style:
        style, path, preview = Pipeline(config, paths, progress=progress).calibrate_style(args.episode)
        print(f"subtitle style ({style.regions} text-like regions): {style.polarity} text, fill {style.fill_min}-"
              f"{style.fill_max}, outline {style.outline_level if style.outline_level is not None else 'none'}, "
              f"stroke {style.stroke:.3f} of the band height (spread {style.stroke_spread:.2f}), letter height "
              f"{style.letter_height:.2f}")
        print(f"saved: {path}")
        print(f"preview (band above, segmentation below): {preview}")
        return 0
    for p in Pipeline(config, paths, progress=progress).calibrate(args.episode):
        print(p)
    print("Adjust video.subtitle_band in config.yaml until the red rectangle covers the subtitle line.")
    return 0


def cmd_run(args, config, paths, progress) -> int:
    from subagent.pipeline import Pipeline

    mode = args.mode or config.review.mode
    on_exists = _resolve_on_exists(config, paths, args.episode, args.on_exists) if mode == "auto" else "fail"
    result = Pipeline(config, paths, progress=progress, use_cache=not args.no_cache).run(
        args.episode, mode=mode, from_stage=args.from_stage, force_stage=args.force, on_exists=on_exists,
        rerun=args.rerun)
    print(f"{args.episode}: {result}")
    return 0


def cmd_batch(args, config, paths, progress) -> int:
    from subagent.episodes import Registry
    from subagent.pipeline import Pipeline

    registry = Registry(paths)
    refs = list(args.episodes)
    if args.pending:
        refs += [e.id for e in registry.load() if e.status not in ("done", "awaiting_review")]
    if not refs:
        print("Nothing to run: name episodes or use --pending.")
        return 1
    mode = args.mode or config.review.mode
    choice = (args.on_exists or config.output.on_exists).replace("-", "_")
    if mode == "auto" and choice == "ask":
        choice = "fail"
        if _interactive() and any(_output_exists(config, paths, r) for r in refs):
            choice = _ask("Some outputs already exist. [o]verwrite, [k]eep both, [c]ancel those? ",
                          {"o": "overwrite", "k": "keep_both", "c": "fail"})
    keep_going = True if args.keep_going else False if args.stop_on_error else None
    items = Pipeline(config, paths, progress=progress, use_cache=not args.no_cache).run_batch(
        refs, mode=mode, on_exists=choice, keep_going=keep_going, max_total_cost=args.max_total_cost,
        rerun=args.rerun)
    for it in items:
        extra = f" ({it.reason})" if it.reason else ""
        print(f"{it.episode_id}: {it.status}{extra}" + (f"  ${it.cost:.4f}" if it.cost else ""))
    print(f"total: ${sum(it.cost for it in items):.4f}")
    return 1 if any(it.status == "failed" for it in items) else 0


def _output_exists(config, paths, ep_ref: str) -> bool:
    from subagent.delivery import target_path
    from subagent.episodes import Registry

    try:
        return target_path(config, Path(Registry(paths).resolve(ep_ref).source_path)).exists()
    except SubagentError:
        return False


def cmd_finish_review(args, config, paths, progress) -> int:
    from subagent.pipeline import Pipeline

    on_exists = _resolve_on_exists(config, paths, args.episode, args.on_exists)
    result = Pipeline(config, paths, progress=progress).finish_review(args.episode, on_exists=on_exists)
    print(f"{args.episode}: {result}")
    return 0


def cmd_render(args, config, paths, progress) -> int:
    from subagent.pipeline import Pipeline

    on_exists = _resolve_on_exists(config, paths, args.episode, args.on_exists)
    final = Pipeline(config, paths, progress=progress).render(args.episode, on_exists=on_exists)
    print(final)
    return 0


def cmd_clean(args, config, paths, progress) -> int:
    from subagent.pipeline import Pipeline

    removed = Pipeline(config, paths, progress=progress).clean(args.episode)
    print("removed: " + (", ".join(removed) or "nothing"))
    return 0


def cmd_baseline(args, config, paths, progress) -> int:
    from subagent.baseline import baseline_dir, complete, freeze
    from subagent.episodes import Registry

    if args.action == "complete":
        added = complete(paths, args.name)
        for ep, files in added.items():
            print(f"{ep}: {', '.join(files) or 'nothing added'}")
        return 0
    registry = Registry(paths)
    eps = [registry.resolve(x).id for x in args.episodes] if args.episodes else None
    done = freeze(config, paths, args.name, eps)
    print(f"frozen into {baseline_dir(paths, args.name)}: {', '.join(done) or 'nothing'}")
    return 0


def cmd_bench(args, config, paths, progress) -> int:
    from subagent import suite
    from subagent.baseline import baseline_dir
    from subagent.util import now_iso

    name = args.baseline or config.bench.baseline or config.baseline.name
    if not name or not (baseline_dir(paths, name) / "manifest.json").is_file():
        print(f"no baseline to score against: {name or 'set bench.baseline'} (folder <work>/_baseline/<name>/)")
        return 2
    folder = baseline_dir(paths, name)
    eps = args.episodes or None
    if args.action == "score":
        system = Path(args.system) if args.system else folder
        gold = suite.load_gold(folder, eps)
        label = args.label or ("recorded" if system == folder else system.name)
        r = suite.score(config, paths, gold, system, label=label)
        stamp = now_iso().replace(":", "").replace("-", "")[:15]
        out = suite.save(paths, r, paths.work / suite.FOLDER / f"{stamp}-{label}")
    else:
        from subagent.bench_run import run

        resume = None
        if args.resume:
            resume = Path(args.resume)
            if not resume.is_absolute() and not resume.exists():
                resume = paths.work / suite.FOLDER / args.resume
        r = run(config, paths, folder, mode=args.mode, from_stage=args.from_stage, episodes=eps,
                label=args.label or "", use_cache=not args.no_cache, progress=progress, resume=resume)
        out = Path(r.system).parent
        if r.run.get("prefix_changed"):
            print(f"prompt memory prefix differs from the replay in: {', '.join(r.run['prefix_changed'])}")
    print(suite.render(r).split("## Per episode")[0])
    print(f"saved: {out}")
    return 0


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


def cmd_audit(args, config, paths, progress) -> int:
    from subagent import audit
    from subagent.episodes import Registry

    registry = Registry(paths)
    done = [e for e in sorted(registry.load(), key=lambda e: e.number) if e.status == "done"]
    chosen = [registry.resolve(x) for x in args.episodes] if args.episodes else done
    if args.action == "sample":
        for ep in chosen:
            work = paths.episode_dir(ep.id)
            if not audit.auditable(config, paths, ep.id):
                print(f"{ep.id}: human-reviewed, not audited (audit.include_human is false)")
                continue
            if audit.load_sample(work) and not args.redraw:
                print(f"{ep.id}: already sampled ({len(audit.load_sample(work))} lines)")
                continue
            s = audit.draw_sample(config, paths, ep.id)
            print(f"{ep.id}: {sum(x.kind == 'random' for x in s)} random + "
                  f"{sum(x.kind == 'disagreement' for x in s)} disagreement lines")
        return 0
    if args.action == "remap-key":
        from pathlib import Path

        from subagent.ocr_benchmark import remap_key

        if not args.archive:
            print("remap-key needs --archive DIR (the folder the old key and events were archived to)")
            return 2
        key, lost = remap_key(paths, Path(args.archive))
        print(f"answer key: {len(key['corrections'])} corrections, {len(key['excluded'])} exclusions moved to "
              f"today's line ids; {len(lost)} found no line: {', '.join(lost) or '-'}")
        note = key["remapped"]
        if note["exclusions_dropped"]:
            print(f"exclusions about a fragment of a merged line, dropped: {', '.join(note['exclusions_dropped'])}")
        if note["conflicting_corrections"]:
            print(f"corrections that disagreed on one line: {', '.join(note['conflicting_corrections'])}")
        return 0
    if args.action == "ocr":
        from subagent.ocr_benchmark import ocr_episodes, run_ocr_benchmark
        from subagent.ocr_benchmark import render as render_ocr

        eps = [e.id for e in chosen] if args.episodes else ocr_episodes(paths)
        r = run_ocr_benchmark(config, paths, eps, label=args.label or "", existing=args.existing, progress=progress)
        print(render_ocr(r).split("## Wrong lines")[0])
        print(f"saved: {r.folder}")
        return 0
    if args.action == "benchmark":
        from subagent.benchmark import benchmark_episodes, render, run_benchmark

        eps = [e.id for e in chosen] if args.episodes else benchmark_episodes(paths)
        missing = {e: audit.missing_answers(paths.episode_dir(e)) for e in eps}
        if any(missing.values()):
            print("note: wrong-speaker marks without the correct speaker are left out: "
                  + ", ".join(f"{e} {n}" for e, n in missing.items() if n))
        r = run_benchmark(config, paths, eps, label=args.label or "", use_cache=not args.no_cache, progress=progress)
        print(render(r))
        print(f"saved: {r.folder}")
        return 0
    r, path = audit.write_report(config, paths, [e.id for e in chosen])
    print(audit.render_report(r))
    print(f"saved: {path}")
    return 0


def cmd_partial_review(args, config, paths, progress) -> int:
    from subagent.episodes import Registry
    from subagent.joblock import job_lock
    from subagent.partial_review import partial_review

    ep = Registry(paths).resolve(args.episode)
    with job_lock(paths, ep.id):
        progress.emit("partial_review", "start", message="learning from the approved lines")
        r = partial_review(config, paths, ep.id)
        progress.emit("partial_review", "done",
                      message=f"{r.suggestions} speaker suggestions for {r.remaining} remaining lines")
    print(f"{ep.id}: learned from {r.reviewed} approved lines; {r.remaining} remaining")
    print(f"  sprites: +{r.sprites_learned} examples this session, {r.sprite_names} unknown sprites named, "
          f"{r.renamed_characters} characters in remaining lines renamed")
    print(f"  voices: {', '.join(r.voices_updated) or 'none'} updated; {r.voice_changed} remaining lines re-matched "
          f"differently")
    print(f"  speaker suggestions: {r.suggestions}")
    return 0


def cmd_sprites(args, config, paths, progress) -> int:
    from subagent.pipeline import Pipeline

    if not config.cast.enabled:
        print("cast.enabled is false in config.yaml: nothing to learn.")
        return 1
    pipe = Pipeline(config, paths, progress=progress)
    for ep, counts in pipe.learn_sprites_backfill():
        print(f"{ep}: " + (", ".join(f"{k}={v}" for k, v in counts.items()) or "already learned"))
    return 0


def cmd_series(args, config, paths, progress) -> int:
    import yaml

    from subagent import series as sr
    from subagent.config import find_root, list_series

    root = find_root()
    if args.action == "list":
        default = ((yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8")) or {}).get("series")
                   or {}).get("default")
        names = list_series(root)
        if not names:
            print("no series yet: data/ holds the single-series layout (`series migrate SLUG` names it)")
        for slug in names:
            print(("* " if slug == default else "  ") + slug)
        return 0
    if not args.slug:
        print(f"series {args.action}: give the series slug")
        return 2
    if args.action == "add":
        folder = sr.add(root, args.slug, args.name or args.slug, args.register, args.work_dir)
        print(f"series {args.slug} created in {folder}; next: `python -m subagent --series {args.slug} bootstrap` "
              "(or the app's Bootstrap screen)")
    elif args.action == "migrate":
        folder = sr.migrate(root, args.slug)
        print(f"single-series data moved to {folder}; config.yaml now uses series.default: {args.slug}")
    elif args.action == "default":
        sr.set_default(root, args.slug)
        print(f"default series: {args.slug}")
    else:
        if not args.new:
            print("series rename OLD NEW")
            return 2
        print(f"renamed to {sr.rename(root, args.slug, args.new)}")
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


def cmd_status(args, config, paths, progress) -> int:
    from subagent.episodes import Registry
    from subagent.pipeline import episode_status

    registry = Registry(paths)
    episodes = [registry.resolve(args.episode)] if args.episode else registry.load()
    rows = [episode_status(paths, ep, config.llm.prices) for ep in episodes]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    if not rows:
        print("No episodes registered. Add some with: python -m subagent add PATH")
    for r in rows:
        cost = f"${r['cost']:.4f}" + ("" if r["cost_complete"] else " + unknown")
        print(f"{r['id']}  {r['status']:<16} cost {cost}  flags {r['flag_total']}  {Path(r['source']).name}")
        if args.episode:
            for stage, st in r["stages"].items():
                print(f"    {stage:<10} {st}")
            for flag, n in sorted(r["flags"].items()):
                print(f"    flag {flag}: {n}")
            from subagent.pipeline import AGENT_NAMES

            for task, cost in sorted(r["cost_by_agent"].items(), key=lambda kv: -kv[1]):
                print(f"    cost {AGENT_NAMES.get(task, task)}: ${cost:.4f}")
    return 0


def cmd_check(args, config, paths, progress) -> int:
    """Startup checks: external binaries, fonts, output folder, API keys (NFR-PT2)."""
    from subagent.delivery import output_folder
    from subagent.device import describe
    from subagent.media import INSTALL_HINTS, missing_binaries
    from subagent.stages.render import font_files

    ok = True
    for name in missing_binaries():
        ok = False
        print(f"missing: {name}. {INSTALL_HINTS[name]}")
    if not font_files(paths):
        ok = False
        print(f"missing: subtitle font in {paths.fonts}")
    try:
        output_folder(config)
    except SubagentError as exc:
        print(f"output: {exc}")
    for role, provider in config.llm.providers.items():
        if not os.environ.get(provider.api_key_env):
            print(f"api key: {provider.api_key_env} is not set ({role})")
    from subagent.llm import missing_prices

    for model in missing_prices(config):
        print(f"price: no entry for {model} under llm.prices (cost shows as unknown, budget not enforced)")
    if config.ocr.preprocess == "segment":
        from subagent.subtitle_style import load_style

        if load_style(paths.bootstrap) is None:
            ok = False
            print("subtitle style: ocr.preprocess is 'segment' but the series has none yet; run "
                  "`python -m subagent calibrate EPISODE --style` once")
    print(f"device: {describe(config)}")
    print("ok" if ok else "some requirements are missing")
    return 0 if ok else 1


# -- parser ----------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    # Global flags work before or after the command; SUPPRESS keeps a subcommand from resetting them.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--progress", choices=["json", "text"], default=argparse.SUPPRESS, help="progress output format")
    common.add_argument("--verbose", action="store_true", default=argparse.SUPPRESS, help="debug logging")
    common.add_argument("--series", default=argparse.SUPPRESS,
                        help="series to work on (data/series/<slug>/; default: series.default in config.yaml)")

    parser = argparse.ArgumentParser(prog="python -m subagent", description=__doc__)
    parser.add_argument("--progress", choices=["json", "text"], default="text", help="progress output format")
    parser.add_argument("--verbose", action="store_true", help="debug logging")
    sub = parser.add_subparsers(dest="command", required=True)
    on_exists_choices = ["overwrite", "keep-both", "fail"]

    p = sub.add_parser("add", parents=[common], help="register video files and/or folders")
    p.add_argument("paths", nargs="+")
    p.add_argument("--recursive", action="store_true", help="include subfolders")
    p.add_argument("--number", type=int, help="episode number (single file only)")
    p.add_argument("--yes", action="store_true", help="register without asking")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("relink", parents=[common], help="point an episode at its moved video")
    p.add_argument("episode")
    p.add_argument("path")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--keep", action="store_true", help="keep existing results on a fingerprint mismatch")
    g.add_argument("--rerun", action="store_true", help="rerun from the start on a fingerprint mismatch")
    p.set_defaults(func=cmd_relink)

    p = sub.add_parser("calibrate", parents=[common], help="save sample frames with the subtitle band drawn")
    p.add_argument("episode")
    p.add_argument("--style", action="store_true",
                   help="learn the series' subtitle style from this episode (once per series, for ocr.preprocess: segment)")
    p.set_defaults(func=cmd_calibrate)

    p = sub.add_parser("bootstrap", parents=[common], help="generate or approve the memory seed")
    p.add_argument("--approve", action="store_true", help="write the (edited) seed draft to memory")
    p.add_argument("--voices", nargs="+", metavar="CHAR_ID", help="recompute only these characters' voices")
    p.add_argument("--no-cache", action="store_true")
    p.set_defaults(func=cmd_bootstrap)

    p = sub.add_parser("run", parents=[common], help="process an episode")
    p.add_argument("episode")
    p.add_argument("--mode", choices=["auto", "human"])
    p.add_argument("--from", dest="from_stage", metavar="STAGE", help="rerun from this stage onward")
    p.add_argument("--force", metavar="STAGE", help="rerun this stage")
    p.add_argument("--rerun", action="store_true",
                   help="run again from OCR correction with today's memory, even when done (a review starts over)")
    p.add_argument("--no-cache", action="store_true", help="bypass the LLM response cache")
    p.add_argument("--on-exists", choices=on_exists_choices)
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("batch", parents=[common], help="process several episodes in episode order, one after another")
    p.add_argument("episodes", nargs="*")
    p.add_argument("--pending", action="store_true", help="every episode not done and not waiting for review")
    p.add_argument("--mode", choices=["auto", "human"])
    p.add_argument("--on-exists", choices=on_exists_choices)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--keep-going", action="store_true", help="carry on after a failed episode (human mode default)")
    g.add_argument("--stop-on-error", action="store_true", help="stop at the first failed episode (auto mode default)")
    p.add_argument("--max-total-cost", type=float, metavar="USD", help="do not start another episode past this total")
    p.add_argument("--rerun", action="store_true", help="run every named episode again, also done ones")
    p.add_argument("--no-cache", action="store_true", help="bypass the LLM response cache")
    p.set_defaults(func=cmd_batch)

    p = sub.add_parser("finish-review", parents=[common], help="finish human review, update memory and render")
    p.add_argument("episode")
    p.add_argument("--on-exists", choices=on_exists_choices)
    p.set_defaults(func=cmd_finish_review)

    p = sub.add_parser("render", parents=[common], help="render and deliver the finished video")
    p.add_argument("episode")
    p.add_argument("--on-exists", choices=on_exists_choices)
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("clean", parents=[common], help="delete temporary files now")
    p.add_argument("episode")
    p.set_defaults(func=cmd_clean)

    p = sub.add_parser("baseline", parents=[common], help="copy finished reviews into a fixed baseline")
    p.add_argument("action", choices=["freeze", "complete"],
                   help="freeze: copy finished reviews; complete: add files an older baseline lacks")
    p.add_argument("name", help="the baseline's name (folder <work>/_baseline/<name>/)")
    p.add_argument("episodes", nargs="*", help="freeze: episodes (default: every finished episode)")
    p.set_defaults(func=cmd_baseline)

    p = sub.add_parser("dream", parents=[common], help="offline memory consolidation")
    p.add_argument("--auto-apply", action="store_true", help="apply proposals that touch no locked entry")
    p.add_argument("--no-cache", action="store_true")
    p.set_defaults(func=cmd_dream)

    p = sub.add_parser("voices", parents=[common], help="learn voices from reviewed episodes, or evaluate them")
    p.add_argument("action", choices=["learn", "evaluate"])
    p.set_defaults(func=cmd_voices)

    p = sub.add_parser("audit", parents=[common], help="accuracy measured on a sample of finished episodes")
    p.add_argument("action", choices=["sample", "report", "benchmark", "ocr", "remap-key"])
    p.add_argument("episodes", nargs="*", help="episodes (default: every finished episode)")
    p.add_argument("--redraw", action="store_true", help="draw a new sample even if one exists")
    p.add_argument("--label", help="benchmark: a name for this run (e.g. before-cleanup)")
    p.add_argument("--no-cache", action="store_true", help="benchmark: bypass the LLM response cache")
    p.add_argument("--existing", action="store_true", help="ocr: score the OCR already on disk instead of rerunning it")
    p.add_argument("--archive", help="remap-key: the folder the old answer key and events were archived to")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("bench", parents=[common], help="benchmark suite against the frozen baseline (6.11e)")
    p.add_argument("action", choices=["score", "run"],
                   help="score: score machine files (default: the recorded output); run: rerun stages in a sandbox")
    p.add_argument("episodes", nargs="*", help="baseline episodes (default: all)")
    p.add_argument("--baseline", help="baseline name (default: bench.baseline)")
    p.add_argument("--system", help="score: a folder of <episode>/ machine files (default: the baseline's own)")
    p.add_argument("--mode", choices=["snapshot", "chain"], default="snapshot",
                   help="run: memory each episode was made with (snapshot) or learned again in order (chain)")
    p.add_argument("--from", dest="from_stage", help="run: first stage to rerun (default: ocr_fix)")
    p.add_argument("--label", help="a name for this run")
    p.add_argument("--no-cache", action="store_true", help="run: bypass the LLM response cache")
    p.add_argument("--resume", help="run: continue a stopped run (its folder, or its name under <work>/_suite/); "
                                    "its own settings are used")
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("partial-review", parents=[common],
                       help="mid-review: learn from the approved lines and re-check the remaining ones")
    p.add_argument("episode")
    p.set_defaults(func=cmd_partial_review)

    p = sub.add_parser("sprites", parents=[common],
                       help="teach the sprite bank from finished episodes (runs the cast stage where missing)")
    p.add_argument("action", choices=["learn"])
    p.set_defaults(func=cmd_sprites)

    p = sub.add_parser("series", parents=[common], help="list, add, rename or choose series; migrate the "
                                                       "single-series layout into one")
    p.add_argument("action", choices=["list", "add", "rename", "default", "migrate"])
    p.add_argument("slug", nargs="?", help="add / default / migrate: the series; rename: the current name")
    p.add_argument("new", nargs="?", help="rename: the new name")
    p.add_argument("--name", help="add: the show's display name (default: the slug)")
    p.add_argument("--register", default="co_trang_tien_hiep", help="add: translation register (show.genre_register)")
    p.add_argument("--work-dir", help="add: its work folder (default: <work_dir>/<slug>/)")
    p.set_defaults(func=cmd_series, no_config=True)

    p = sub.add_parser("status", parents=[common], help="stage completion, cost, flag counts")
    p.add_argument("episode", nargs="?")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("check", parents=[common], help="check binaries, fonts, output folder and API keys")
    p.set_defaults(func=cmd_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):   # Chinese / Vietnamese on legacy Windows consoles (NFR-PT3)
        with contextlib.suppress(AttributeError, ValueError, OSError):
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    args = build_parser().parse_args(argv)
    _setup_logging(args.verbose)
    progress = Progress(args.progress)
    try:
        if getattr(args, "no_config", False):        # works before any series exists or loads
            return args.func(args, None, None, progress)
        config, paths = load_config(series=getattr(args, "series", None))
        return args.func(args, config, paths, progress)
    except SubagentError as exc:
        progress.emit(getattr(args, "command", "cli"), "error", message=str(exc), error_code=exc.code)
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        progress.emit(getattr(args, "command", "cli"), "error", message="cancelled", error_code="cancelled")
        return 130
    except Exception as exc:  # noqa: BLE001 - last-resort report for the app
        log.exception("unexpected error")
        progress.emit(getattr(args, "command", "cli"), "error", message=str(exc), error_code="internal")
        return 2


if __name__ == "__main__":
    sys.exit(main())
