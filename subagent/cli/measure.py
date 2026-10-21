"""Measuring commands: audit, baseline, benchmark suite (6.11)."""

from __future__ import annotations

import logging
from pathlib import Path

from subagent.cli.common import (  # noqa: F401
    ON_EXISTS_CHOICES,
    _ask,
    _interactive,
    _output_exists,
    _resolve_on_exists,
)

log = logging.getLogger("subagent")


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
    from subagent.kernel.util import now_iso

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


# -- parsers --


def add_audit(sub, common) -> None:
    p = sub.add_parser("audit", parents=[common], help="accuracy measured on a sample of finished episodes")
    p.add_argument("action", choices=["sample", "report", "benchmark", "ocr", "remap-key"])
    p.add_argument("episodes", nargs="*", help="episodes (default: every finished episode)")
    p.add_argument("--redraw", action="store_true", help="draw a new sample even if one exists")
    p.add_argument("--label", help="benchmark: a name for this run (e.g. before-cleanup)")
    p.add_argument("--no-cache", action="store_true", help="benchmark: bypass the LLM response cache")
    p.add_argument("--existing", action="store_true", help="ocr: score the OCR already on disk instead of rerunning it")
    p.add_argument("--archive", help="remap-key: the folder the old answer key and events were archived to")
    p.set_defaults(func=cmd_audit)


def add_baseline(sub, common) -> None:
    p = sub.add_parser("baseline", parents=[common], help="copy finished reviews into a fixed baseline")
    p.add_argument("action", choices=["freeze", "complete"],
                   help="freeze: copy finished reviews; complete: add files an older baseline lacks")
    p.add_argument("name", help="the baseline's name (folder <work>/_baseline/<name>/)")
    p.add_argument("episodes", nargs="*", help="freeze: episodes (default: every finished episode)")
    p.set_defaults(func=cmd_baseline)


def add_bench(sub, common) -> None:
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


PARSERS = {"audit": add_audit, "baseline": add_baseline, "bench": add_bench}
