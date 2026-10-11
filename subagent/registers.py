"""Translation styles (registers): prompts/registers/<id>.md, shared by every series (5.11).

A style is the register section of the translator prompt (tone, naming, pronoun system) plus the Vietnamese
pronoun words the pronoun rule check looks for. A series picks one with `show.genre_register`; the translator
prompt's `{{register}}` is replaced by its text. File format:

    ---
    name: Cổ trang / tiên hiệp
    pronoun_terms: [ta, ngươi, huynh]
    ---
    ## Register: cổ trang / tiên hiệp
    ...
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from subagent.errors import SubagentError

REGISTER_DIR = "registers"
STYLE_ID = re.compile(r"[a-z0-9][a-z0-9_]{0,39}")
TEMPLATE = """## Register: {name}

The series is ... (setting, era, genre).
- Names, titles, places and special terms: how to render them (Hán-Việt, Vietnamese, kept as is), with examples.
- Pronoun system: which Vietnamese pronouns fit (for example anh / em, tôi / bạn, ta / ngươi). The pronoun matrix
  decides which pair applies.
- Tone: formal or casual, slang allowed or not, how to translate idioms.
"""


@dataclass
class Register:
    id: str
    name: str
    body: str
    pronoun_terms: list[str] = field(default_factory=list)


def register_dir(root: Path) -> Path:
    return root / "prompts" / REGISTER_DIR


def _parse(rid: str, text: str) -> Register:
    meta: dict = {}
    body = text
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if m:
        meta = yaml.safe_load(m.group(1)) or {}
        body = text[m.end():]
    terms = [str(t).strip() for t in meta.get("pronoun_terms") or [] if str(t).strip()]
    return Register(id=rid, name=str(meta.get("name") or rid), body=body, pronoun_terms=terms)


def list_registers(root: Path) -> list[Register]:
    folder = register_dir(root)
    if not folder.is_dir():
        return []
    return [_parse(p.stem, p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.md"))]


def load_register(root: Path, rid: str) -> Register | None:
    path = register_dir(root) / f"{rid}.md"
    return _parse(rid, path.read_text(encoding="utf-8")) if path.is_file() else None


def check_id(rid: str) -> str:
    if not STYLE_ID.fullmatch(rid or ""):
        raise SubagentError(f"'{rid}' is not a valid style id: lowercase letters, digits or '_', at most 40 "
                            "characters, starting with a letter or digit", code="bad_style")
    return rid


def save_register(root: Path, rid: str, name: str, body: str, pronoun_terms: list[str]) -> Path:
    """A new style file. An existing style is never overwritten (series may use it)."""
    from subagent.util import atomic_write_text

    check_id(rid)
    if not body.strip():
        raise SubagentError("the style needs its instructions for the translator", code="bad_style")
    path = register_dir(root) / f"{rid}.md"
    if path.exists():
        raise SubagentError(f"style '{rid}' already exists", code="style_exists")
    terms = list(dict.fromkeys(t.strip() for t in pronoun_terms if t.strip()))
    meta = yaml.safe_dump({"name": name.strip() or rid, "pronoun_terms": terms}, allow_unicode=True,
                          sort_keys=False, default_flow_style=None, width=10000)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, f"---\n{meta}---\n{body.rstrip()}\n")
    return path


def split_terms(text: str) -> list[str]:
    """Pronoun words typed as "anh, em; tôi" (commas, semicolons or new lines)."""
    return [t for t in (x.strip() for x in re.split(r"[,;\n]", text or "")) if t]
