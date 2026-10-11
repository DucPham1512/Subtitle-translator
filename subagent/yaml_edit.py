"""Edit values in a block-style YAML file without touching anything else (comments, order, blank lines).

config.yaml and series.yaml carry a comment per tuned value (the measurement behind it); a plain YAML dump would
drop them. `set_value` rewrites only the value on a key's own line (a list or a mapping becomes flow style on
that line), adds a missing key at the end of its parent block (creating parent sections as needed), and
`delete_key` removes a key with its nested lines. Each edit is checked by parsing the result.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

_KEY = re.compile(r"^(?P<indent> *)(?P<key>[^\s#:][^:#]*?|\"[^\"]*\"|'[^']*'):(?P<rest>.*)$")


def _split_comment(rest: str) -> tuple[str, str]:
    """(value text, comment with its leading spaces) of what follows `key:` on a line; quote-aware."""
    quote = None
    for i, ch in enumerate(rest):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or rest[i - 1] in " \t"):
            j = i
            while j > 0 and rest[j - 1] in " \t":
                j -= 1
            return rest[:j], rest[j:]
    return rest.rstrip(), ""


def _plain(key: str) -> str:
    key = key.strip()
    return key[1:-1] if len(key) >= 2 and key[0] == key[-1] and key[0] in "'\"" else key


def _is_child(line: str, indent: int) -> bool:
    """A line inside a block whose key sits at `indent` (blank and comment lines count as inside)."""
    stripped = line.strip()
    if not stripped:
        return True
    ind = len(line) - len(line.lstrip(" "))
    return ind > indent or (stripped.startswith("- ") and ind == indent) or stripped == "-"


def _block_end(lines: list[str], start: int, indent: int) -> int:
    """Index after the last line belonging to the key on line `start` (trailing blank/comment lines excluded)."""
    end = start + 1
    last = start + 1
    while end < len(lines) and _is_child(lines[end], indent):
        if lines[end].strip() and not lines[end].strip().startswith("#"):
            last = end + 1
        end += 1
    return last


def _find(lines: list[str], path: list[str]) -> tuple[int, int] | None:
    """(line index, indent) of the key at `path`, searching each parent's block."""
    lo, hi, indent = 0, len(lines), -1
    found = None
    for key in path:
        found = None
        child_indent = None
        for i in range(lo, hi):
            m = _KEY.match(lines[i].rstrip("\n"))
            if not m or lines[i].lstrip().startswith(("#", "- ")):
                continue
            ind = len(m.group("indent"))
            if ind <= indent:
                break
            if child_indent is None:
                child_indent = ind
            if ind == child_indent and _plain(m.group("key")) == key:
                found = (i, ind)
                break
        if found is None:
            return None
        lo, hi, indent = found[0] + 1, _block_end(lines, found[0], found[1]), found[1]
    return found


def _dump(value: Any) -> str:
    text = yaml.safe_dump(value, default_flow_style=True, allow_unicode=True, width=10000, sort_keys=False).strip()
    if text.endswith("\n..."):
        text = text[:-4].rstrip()
    return text[:-3].rstrip() if text.endswith("...") else text


def _get(data: Any, path: list[str]) -> Any:
    for key in path:
        if not isinstance(data, dict) or key not in data:
            return _MISSING
        data = data[key]
    return data


_MISSING = object()


def _path(path: str | list[str]) -> list[str]:
    """A key path: "video.subtitle_band.top", or a list of keys when a key itself has dots (model names)."""
    return list(path) if isinstance(path, (list, tuple)) else path.split(".")


def set_value(text: str, path: str | list[str], value: Any) -> str:
    """`text` with the value at `path` (e.g. "video.subtitle_band.top") set; everything else unchanged."""
    path = _path(path)
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    hit = _find(lines, path)
    if hit is not None:
        i, ind = hit
        m = _KEY.match(lines[i].rstrip("\n"))
        _, comment = _split_comment(m.group("rest"))
        end = _block_end(lines, i, ind)
        lines[i:end] = [f"{m.group('indent')}{m.group('key')}: {_dump(value)}{comment}\n"]
    else:
        # deepest existing parent, then the missing keys as nested lines at the end of its block
        depth = len(path) - 1
        parent = None
        while depth > 0:
            parent = _find(lines, path[:depth])
            if parent is not None:
                break
            depth -= 1
        if parent is None:
            at, indent = len(lines), 0
            while at > 0 and not lines[at - 1].strip():
                at -= 1
        else:
            at, indent = _block_end(lines, parent[0], parent[1]), parent[1] + 2
            m = _KEY.match(lines[parent[0]].rstrip("\n"))
            value_text, comment = _split_comment(m.group("rest"))
            if value_text.strip() and value_text.strip() not in ("{}", "null", "~"):
                # the parent holds an inline value (flow mapping): rewrite it whole
                whole = _get(yaml.safe_load(text) or {}, path[:depth])
                whole = dict(whole) if isinstance(whole, dict) else {}
                node = whole
                for key in path[depth:-1]:
                    node = node.setdefault(key, {})
                node[path[-1]] = value
                return set_value(text, path[:depth], whole)
            if value_text.strip():
                lines[parent[0]] = f"{m.group('indent')}{m.group('key')}:{comment}\n"
        new = []
        for k, key in enumerate(path[depth:]):
            pad = " " * (indent + 2 * k)
            last = k == len(path) - depth - 1
            new.append(f"{pad}{key}: {_dump(value)}\n" if last else f"{pad}{key}:\n")
        lines[at:at] = new
    out = "".join(lines)
    if _get(yaml.safe_load(out) or {}, path) != value:
        raise ValueError(f"could not set {'.'.join(path)} in place")
    return out


def delete_key(text: str, path: str | list[str]) -> str:
    """`text` without the key at `path` (and its nested lines); unchanged when it is not there."""
    path = _path(path)
    lines = text.splitlines(keepends=True)
    hit = _find(lines, path)
    if hit is None:
        return text
    i, ind = hit
    del lines[i:_block_end(lines, i, ind)]
    out = "".join(lines)
    if _get(yaml.safe_load(out) or {}, path) is not _MISSING:
        raise ValueError(f"could not delete {'.'.join(path)} in place")
    return out


def set_mapping(text: str, path: str | list[str], mapping: dict) -> str:
    """Make the mapping at `path` equal to `mapping`: changed and new keys set, missing keys deleted
    (e.g. a price table row removed). Nested mappings are handled key by key, so comments on kept keys stay."""
    path = _path(path)
    current = _get(yaml.safe_load(text) or {}, path)
    current = current if isinstance(current, dict) else {}
    for key in list(current):
        if key not in mapping:
            text = delete_key(text, [*path, key])
    for key, value in mapping.items():
        if isinstance(value, dict) and isinstance(current.get(key), dict):
            text = set_mapping(text, [*path, key], value)
        elif current.get(key, _MISSING) != value:
            text = set_value(text, [*path, key], value)
    return text
