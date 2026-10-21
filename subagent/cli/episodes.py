"""Episode commands: add, relink, calibrate, run, batch, partial review, finish review, render, clean, status, check (5.20)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from subagent.cli.common import (  # noqa: F401
    ON_EXISTS_CHOICES,
    _ask,
    _interactive,
    _output_exists,
    _resolve_on_exists,
    build_pipeline,
)
from subagent.kernel.errors import SubagentError
from subagent.kernel.progress import Progress
from subagent.settings.config import Config, Paths

log = logging.getLogger("subagent")


def cmd_add(args, config: Config, paths: Paths, progress: Progress) -> int:
    from subagent.workspace.episodes import Registry

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
    from subagent.workspace.episodes import Registry
    from subagent.workspace.state import state_path

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
    if args.style:
        style, path, preview = build_pipeline(config, paths, progress=progress).calibrate_style(args.episode)
        print(f"subtitle style ({style.regions} text-like regions): {style.polarity} text, fill {style.fill_min}-"
              f"{style.fill_max}, outline {style.outline_level if style.outline_level is not None else 'none'}, "
              f"stroke {style.stroke:.3f} of the band height (spread {style.stroke_spread:.2f}), letter height "
              f"{style.letter_height:.2f}")
        print(f"saved: {path}")
        print(f"preview (band above, segmentation below): {preview}")
        return 0
    for p in build_pipeline(config, paths, progress=progress).calibrate(args.episode):
        print(p)
    print("Adjust video.subtitle_band in config.yaml until the red rectangle covers the subtitle line.")
    return 0


def cmd_run(args, config, paths, progress) -> int:
    mode = args.mode or config.review.mode
    on_exists = _resolve_on_exists(config, paths, args.episode, args.on_exists) if mode == "auto" else "fail"
    result = build_pipeline(config, paths, progress=progress, use_cache=not args.no_cache).run(
        args.episode, mode=mode, from_stage=args.from_stage, force_stage=args.force, on_exists=on_exists,
        rerun=args.rerun)
    print(f"{args.episode}: {result}")
    return 0


def cmd_batch(args, config, paths, progress) -> int:
    from subagent.workspace.episodes import Registry
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
    items = build_pipeline(config, paths, progress=progress, use_cache=not args.no_cache).run_batch(
        refs, mode=mode, on_exists=choice, keep_going=keep_going, max_total_cost=args.max_total_cost,
        rerun=args.rerun)
    for it in items:
        extra = f" ({it.reason})" if it.reason else ""
        print(f"{it.episode_id}: {it.status}{extra}" + (f"  ${it.cost:.4f}" if it.cost else ""))
    print(f"total: ${sum(it.cost for it in items):.4f}")
    return 1 if any(it.status == "failed" for it in items) else 0


def cmd_partial_review(args, config, paths, progress) -> int:
    from subagent.infra.joblock import job_lock
    from subagent.review.partial import partial_review
    from subagent.workspace.episodes import Registry

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


def cmd_finish_review(args, config, paths, progress) -> int:
    on_exists = _resolve_on_exists(config, paths, args.episode, args.on_exists)
    result = build_pipeline(config, paths, progress=progress).finish_review(args.episode, on_exists=on_exists)
    print(f"{args.episode}: {result}")
    return 0


def cmd_render(args, config, paths, progress) -> int:
    on_exists = _resolve_on_exists(config, paths, args.episode, args.on_exists)
    final = build_pipeline(config, paths, progress=progress).render(args.episode, on_exists=on_exists)
    print(final)
    return 0


def cmd_clean(args, config, paths, progress) -> int:
    removed = build_pipeline(config, paths, progress=progress).clean(args.episode)
    print("removed: " + (", ".join(removed) or "nothing"))
    return 0


def cmd_status(args, config, paths, progress) -> int:
    from subagent.pipeline import episode_status
    from subagent.workspace.episodes import Registry

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
    from subagent.infra.device import describe
    from subagent.infra.media import INSTALL_HINTS, missing_binaries
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
    from subagent.llm.client import missing_prices

    for model in missing_prices(config):
        print(f"price: no entry for {model} under llm.prices (cost shows as unknown, budget not enforced)")
    if config.ocr.preprocess == "segment":
        from subagent.ocr.subtitle_style import load_style

        if load_style(paths.bootstrap) is None:
            ok = False
            print("subtitle style: ocr.preprocess is 'segment' but the series has none yet; run "
                  "`python -m subagent calibrate EPISODE --style` once")
    print(f"device: {describe(config)}")
    print("ok" if ok else "some requirements are missing")
    return 0 if ok else 1


# -- parsers --


def add_add(sub, common) -> None:
    p = sub.add_parser("add", parents=[common], help="register video files and/or folders")
    p.add_argument("paths", nargs="+")
    p.add_argument("--recursive", action="store_true", help="include subfolders")
    p.add_argument("--number", type=int, help="episode number (single file only)")
    p.add_argument("--yes", action="store_true", help="register without asking")
    p.set_defaults(func=cmd_add)


def add_relink(sub, common) -> None:
    p = sub.add_parser("relink", parents=[common], help="point an episode at its moved video")
    p.add_argument("episode")
    p.add_argument("path")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--keep", action="store_true", help="keep existing results on a fingerprint mismatch")
    g.add_argument("--rerun", action="store_true", help="rerun from the start on a fingerprint mismatch")
    p.set_defaults(func=cmd_relink)


def add_calibrate(sub, common) -> None:
    p = sub.add_parser("calibrate", parents=[common], help="save sample frames with the subtitle band drawn")
    p.add_argument("episode")
    p.add_argument("--style", action="store_true",
                   help="learn the series' subtitle style from this episode (once per series, for ocr.preprocess: segment)")
    p.set_defaults(func=cmd_calibrate)


def add_run(sub, common) -> None:
    on_exists_choices = ON_EXISTS_CHOICES
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


def add_batch(sub, common) -> None:
    on_exists_choices = ON_EXISTS_CHOICES
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


def add_partial_review(sub, common) -> None:
    p = sub.add_parser("partial-review", parents=[common],
                       help="mid-review: learn from the approved lines and re-check the remaining ones")
    p.add_argument("episode")
    p.set_defaults(func=cmd_partial_review)


def add_finish_review(sub, common) -> None:
    on_exists_choices = ON_EXISTS_CHOICES
    p = sub.add_parser("finish-review", parents=[common], help="finish human review, update memory and render")
    p.add_argument("episode")
    p.add_argument("--on-exists", choices=on_exists_choices)
    p.set_defaults(func=cmd_finish_review)


def add_render(sub, common) -> None:
    on_exists_choices = ON_EXISTS_CHOICES
    p = sub.add_parser("render", parents=[common], help="render and deliver the finished video")
    p.add_argument("episode")
    p.add_argument("--on-exists", choices=on_exists_choices)
    p.set_defaults(func=cmd_render)


def add_clean(sub, common) -> None:
    p = sub.add_parser("clean", parents=[common], help="delete temporary files now")
    p.add_argument("episode")
    p.set_defaults(func=cmd_clean)


def add_status(sub, common) -> None:
    p = sub.add_parser("status", parents=[common], help="stage completion, cost, flag counts")
    p.add_argument("episode", nargs="?")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)


def add_check(sub, common) -> None:
    p = sub.add_parser("check", parents=[common], help="check binaries, fonts, output folder and API keys")
    p.set_defaults(func=cmd_check)


PARSERS = {"add": add_add, "relink": add_relink, "calibrate": add_calibrate, "run": add_run, "batch": add_batch, "partial-review": add_partial_review, "finish-review": add_finish_review, "render": add_render, "clean": add_clean, "status": add_status, "check": add_check}
