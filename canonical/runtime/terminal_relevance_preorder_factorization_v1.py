from __future__ import annotations

from itertools import combinations, product
from typing import Iterable, Mapping


def _subsets(items: tuple[str, ...]) -> Iterable[frozenset[str]]:
    for n in range(len(items) + 1):
        for rows in combinations(items, n):
            yield frozenset(rows)


def upper_sets(items: tuple[str, ...], geq: set[tuple[str, str]]) -> tuple[frozenset[str], ...]:
    """Return all upward-closed sets for a finite preorder/poset.

    geq contains (y, x) when y >= x in terminal relevance.
    """
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
    eps: float = 1e-12,
) -> bool:
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
    return all(
        expected(brain, f) + 1e-12 >= expected(opus, f)
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
