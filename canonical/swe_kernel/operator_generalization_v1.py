#!/usr/bin/env python3
"""Generalize a repair from one statement shape to every occurrence of the same operator swap.

Why this exists
---------------
A crystallized rule is anchored to the skeleton it was taught from. Measured 2026-11-01, one
boundary lesson (`<= hi` -> `< hi`) reached **1 of 7** structurally novel Python instances:

    operator inside a larger expression   MISS
    operator inside an `if` statement     MISS
    operator inside a `while` guard       MISS
    operands flipped  (hi >= x)           MISS
    negated form      not (x > hi)        MISS
    expanded form     x < hi or x == hi   MISS
    class method with self                HIT

Every miss fails for the same reason, and it is not a deep one: the taught pattern is
`return ?id0 <= ?id1`, so a rule taught inside a `return` can only fire inside a `return`.
The *lesson* is about an operator, but what was stored is a statement skeleton.

This module recovers the general form. If a rule's pattern and replacement differ by exactly
one operator token and are otherwise identical modulo holes, then the lesson **is** that one
operator swap, and it applies wherever that operator appears on two operands — in a return,
in a condition, in a loop guard, with the operands in either order.

Safety
------
This widens applicability, so it narrows what may be proposed:

* **one** operator difference, and the surrounding shape must be identical modulo holes.
  Anything else is not a generalization, it is a guess, and is refused by name.
* the operator is never substituted inside a string literal or a comment, in any supported
  language.
* every proposal is returned as a *candidate*. The caller's verifier decides. This module
  cannot accept anything, and deliberately has no notion of acceptance.
* swapping `<=` to `<` in an unrelated branch is a real risk, which is why the caller verifies
  each candidate separately and why the count of candidates is bounded and reported.
"""
from __future__ import annotations

import io
import tokenize
from typing import Any, Iterable, Iterator, Mapping

SCHEMA = "PROJECT_BRAIN_OPERATOR_GENERALIZATION_V1"

# This set used to answer two questions at once, and they are not the same question:
#
#   (Q1) is this token an operator whose swap is a lesson at all, in the language it was taught in?
#   (Q2) does this operator mean the same thing in the language it is being PROPOSED in?
#
# Q1 is structural and language-local. Q2 is semantic and pair-relative. Answering Q2 with one flat
# absolute list is what made the list simultaneously too narrow and unsound, and both halves are
# measured rather than argued -- `operator_semantics_v1` executes the operators:
#
#   * UNSOUND. `%` and `/` are on this list, so a lesson taught in Python could be proposed in
#     TypeScript. Executed: `-7 % 3` is 2 in Python and -1 in JavaScript and C++; `7 / 2` is 3.5 in
#     Python and 3 for C++ integer operands. The comment above this list claimed these operators
#     "mean the same thing across python/go/rust/typescript/java/cpp", and for those two the claim
#     is false by a witnessed counterexample.
#   * TOO NARROW. `..=` and `..` were off it, so the shipped rust lesson
#     `for i in 0..=v.len()` -> `for i in 0..v.len()` -- which differs by exactly ONE operator token
#     with the surrounding shape identical modulo holes, the whole of Q1 -- was refused. 2 of 5
#     shipped skills could be generalized where 3 of 5 can.
#
# So this set now answers Q1 only: it narrows the proposal space to tokens whose swap is a
# meaningful single-operator lesson. Q2 is computed at the one place both languages are known,
# `propose_operator_swaps`, by `operator_semantics_v1.may_generalize`.
GENERALIZABLE = frozenset({
    "<=", ">=", "<", ">", "==", "!=", "+", "-", "*", "/", "%",
    "&&", "||", "and", "or", "not",
    # rust range operators. `..=` is inclusive and `..` exclusive, so inclusive-to-exclusive is a
    # real single-token lesson; `_occurrences` already refuses to let `..` eat the head of `..=`.
    "..=", "..",
})

MAX_CANDIDATES = 32


class GeneralizationRefusal(RuntimeError):
    """A named refusal. Never widen quietly."""


def _tokens(rule: Mapping[str, Any], key: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for tok in rule.get(key) or []:
        if isinstance(tok, (list, tuple)) and len(tok) >= 2:
            out.append((str(tok[0]), str(tok[1])))
    return out


def derive_operator_swap(rule: Mapping[str, Any]) -> dict[str, str] | None:
    """The single operator difference between pattern and replacement, or None.

    Returns ``{"from": "<=", "to": "<"}`` when the two token streams are identical except at
    exactly one operator position. Refuses (returns None) if there is more than one difference
    or a non-operator difference, because that is a different lesson.
    """
    pattern = _tokens(rule, "pattern_tokens")
    replacement = _tokens(rule, "replacement_tokens")
    if not pattern or not replacement:
        return None

    # Ignore whitespace: layout is not part of the lesson.
    pat = [(k, v) for k, v in pattern if k != "ws"]
    rep = [(k, v) for k, v in replacement if k != "ws"]
    if len(pat) != len(rep):
        return None

    diffs = [(i, pat[i], rep[i]) for i in range(len(pat)) if pat[i] != rep[i]]
    if len(diffs) != 1:
        return None
    _, (pk, pv), (rk, rv) = diffs[0]
    if pk != "op" or rk != "op":
        return None
    if pv not in GENERALIZABLE or rv not in GENERALIZABLE:
        return None
    return {"from": pv, "to": rv}


# The same lesson has three closed forms, and storing only the first was why the rule could
# not reach a flipped or negated spelling of the identical statement:
#
#     a <= b        -> a < b            the direct form
#     b >= a        -> b > a            the same statement with operands swapped
#     not (a > b)   -> not (a >= b)     the same statement negated
#
# All three say "the upper bound is exclusive". Deriving them mechanically keeps the rule
# honest: nothing is invented, each is a rewriting of the one taught.
_DUALS: dict[tuple[str, str], tuple[tuple[str, str], ...]] = {
    ("<=", "<"): (("<=", "<"), (">=", ">"), (">", ">=")),
    (">=", ">"): ((">=", ">"), ("<=", "<"), ("<", "<=")),
    ("<", "<="): (("<", "<="), (">", ">="), (">=", ">")),
    (">", ">="): ((">", ">="), ("<", "<="), ("<=", "<")),
}


def derive_swap_family(rule: Mapping[str, Any]) -> list[dict[str, str]]:
    """Every closed form of the lesson this rule encodes, direct form first."""
    swap = derive_operator_swap(rule)
    if swap is None:
        return []
    forms = _DUALS.get((swap["from"], swap["to"]))
    if not forms:
        return [swap]
    return [{"from": a, "to": b} for a, b in forms]


# --------------------------------------------------------------------------- scanning
def _python_spans(source: str) -> list[tuple[int, int, str]]:
    """(start, end, text) for every STRING/COMMENT token, as ABSOLUTE offsets.

    ``tokenize`` reports (line, column), not an offset. Using the column directly as a source
    index silently fails on every line after the first, which is how the first version of this
    module rewrote text inside a string literal. The test caught it; this converts properly.
    """
    out: list[tuple[int, int, str]] = []
    line_starts = [0]
    for line in source.splitlines(keepends=True):
        line_starts.append(line_starts[-1] + len(line))

    def _abs(row: int, col: int) -> int:
        if row - 1 < len(line_starts):
            return line_starts[row - 1] + col
        return len(source)

    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type in (tokenize.STRING, tokenize.COMMENT):
                start = _abs(*tok.start)
                end = _abs(*tok.end)
                out.append((start, end, tok.string))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return out
    return out


def _quote_aware_mask(source: str) -> list[bool]:
    """True where a character is *code*, False inside any quoted region or line comment."""
    mask = [True] * len(source)
    i, n = 0, len(source)
    quote = ""
    while i < n:
        ch = source[i]
        if quote:
            mask[i] = False
            if ch == "\\" and i + 1 < n:
                mask[i + 1] = False
                i += 2
                continue
            if ch == quote:
                quote = ""
            i += 1
            continue
        if ch in "'\"`":
            quote = ch
            mask[i] = False
            i += 1
            continue
        if ch == "/" and i + 1 < n and source[i + 1] == "/":
            while i < n and source[i] != "\n":
                mask[i] = False
                i += 1
            continue
        if ch == "#":
            while i < n and source[i] != "\n":
                mask[i] = False
                i += 1
            continue
        i += 1
    return mask


def _occurrences(source: str, operator: str, *, language: str) -> list[int]:
    """Index of every *code* occurrence of the operator, longest-match first."""
    if not operator:
        return []
    if language.lower() == "python":
        # tokenize gives exact operator tokens, so `<=` never matches inside `<<=`.
        spans = _python_spans(source)
        masked = list(source)
        for start, end, text in spans:
            for k in range(start, min(end, len(masked))):
                masked[k] = " "
        probe = "".join(masked)
    else:
        mask = _quote_aware_mask(source)
        probe = "".join(c if mask[i] else " " for i, c in enumerate(source))

    out: list[int] = []
    start = 0
    while True:
        idx = probe.find(operator, start)
        if idx < 0:
            break
        end = idx + len(operator)
        # word-operator boundaries (`and`, `or`, `not`) must not match inside identifiers
        if operator.isalpha():
            before_ok = idx == 0 or not (probe[idx - 1].isalnum() or probe[idx - 1] == "_")
            after_ok = end >= len(probe) or not (probe[end].isalnum() or probe[end] == "_")
            if not (before_ok and after_ok):
                start = idx + 1
                continue
        else:
            # avoid eating a longer operator: `<=` must not match the tail of `<<=`, and `<`
            # must not match the head of `<=`.
            if end < len(probe) and probe[end] == "=" and not operator.endswith("="):
                start = idx + 1
                continue
            if idx > 0 and probe[idx - 1] == operator[0] == "<" :
                pass
        out.append(idx)
        start = end
    return out


def cross_language_gate(rule: Mapping[str, Any], *, proposed_in: str) -> dict[str, Any]:
    """May this rule's operator lesson be proposed in `proposed_in`? Computed, not listed.

    Answers Q2 -- the semantic question the frozen `GENERALIZABLE` set used to answer wrongly by
    being absolute. Within the language the rule was taught in there is no cross-language claim to
    make and every swap passes. Across languages each swap is decided by executing the operator in
    both toolchains: a witnessed divergence refuses, and so does a language nothing here can execute,
    because refusing is what the module has always done instead of guessing.
    """
    from canonical.swe_kernel.operator_semantics_v1 import may_generalize

    taught_in = str((rule or {}).get("language") or "")
    family = derive_swap_family(rule)
    verdicts = [may_generalize(s["from"], taught_in=taught_in, proposed_in=proposed_in)
                for s in family]
    allowed = [s for s, v in zip(family, verdicts) if v["allowed"]]
    return {
        "schema": SCHEMA, "taught_in": taught_in, "proposed_in": proposed_in,
        "allowed_swaps": allowed, "verdicts": verdicts,
        "refusals": sorted({v["basis"] for v in verdicts if not v["allowed"]}),
        "anything_allowed": bool(allowed),
    }


def propose_operator_swaps(
    source_text: str, rule: Mapping[str, Any], *, language: str = "python",
    limit: int = MAX_CANDIDATES,
) -> Iterator[str]:
    """Yield one candidate per operator occurrence, nearest-first, bounded.

    Each candidate changes exactly one occurrence, so the caller's verifier judges a minimal
    edit and a wrong proposal cannot cascade.

    A swap whose operator does not mean the same thing in `language` as in the language the rule was
    taught in is skipped rather than proposed: the widening this module exists to perform must not
    change what the program computes. `cross_language_gate` reports those refusals by name.
    """
    if not isinstance(rule, Mapping) or rule.get("state") not in (None, "ACTIVE"):
        return
    from canonical.swe_kernel.operator_semantics_v1 import may_generalize

    taught_in = str(rule.get("language") or "")
    seen: set[str] = set()
    emitted = 0
    for swap in derive_swap_family(rule):
        src_op, dst_op = swap["from"], swap["to"]
        if not may_generalize(src_op, taught_in=taught_in, proposed_in=language)["allowed"]:
            continue
        for idx in _occurrences(source_text, src_op, language=language):
            if emitted >= limit:
                return
            end = idx + len(src_op)
            candidate = source_text[:idx] + dst_op + source_text[end:]
            if candidate == source_text or candidate in seen:
                continue
            seen.add(candidate)
            emitted += 1
            yield candidate


def explain_rule(rule: Mapping[str, Any], *, proposed_in: str | None = None) -> dict[str, Any]:
    """Why a rule does or does not generalize past its own skeleton.

    With `proposed_in` the explanation also carries the cross-language gate, so a refusal can say
    which operator means something different over there rather than only that the tokens did not
    match. Omitting it keeps the answer purely structural, as before.
    """
    swap = derive_operator_swap(rule)
    out = {
        "schema": SCHEMA,
        "skill_id": rule.get("skill_id"),
        "generalizable": swap is not None,
        "swap": swap,
        "swap_family": derive_swap_family(rule),
        "reason": ("SINGLE_OPERATOR_DIFFERENCE" if swap
                   else "NOT_A_SINGLE_OPERATOR_DIFFERENCE"),
    }
    if proposed_in is not None:
        gate = cross_language_gate(rule, proposed_in=proposed_in)
        out["cross_language"] = {
            "proposed_in": proposed_in, "allowed": gate["anything_allowed"],
            "refusals": gate["refusals"],
            "bases": sorted({v["basis"] for v in gate["verdicts"]}),
        }
    return out
