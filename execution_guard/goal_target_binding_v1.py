#!/usr/bin/env python3
"""Turn a plain sentence into a number the machine can chase.

FIRST PRINCIPLE: do not re-implement what already works.

semantic_operator_counterfactuals.extract_semantic_operators already pulls a
numeric bound and its relation out of a sentence, deterministically, and it is
guarded by a counterfactual oracle that fails closed when an extractor maps
"at least 3" to the wrong relation:

    'Earn at least 1000000 USD'    -> MIN_INCLUSIVE  bound 1000000.0
    'Keep costs at most 250.75 USD'-> MAX_INCLUSIVE  bound    250.75
    'no less than 1000000.50 USD'  -> MIN_INCLUSIVE  bound 1000000.5

Its one blind spot is that it only reads digits. "Make me a million dollars"
-- the sentence this whole thing exists for -- yields nothing, because "a
million" is a word.

So this module does exactly one job: rewrite number WORDS and scaled suffixes
into digits, then hand the rewritten sentence to the extractor that already
exists. Nothing is re-parsed, no relation is re-derived, and the counterfactual
guard still applies to the result.

FAIL-CLOSED RULE: if no numeric bound can be found, no target is invented.
"Make me rich" has no number, and a guessed number is worse than no number --
it would let the machine declare MET against a target the owner never set.

Authority: NONE. Credit: 0.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_GOAL_TARGET_BINDING_V1"

BOUND_SCHEMA = "PROJECT_BRAIN_GOAL_TARGET_BINDING_V1_BOUND"

NO_TARGET = "FAIL_CLOSED__NO_NUMERIC_TARGET_IN_GOAL"

# direction: which way the number has to move for the goal to be met
MAXIMIZE = "maximize"   # "at least N"  -> N is a floor to climb to
MINIMIZE = "minimize"   # "at most N"   -> N is a ceiling to get under

# relation -> direction. Anything unrecognised is deliberately absent.
_RELATION_DIRECTION = {"MIN_INCLUSIVE": MAXIMIZE, "MAX_INCLUSIVE": MINIMIZE}

_ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_SCALES = {
    "hundred": 100,
    "thousand": 1_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
    "trillion": 1_000_000_000_000,
}
_SUFFIXES = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000, "t": 1_000_000_000_000}

_WORD_VALUE = {**_ONES, **_TENS}
_ALL_WORDS = sorted(set(_ONES) | set(_TENS) | set(_SCALES), key=len, reverse=True)

# "a million", "one million", "2.5 million"
_WORD_SCALE = re.compile(
    r"\b(?P<num>[+-]?\d+(?:\.\d+)?|a|an|" + "|".join(_ALL_WORDS) + r")\s+"
    r"(?P<scale>" + "|".join(_SCALES) + r")\b",
    re.IGNORECASE,
)
# "1M", "2.5k" -- no space, so "5 m" in "5 metres" is left alone
_SUFFIX = re.compile(r"(?<![\w.])(?P<num>\d+(?:\.\d+)?)(?P<suffix>[kmbt])(?![\w.])", re.IGNORECASE)

_UNITS = {
    "usd": "USD", "dollar": "USD", "dollars": "USD", "$": "USD",
    "eur": "EUR", "euro": "EUR", "euros": "EUR",
    "gbp": "GBP", "pound": "GBP", "pounds": "GBP",
    "inr": "INR", "jpy": "JPY",
    "users": "users", "tests": "tests", "files": "files",
    "bytes": "bytes", "points": "points", "percent": "percent", "%": "percent",
}
_UNIT_TOKEN = re.compile(r"[A-Za-z%$]+")

# A bare quantity ("Make me 1000000 dollars") states no relation at all. The
# extractor correctly refuses it. But refusing the owner's own sentence is not
# useful either, so the relation is INFERRED from the verb -- and recorded as
# inferred, never as extracted. Anything outside these lists stays refused.
_MAXIMIZE_VERBS = frozenset({
    "make", "earn", "reach", "get", "achieve", "hit", "generate", "grow",
    "obtain", "secure", "raise", "gain", "produce", "accumulate", "save",
    "win", "collect", "bank", "net", "clear",
})
_MINIMIZE_VERBS = frozenset({
    "keep", "reduce", "cut", "cap", "limit", "lower", "minimise", "minimize",
    "drop", "shrink", "hold", "stay", "spend", "cost",
})
_BARE_NUMBER = re.compile(r"(?<![\w.])(?P<num>\d+(?:\.\d+)?)(?![\w.])")


def _word_to_number(token: str) -> float | None:
    low = token.lower()
    if low in ("a", "an"):
        return 1.0
    if low in _WORD_VALUE:
        return float(_WORD_VALUE[low])
    return None


def _fmt(value: float) -> str:
    """Plain digits, no float noise: 1000000.0 -> '1000000'."""
    if value == int(value):
        return str(int(value))
    return repr(round(value, 6))


def normalize_number_words(text: str) -> str:
    """Rewrite 'a million' -> '1000000', '1M' -> '1000000'. Nothing else moves."""

    def _suffix(m: re.Match[str]) -> str:
        return _fmt(float(m.group("num")) * _SUFFIXES[m.group("suffix").lower()])

    def _words(m: re.Match[str]) -> str:
        raw = m.group("num").lower()
        base = _word_to_number(raw)
        if base is None:
            base = float(raw)
        return _fmt(base * _SCALES[m.group("scale").lower()])

    out = _SUFFIX.sub(_suffix, text)
    out = _WORD_SCALE.sub(_words, out)
    return out


def _unit_after(text: str, bound_text: str) -> str:
    """Conservative: only report a unit we actually recognise."""
    start = text.lower().find(bound_text.lower())
    if start < 0:
        return ""
    tail = text[start + len(bound_text):]
    for token in _UNIT_TOKEN.findall(tail):
        key = token.lower()
        if key in _UNITS:
            return _UNITS[key]
        if key in _SCALES or key in _SUFFIXES:
            continue  # 'million dollars' -- the scale is not the unit
        break
    return ""


def _infer_from_verb(normalized: str) -> tuple[str, float, str, str] | None:
    """Bare quantity + a verb whose direction is unambiguous.

    Returns (direction, value, matched_text, unit) or None. It never invents a
    number and never guesses a verb outside the whitelists: an unlisted verb
    leaves the goal refused rather than half-understood.
    """
    verbs = set(re.findall(r"[A-Za-z]+", normalized.lower()))
    direction = None
    if verbs & _MAXIMIZE_VERBS and not verbs & _MINIMIZE_VERBS:
        direction = MAXIMIZE
    elif verbs & _MINIMIZE_VERBS and not verbs & _MAXIMIZE_VERBS:
        direction = MINIMIZE
    if direction is None:
        return None

    candidates = []
    for m in _BARE_NUMBER.finditer(normalized):
        tail = normalized[m.end():]
        unit = ""
        for token in _UNIT_TOKEN.findall(tail):
            key = token.lower()
            if key in _UNITS:
                unit = _UNITS[key]
            break
        candidates.append((m.group("num"), unit, m.start()))
    if not candidates:
        return None
    # Prefer a number carrying a recognised unit; if none does, accept a lone
    # unambiguous number. Several undifferentiated numbers is ambiguous -> refuse.
    with_unit = [c for c in candidates if c[1]]
    if with_unit:
        if len(with_unit) > 1:
            return None
        chosen = with_unit[0]
    else:
        if len(candidates) > 1:
            return None
        chosen = candidates[0]
    return direction, float(chosen[0]), chosen[0], chosen[1]


def bind(goal: str) -> dict[str, Any]:
    """Extract {target, direction, unit} from a sentence, or fail closed."""
    if not isinstance(goal, str) or not goal.strip():
        return {"schema": SCHEMA, "status": NO_TARGET, "pass": False, "reason": "GOAL_EMPTY"}

    # Imported here so the module stays importable without the rest of the tree.
    from canonical.runtime.semantic_operator_counterfactuals import (
        extract_semantic_operators,
    )

    normalized = normalize_number_words(goal)
    operators = extract_semantic_operators(normalized, source="goal_target_binding")

    for op in operators:
        direction = _RELATION_DIRECTION.get(op.semantic_class)
        if direction is None or op.bound_value is None:
            continue
        return {
            "schema": SCHEMA,
            "status": "PASS__GOAL_TARGET_BOUND",
            "pass": True,
            "goal": goal,
            "normalized_goal": normalized,
            "target": float(op.bound_value),
            "direction": direction,
            "unit": _unit_after(normalized, op.text),
            "relation": op.semantic_class,
            "relation_source": "EXPLICIT_OPERATOR",
            "evidence": {
                "operator_id": op.operator_id,
                "matched_text": op.text,
                "extractor": "canonical.runtime.semantic_operator_counterfactuals",
            },
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    inferred = _infer_from_verb(normalized)
    if inferred is not None:
        direction, value, matched, unit = inferred
        return {
            "schema": SCHEMA,
            "status": "PASS__GOAL_TARGET_BOUND",
            "pass": True,
            "goal": goal,
            "normalized_goal": normalized,
            "target": value,
            "direction": direction,
            "unit": unit,
            "relation": "INFERRED_" + ("MIN_INCLUSIVE" if direction == MAXIMIZE else "MAX_INCLUSIVE"),
            "relation_source": "INFERRED_FROM_VERB__NOT_AN_EXTRACTION",
            "evidence": {
                "matched_text": matched,
                "extractor": "goal_target_binding_v1._infer_from_verb",
                "warning": "no explicit 'at least'/'at most' operator in the goal; "
                           "direction inferred from the verb and recorded as inferred",
            },
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "status": NO_TARGET,
        "pass": False,
        "goal": goal,
        "normalized_goal": normalized,
        "reason": (
            "NO_NUMERIC_BOUND_IN_GOAL"
            if not operators
            else "NO_MIN_OR_MAX_INCLUSIVE_OPERATOR_AND_NO_INFERABLE_VERB"
        ),
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
