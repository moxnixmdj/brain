"""Capability-first development scheduler.

This module ranks work by conservative reusable capability gain per resource and
keeps benchmark activity as instrumentation unless it localizes a real
capability defect, validates a new capability, falsifies a capability claim, or
certifies a frontier milestone.

Planning only. It does not grant execution, acceptance, capability, ownership,
or terminal credit by itself.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_CAPABILITY_FIRST_SCHEDULER_V1"
MISSION_OBJECTIVE = "BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE"\nMILESTONE = "OPUS_5_5_FIRST_FRONTIER_CHECKPOINT__NOT_TERMINAL_OBJECTIVE"
OPTION_PRESERVATION_POLICY = "canonical/governance/CURRENT_OPTION_PRESERVING_OPTIMIZATION.json"
CAPABILITY_LEARNING_LOOP = (
    "SOLVE",
    "VERIFY",
    "EXTRACT_MECHANISM",
    "GENERALIZE",
    "COMPRESS",
    "REUSE_CHEAPER",
)
ALLOWED_BENCHMARK_ROLES = frozenset(
    {
        "CAPABILITY_DEFECT_LOCALIZATION",
        "NEW_CAPABILITY_VALIDATION",
        "CAPABILITY_CLAIM_FALSIFICATION",
        "MILESTONE_CERTIFICATION",
    }
)
WORK_TYPES = frozenset(
    {
        "CAPABILITY_BUILD",
        "EFFICIENCY_IMPROVEMENT",
        "RELIABILITY_IMPROVEMENT",
        "BENCHMARK_INSTRUMENTATION",
        "FALSIFICATION",
    }
)


class CapabilityFirstSchedulerError(ValueError):
    pass


def _s(x: Any) -> str:
    return " ".join(str(x or "").split())


def _f(x: Any, name: str) -> Fraction:
    if isinstance(x, bool):
        raise CapabilityFirstSchedulerError(name.upper() + "_INVALID")
    try:
        out = x if isinstance(x, Fraction) else Fraction(str(x))
    except Exception as exc:
        raise CapabilityFirstSchedulerError(name.upper() + "_INVALID") from exc
    if out < 0:
        raise CapabilityFirstSchedulerError(name.upper() + "_NEGATIVE")
    return out


def _eligible(raw: Mapping[str, Any]) -> tuple[bool, str]:
    work_type = _s(raw.get("work_type"))
    if work_type not in WORK_TYPES:
        raise CapabilityFirstSchedulerError("WORK_TYPE_INVALID")
    if work_type != "BENCHMARK_INSTRUMENTATION":
        return True, "ELIGIBLE"
    role = _s(raw.get("benchmark_role"))
    if role in ALLOWED_BENCHMARK_ROLES:
        return True, "ELIGIBLE"
    return False, "DEMOTED_BENCHMARK_BOOKKEEPING"


def _score(raw: Mapping[str, Any]) -> Fraction:
    capability = _f(raw.get("expected_capability_gain_lcb", 0), "expected_capability_gain_lcb")
    efficiency = _f(raw.get("expected_efficiency_gain_lcb", 0), "expected_efficiency_gain_lcb")
    reliability = _f(raw.get("expected_reliability_gain_lcb", 0), "expected_reliability_gain_lcb")
    breadth = _f(raw.get("reuse_breadth_lcb", 0), "reuse_breadth_lcb")
    generalization = _f(raw.get("generalization_lcb", 0), "generalization_lcb")
    success = _f(raw.get("success_probability_lcb", 0), "success_probability_lcb")
    if success > 1:
        raise CapabilityFirstSchedulerError("SUCCESS_PROBABILITY_LCB_GT_ONE")
    costs = (
        _f(raw.get("wall_clock_cost_ub", 0), "wall_clock_cost_ub")
        + _f(raw.get("compute_cost_ub", 0), "compute_cost_ub")
        + _f(raw.get("memory_cost_ub", 0), "memory_cost_ub")
        + _f(raw.get("complexity_cost_ub", 0), "complexity_cost_ub")
    )
    if costs <= 0:
        raise CapabilityFirstSchedulerError("TOTAL_RESOURCE_COST_MUST_BE_POSITIVE")
    return (capability + efficiency + reliability) * breadth * generalization * success / costs


def rank_work(work: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in work:
        work_id = _s(raw.get("work_id"))
        if not work_id:
            raise CapabilityFirstSchedulerError("WORK_ID_REQUIRED")
        if work_id in seen:
            raise CapabilityFirstSchedulerError("WORK_ID_DUPLICATE:" + work_id)
        seen.add(work_id)
        eligible, eligibility = _eligible(raw)
        score = _score(raw) if eligible else Fraction(0)
        rows.append(
            {
                "work_id": work_id,
                "work_type": _s(raw.get("work_type")),
                "benchmark_role": _s(raw.get("benchmark_role")) or None,
                "eligibility": eligibility,
                "priority_score_fraction": score,
            }
        )
    rows.sort(
        key=lambda x: (
            0 if x["eligibility"] == "ELIGIBLE" else 1,
            -x["priority_score_fraction"],
            x["work_id"],
        )
    )
    return {
        "schema": SCHEMA,
        "status": "CAPABILITY_FIRST_RANKING",
        "objective": "MAXIMIZE_REUSABLE_VERIFIED_CAPABILITY_GENERALIZATION_RELIABILITY_AND_EFFICIENCY_PER_RESOURCE",
        "mission_objective": MISSION_OBJECTIVE,
        "milestone": MILESTONE,
        "option_preservation_policy": OPTION_PRESERVATION_POLICY,
        "optimization_rule": "OPTIMIZE_IMPLEMENTATIONS_NOT_POSSIBILITIES",
        "capability_learning_loop": list(CAPABILITY_LEARNING_LOOP),
        "ranked": [
            {
                "rank": i + 1,
                "work_id": row["work_id"],
                "work_type": row["work_type"],
                "benchmark_role": row["benchmark_role"],
                "eligibility": row["eligibility"],
                "priority_score": str(row["priority_score_fraction"]),
            }
            for i, row in enumerate(rows)
        ],
        "planning_only": True,
        "execution_authority": False,
        "acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
        "physical_deletion_authority": False,
    }


_BENEFITS = ("capability", "generalization", "reliability")
_COSTS = ("latency", "compute", "memory", "incremental_spend_usd")


def _metrics(raw: Mapping[str, Any]) -> dict[str, Fraction]:
    return {k: _f(raw.get(k, 0), k) for k in (*_BENEFITS, *_COSTS)}


def _dominates(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    am, bm = _metrics(a), _metrics(b)
    weak = all(am[k] >= bm[k] for k in _BENEFITS) and all(am[k] <= bm[k] for k in _COSTS)
    strict = any(am[k] > bm[k] for k in _BENEFITS) or any(am[k] < bm[k] for k in _COSTS)
    return weak and strict


def update_pareto_frontier(
    frontier: Sequence[Mapping[str, Any]], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    cid = _s(candidate.get("capability_id"))
    if not cid:
        raise CapabilityFirstSchedulerError("CAPABILITY_ID_REQUIRED")
    if candidate.get("reusable_capability") is not True:
        return {"admitted": False, "reason": "REUSABLE_CAPABILITY_REQUIRED", "frontier": list(frontier)}
    if candidate.get("independently_verified") is not True:
        return {"admitted": False, "reason": "INDEPENDENT_VERIFICATION_REQUIRED", "frontier": list(frontier)}
    _metrics(candidate)
    for incumbent in frontier:
        if _dominates(incumbent, candidate):
            return {
                "admitted": False,
                "reason": "DOMINATED_BY_EXISTING_FRONTIER",
                "dominated_by": _s(incumbent.get("capability_id")),
                "frontier": list(frontier),
            }
    removed = [_s(x.get("capability_id")) for x in frontier if _dominates(candidate, x)]
    # "removed" is strictly active-frontier retirement. The implementation,
    # semantic contract, evidence, and reconstruction state remain preserved.
    # Permanent destruction is governed separately by
    # option_preserving_capability_optimizer_v1.
    kept = [dict(x) for x in frontier if not _dominates(candidate, x)]
    kept.append(dict(candidate))
    kept.sort(key=lambda x: _s(x.get("capability_id")))
    return {
        "admitted": True,
        "reason": "NONDOMINATED_VERIFIED_REUSABLE_CAPABILITY",
        "removed_dominated": removed,
        "retired_from_active_frontier": removed,
        "dominated_means_deleted": False,
        "physical_deletion_authority": False,
        "option_preservation_policy": OPTION_PRESERVATION_POLICY,
        "frontier": kept,
    }
