"""Text helpers shared by stages: CJK filtering, edit distance, Vietnamese word matching and wrapping."""

from __future__ import annotations

import re
import unicodedata

# CJK ideographs (unified + ext A + compatibility), CJK symbols/punctuation, full-width forms,
# the general punctuation marks Chinese subtitles use, and ASCII digits.
_KEEP = re.compile(
    "[^"
    "\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
    "\u3000-\u303f\uff00-\uffef"
    "\u2014\u2026\u00b7\u2018\u2019\u201c\u201d"
    "0-9"
    "]"
)
_PUNCT = re.compile(r"[\u3000-\u303f\uff01-\uff0f\uff1a-\uff20\uff3b-\uff40\uff5b-\uff65\u2014\u2026\u00b7\u2018\u2019\u201c\u201d\s]")


def keep_cjk(text: str) -> str:
    """Strip characters outside CJK, CJK punctuation and digits (5.4)."""
    return _KEEP.sub("", text)


def normalize_zh(text: str) -> str:
    """Comparison form: no punctuation, no spaces, full-width digits folded."""
    return _PUNCT.sub("", unicodedata.normalize("NFKC", text))


def is_han(ch: str) -> bool:
    cp = ord(ch)
    return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or 0xF900 <= cp <= 0xFAFF


def edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def contains_term(text: str, term: str) -> bool:
    """Case-insensitive whole-word match (Unicode aware, Vietnamese diacritics included)."""
    if not term.strip():
        return False
    pattern = r"(?<!\w)" + re.escape(nfc(term.strip())) + r"(?!\w)"
    return re.search(pattern, nfc(text), flags=re.IGNORECASE) is not None


def found_terms(text: str, terms: list[str]) -> list[str]:
    """Terms present as whole words; a term inside a longer found term does not count separately."""
    hits = [t for t in terms if contains_term(text, t)]
    hits.sort(key=len, reverse=True)
    out: list[str] = []
    for t in hits:
        if not any(contains_term(longer, t) and longer.lower() != t.lower() for longer in out):
            out.append(t)
    return out


def split_explicit_lines(vi: str) -> list[str]:
    return [p.strip() for p in re.split(r"\\N|\n", vi) if p.strip()]


def wrap_words(text: str, max_chars: int) -> list[str]:
    """Greedy word wrap; a single word longer than max_chars stays on its own line."""
    lines: list[str] = []
    for part in split_explicit_lines(text) or [""]:
        current = ""
        for word in part.split():
            candidate = f"{current} {word}" if current else word
            if len(candidate) <= max_chars or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return [ln for ln in lines if ln] or [""]


def balanced_wrap(text: str, max_chars: int) -> list[str]:
    """Wrap into the fewest lines, then balance line lengths (nicer subtitles than greedy)."""
    greedy = wrap_words(text, max_chars)
    if len(greedy) != 2 or split_explicit_lines(text) != [text.strip()]:
        return greedy
    words = text.split()
    best: tuple[int, list[str]] | None = None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        if len(a) <= max_chars and len(b) <= max_chars:
            score = abs(len(a) - len(b))
            if best is None or score < best[0]:
                best = (score, [a, b])
    return best[1] if best else greedy


def visible_chars(vi: str) -> int:
    """Characters counted for reading speed: explicit breaks removed, spaces collapsed."""
    return len(" ".join(split_explicit_lines(vi)))
