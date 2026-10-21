"""Series commands (5.2a)."""

from __future__ import annotations

import logging

from subagent.cli.common import (  # noqa: F401
    ON_EXISTS_CHOICES,
    _ask,
    _interactive,
    _output_exists,
    _resolve_on_exists,
)

log = logging.getLogger("subagent")


def cmd_series(args, config, paths, progress) -> int:
    import yaml

    from subagent.settings import find_root, list_series
    from subagent.workspace import series as sr

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
        if bool(args.identify_characters) == bool(args.pronouns):
            print("series add: choose how pronouns are decided: --identify-characters (speaker and listener per "
                  "line, the pronoun matrix) or --pronouns SELF ADDRESS (one default pair for every line)")
            return 2
        self_term, address_term = args.pronouns or ("", "")
        folder = sr.add(root, args.slug, args.name or args.slug, args.register, args.work_dir,
                        identify=bool(args.identify_characters), self_term=self_term, address_term=address_term)
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


# -- parsers --


def add_series(sub, common) -> None:
    p = sub.add_parser("series", parents=[common], help="list, add, rename or choose series; migrate the "
                                                       "single-series layout into one")
    p.add_argument("action", choices=["list", "add", "rename", "default", "migrate"])
    p.add_argument("slug", nargs="?", help="add / default / migrate: the series; rename: the current name")
    p.add_argument("new", nargs="?", help="rename: the new name")
    p.add_argument("--name", help="add: the show's display name (default: the slug)")
    p.add_argument("--register", default="co_trang_tien_hiep", help="add: translation register (show.genre_register)")
    p.add_argument("--work-dir", help="add: its work folder (default: <work_dir>/<slug>/)")
    p.add_argument("--identify-characters", action="store_true",
                   help="add: find speaker and listener per line (voice, cast); the pronoun matrix decides xưng hô")
    p.add_argument("--pronouns", nargs=2, metavar=("SELF", "ADDRESS"),
                   help="add: no character identification; every line uses this pronoun pair, e.g. ta ngươi")
    p.set_defaults(func=cmd_series, no_config=True)


PARSERS = {"series": add_series}
