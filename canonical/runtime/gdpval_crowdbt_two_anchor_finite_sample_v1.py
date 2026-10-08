"""Finite-sample robust noninferiority certificate for two-anchor Crowd-BT.

Conditional statistical theorem only. This module assumes:
  * the same informative Crowd-BT judge or fixed judge-mixture semantics apply to both anchors;
  * anchor ratings and the target rating are exact coordinates on one frozen scale;
  * observations within each anchor sample satisfy the independence/boundedness premise
    needed by the supplied Hoeffding contract;
  * outcomes are encoded Brain win=1, tie=1/2, reference win=0.

For each anchor j, Hoeffding gives a simultaneous confidence interval for q_j.
Writing z_j=2 q_j - 1, the two-anchor ratio rho=z1/z2 identifies candidate
strength independently of judge quality. For r1<r2<T, any finite candidate
strength s satisfies:
  s >= T  iff  1 < rho(s) <= rho(T)
on the upper branch s>r2.

The runtime computes the entire ratio interval induced by the simultaneous
confidence rectangle. PASS occurs only when every compatible ratio lies inside
that target-implying region. Otherwise it returns UNKNOWN.

This runtime does not prove the semantic premises and grants no terminal credit.
"""
from __future__ import annotations

import math
from typing import Any, Mapping


class TwoAnchorFiniteSampleError(ValueError):
    pass


def _real(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TwoAnchorFiniteSampleError(f"{label}_MUST_BE_REAL")
    x = float(value)
    if not math.isfinite(x):
        raise TwoAnchorFiniteSampleError(f"{label}_MUST_BE_FINITE")
    return x


def _count(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TwoAnchorFiniteSampleError(f"{label}_MUST_BE_NONNEGATIVE_INT")
    return value


def _sample(row: Mapping[str, Any], label: str, alpha_share: float) -> dict[str, float | int]:
    wins = _count(row.get("brain_wins"), f"{label}_BRAIN_WINS")
    ties = _count(row.get("ties"), f"{label}_TIES")
    losses = _count(row.get("reference_wins"), f"{label}_REFERENCE_WINS")
    n = wins + ties + losses
    if n <= 0:
        raise TwoAnchorFiniteSampleError(f"{label}_NO_OBSERVATIONS")

    mean = (wins + 0.5 * ties) / n
    eps = math.sqrt(math.log(2.0 / alpha_share) / (2.0 * n))
    q_lower = max(0.0, mean - eps)
    q_upper = min(1.0, mean + eps)
    return {
        "brain_wins": wins,
        "ties": ties,
        "reference_wins": losses,
        "n": n,
        "empirical_mean": mean,
        "epsilon": eps,
        "q_lower": q_lower,
        "q_upper": q_upper,
        "z_lower": 2.0 * q_lower - 1.0,
        "z_upper": 2.0 * q_upper - 1.0,
    }


def _ratio_interval(z1l: float, z1u: float, z2l: float, z2u: float) -> tuple[float, float] | None:
    pos = z1l > 0.0 and z2l > 0.0
    neg = z1u < 0.0 and z2u < 0.0
    if not (pos or neg):
        return None
    corners = [
        z1l / z2l,
        z1l / z2u,
        z1u / z2l,
        z1u / z2u,
    ]
    return min(corners), max(corners)


def _target_ratio(r1: float, r2: float, target: float) -> float:
    c = math.log(10.0) / 800.0
    a = math.tanh(c * (target - r1))
    b = math.tanh(c * (target - r2))
    if b == 0.0:
        raise TwoAnchorFiniteSampleError("TARGET_MUST_NOT_EQUAL_SECOND_ANCHOR")
    return a / b


def certify(task: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(task, Mapping):
        raise TwoAnchorFiniteSampleError("TASK_INVALID")

    r1 = _real(task.get("anchor1_rating"), "ANCHOR1_RATING")
    r2 = _real(task.get("anchor2_rating"), "ANCHOR2_RATING")
    target = _real(task.get("target_rating"), "TARGET_RATING")
    alpha = _real(task.get("alpha"), "ALPHA")

    if not (0.0 < alpha < 1.0):
        raise TwoAnchorFiniteSampleError("ALPHA_MUST_BE_BETWEEN_ZERO_AND_ONE")
    if not (r1 < r2 < target):
        raise TwoAnchorFiniteSampleError("REQUIRE_ANCHOR1_LT_ANCHOR2_LT_TARGET")

    row1 = task.get("anchor1_sample")
    row2 = task.get("anchor2_sample")
    if not isinstance(row1, Mapping) or not isinstance(row2, Mapping):
        raise TwoAnchorFiniteSampleError("TWO_ANCHOR_SAMPLES_REQUIRED")

    a1 = _sample(row1, "ANCHOR1", alpha / 2.0)
    a2 = _sample(row2, "ANCHOR2", alpha / 2.0)

    ratio = _ratio_interval(
        float(a1["z_lower"]), float(a1["z_upper"]),
        float(a2["z_lower"]), float(a2["z_upper"]),
    )
    rho_target = _target_ratio(r1, r2, target)

    blockers: list[str] = []
    passed = False
    rho_lower = None
    rho_upper = None

    if ratio is None:
        blockers.append("SIMULTANEOUS_Z_INTERVALS_DO_NOT_ESTABLISH_A_COMMON_NONZERO_ORIENTATION")
    else:
        rho_lower, rho_upper = ratio
        if not (rho_lower > 1.0):
            blockers.append("RATIO_LOWER_BOUND_DOES_NOT_PROVE_CANDIDATE_ABOVE_SECOND_ANCHOR")
        if not (rho_upper <= rho_target):
            blockers.append("RATIO_UPPER_BOUND_DOES_NOT_PROVE_TARGET_NONINFERIORITY")
        passed = rho_lower > 1.0 and rho_upper <= rho_target

    return {
        "schema": "PROJECT_BRAIN_GDPVAL_CROWDBT_TWO_ANCHOR_FINITE_SAMPLE_RESULT_V1",
        "status": "PASS__HOEFFDING_ROBUST_TARGET_NONINFERIORITY" if passed else "UNKNOWN__FINITE_SAMPLE_BOUND_INSUFFICIENT",
        "confidence_level_at_least": 1.0 - alpha,
        "alpha": alpha,
        "anchor1_rating": r1,
        "anchor2_rating": r2,
        "target_rating": target,
        "anchor1_sample": a1,
        "anchor2_sample": a2,
        "ratio_interval": None if ratio is None else {"lower": rho_lower, "upper": rho_upper},
        "target_boundary_ratio": rho_target,
        "conditional_candidate_rating_ge_target": passed,
        "blockers": blockers,
        "theorem": [
            "TWO_SIDED_HOEFFDING_PER_ANCHOR",
            "UNION_BOUND_OVER_TWO_ANCHOR_MEANS",
            "FULL_RECTANGULAR_RATIO_PROPAGATION_WITH_DENOMINATOR_EXCLUDING_ZERO",
            "FOR_R1_LT_R2_LT_TARGET__ONE_LT_RHO_LE_TARGET_RHO_IMPLIES_CANDIDATE_RATING_GE_TARGET",
            "JUDGE_QUALITY_AND_ORIENTATION_CANCEL_FROM_TWO_ANCHOR_RATIO",
        ],
        "semantic_premises_verified_by_this_runtime": False,
        "anchor_coordinate_uncertainty_included": False,
        "owner_exact_reproduction": False,
        "terminal_authority": False,
        "promotion_authority": False,
        "terminal_credit_delta": 0,
    }
