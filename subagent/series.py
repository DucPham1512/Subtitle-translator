"""Several series in one project: data/series/<slug>/ each, with series.yaml overriding config.yaml sections.

`migrate` turns the single-series layout (everything directly under data/, one config.yaml) into a named series;
`add` creates a new one; `rename` renames one; `set_default` chooses the series the app and the CLI use.
config.yaml is edited as text so its comments stay.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import yaml

from subagent.config import SERIES_FILE, SERIES_SECTIONS, list_series, series_root
from subagent.errors import SubagentError

SLUG = re.compile(r"[a-z0-9][a-z0-9_-]{0,39}")
# folders of the single-series layout that belong to the series (relative to the project root)
SERIES_FOLDERS = {"data/memory": "memory", "data/bootstrap": "bootstrap", "data/episodes": "episodes",
                  "data/character_cards": "character_cards", "fonts": "fonts"}
DEFAULT_FONT = Path(__file__).resolve().parent.parent / "app" / "fonts"


def registers(root: Path) -> list[str]:
    """Translation styles a series can use: prompts/registers/<id>.md (5.11)."""
    from subagent.registers import list_registers

    return [r.id for r in list_registers(root)]


def check_slug(slug: str) -> str:
    if not SLUG.fullmatch(slug or ""):
        raise SubagentError(f"'{slug}' is not a valid series slug: lowercase letters, digits, '-' or '_', "
                            "at most 40 characters, starting with a letter or digit", code="bad_series")
    return slug


# -- config.yaml as text --------------------------------------------------------------------------

def _blocks(text: str) -> list[tuple[str | None, list[str]]]:
    """Top-level blocks of a YAML file as (key, lines); comment / blank lines before a key belong to it."""
    out: list[tuple[str | None, list[str]]] = []
    pending: list[str] = []
    for line in text.splitlines(keepends=True):
        m = re.match(r"([A-Za-z_][\w-]*):", line)
        if m:
            out.append((m.group(1), pending + [line]))
            pending = []
        elif out and (line.startswith((" ", "\t", "-")) and line.strip()):
            out[-1][1].append(line)
        else:
            pending.append(line)
    if pending:
        out.append((None, pending))
    return out


def split_sections(text: str, keys: tuple[str, ...]) -> tuple[str, str]:
    """(config text without `keys`, the removed blocks), both keeping their comments."""
    keep, moved = [], []
    for key, lines in _blocks(text):
        (moved if key in keys else keep).extend(lines)
    return "".join(keep), "".join(moved)


def set_default(root: Path, slug: str | None) -> None:
    """Write `series.default` in config.yaml (the series the app and the CLI use when none is given)."""
    if slug is not None and slug not in list_series(root):
        raise SubagentError(f"series '{slug}' not found", code="series_not_found")
    path = root / "config.yaml"
    text, _ = split_sections(path.read_text(encoding="utf-8"), ("series",))
    block = f"series:\n  default: {slug if slug else 'null'}    # the series the app and the CLI use\n"
    text = text.rstrip("\n") + "\n" + block
    yaml.safe_load(text)                      # never write a file that no longer parses
    path.write_text(text, encoding="utf-8")


# -- commands -------------------------------------------------------------------------------------

def migrate(root: Path, slug: str) -> Path:
    """The single-series layout becomes series `slug`: its folders move to data/series/<slug>/, its sections of
    config.yaml to series.yaml (a `paths.work_dir` moves too, so the work folder stays where it is), and
    config.yaml gets `series.default: <slug>`. Card caches move to cache/character_cards/<slug>/."""
    check_slug(slug)
    folder = series_root(root) / slug
    if folder.exists():
        raise SubagentError(f"series '{slug}' already exists", code="series_exists")
    if not (root / "data" / "memory").is_dir():
        raise SubagentError("no single-series data to migrate (data/memory/ not found)", code="nothing_to_migrate")
    _refuse_while_jobs_run(root)
    config = root / "config.yaml"
    text = config.read_text(encoding="utf-8")
    rest, moved = split_sections(text, SERIES_SECTIONS)
    yaml.safe_load(rest)
    yaml.safe_load(moved)
    folder.mkdir(parents=True)
    for src, dst in SERIES_FOLDERS.items():
        if (root / src).exists():
            shutil.move(str(root / src), str(folder / dst))
    (folder / "prompts").mkdir(exist_ok=True)
    (folder / SERIES_FILE).write_text(f"# series '{slug}': overrides of config.yaml sections for this show\n"
                                      + moved.lstrip("\n"), encoding="utf-8")
    cards = root / "cache" / "character_cards"
    if cards.is_dir():
        target = cards / slug
        target.mkdir()
        for item in list(cards.iterdir()):
            if item != target:
                shutil.move(str(item), str(target / item.name))
    config.write_text(rest, encoding="utf-8")
    set_default(root, slug)
    return folder


def add(root: Path, slug: str, name: str, register: str = "co_trang_tien_hiep",
        work_dir: str | None = None, *, identify: bool = True, self_term: str = "", address_term: str = "") -> Path:
    """A new, empty series: series.yaml with its name, register, character identification mode and default
    pronoun pair (required when identification is off, 5.11a), its work folder when given (else
    <work_dir>/<slug>/), the bundled subtitle font, and the empty folders bootstrap starts from."""
    from pydantic import ValidationError

    from subagent.config import ShowConfig

    check_slug(slug)
    show: dict = {"name": name, "genre_register": register, "character_identification": identify}
    if self_term.strip() or address_term.strip():
        show |= {"self_term": self_term.strip(), "address_term": address_term.strip()}
    try:
        ShowConfig.model_validate(show)
    except ValidationError as exc:
        raise SubagentError(exc.errors()[0]["msg"].removeprefix("Value error, "), code="bad_pronouns") from exc
    folder = series_root(root) / slug
    if folder.exists():
        raise SubagentError(f"series '{slug}' already exists", code="series_exists")
    styles = registers(root)
    if styles and register not in styles:
        raise SubagentError(f"no translation style '{register}' (styles: {', '.join(styles)})", code="bad_style")
    data: dict = {"show": show}
    if work_dir:
        data["paths"] = {"work_dir": work_dir}
    for sub in ("bootstrap/voices", "bootstrap/sprites", "prompts", "fonts"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    (folder / SERIES_FILE).write_text(f"# series '{slug}': overrides of config.yaml sections for this show\n"
                                      + yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    for font in sorted(DEFAULT_FONT.glob("*.tt[fc]")) + sorted(DEFAULT_FONT.glob("*.otf")):
        if font.name.lower().startswith("notosans-"):          # the Latin + Vietnamese + pinyin subtitle font
            shutil.copy2(font, folder / "fonts" / font.name)
    for f in DEFAULT_FONT.glob("OFL*.txt"):
        shutil.copy2(f, folder / "fonts" / f.name)
    return folder


def rename(root: Path, old: str, new: str) -> Path:
    """Rename a series: its folder, its card cache, its default work folder (<work_dir>/<old>/, when it has no
    work_dir of its own), and `series.default` when it pointed at it."""
    from subagent.config import load_config

    check_slug(new)
    src, dst = series_root(root) / old, series_root(root) / new
    if not src.is_dir():
        raise SubagentError(f"series '{old}' not found", code="series_not_found")
    if dst.exists():
        raise SubagentError(f"series '{new}' already exists", code="series_exists")
    _refuse_while_jobs_run(root, old)
    own = yaml.safe_load((src / SERIES_FILE).read_text(encoding="utf-8")) if (src / SERIES_FILE).is_file() else {}
    _, paths = load_config(root, old)
    old_work = paths.work
    shutil.move(str(src), str(dst))
    cache = root / "cache" / "character_cards"
    if (cache / old).is_dir():
        shutil.move(str(cache / old), str(cache / new))
    if not ((own or {}).get("paths") or {}).get("work_dir") and old_work.is_dir():
        shutil.move(str(old_work), str(old_work.parent / new))
    current = (yaml.safe_load((root / "config.yaml").read_text(encoding="utf-8")) or {}).get("series") or {}
    if current.get("default") == old:
        set_default(root, new)
    return dst


def _refuse_while_jobs_run(root: Path, slug: str | None = None) -> None:
    """No series change while a job of that series (or of the single-series layout) runs."""
    from subagent.config import load_config
    from subagent.errors import JobRunningError
    from subagent.joblock import running_jobs

    try:
        _, paths = load_config(root, slug)
    except SubagentError:
        return
    jobs = running_jobs(paths, exclude_self=True)
    if jobs:
        raise JobRunningError(f"a job is running ({', '.join(jobs)}); try again when it has finished")
