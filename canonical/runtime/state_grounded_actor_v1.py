"""Act on STATE for the class of tasks where the target is a token in the goal.

WHY (r85, measured). The pixel loop failed `choose-date` while the answer sat in the goal
text and a state channel could see the exact control:

    goal  : "Select 08/26/2016 as the date and hit submit."
    state : INPUT id=datepicker (empty), BUTTON id=subbtn "Submit"

Two separate misses compounded there:
  1. the runner extracted only QUOTED literals, so this goal yielded no literal, and the
     no-literal branch performed zero actions and was then scored as a failure (r84);
  2. even given the literal, the actor had no way to address a control by identity.

This module is the r71 design law applied where it is cheap: the page reports location by
STRUCTURE (a state read), and the model is not consulted at all (zero calls). It is NOT a
replacement for the demonstration path -- it is the other half of the delegation rule:

    token named in the goal + a state-readable control  -> act on state   (this module)
    predicate referent ("the shortest one")             -> must be DEMONSTRATED
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

# Tokens a goal may name as a concrete target. Deliberately conservative: dates, numbers
# with separators, quoted strings, capitalised words, and alphanumeric ids.
_TOKEN_PATTERNS = (
    ("date", re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b")),
    ("time", re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")),
    ("quoted", re.compile(r'["\u201c\u2018]([^"\u201d\u2019]{1,60})["\u201d\u2019]')),
    ("ident", re.compile(r"\b(?=[A-Za-z0-9]*[0-9])[A-Za-z0-9]{2,}\b|\b[A-Za-z]{3,}\b")),
)


def extract_targets(goal: str) -> list[tuple[str, str]]:
    """Every concrete token in the goal, most specific first. No model, no guessing."""
    found: list[tuple[str, int, str]] = []
    taken: list[tuple[int, int]] = []
    for kind, rx in _TOKEN_PATTERNS:
        for m in rx.finditer(goal or ""):
            s, e = m.span(1) if m.groups() else m.span()
            if any(not (e <= a or s >= b) for a, b in taken):
                continue
            val = (m.group(1) if m.groups() else m.group(0)).strip()
            if not val:
                continue
            taken.append((s, e))
            found.append((kind, s, val))
    return [(k, v) for k, _, v in found]


# Words that name an ACTION or a goal shape, never a target.
_STOP = {"click", "select", "from", "and", "the", "with", "press", "submit", "enter",
         "type", "into", "down", "one", "two", "list", "date", "hit", "then", "on", "of",
         "your", "answer", "below", "above", "field", "hit", "now", "here"}


def rank_targets(goal: str, state: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Rank (token, control) pairs by whether the control's text contains the token.

    Pure structure: `state` comes from state_read_v1.list_of. No pixels, no model.
    """
    toks = [(k, v) for k, v in extract_targets(goal) if v.lower() not in _STOP]
    out: list[dict[str, Any]] = []
    for kind, tok in toks:
        for n in state:
            text = (n.get("text") or "")
            hit = tok.lower() in text.lower()
            out.append({"kind": kind, "token": tok, "tag": n.get("tag"), "id": n.get("id"),
                        "text_contains_token": hit})
    out.sort(key=lambda r: (not r["text_contains_token"], r["kind"] != "date"))
    return out


def pick_write_target(goal: str, state: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """The control to WRITE a named token into, if one is unambiguous.

    A writable control is an <input>/<textarea> that is visible and empty or editable.
    If more than one is writable the choice is ambiguous and this returns None -- a
    router that cannot tell two targets apart must refuse (r68).
    """
    writable = [n for n in state
                if str(n.get("tag", "")).upper() in ("INPUT", "TEXTAREA")
                and n.get("vis") and str(n.get("text") or "") == ""]
    if len(writable) != 1:
        return None
    toks = [(k, v) for k, v in extract_targets(goal) if v.lower() not in _STOP]
    date = [v for k, v in toks if k in ("date", "time")]
    if not date:
        return None
    return {"control": writable[0], "value": date[0]}


def pick_submit_target(state: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """The single visible control named submit/go/send/done, if unambiguous."""
    want = {"submit", "go", "send", "done", "ok"}
    hits = [n for n in state
            if n.get("vis") and str(n.get("text") or "").strip().lower() in want]
    if len(hits) != 1:
        return None
    return {"control": hits[0]}
