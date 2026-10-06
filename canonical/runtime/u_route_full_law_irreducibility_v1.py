from __future__ import annotations

from typing import Iterable


def dominates_all_indicator_utilities(brain: Iterable[float], target: Iterable[float]) -> bool:
    b = tuple(float(x) for x in brain)
    t = tuple(float(x) for x in target)
    if len(b) != len(t) or not b:
        raise ValueError("laws must have same finite support and be nonempty")
    if abs(sum(b) - 1.0) > 1e-12 or abs(sum(t) - 1.0) > 1e-12:
        raise ValueError("laws must sum to one")
    n = len(b)
    for mask in range(1 << n):
        eb = sum(b[i] for i in range(n) if mask & (1 << i))
        et = sum(t[i] for i in range(n) if mask & (1 << i))
        if eb + 1e-12 < et:
            return False
    return True


def finite_u_route_theorem(brain: Iterable[float], target: Iterable[float]) -> dict[str, object]:
    b = tuple(float(x) for x in brain)
    t = tuple(float(x) for x in target)
    dominates = dominates_all_indicator_utilities(b, t)
    equal = all(abs(x-y) <= 1e-12 for x,y in zip(b,t))
    return {
        "indicator_noninferiority_for_all_events": dominates,
        "laws_equal": equal,
        "theorem_holds": dominates == equal,
        "terminal_credit": False,
    }


def partial_information_counterexample() -> dict[str, object]:
    target_a = (0.9, 0.1)
    target_b = (0.1, 0.9)
    brain = (0.5, 0.5)
    return {
        "ambiguity_set": [target_a, target_b],
        "brain": brain,
        "dominates_target_a_for_all_indicators": dominates_all_indicator_utilities(brain, target_a),
        "dominates_target_b_for_all_indicators": dominates_all_indicator_utilities(brain, target_b),
        "nontrivial_u_robust_dominance_exists": False,
    }
