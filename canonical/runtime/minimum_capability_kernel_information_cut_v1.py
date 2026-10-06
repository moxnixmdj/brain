from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BinaryCutResult:
    q_action0: float
    success_w0: float
    success_w1: float
    worst_case_success: float


def indistinguishable_binary_worlds(q_action0: float) -> BinaryCutResult:
    if isinstance(q_action0, bool) or not isinstance(q_action0, (int, float)):
        raise TypeError("q_action0 must be numeric")
    q = float(q_action0)
    if q < 0.0 or q > 1.0:
        raise ValueError("q_action0 must be in [0,1]")
    # The pre-action transcript is identical in w0 and w1.
    # Therefore one policy induces the same action distribution in both worlds.
    s0 = q
    s1 = 1.0 - q
    return BinaryCutResult(q, s0, s1, min(s0, s1))


def best_worst_case_without_separator(grid: int = 1000) -> float:
    if grid <= 0:
        raise ValueError("grid must be positive")
    vals = [
        indistinguishable_binary_worlds(i / grid).worst_case_success
        for i in range(grid + 1)
    ]
    return max(vals)


def separator_aware_success() -> tuple[float, float]:
    # One admissible precommitment bit identifies the world.
    return (1.0, 1.0)


def delayed_separator_usable(*, separator_arrival: int, decision_deadline: int) -> bool:
    return separator_arrival <= decision_deadline


def absolute_verifier_success() -> tuple[float, float]:
    # A complete verifier that reveals which action is terminally correct
    # is itself a sufficient discriminator.
    return (1.0, 1.0)


def verify_information_cut() -> dict[str, object]:
    bound = best_worst_case_without_separator()
    sep = separator_aware_success()
    verifier = absolute_verifier_success()

    assert abs(bound - 0.5) < 1e-12
    assert sep == (1.0, 1.0)
    assert verifier == (1.0, 1.0)
    assert delayed_separator_usable(separator_arrival=1, decision_deadline=0) is False

    return {
        "no_separator_worst_case_upper_bound": bound,
        "separator_aware_success": sep,
        "absolute_verifier_success": verifier,
        "late_separator_rejected": True,
        "generic_search_without_information_not_universally_sufficient": True,
    }
