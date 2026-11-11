"""Decide, per task, WHICH KIND of problem it is -- before attempting it.

This module exists because a single aggregate success rate conflates three different
things, and the conflation hid the real limiting factor for four rounds:

    1. state-addressable   -- a code path to the target artifact exists (file, HTTP, SQL,
                              CLI, URL, or the DOM/accessibility tree of the end state)
    2. hybrid              -- mostly state, with one irreducibly visual subgoal
    3. render-only         -- the task IS a pixel/appearance judgment

The taxonomy is not invented here. StateAct (arXiv 2607.22798) found the same three
classes and a delegation rule: use the GUI subagent only when "no file/backend/DOM path
to the target could be found by probing". It measured that path being needed on 28 of
108 tasks, 1.1% of main-agent steps, and that state-grounding moved partial success from
54.8% to 61.6% at ~9x lower cost.

The finding this module is built to test, measured on MiniWob++ in r83:
TaskFamily has a terminal state that lives ONLY in the DOM. No URL, form, file or
database observes it. So a postcondition compiler -- which is what the five shapes are --
can VERIFY none of them and ELEVATE none of them. That is not a bug in the compiler; it
is the boundary of its class, and it is the same boundary SkillShift-Bench measured as
"Execution Shift" pressure (Src 56.67 -> Src-Exec 33.23).

The rule, in one line: A SKILL REQUIRES AN ADDRESSABLE POSTCONDITION.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

STATE_ADDRESSABLE = "state_addressable"
HYBRID = "hybrid"
RENDER_ONLY = "render_only"
DOM_ONLY_UNOBSERVABLE = "dom_only_unobservable"   # state exists, but in no channel that is code-readable

# Signals that a terminal state is observable WITHOUT reading pixels.
_STATE_SIGNALS = (
    (re.compile(r"<form\b", re.I), "form"),
    (re.compile(r"\bdocument\.location\s*=|location\.search|URLSearchParams", re.I), "url"),
    (re.compile(r"\bfetch\(|XMLHttpRequest|axios", re.I), "http"),
    (re.compile(r"\blocalStorage|\bsessionStorage|\bindexedDB", re.I), "storage"),
    (re.compile(r"\bopen\(|\bsqlite|\.db\b", re.I), "file"),
)

# Signals that the judged property is appearance or geometry.
_RENDER_SIGNALS = (
    (re.compile(r"getBoundingClientRect", re.I), "geometry"),
    (re.compile(r"\bcanvas\b|getContext", re.I), "canvas"),
    (re.compile(r"\b(rgb|rgba|hsl)\(|#[0-9a-f]{6}\b", re.I), "colour"),
    (re.compile(r"\bangle\b|Math\.atan2|\bbisect", re.I), "angle"),
    (re.compile(r"\bdrag|mousedown.*mousemove|dragstart", re.I | re.S), "drag"),
    (re.compile(r"\bfont-?size|opacity|gradient|transform\s*:", re.I), "style"),
)

# Goal shapes whose referent cannot be a token in the goal text.
_REFERENT_BY_PREDICATE = re.compile(
    r"\b(shortest|longest|cheapest|fastest|highest|lowest|largest|smallest|"
    r"ascending|descending|alphabetical|closest|farthest|center|centre)\b", re.I)


_READABLE = re.compile(r"<input[^>]*name\s*=|document\.location|URLSearchParams|fetch\(|"
                       r"localStorage|indexedDB", re.I)


def classify_source(html: str) -> dict[str, Any]:
    """Classify a task's SOURCE by where its terminal state can be observed."""
    # MEASURED FAILURE (r84): a bare <form> tag was enough to call a page skillable. Every
    # MiniWob family has a `<form>` wrapper, so this classified a page we MEASURED as
    # working -- :8901 -- the same way as a family with nothing readable in it. A form is a
    # transport, not a channel: something must NAME the effect (a named input, a URL it
    # drives, a fetch, a store) before a code path exists.
    state = [name for rx, name in _STATE_SIGNALS if rx.search(html)]
    if state == ["form"] and not _READABLE.search(html):
        state = []
    render = [name for rx, name in _RENDER_SIGNALS if rx.search(html)]

    # A family that keeps its state in the DOM alone is render-only for our purposes even
    # when it draws no picture: no code path can OBSERVE the outcome. That distinction --
    # observable without pixels -- is the one that decides whether a skill can exist.
    if state and not render:
        kind = STATE_ADDRESSABLE
    elif state and render:
        kind = HYBRID
    elif render:
        kind = RENDER_ONLY
    else:
        # MEASURED FAILURE (r83). The first version had no fourth case, so a family with
        # NEITHER signal -- no form, no colour, no geometry -- fell into "render_only" by
        # default. That silently claimed 129/130 were pixel problems when the honest answer
        # for most of them was "the terminal state is in neither place we can see". A
        # default must never be an accusation.
        kind = DOM_ONLY_UNOBSERVABLE
    return {"kind": kind, "state_signals": state, "render_signals": render}


def referent_is_predicate(goal: str) -> bool:
    """True when the target is named by a property ("the shortest one"), not a token.

    Measured r83: 39 of 130 MiniWob goals name their target this way and contain no
    literal at all. A demonstration IS the only way to learn which object a predicate
    picked -- which is the one part of the user's thesis that is exactly right.
    """
    return bool(_REFERENT_BY_PREDICATE.search(goal or ""))


def decides_skill(goal: str, html: str) -> dict[str, Any]:
    """Can a compiled skill with an exact postcondition exist for this task?"""
    src = classify_source(html)
    predicate = referent_is_predicate(goal)
    skill_possible = src["kind"] in (STATE_ADDRESSABLE, HYBRID)
    return {
        "task_kind": src["kind"],
        "state_signals": src["state_signals"],
        "render_signals": src["render_signals"],
        "referent_is_predicate": predicate,
        "exact_postcondition_possible": skill_possible,
        "why": ("the terminal state is observable without pixels" if skill_possible else
                "the terminal state exists only as a rendered result; no code path observes it"
                if src["kind"] == RENDER_ONLY else
                "the terminal state is not reachable through any code-readable channel "
                "found by static inspection; it may still be observable at runtime"),
    }
