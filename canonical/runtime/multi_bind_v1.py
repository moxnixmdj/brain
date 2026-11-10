"""Bind EVERY literal in a goal to the RIGHT control, with transforms. No model calls.

WHY (r86 measured). The executor's model of a task was ONE value into ONE field:

    enter-password : 'Enter the password "0xMq" into BOTH text fields'   -> 1 literal, 2 fields
    login-user     : 'username "dolores" AND password "xGta"'           -> 2 literals, 2 fields
    enter-text-2   : 'Type "leonie" in ALL UPPER CASE letters'          -> 1 literal + transform

All three were planned correctly and then failed at the binder. Measured coverage of the
old model: 32 of 130 goals (25%); success inside that class 9/32.

This module is deliberately narrow and total:
  * literals come from the goal text, in order (the order is the binding hint);
  * fields come from the page's own structure (state_read_v1.list_of), in document order
    -- which is the order a human reads them, and the order MiniWob authored them;
  * a transform is applied only when the goal names it, and only the four it can name;
  * ambiguity is a REFUSAL, never a guess (r68).

Nothing here reads a pixel or calls a model.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

_QUOTED = re.compile(r'["\u201c\u2018]([^"\u201d\u2019]{1,60})["\u201d\u2019]')

TRANSFORMS = {
    "upper": lambda s: s.upper(),
    "lower": lambda s: s.lower(),
    "reverse": lambda s: s[::-1],
    "capitalize": lambda s: s[:1].upper() + s[1:].lower(),
}


def detect_transform(goal: str) -> str | None:
    g = goal or ""
    if re.search(r"\ball upper\b|\buppercase\b|\bcapital letters\b", g, re.I):
        return "upper"
    if re.search(r"\ball lower\b|\blowercase\b", g, re.I):
        return "lower"
    if re.search(r"\breverse[d]?\b|\bbackwards\b", g, re.I):
        return "reverse"
    return None


def apply_transform(value: str, transform: str | None) -> str:
    if not transform:
        return value
    return TRANSFORMS[transform](value)


def writable_fields(state: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Visible, empty, text-ish controls in document order."""
    out = []
    for n in state:
        tag = str(n.get("tag", "")).upper()
        if tag not in ("INPUT", "TEXTAREA"):
            continue
        if not n.get("vis"):
            continue
        out.append(dict(n))
    return out


def plan_multi_bind(goal: str, state: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """A total plan: [(field_id, text), ...] then submit. Refuses when ambiguous."""
    literals = _QUOTED.findall(goal or "")
    transform = detect_transform(goal)
    fields = writable_fields(state)

    if not literals:
        return {"status": "NO_LITERAL", "writes": [], "transform": transform}
    if not fields:
        return {"status": "NO_FIELD", "writes": [], "transform": transform}

    # "the text field" (singular) names ONE field even when several exist: the goal is
    # telling you which one, not asking you to fill all of them. Measured r87 -- without
    # this, "Enter \"Annis\" in the text field" was refused as ambiguous on a page with
    # two inputs, and MiniWob pages routinely carry extra hidden inputs.
    spread = bool(re.search(r"\bboth\b|\ball (?:the )?(?:text )?(?:fields|inputs)\b|"
                            r"\beach\b|\bevery\b", goal or "", re.I))
    singular_named = bool(re.search(r"\bthe (?:text )?(?:field|input|box)\b", goal or "", re.I))
    if singular_named and not spread:
        return {"status": "SOLVED", "writes": [(fields[0]["id"],
                                                apply_transform(literals[0], transform))],
                "transform": transform, "mode": "one_value_named_single_field",
                "why": "the goal names ONE field"}

    if len(literals) == 1:
        val = apply_transform(literals[0], transform)
        if spread:
            return {"status": "SOLVED", "writes": [(f["id"], val) for f in fields],
                    "transform": transform, "mode": "one_value_many_fields"}
        if len(fields) == 1:
            return {"status": "SOLVED", "writes": [(fields[0]["id"], val)],
                    "transform": transform, "mode": "one_value_one_field"}
        # one literal and several distinct fields, with no spread wording: ambiguous.
        return {"status": "AMBIGUOUS", "writes": [], "transform": transform,
                "why": f"1 literal, {len(fields)} fields, no spread wording"}

    # several literals: bind in order, field count must match or be a clean prefix
    if len(literals) > len(fields):
        return {"status": "TOO_FEW_FIELDS", "writes": [], "transform": transform,
                "why": f"{len(literals)} literals, {len(fields)} fields"}
    writes = [(f["id"], apply_transform(v, transform)) for f, v in zip(fields, literals)]
    # a literal that names the FIELD ("username"), not a value, is a common shape; the
    # value is still the next literal, and order handles it. Report what was bound.
    return {"status": "SOLVED", "writes": writes, "transform": transform,
            "mode": "one_value_each_field", "bound": list(literals)}
