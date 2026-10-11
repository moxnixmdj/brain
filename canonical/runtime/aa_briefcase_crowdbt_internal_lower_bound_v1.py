from __future__ import annotations

import math
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_AA_BRIEFCASE_CROWD_BT_INTERNAL_LOWER_BOUND_V1"


class BoundError(ValueError):
    pass


def crowd_bt_observed_preference(true_preference: float, judge_quality: float) -> float:
    p = float(true_preference)
    eta = float(judge_quality)
    if not 0.0 <= p <= 1.0:
        raise BoundError("TRUE_PREFERENCE_OUT_OF_RANGE")
    if not 0.0 <= eta <= 1.0:
        raise BoundError("JUDGE_QUALITY_OUT_OF_RANGE")
    return eta * p + (1.0 - eta) * (1.0 - p)


def signal_slope(judge_quality: float) -> float:
    eta = float(judge_quality)
    if not 0.0 <= eta <= 1.0:
        raise BoundError("JUDGE_QUALITY_OUT_OF_RANGE")
    return 2.0 * eta - 1.0


def all_loss_probability(observed_preference: float, comparison_count: int) -> float:
    p = float(observed_preference)
    n = int(comparison_count)
    if not 0.0 <= p <= 1.0:
        raise BoundError("OBSERVED_PREFERENCE_OUT_OF_RANGE")
    if n < 1:
        raise BoundError("COMPARISON_COUNT_INVALID")
    return (1.0 - p) ** n


def internal_only_lower_bound_cut(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise BoundError("PAYLOAD_NOT_OBJECT")

    task_scope_complete = payload.get("task_scope_complete") is True
    universal_material_top_support = payload.get("universal_material_top_support") is True
    frozen_judge_quality_lower_bound = payload.get("frozen_judge_quality_lower_bound")
    frozen_realized_outcomes_bound = payload.get("frozen_realized_outcomes_bound") is True
    frozen_scorer_monotonicity_bound = payload.get("frozen_scorer_monotonicity_bound") is True

    if frozen_judge_quality_lower_bound is not None:
        eta_lb = float(frozen_judge_quality_lower_bound)
        if not 0.0 <= eta_lb <= 1.0:
            raise BoundError("FROZEN_JUDGE_QUALITY_LOWER_BOUND_OUT_OF_RANGE")
    else:
        eta_lb = None

    blockers: list[str] = []
    if not task_scope_complete:
        blockers.append("PRIVATE_91_TASK_SCOPE_NOT_SCOPE_COMPLETE")
    if not universal_material_top_support:
        blockers.append("BRAIN_UNIVERSAL_TOP_SUPPORT_NOT_PROVED")
    if eta_lb is None or eta_lb <= 0.5:
        blockers.append("CROWD_BT_JUDGE_SIGNAL_LOWER_BOUND_NOT_STRICTLY_ABOVE_HALF")
    if not frozen_realized_outcomes_bound:
        blockers.append("REALIZED_PAIRWISE_OUTCOMES_UNBOUND")
    if not frozen_scorer_monotonicity_bound:
        blockers.append("FROZEN_1822_SCORER_MONOTONICITY_NOT_BOUND")

    information_erasure_witness = crowd_bt_observed_preference(1.0, 0.5) == 0.5
    strict_superiority_erased = (
        crowd_bt_observed_preference(0.999999, 0.5)
        == crowd_bt_observed_preference(0.500001, 0.5)
        == 0.5
    )
    finite_noise_witness = all_loss_probability(0.999, 91) > 0.0

    if blockers:
        return {
            "schema": SCHEMA,
            "status": "NO_INTERNAL_FINITE_ELO_LOWER_BOUND",
            "threshold_1822_certified": False,
            "blockers": blockers,
            "information_erasure_witness": information_erasure_witness,
            "strict_superiority_erased_at_eta_half": strict_superiority_erased,
            "finite_realization_can_reverse_expected_order": finite_noise_witness,
            "reason": (
                "Material capability evidence alone cannot determine a finite realized "
                "Crowd-BT rating while task scope, judge signal, realized outcomes, or "
                "the frozen scoring monotonicity relation remain unbound."
            ),
            "acceptance_credit_delta": 0,
            "terminal_authority": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PREMISES_SUFFICIENT_TO_ATTEMPT_NUMERIC_LOWER_BOUND",
        "threshold_1822_certified": False,
        "blockers": [],
        "reason": (
            "The information-theoretic cut is cleared, but a separate numeric rating "
            "bound must still be derived under the now-bound frozen scorer state."
        ),
        "acceptance_credit_delta": 0,
        "terminal_authority": False,
    }
