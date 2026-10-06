from __future__ import annotations

from typing import Iterable


def pareto_frontier_1d(points: Iterable[float]) -> tuple[float, ...]:
    values = tuple(float(x) for x in points)
    if not values:
        return ()
    return (max(values),)


def support_frontier_simulates(opus_support: Iterable[float], brain_support: Iterable[float]) -> bool:
    opus = pareto_frontier_1d(opus_support)
    brain = pareto_frontier_1d(brain_support)
    return all(any(b >= o for b in brain) for o in opus)


def expected_success(prob_success: float) -> float:
    p = float(prob_success)
    if not 0.0 <= p <= 1.0:
        raise ValueError("PROBABILITY_OUT_OF_RANGE")
    return p


def stochastic_reliability_countermodel() -> dict[str, object]:
    opus_p = 0.99
    brain_p = 0.51
    support = (0.0, 1.0)
    point_frontier_pass = support_frontier_simulates(support, support)
    reliability_pass = expected_success(brain_p) >= expected_success(opus_p)
    return {
        "opus_success_probability": opus_p,
        "brain_success_probability": brain_p,
        "same_outcome_support": True,
        "same_point_pareto_frontier": pareto_frontier_1d(support),
        "point_frontier_simulation_passes": point_frontier_pass,
        "terminal_reliability_noninferiority_passes": reliability_pass,
        "countermodel_valid": point_frontier_pass and not reliability_pass,
    }


def compile_countermodel() -> dict[str, object]:
    out = stochastic_reliability_countermodel()
    if out["countermodel_valid"] is not True:
        return {"status": "FAIL_CLOSED", "error": "COUNTERMODEL_NOT_CONSTRUCTED"}
    return {
        "status": "PASS__POINT_SUPPORT_FRONTIER_INSUFFICIENT_FOR_STOCHASTIC_RELIABILITY",
        "classification": "TRUTH_REPAIR",
        "terminal_credit": False,
        "minimum_repair": "LIFT_FRONTIER_OBJECT_TO_POLICY_INDUCED_OUTCOME_DISTRIBUTIONS_OR_EQUIVALENT_PROBABILISTIC_SEMANTICS",
    }
