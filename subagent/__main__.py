"""CLI entry point: python -m subagent <command> (5.20)."""

from __future__ import annotations

import argparse
import contextlib
import logging
import sys

from subagent.cli import episodes, measure, memory, series
from subagent.kernel import Progress, SubagentError
from subagent.settings import load_config

log = logging.getLogger("subagent")

COMMANDS = ["add", "relink", "calibrate", "bootstrap", "run", "batch", "finish-review", "render", "clean", "baseline", "dream", "voices", "audit", "bench", "partial-review", "sprites", "series", "status", "check"]   # --help lists them in this order


def _setup_logging(verbose: bool) -> None:
    # Logs go to stderr so `--progress json` keeps stdout machine-readable.
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger("subagent")
    root.handlers[:] = [handler]
    root.setLevel(logging.DEBUG if verbose else logging.INFO)


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

    parsers = {**episodes.PARSERS, **memory.PARSERS, **measure.PARSERS, **series.PARSERS}
    for name in COMMANDS:
        parsers[name](sub, common)
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
