"""Ground a goal by SEARCHING THE PAGE, not by parsing the sentence.

THE INVERSION (r92). Everything before this round tried to read the instruction and
extract a target: quoted literals, then dates, then "capitalised words that are not
verbs". Two of those three attempts produced false positives that would have inflated the
result, and the third produced nothing. The approach was wrong, not the implementation.

The goal is UNDERSPECIFIED LANGUAGE. The page is FULLY SPECIFIED DATA. So the question is
not "what does the sentence mean", it is:

    which string that ALREADY EXISTS ON THE PAGE is mentioned in the sentence?

That is a set intersection, not a parse. It needs no verb list, no capitalisation rule, no
date grammar, and no demonstration. It is also self-verifying: the answer is a string the
page actually renders, so it can be clicked and checked.

    candidates = every rendered text run and control name on the page
    score      = how much of the candidate appears in the goal
    pick       = the longest candidate the goal mentions, ties refused

Nothing here knows what a date is. It does not need to.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Sequence

_WS = re.compile(r"\s+")

# Words so common on a page that matching them says nothing about the goal.
_BOILERPLATE = {
    "submit", "go", "send", "done", "ok", "click", "select", "enter", "type", "press",
    "button", "input", "text", "field", "the", "a", "an", "and", "or", "of", "to", "in",
    "on", "for", "with", "date", "list", "item", "one", "two", "three", "here", "now",
    "last", "first", "next", "back", "cancel", "close", "open", "yes", "no", "true", "false",
}


def candidates(page_texts: Iterable[str], control_names: Iterable[str] = ()) -> list[str]:
    """Every string the page actually shows, cleaned and deduplicated."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in list(page_texts) + list(control_names):
        s = _WS.sub(" ", str(raw or "")).strip()
        if not s or len(s) > 80:
            continue
        low = s.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(s)
    return out


def ground(goal: str, page_texts: Iterable[str], control_names: Iterable[str] = ()) -> dict[str, Any]:
    """Which page string does the goal mention? Longest wins; a tie is refused."""
    goal_low = _WS.sub(" ", str(goal or "")).lower()

    # MEASURED FAILURE (r92). MiniWob RENDERS THE GOAL onto the page, so "the longest page
    # string mentioned in the goal" was the goal itself -- every match was the instruction
    # quoting itself back. The goal is not evidence about the page; it must be removed from
    # the candidate set before searching.
    def _not_the_goal(x: Iterable[str]) -> list[str]:
        """Remove only the RENDERED GOAL, never the target.

        My first version removed any page string that appeared IN the goal -- which is
        precisely the target being searched for. 'Tab #1' was on the page and in the goal
        and got deleted, so a trivially solvable task reported NOT_MENTIONED. The page
        renders the whole instruction, so the thing to remove is a string that CONTAINS
        the goal and is longer than it.
        """
        out = []
        for t in x:
            tl = _WS.sub(" ", str(t or "")).lower().strip()
            if not tl:
                continue
            if goal_low in tl and len(tl) >= len(goal_low):
                continue          # this is the goal rendered onto the page
            out.append(t)
        return out
    page_texts = _not_the_goal(page_texts)
    control_names = _not_the_goal(control_names)
    scored: list[tuple[int, str]] = []
    for cand in candidates(page_texts, control_names):
        cl = cand.lower()
        if not cl.strip():
            continue
        if cl in goal_low:
            # A generic control name is almost always the SUBMIT step, not the target:
            # "Submit" appears in "Select X and click Submit" on nearly every goal and is
            # the longest match after the goal itself, so it won every tie and produced
            # target='Submit' on 4 of 6 tasks (measured r92). Rank it far below everything.
            if cl in _BOILERPLATE:
                scored.append((1, cand))
            else:
                scored.append((len(cl) + 100, cand))
    if not scored:
        return {"status": "NOT_MENTIONED", "target": None, "considered": 0}
    scored.sort(key=lambda t: -t[0])
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        # two page strings of equal length both appear in the goal: refuse to pick
        return {"status": "AMBIGUOUS", "target": None,
                "tied": [c for n, c in scored if n == scored[0][0]][:5]}
    return {"status": "GROUNDED", "target": scored[0][1],
            "rank": scored[:5], "considered": len(scored)}
