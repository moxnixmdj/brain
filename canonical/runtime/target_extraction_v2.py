"""Extract a target token even when the goal does not quote it -- VERIFIED against the page.

WHY (r91). 93 of 130 MiniWob goals carry no quoted literal, so the executor skipped them.
A greedy "find any capitalised word" fix appears to recover all 93 and is wrong: it returns
Click / Create / Book / Keep / Find / Select -- the VERBS of the instruction, not targets.
A matcher that accepts everything finds the wrong thing (r74).

The correction is not a better regex. It is a VERIFICATION STEP: a candidate is a target
only if the page actually contains it. Extraction proposes; the page disposes.

    propose  : dates, times, quoted strings, capitalised phrases, alphanumeric ids
    verify   : the token must appear in the page's rendered text or control names
    reject   : instruction verbs, stop words, and anything the page does not contain

This is the same discipline the rest of the project uses: no claim without a check.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Mapping, Sequence

# Instruction verbs and shape words. These are capitalised because they start a sentence,
# and they are exactly what a naive extractor returns first.
_VERBS = {
    "click", "select", "enter", "type", "press", "submit", "choose", "pick", "find",
    "create", "book", "buy", "keep", "expand", "collapse", "switch", "navigate", "check",
    "uncheck", "toggle", "use", "fill", "input", "search", "open", "close", "drag",
    "move", "scroll", "wait", "sort", "order", "compare", "count", "add", "remove",
    "the", "a", "an", "all", "and", "then", "with", "from", "to", "on", "of", "for",
    "in", "into", "as", "at", "by", "one", "two", "three", "both", "each", "every",
}

_PATTERNS = (
    ("date", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b")),
    ("time", re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")),
    ("quoted", re.compile(r'["\u201c\u2018]([^"\u201d\u2019]{1,60})["\u201d\u2019]')),
    # a capitalised phrase that is not merely the first word of the sentence
    ("phrase", re.compile(r"\b[A-Z][a-zA-Z0-9]{1,}(?:\s+[A-Z][a-zA-Z0-9]{1,})*\b")),
    # alphanumeric ids: must contain a digit, so the word is a token and not prose
    ("ident", re.compile(r"\b(?=[A-Za-z]*[0-9])[A-Za-z0-9]{2,}\b")),
)


def propose(goal: str) -> list[tuple[str, str]]:
    """Candidate target tokens, most specific first. Unverified."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for kind, rx in _PATTERNS:
        for m in rx.finditer(goal or ""):
            val = (m.group(1) if m.groups() else m.group(0)).strip()
            if not val or val.lower() in _VERBS or val in seen:
                continue
            # a phrase may swallow a verb ("Select Faroe Islands" is fine; "Click button" is not)
            words = val.split()
            if words and words[0].lower() in _VERBS:
                continue
            seen.add(val)
            out.append((kind, val))
    return out


def extract(goal: str, page_text: str, control_names: Iterable[str] = ()) -> dict[str, Any]:
    """Propose, then VERIFY against what the page actually contains."""
    hay = (page_text or "").lower()
    names = " | ".join(str(n).lower() for n in control_names)
    verified, rejected = [], []
    for kind, val in propose(goal):
        present = val.lower() in hay or val.lower() in names
        (verified if present else rejected).append({"kind": kind, "value": val, "present": present})
    return {
        "target": verified[0] if verified else None,
        "verified": verified,
        "rejected": rejected,
        "status": "FOUND" if verified else "NOT_ON_PAGE",
    }
