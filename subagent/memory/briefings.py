"""Markdown memory helpers (4.2). Read functions are public; the Memory Manager does all writing."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

INDEX_HEADER = "# Episode index\n\nOne line per episode: id | summary | characters introduced | file.\n\n"
STYLE_HEADER = "# Style rules\n\nMined from human edits by dreaming. Most-used first.\n\n"


class IndexEntry(BaseModel):
    episode_id: str
    summary: str
    characters: list[str] = []
    file: str

    @property
    def number(self) -> int:
        m = re.search(r"\d+", self.episode_id)
        return int(m.group()) if m else 0


class StyleRule(BaseModel):
    rule: str
    example: str = ""
    uses: int = 1


def briefings_dir(memory: Path) -> Path:
    return memory / "briefings"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def word_count(text: str) -> int:
    return len(text.split())


# -- index -----------------------------------------------------------------------------------------

_INDEX_LINE = re.compile(r"^- (?P<id>[^|]+?) \| (?P<summary>.*?) \| (?P<chars>.*?) \| (?P<file>\S+)\s*$")


def read_index(memory: Path) -> list[IndexEntry]:
    entries = []
    for line in _read(briefings_dir(memory) / "INDEX.md").splitlines():
        m = _INDEX_LINE.match(line)
        if m:
            chars = [c.strip() for c in m.group("chars").split(",") if c.strip() and c.strip() != "-"]
            entries.append(IndexEntry(episode_id=m.group("id").strip(), summary=m.group("summary").strip(),
                                      characters=chars, file=m.group("file")))
    return entries


def render_index(entries: list[IndexEntry]) -> str:
    lines = []
    for e in sorted(entries, key=lambda e: e.number):   # episode order, never processing order
        chars = ", ".join(e.characters) or "-"
        summary = e.summary.replace("|", "/").replace("\n", " ")
        lines.append(f"- {e.episode_id} | {summary} | {chars} | {e.file}")
    return INDEX_HEADER + "\n".join(lines) + ("\n" if lines else "")


def upsert_index(entries: list[IndexEntry], entry: IndexEntry) -> list[IndexEntry]:
    return [e for e in entries if e.episode_id != entry.episode_id] + [entry]


# -- story / episodes ------------------------------------------------------------------------------

def read_story(memory: Path) -> str:
    return _read(briefings_dir(memory) / "story_so_far.md")


def read_episode_briefing(memory: Path, episode_id: str) -> str:
    return _read(briefings_dir(memory) / f"{episode_id}.md")


def list_episode_briefings(memory: Path) -> list[str]:
    d = briefings_dir(memory)
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("ep*.md"))


# -- style rules -----------------------------------------------------------------------------------

_RULE_LINE = re.compile(r"^- \[uses: (?P<uses>\d+)\] (?P<rule>.+)$")
_EXAMPLE_LINE = re.compile(r"^\s+Example: (?P<example>.+)$")


def read_style_rules(memory: Path) -> list[StyleRule]:
    rules: list[StyleRule] = []
    for line in _read(memory / "style_rules.md").splitlines():
        m = _RULE_LINE.match(line)
        if m:
            rules.append(StyleRule(rule=m.group("rule").strip(), uses=int(m.group("uses"))))
            continue
        m = _EXAMPLE_LINE.match(line)
        if m and rules:
            rules[-1].example = m.group("example").strip()
    return rules


def render_style_rules(rules: list[StyleRule]) -> str:
    lines = []
    for r in sorted(rules, key=lambda r: -r.uses):
        lines.append(f"- [uses: {r.uses}] {r.rule.strip()}")
        if r.example:
            lines.append(f"  Example: {r.example.strip()}")
    return STYLE_HEADER + "\n".join(lines) + ("\n" if lines else "")


def cap_style_rules(rules: list[StyleRule], limit: int) -> list[StyleRule]:
    """Keep at most `limit` rules, dropping the least-used (stable for ties: older rules kept)."""
    ranked = sorted(enumerate(rules), key=lambda pair: (-pair[1].uses, pair[0]))
    return [r for _, r in ranked[:limit]]
