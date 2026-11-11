"""How many DISTINCT writes does a goal require? Measured before attempting it.

WHY (r86). Seven tasks were planned successfully and lost anyway:

    enter-password : "Enter the password "0xMq" into BOTH text fields"
    login-user     : "Enter the username "dolores" AND the password "xGta" ..."
    enter-text-2   : "Type "leonie" in ALL UPPER CASE letters"

The executor bound ONE literal to ONE control. Every one of those goals is arity >= 2 or
carries a TRANSFORM. The planner was never the bottleneck; the binder was. An instrument
that reports one failure number for all of them hides that completely.

This is the same distinction LatentGUIWorld (arXiv 2610.16720) draws between I_0 (prior
knowledge suffices), I_1 (a probe reveals the hidden semantics) and I_2 (the dynamics must
be inferred from action-response). Arity is a cheaper question than either, and it is
decidable from the goal text alone.
"""

from __future__ import annotations

import re
from typing import Any

_QUOTED = re.compile(r'["\u201c\u2018]([^"\u201d\u2019]{1,60})["\u201d\u2019]')

_TRANSFORMS = {
    "upper": re.compile(r"\ball upper\b|\buppercase\b|\bcapital", re.I),
    "lower": re.compile(r"\ball lower\b|\blowercase\b", re.I),
    "reverse": re.compile(r"\breverse[d]?\b|\bbackwards\b", re.I),
    "length": re.compile(r"\blength of\b|\bnumber of characters\b", re.I),
}

_MULTI = re.compile(r"\bboth\b|\ball (?:the )?(?:text )?(?:fields|inputs|boxes)\b|"
                    r"\beach\b|\bevery\b|\band the\b", re.I)


def goal_shape(goal: str) -> dict[str, Any]:
    """Describe the goal's write arity and any transform, from the text alone."""
    g = goal or ""
    literals = _QUOTED.findall(g)
    transforms = [k for k, rx in _TRANSFORMS.items() if rx.search(g)]
    multi = bool(_MULTI.search(g))
    arity = len(literals)
    return {
        "literals": literals,
        "arity": arity,
        "transform": transforms,
        "spreads_across_fields": multi,
        # a single (literal, control) binding is sufficient only in this case
        "single_binding_suffices": arity == 1 and not transforms and not multi,
        "why_not": ([f"needs {arity} literals"] if arity > 1 else [])
                   + ([f"transform {transforms}"] if transforms else [])
                   + (["value spread across several fields"] if multi else []),
    }
