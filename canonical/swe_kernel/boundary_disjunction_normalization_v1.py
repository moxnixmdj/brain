"""Boundary disjunction normalisation: the third hypothesis, made real.

THE GAP
-------
`operator_generalization_v1` can only represent a lesson whose difference is **exactly one
operator**. Measured this session: a boundary lesson taught once reaches 6 of 7 re-spellings,
and the seventh -- `x < hi or x == hi` -- is unreachable at *any* number of exposures, because
`derive_operator_swap` returns `None` for it. Teaching the missed lesson directly stores a rule
that replays the skeleton and still cannot widen.

`rule_scope_learning_v1` declares three scope hypotheses but only offers two
(`SCOPE_STATEMENT`, `SCOPE_OPERATOR`), with a note that `SCOPE_SEMANTIC` -- same meaning,
different shape -- is not offered because nothing in the tree realises it. This module is that
realiser, for the one family where it can be done honestly and mechanically.

WHAT IT DOES
------------
`a < b or a == b` and `a > b or a == b` are the same predicates as `a <= b` and `a >= b`. A
source written in the disjunctive form is therefore *semantically* the taught boundary lesson,
and once normalised into the comparison form the existing operator swap applies.

It rewrites **only** that family, only through the AST, and only by splicing the exact original
operand text -- so a `or` inside a string literal or a comment is never touched, because the AST
never sees it as a `BoolOp`.

WHAT IT IS NOT
--------------
The agreement sample is **not a proof**. It evaluates both forms over a bounded integer grid and
reports how many points agreed. Two predicates can agree on every sampled point and differ
elsewhere, and Python floats containing `NaN` are not a total order at all, so the identity
itself can fail there.

That is tolerable because this module **cannot accept anything**. It is a proposal source: every
candidate it yields must still be executed against the caller's own verifier. It carries
`terminal_authority: False` and has no function that applies, accepts, stores or commits an edit.
An unsound proposal costs a wasted verification, never a wrong accepted change.
"""
from __future__ import annotations

import ast
from typing import Any, Iterator, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_BOUNDARY_DISJUNCTION_NORMALISATION_V1"

MAX_CANDIDATES = 32
SAMPLE_RADIUS = 32  # values in [-32, 32], both operands

# op pair -> the comparison the disjunction is equivalent to
_IDENTITIES: dict[frozenset[str], str] = {
    frozenset({"Lt", "Eq"}): "LtE",
    frozenset({"Gt", "Eq"}): "GtE",
}


class NormalizationError(RuntimeError):
    """Raised when the input cannot be handled honestly."""


def _span(source: str, node: ast.AST) -> str:
    """The exact original text of a node, so unrelated formatting survives untouched."""
    segment = ast.get_source_segment(source, node)
    if segment is None:
        raise NormalizationError("SOURCE_SEGMENT_UNAVAILABLE")
    return segment


def _single_compare(node: ast.AST) -> ast.Compare | None:
    if not isinstance(node, ast.Compare):
        return None
    if len(node.ops) != 1 or len(node.comparators) != 1:
        return None
    return node


def _is_boundary_disjunction(node: ast.AST) -> tuple[ast.Compare, ast.Compare] | None:
    """Return the two comparisons if `node` is `a < b or a == b` (either order)."""
    if not isinstance(node, ast.BoolOp) or not isinstance(node.op, ast.Or):
        return None
    if len(node.values) != 2:
        return None
    first, second = _single_compare(node.values[0]), _single_compare(node.values[1])
    if first is None or second is None:
        return None
    pair = frozenset(
        {type(first.ops[0]).__name__, type(second.ops[0]).__name__}
    )
    if pair not in _IDENTITIES:
        return None
    # The two comparisons must be about the same two operands, or the identity is false.
    if ast.dump(first.left) != ast.dump(second.left):
        return None
    if ast.dump(first.comparators[0]) != ast.dump(second.comparators[0]):
        return None
    return first, second


def _sample_agreement(left_text: str, right_text: str, op: str) -> dict[str, Any]:
    """Evaluate both forms over a bounded integer grid.

    Reported as agreement, never as proof. See the module docstring.
    """
    points = 0
    agreed = 0
    for a in range(-SAMPLE_RADIUS, SAMPLE_RADIUS + 1):
        for b in range(-SAMPLE_RADIUS, SAMPLE_RADIUS + 1):
            points += 1
            disjunction = (a < b or a == b) if op == "LtE" else (a > b or a == b)
            comparison = (a <= b) if op == "LtE" else (a >= b)
            if disjunction == comparison:
                agreed += 1
    return {
        "points": points,
        "agreed": agreed,
        "domain": f"integers in [{-SAMPLE_RADIUS}, {SAMPLE_RADIUS}]",
        "means": "agreement sample, NOT a proof of equivalence",
    }


def normalize(source: str) -> list[dict[str, Any]]:
    """Every distinct normalisation of `source`, each with its identity and agreement sample."""
    if not isinstance(source, str) or not source.strip():
        raise NormalizationError("SOURCE_REQUIRED")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise NormalizationError("SOURCE_NOT_PARSEABLE") from exc

    found: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()

    for node in ast.walk(tree):
        pair = _is_boundary_disjunction(node)
        if pair is None:
            continue
        first, second = pair
        if node.lineno is None or node.end_lineno is None:
            continue
        marker = (node.lineno, node.col_offset)
        if marker in seen:
            continue
        seen.add(marker)

        op_pair = frozenset({type(first.ops[0]).__name__, type(second.ops[0]).__name__})
        equivalent = _IDENTITIES[op_pair]
        operator = "<=" if equivalent == "LtE" else ">="
        left_text = _span(source, first.left)
        right_text = _span(source, first.comparators[0])
        replacement = f"{left_text} {operator} {right_text}"

        # Splice by the node's own span so nothing outside it is reformatted.
        lines = source.splitlines(keepends=True)
        if node.lineno != node.end_lineno:
            raise NormalizationError("MULTILINE_DISJUNCTION_UNSUPPORTED")
        line = lines[node.lineno - 1]
        start = node.col_offset
        end = node.end_col_offset
        normalised_line = line[:start] + replacement + line[end:]
        candidate = "".join(lines[: node.lineno - 1] + [normalised_line] + lines[node.lineno:])

        if candidate == source:
            continue
        found.append({
            "source_text": candidate,
            "identity": f"{_IDENTITIES[op_pair]}: a or b written as a disjunction",
            "replacement": replacement,
            "line": node.lineno,
            "column": node.col_offset,
            "agreement": _sample_agreement(left_text, right_text, equivalent),
        })
        if len(found) >= MAX_CANDIDATES:
            break

    return found


def propose_semantic_swaps(
    source: str,
    rule: Mapping[str, Any],
    *,
    operator_swaps: Any,
) -> Iterator[str]:
    """Yield operator-swap candidates for each normalised spelling of `source`.

    `operator_swaps` is passed in rather than imported, so this module stays a pure proposal
    source with no opinion about what a rule is.
    """
    if not callable(operator_swaps):
        raise NormalizationError("OPERATOR_SWAPS_NOT_CALLABLE")
    seen: set[str] = set()
    for form in [source] + [item["source_text"] for item in normalize(source)]:
        if form in seen:
            continue
        seen.add(form)
        for candidate in operator_swaps(form, rule):
            if candidate is None or candidate in seen:
                continue
            seen.add(candidate)
            yield candidate


def explain(source: str) -> dict[str, Any]:
    """A receipt for what was recognised, with no authority attached."""
    try:
        forms = normalize(source)
    except NormalizationError as exc:
        return {
            "schema": SCHEMA,
            "status": "REFUSED",
            "reason": str(exc),
            "terminal_authority": False,
        }
    return {
        "schema": SCHEMA,
        "status": "NORMALISED" if forms else "NO_BOUNDARY_DISJUNCTION",
        "forms": [
            {
                "identity": item["identity"],
                "line": item["line"],
                "column": item["column"],
                "replacement": item["replacement"],
                "agreement": item["agreement"],
            }
            for item in forms
        ],
        "terminal_authority": False,
    }
