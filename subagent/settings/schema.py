"""What the settings form shows (6.9): one entry per config field, with the control it needs, its help text and
the file a change is saved to. No Qt here; the app builds the widgets from these specs.

Kinds: choice (fixed values: a Literal, or a known set such as the translation styles), bool, int, float, text,
optional_text, path (text + folder picker), list (tags; `numeric` for list[float]), providers (llm.providers),
prices (llm.prices). Help text: the comment on the key's line in config.yaml / series.yaml, then the note next to
the field in config.py.
"""

from __future__ import annotations

import inspect
import re
import types
import typing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from subagent.settings.config import SERIES_FILE, SERIES_SECTIONS, Config, list_series, series_root

HIDDEN_SECTIONS = ("series",)              # series.default is chosen with the series picker
PATH_FIELDS = {("output", "folder"), ("paths", "work_dir"), ("render", "font_dir")}
NONE = "(none)"
# flags a line can carry (voice.learn_auto_allowed_flags suggestions)
KNOWN_FLAGS = ("cps_exceeded", "check_pinyin", "check_pronouns", "low_speaker_conf", "speaker_override",
               "retry_cap", "not_evaluated", "non_dialogue_suspect", "ocr_uncertain", "ocr_low_conf", "ocr_fragment",
               "script_ocr", "script_suspect", "sprite_unresolved", "partial_speaker", "line_too_long",
               "glossary_mismatch", "pronoun_mismatch", "speaker_invalid", "missing_translation")


@dataclass
class FieldSpec:
    path: list[str]
    kind: str
    default: Any = None
    choices: list[str] = field(default_factory=list)     # choice kinds; tag suggestions for lists
    editable: bool = False                               # a choice that also accepts a new value
    numeric: bool = False                                # list of numbers
    help: str = ""

    @property
    def section(self) -> str:
        return self.path[0]

    @property
    def key(self) -> str:
        return ".".join(self.path)


def _code_notes(cls: type) -> dict[str, str]:
    """field -> the comment after its line in the class source (`name: type = default   # note`)."""
    try:
        source = inspect.getsource(cls)
    except (OSError, TypeError):
        return {}
    notes: dict[str, str] = {}
    for m in re.finditer(r"^\s{4}(\w+)\s*:[^\n#]*#\s*(.+)$", source, re.M):
        notes[m.group(1)] = m.group(2).strip()
    return notes


def _unwrap(annotation: Any) -> tuple[Any, bool]:
    """(type, optional) of `X | None`."""
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        if len(args) == 1:
            return args[0], True
    return annotation, False


def fields(config: Config | None = None) -> list[FieldSpec]:
    """Every editable field, in section order, from the Config model."""
    out: list[FieldSpec] = []

    def walk(model: type[BaseModel], prefix: list[str]) -> None:
        notes = _code_notes(model)
        for name, info in model.model_fields.items():
            path = [*prefix, name]
            if path[0] in HIDDEN_SECTIONS:
                continue
            ann, optional = _unwrap(info.annotation)
            origin, args = typing.get_origin(ann), typing.get_args(ann)
            default = None if info.is_required() else info.get_default(call_default_factory=True)
            help_text = notes.get(name, "")
            if path == ["llm", "providers"]:
                out.append(FieldSpec(path, "providers", default, help=help_text))
            elif path == ["llm", "prices"]:
                out.append(FieldSpec(path, "prices", default, help=help_text))
            elif isinstance(ann, type) and issubclass(ann, BaseModel):
                walk(ann, path)
            elif tuple(path) in PATH_FIELDS:
                out.append(FieldSpec(path, "path", default, help=help_text))
            elif origin is typing.Literal:
                out.append(FieldSpec(path, "choice", default, choices=[str(a) for a in args], help=help_text))
            elif ann is bool:
                out.append(FieldSpec(path, "bool", default, help=help_text))
            elif ann is int:
                out.append(FieldSpec(path, "int", default, help=help_text))
            elif ann is float:
                out.append(FieldSpec(path, "float", default, help=help_text))
            elif origin is list:
                numeric = bool(args) and args[0] in (int, float)
                out.append(FieldSpec(path, "list", default, numeric=numeric, help=help_text))
            elif ann is str:
                out.append(FieldSpec(path, "optional_text" if optional else "text", default, help=help_text))
    walk(Config, [])
    return out


def known_sets(root: Path, work: Path) -> dict[str, tuple[list[str], bool]]:
    """Dropdowns for text fields with a known set of values: key -> (choices, accepts a new value)."""
    from subagent.settings.registers import list_registers

    baselines = sorted(p.name for p in (work / "_baseline").iterdir() if (p / "manifest.json").is_file()) \
        if (work / "_baseline").is_dir() else []
    return {
        "show.genre_register": ([r.id for r in list_registers(root)], False),
        "bench.baseline": ([NONE, *baselines], False),
        "baseline.name": ([NONE, *baselines], True),
        "voice.learn_auto_allowed_flags": (list(KNOWN_FLAGS), True),
    }


def with_known_sets(specs: list[FieldSpec], root: Path, work: Path) -> list[FieldSpec]:
    sets = known_sets(root, work)
    for spec in specs:
        if spec.key in sets:
            choices, editable = sets[spec.key]
            if spec.kind == "list":
                spec.choices = choices                          # tag suggestions
            else:
                spec.kind, spec.choices, spec.editable = "choice", choices, editable
    return specs


def target(root: Path, path: list[str], series: str | None) -> str:
    """"series" when a change at `path` is saved in the active series' series.yaml, else "shared" (5.2a)."""
    if not series:
        return "shared"
    import yaml

    own_file = series_root(root) / series / SERIES_FILE
    own = (yaml.safe_load(own_file.read_text(encoding="utf-8")) or {}) if own_file.is_file() else {}
    return "series" if path[0] in SERIES_SECTIONS or path[0] in own else "shared"


def value_at(config: Config, path: list[str]) -> Any:
    data: Any = config.model_dump(mode="json")
    for key in path:
        data = data.get(key) if isinstance(data, dict) else None
    return data


def file_comment(text: str, path: list[str]) -> str:
    """The comment on the key's own line in a YAML text (the measurement behind a tuned value), or ""."""
    from subagent.settings.yaml_edit import _KEY, _find, _split_comment

    lines = text.splitlines(keepends=True)
    hit = _find(lines, path)
    if hit is None:
        return ""
    m = _KEY.match(lines[hit[0]].rstrip("\n"))
    _, comment = _split_comment(m.group("rest")) if m else ("", "")
    return comment.strip().lstrip("#").strip()


__all__ = ["FieldSpec", "fields", "with_known_sets", "target", "value_at", "file_comment", "NONE", "list_series"]
