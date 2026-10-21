"""Pure helpers on proposals: merging, the reviewer's replacement of a term (5.16)."""

from __future__ import annotations

import difflib
import logging

from subagent.kernel import EditRecord, MemoryProposal, contains_term
from subagent.memory.store import (
    dumps,
)

log = logging.getLogger(__name__)


def merge_proposals(proposals: list[MemoryProposal]) -> list[MemoryProposal]:
    """Identical proposals (same kind, source and payload) merge, pooling their evidence."""
    merged: dict[str, MemoryProposal] = {}
    for p in proposals:
        key = dumps([p.kind, p.source, p.payload])
        if key in merged:
            ev = merged[key].evidence
            merged[key].evidence = ev + [e for e in p.evidence if e not in ev]
        else:
            merged[key] = p.model_copy(deep=True)
    return list(merged.values())


def replaced_term(before: str, after: str, term: str) -> str | None:
    """If `term` was in `before` and a human changed it, return what stands in its place in `after`.

    The edit may replace the whole term ("Trúc Cơ" -> "Xây Nền") or only some of its words
    ("Hàng lưỡi Thập Bát Điếu" -> "Hàng Ngư Thập Bát Điếu"); the term's span is followed through the word diff.
    None when the term is still there, was not there, or its new form cannot be told apart (it was deleted, or
    the edit around it is much longer than the term)."""
    if not contains_term(before, term) or contains_term(after, term):
        return None
    a, b = before.split(), after.split()
    t_words = term.split()
    lowered = [w.lower().strip(_PUNCT) for w in a]
    start = next((i for i in range(len(a) - len(t_words) + 1)
                  if lowered[i:i + len(t_words)] == [w.lower() for w in t_words]), None)
    if start is None:
        return None
    end = start + len(t_words)
    js = je = None
    kept: set[int] = set()                       # words of `before` the edit left unchanged
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal":
            kept.update(range(i1, i2))
        if js is None and i1 <= start < i2:
            js = j1 + (start - i1) if op == "equal" else j1
        if je is None and i1 < end <= i2:
            je = j1 + (end - i1) if op == "equal" else j2
    if js is None or je is None or je <= js or je - js > len(t_words) + 2:
        return None
    new = " ".join(b[js:je]).strip(_PUNCT)
    if not new or new.lower() == term.lower():
        return None
    # the new words stand in the term's place only if they share a word with it or a neighbouring word of the
    # line is unchanged; a rewritten line ("Cơ huynh" -> "Đi thôi") gives no form
    shares = bool({w.lower() for w in t_words} & {w.lower().strip(_PUNCT) for w in b[js:je]})
    anchored = (start - 1) in kept or end in kept
    return new if shares or anchored else None


_PUNCT = ".,!?;:…\"'“”"


def reviewed_glossary(proposals: list[MemoryProposal], edits: list[EditRecord]) -> list[MemoryProposal]:
    """A translator's new glossary term cites lines the reviewer may have corrected. Where the reviewer changed
    the term on one of them, the reviewer's form is kept instead (a human proposal, evidence = those edits);
    where the term was removed and its new form cannot be read from the edit, the proposal is dropped. Other
    proposals pass unchanged."""
    vi_edits = {e.event_id: e for e in edits if e.field == "vi" and e.before and e.after}
    out: list[MemoryProposal] = []
    for p in proposals:
        term = str(p.payload.get("vi") or "")
        touched = [vi_edits[e] for e in p.evidence if e in vi_edits] if p.kind == "glossary" else []
        changed = [e for e in touched if contains_term(e.before, term) and not contains_term(e.after, term)]
        if p.source != "translator" or not term or not changed:
            out.append(p)
            continue
        forms = {replaced_term(e.before, e.after, term) for e in changed}
        if len(forms) == 1 and None not in forms:
            out.append(MemoryProposal(kind="glossary", source="human", payload={**p.payload, "vi": forms.pop()},
                                      evidence=[e.edit_id for e in changed]))
            log.info("glossary %s: the reviewer's form replaces the translator's %r", p.payload.get("zh"), term)
        else:
            log.info("glossary %s: dropped, the reviewer changed %r on its lines", p.payload.get("zh"), term)
    return out
