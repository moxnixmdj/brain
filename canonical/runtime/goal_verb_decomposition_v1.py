"""Read the verb, not the sentence.

THE FAILURE THIS REPLACES
-------------------------
r130/r131 measured this project's reach on unselected MiniWob++ samples: 6/60 and
5/40. The dominant failure was not perception, not resolution and not learning --
28 of 40 tasks were never ATTEMPTED. The policy matched five hand-written goal
shapes and MinimWob has dozens.

Reading all 130 task files showed why that was the wrong shape of solution. The
goals are not infinitely varied. They share one structure:

    VERB  <operand>

with about sixteen verbs in total (click, enter, type, select, drag, draw, find,
highlight, scroll, focus, copy, set, sort, push, switch, move, expand) and an
operand that is one of a small number of kinds (a quoted token, an ordinal, a
colour, a coordinate, a number, a direction, a repeated item). Forty-five
sentence patterns collapse to sixteen verbs times a handful of operand kinds.

A policy that hard-codes sentence patterns has coverage proportional to how many
patterns somebody wrote. A policy that parses verb and operand has coverage
proportional to how many VERBS it implements, and verbs are what the environment
actually offers. That is the difference between 30% and something worth measuring.

WHAT THIS MODULE DOES
---------------------
It is pure: text in, plan out. No browser, no environment. It answers one
question -- "what verb is this goal asking for, and what is the operand" -- and
returns a plan carrying the primitive the runner should use. It never invents a
verb it does not implement; an unrecognised goal returns UNSUPPORTED_VERB with
the verb it saw, so coverage gaps are counted rather than hidden behind a
generic click.

THE HONEST LIMIT
----------------
Parsing the verb does not make the verb work. `draw-line` needs a freehand
stroke, `simon-says` needs memory, `bisect-angle` needs geometry. A verb plan
raises COVERAGE, which is the factor this project measured at 30%; it does not
raise the success rate within a verb, which was already 5/12 among attempted
tasks. Both numbers must be reported separately or the improvement is fake.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_GOAL_VERB_DECOMPOSITION_V1"

# (verb, regex on the lowered goal). Order matters: more specific first.
VERB_PATTERNS = (
    ("SET_SLIDERS", r"\bset the sliders to the combination\b"),
    ("SORT", r"\bsort the numbers\b"),
    ("PUSH_SEQUENCE", r"\bpush the buttons in the order\b"),
    ("SIMON", r"\b(repeat|memorize|watch the sequence)\b"),
    ("COPY_PASTE", r"\bcopy the text\b.*\bpaste\b"),
    ("FIND_AND_TYPE", r"\bfind the last word in the text area\b"),
    ("SWITCH_TABS", r"\bswitch between the tabs\b"),
    ("EXPAND_AND_CLICK", r"\bexpand the (pie menu|section)"),
    ("HIGHLIGHT", r"\bhighlight the text\b"),
    ("SCROLL_TO", r"\bscroll the textarea to the\b"),
    ("FOCUS", r"\bfocus into the\b"),
    ("DRAW", r"\bdraw (a|the number)\b"),
    ("MOVE", r"\bmove the cube around\b"),
    ("DRAG", r"\bdrag (the|all)\b"),
    ("ENTER", r"\b(enter|type)\b"),
    ("SELECT", r"\bselect\b"),
    ("FIND", r"\bfind the\b"),
    ("CLICK", r"\bclick\b"),
)


def _number(text: str) -> int | None:
    m = re.search(r"(-?\d+)", text)
    return int(m.group(1)) if m else None


def _quoted(text: str) -> str | None:
    m = re.search(r'"([^"]*)"', text) or re.search(r"\u201c([^\u201d]*)\u201d", text)
    return m.group(1).strip() if m else None


def _colour(text: str) -> str | None:
    """Colour words, from the one list this repo already keeps.

    This used to be an absolute package import (`from canonical.runtime import ...`) executed
    at call time. When the module is loaded from a file path -- which every measurement
    harness in this project does -- that import raises ModuleNotFoundError, the exception
    escapes decompose(), and the episode is recorded as a generic failure with no action
    attempted. That silently removed every colour-operand goal from r137 while leaving the
    other tasks intact, so the run looked like a capability loss and was really an import
    bug. The sibling import is now guarded and falls back to a local list.
    """
    try:
        from canonical.runtime import appearance_address_v1 as appearance   # noqa: PLC0415
        colours = appearance.COLOURS
    except Exception:
        colours = ("black", "white", "red", "green", "blue", "yellow", "olive",
                   "cyan", "magenta", "pink", "gray", "grey", "orange", "purple",
                   "brown", "navy", "teal", "silver", "lime", "maroon")
    for word in colours:
        if re.search(r"\b" + re.escape(word) + r"\b", text, re.I):
            return word
    return None


def _path(text: str) -> list[str] | None:
    """A>B>C nesting, as used by the menu tasks."""
    m = re.search(r"select\s+([^\s>]+(?:>[^\s>]+)+)", text, re.I)
    return [p.strip() for p in m.group(1).split(">")] if m else None


def decompose(goal: str) -> dict[str, Any]:
    """Return {verb, operand, plan} for a goal sentence, or an explicit refusal."""
    text = " ".join(str(goal or "").split())
    if not text:
        return {"schema": SCHEMA, "verb": None, "status": "EMPTY_GOAL", "plan": None}

    lowered = text.lower()
    verb = None
    for name, pattern in VERB_PATTERNS:
        if re.search(pattern, lowered):
            verb = name
            break
    if verb is None:
        return {"schema": SCHEMA, "verb": None, "status": "UNSUPPORTED_VERB",
                "plan": None, "goal": text,
                "reason": "no known verb appears in this goal"}

    operand: dict[str, Any] = {}
    if verb in ("SET_SLIDERS",):
        operand["values"] = [int(x) for x in re.findall(r"-?\d+", text)]
    elif verb in ("DRAG", "MOVE", "SORT"):
        operand["quoted"] = _quoted(text)
        operand["number"] = _number(text)
    elif verb in ("SELECT",):
        operand["path"] = _path(text)
        if operand["path"] is None:
            m = re.search(r"select\s+(.+?)\s*(?:from the list|and click submit|$)", text, re.I)
            operand["token"] = m.group(1).strip() if m else None
        operand["colour"] = _colour(text)
    elif verb in ("ENTER", "FIND_AND_TYPE"):
        operand["token"] = _quoted(text)
        if operand["token"] is None:
            m = re.search(r"(?:enter|type)\s+([A-Za-z0-9_\-]+)", text, re.I)
            operand["token"] = m.group(1) if m else None
        operand["field"] = "textarea" if "textarea" in lowered else "text"
    elif verb in ("CLICK", "FIND", "HIGHLIGHT", "SCROLL_TO", "FOCUS", "EXPAND_AND_CLICK"):
        operand["quoted"] = _quoted(text)
        operand["colour"] = _colour(text)
        operand["number"] = _number(text)
        if operand["quoted"] is None:
            m = re.search(r"click on the\s+([a-z][a-z\- ]{2,20}?)\s+button", lowered)
            operand["button_word"] = m.group(1).strip() if m else None
    elif verb in ("DRAW",):
        operand["quoted"] = _quoted(text) or (str(_number(text)) if _number(text) is not None else None)
    elif verb in ("PUSH_SEQUENCE", "SIMON", "COPY_PASTE", "SWITCH_TABS"):
        operand["quoted"] = _quoted(text)
    elif verb in ("SCROLL_TO",):
        operand["quoted"] = _quoted(text)

    return {"schema": SCHEMA, "verb": verb, "status": "DECOMPOSED",
            "operand": operand, "goal": text}


def coverage_of(goals: list[str]) -> dict[str, Any]:
    """How many of these goals decompose at all, and to which verbs."""
    counts: dict[str, int] = {}
    unsupported = []
    for g in goals:
        d = decompose(g)
        if d["status"] == "DECOMPOSED":
            counts[d["verb"]] = counts.get(d["verb"], 0) + 1
        else:
            unsupported.append(g[:70])
    total = len(goals)
    covered = total - len(unsupported)
    return {"total": total, "covered": covered,
            "coverage": round(covered / total, 4) if total else 0.0,
            "by_verb": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
            "unsupported": unsupported}
