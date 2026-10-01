"""Deterministic bounded decomposition of explicit compound requirements.

This component only decomposes source forms whose coordination is structurally
unambiguous. Anything with ambiguous scope, implicit semantics, pronouns,
comparatives, exceptions, nested coordination, or long-range context fails closed.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "BRAIN_EXPLICIT_COMPOUND_REQUIREMENT_DECOMPOSER_V1"

_BULLET = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+(.+?)\s*$")
_MODAL = re.compile(r"\b(must|shall|required to|is required to)\b", re.I)
_AMBIGUOUS = re.compile(
    r"\b(unless|except|excepting|either|neither|respectively|former|latter|"
    r"it|they|them|this|that|these|those|above|below)\b",
    re.I,
)


def _clean(s: str) -> str:
    return " ".join(s.strip().split())


def _has_single_modal(s: str) -> bool:
    return len(list(_MODAL.finditer(s))) == 1


def decompose_explicit_compound(text: str) -> dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "EMPTY"}

    raw_lines = [line for line in text.splitlines() if line.strip()]
    bullets = []
    all_bullets = True
    for line in raw_lines:
        m = _BULLET.match(line)
        if not m:
            all_bullets = False
            break
        bullets.append(_clean(m.group(1)))

    if all_bullets and len(bullets) >= 2:
        if any(_AMBIGUOUS.search(x) for x in bullets):
            return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "AMBIGUOUS_REFERENCE"}
        return {
            "schema": SCHEMA,
            "status": "DECOMPOSED",
            "route": "EXPLICIT_LIST",
            "obligations": bullets,
            "count": len(bullets),
            "terminal_authority": False,
        }

    s = _clean(text)
    if _AMBIGUOUS.search(s):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "AMBIGUOUS_SCOPE"}

    # Bounded route: one explicit modal applying to a flat "X and Y" predicate
    # where both conjuncts are nonempty and no nested coordinator appears.
    if not _has_single_modal(s):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "MODAL_SHAPE_UNSUPPORTED"}

    modal = next(_MODAL.finditer(s))
    prefix = s[: modal.end()]
    tail = s[modal.end():].strip()

    if " or " in tail.lower() or ";" in tail or "," in tail:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "NESTED_OR_AMBIGUOUS_COORDINATION"}

    parts = re.split(r"\s+and\s+", tail, flags=re.I)
    if len(parts) != 2 or any(not p.strip() for p in parts):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "COMPOUND_SHAPE_UNSUPPORTED"}

    left, right = (_clean(p) for p in parts)
    if any(_MODAL.search(p) for p in (left, right)):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "error": "NESTED_MODAL"}

    obligations = [f"{prefix} {left}", f"{prefix} {right}"]
    return {
        "schema": SCHEMA,
        "status": "DECOMPOSED",
        "route": "FLAT_SHARED_MODAL_AND",
        "obligations": obligations,
        "count": 2,
        "terminal_authority": False,
    }
