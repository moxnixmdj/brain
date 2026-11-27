from __future__ import annotations

from itertools import combinations, product
from math import isfinite
from typing import Iterable, Mapping

EPS = 1e-12


class RelevancePreorderError(ValueError):
    pass


def _validate_preorder(items: tuple[str, ...], geq: set[tuple[str, str]]) -> None:
    if not items or len(set(items)) != len(items):
        raise RelevancePreorderError("NONEMPTY_UNIQUE_ITEMS_REQUIRED")
    universe=set(items)
    if any(a not in universe or b not in universe for a,b in geq):
        raise RelevancePreorderError("RELATION_OUTSIDE_UNIVERSE")
    if any((x,x) not in geq for x in items):
        raise RelevancePreorderError("RELATION_NOT_REFLEXIVE")
    for a,b in geq:
        for c,d in geq:
            if b == c and (a,d) not in geq:
                raise RelevancePreorderError("RELATION_NOT_TRANSITIVE")


def _validate_probability_law(law: Mapping[str,float], items: tuple[str,...]) -> None:
    if set(law) != set(items):
        raise RelevancePreorderError("PROBABILITY_LAW_MUST_EXPLICITLY_BIND_THE_COMMON_OUTCOME_SPACE")
    vals=[float(law[x]) for x in items]
    if any((not isfinite(v)) or v < -EPS for v in vals):
        raise RelevancePreorderError("INVALID_PROBABILITY")
    if abs(sum(vals)-1.0) > 1e-9:
        raise RelevancePreorderError("PROBABILITY_MASS_MUST_SUM_TO_ONE")


def _subsets(items: tuple[str, ...]) -> Iterable[frozenset[str]]:
    for n in range(len(items) + 1):
        for rows in combinations(items, n):
            yield frozenset(rows)


def upper_sets(items: tuple[str, ...], geq: set[tuple[str, str]]) -> tuple[frozenset[str], ...]:
    """Return all upward-closed sets for a finite preorder.

    geq contains (y, x) when y >= x in terminal relevance.
    The relation is validated fail-closed before theorem use.
    """
    _validate_preorder(items,geq)
    out = []
    for u in _subsets(items):
        ok = True
        for x in u:
            for y in items:
                if (y, x) in geq and y not in u:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            out.append(u)
    return tuple(out)


def event_mass(law: Mapping[str, float], event: frozenset[str]) -> float:
    return sum(float(law.get(x, 0.0)) for x in event)


def upper_set_dominates(
    brain: Mapping[str, float],
    opus: Mapping[str, float],
    *,
    items: tuple[str, ...],
    geq: set[tuple[str, str]],
    eps: float = EPS,
) -> bool:
    _validate_preorder(items,geq)
    _validate_probability_law(brain,items)
    _validate_probability_law(opus,items)
    return all(
        event_mass(brain, u) + eps >= event_mass(opus, u)
        for u in upper_sets(items, geq)
    )


def monotone_integer_evaluators(
    items: tuple[str, ...],
    geq: set[tuple[str, str]],
    values: tuple[int, ...] = (0, 1, 2),
) -> tuple[dict[str, int], ...]:
    """Finite exhaustive test family; theorem itself is not limited to integer utilities."""
    _validate_preorder(items,geq)
    out = []
    for row in product(values, repeat=len(items)):
        f = dict(zip(items, row))
        if all(f[y] >= f[x] for y, x in geq):
            out.append(f)
    return tuple(out)


def expected(law: Mapping[str, float], evaluator: Mapping[str, float]) -> float:
    return sum(float(law.get(x, 0.0)) * float(evaluator[x]) for x in evaluator)


def exhaustive_monotone_dominates(
    brain: Mapping[str, float],
    opus: Mapping[str, float],
    *,
    items: tuple[str, ...],
    geq: set[tuple[str, str]],
) -> bool:
    _validate_preorder(items,geq)
    _validate_probability_law(brain,items)
    _validate_probability_law(opus,items)
    return all(
        expected(brain, f) + EPS >= expected(opus, f)
        for f in monotone_integer_evaluators(items, geq)
    )


def hidden_evaluator_counterexample() -> dict[str, object]:
    # bad < good. A declared constant evaluator cannot distinguish the laws,
    # but the order-generated upper set {good} does.
    items = ("bad", "good")
    geq = {("bad", "bad"), ("good", "good"), ("good", "bad")}
    brain = {"bad": 1.0, "good": 0.0}
    opus = {"bad": 0.0, "good": 1.0}
    declared = {"bad": 0.0, "good": 0.0}
    declared_pass = expected(brain, declared) >= expected(opus, declared)
    structural_pass = upper_set_dominates(brain, opus, items=items, geq=geq)
    return {
        "declared_finite_evaluator_passes": declared_pass,
        "upper_set_basis_passes": structural_pass,
        "hidden_terminal_gap_detected": declared_pass and not structural_pass,
    }
