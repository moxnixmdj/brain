"""Capability-first development scheduler.

This module ranks work by conservative reusable capability gain per resource and
keeps benchmark activity as instrumentation unless it localizes a real
capability defect, validates a new capability, falsifies a capability claim, or
certifies a frontier milestone.

Planning only. It does not grant execution, acceptance, capability, ownership,
or terminal credit by itself.
"""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA = "PROJECT_BRAIN_CAPABILITY_FIRST_SCHEDULER_V1"
MISSION_OBJECTIVE = "BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE"
MILESTONE = "OPUS_5_5_FIRST_FRONTIER_CHECKPOINT__NOT_TERMINAL_OBJECTIVE"
OPTION_PRESERVATION_POLICY = "canonical/governance/CURRENT_OPTION_PRESERVING_OPTIMIZATION.json"
CAPABILITY_LEARNING_LOOP = (
    "SOLVE",
    "VERIFY",
    "EXTRACT_MECHANISM",
    "GENERALIZE",
    "COMPRESS",
    "PRESERVE_OPTIONS",
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

LOAD_BEARING_PRIMARY_LANE = "LOAD_BEARING_PRIMARY"
SECONDARY_CAPABILITY_LANE = "SECONDARY_CAPABILITY"
CURRENT_TERMINAL_AUTHORITY = (
    Path(__file__).resolve().parents[1] / "governance" / "CURRENT_TERMINAL_AUTHORITY.json"
)


def _ids(raw: Mapping[str, Any], key: str) -> list[str]:
    value = raw.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) and _s(x) for x in value):
        raise CapabilityFirstSchedulerError(key.upper() + "_INVALID")
    return sorted(set(_s(x) for x in value))


def _current_open_obligation_count() -> int:
    """Read the current independent load-bearing acceptance count fail-closed."""
    try:
        doc = json.loads(CURRENT_TERMINAL_AUTHORITY.read_text(encoding="utf-8"))
        live = doc.get("live_truth", {})
        value = live.get("independent_open_acceptance_obligations")
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            return value
    except Exception:
        pass
    # Unknown current authority is not permission to schedule generic side work.
    raise CapabilityFirstSchedulerError("CURRENT_OPEN_OBLIGATION_COUNT_UNAVAILABLE")


def _load_bearing_score(raw: Mapping[str, Any]) -> Fraction:
    discharge = _f(
        raw.get("expected_obligation_discharge_lcb", 0),
        "expected_obligation_discharge_lcb",
    )
    unlock = _f(
        raw.get("expected_obligation_unlock_lcb", 0),
        "expected_obligation_unlock_lcb",
    )
    success = _f(raw.get("success_probability_lcb", 0), "success_probability_lcb")
    if success > 1:
        raise CapabilityFirstSchedulerError("SUCCESS_PROBABILITY_LCB_GT_ONE")
    wall = _f(raw.get("wall_clock_cost_ub", 0), "wall_clock_cost_ub")
    if wall <= 0:
        raise CapabilityFirstSchedulerError("WALL_CLOCK_COST_MUST_BE_POSITIVE")
    return (discharge + unlock) * success / wall


def _has_load_bearing_path(raw: Mapping[str, Any]) -> bool:
    return bool(
        _ids(raw, "open_obligation_ids")
        or _ids(raw, "constructive_gap_for_open_obligation_ids")
        or raw.get("scope_complete_discharge") is True
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


def _eligible(
    raw: Mapping[str, Any], checkpoint_open_obligation_count: int
) -> tuple[bool, str]:
    work_type = _s(raw.get("work_type"))
    if work_type not in WORK_TYPES:
        raise CapabilityFirstSchedulerError("WORK_TYPE_INVALID")

    if checkpoint_open_obligation_count > 0:
        lane = _s(raw.get("scheduling_lane"))
        if lane != LOAD_BEARING_PRIMARY_LANE:
            return False, "DEMOTED_NON_LOAD_BEARING_WHILE_OPEN_OBLIGATIONS"
        if not _has_load_bearing_path(raw):
            return False, "DEMOTED_NO_CAUSAL_PATH_TO_OPEN_OBLIGATION"
        if _load_bearing_score(raw) <= 0:
            return False, "DEMOTED_ZERO_EXPECTED_LOAD_BEARING_YIELD"

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


def rank_work(
    work: Sequence[Mapping[str, Any]],
    *,
    checkpoint_open_obligation_count: int | None = None,
) -> dict[str, Any]:
    if checkpoint_open_obligation_count is None:
        checkpoint_open_obligation_count = _current_open_obligation_count()
    if (
        isinstance(checkpoint_open_obligation_count, bool)
        or not isinstance(checkpoint_open_obligation_count, int)
        or checkpoint_open_obligation_count < 0
    ):
        raise CapabilityFirstSchedulerError("CHECKPOINT_OPEN_OBLIGATION_COUNT_INVALID")

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in work:
        work_id = _s(raw.get("work_id"))
        if not work_id:
            raise CapabilityFirstSchedulerError("WORK_ID_REQUIRED")
        if work_id in seen:
            raise CapabilityFirstSchedulerError("WORK_ID_DUPLICATE:" + work_id)
        seen.add(work_id)
        eligible, eligibility = _eligible(raw, checkpoint_open_obligation_count)
        if eligible:
            score = (
                _load_bearing_score(raw)
                if checkpoint_open_obligation_count > 0
                else _score(raw)
            )
        else:
            score = Fraction(0)
        rows.append(
            {
                "work_id": work_id,
                "work_type": _s(raw.get("work_type")),
                "benchmark_role": _s(raw.get("benchmark_role")) or None,
                "scheduling_lane": _s(raw.get("scheduling_lane")) or None,
                "open_obligation_ids": _ids(raw, "open_obligation_ids"),
                "constructive_gap_for_open_obligation_ids": _ids(
                    raw, "constructive_gap_for_open_obligation_ids"
                ),
                "scope_complete_discharge": raw.get("scope_complete_discharge") is True,
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
    gate_active = checkpoint_open_obligation_count > 0
    return {
        "schema": SCHEMA,
        "status": (
            "LOAD_BEARING_PRIMARY_RANKING"
            if gate_active
            else "CAPABILITY_FIRST_RANKING"
        ),
        "objective": (
            "MAXIMIZE_EXPECTED_INDEPENDENT_LOAD_BEARING_OBLIGATION_DISCHARGE_OR_UNLOCK_PER_WALL_CLOCK"
            if gate_active
            else "MAXIMIZE_REUSABLE_VERIFIED_CAPABILITY_GENERALIZATION_RELIABILITY_AND_EFFICIENCY_PER_RESOURCE"
        ),
        "mission_objective": MISSION_OBJECTIVE,
        "milestone": MILESTONE,
        "checkpoint_open_obligation_count": checkpoint_open_obligation_count,
        "load_bearing_primary_gate_active": gate_active,
        "primary_admission_rule": (
            "WHILE_OPEN_OBLIGATIONS_EXIST__PRIMARY_WORK_REQUIRES_EXPLICIT_CAUSAL_PATH_TO_OPEN_OBLIGATION_AND_POSITIVE_EXPECTED_LOAD_BEARING_YIELD"
        ),
        "option_preservation_policy": OPTION_PRESERVATION_POLICY,
        "optimization_rule": "OPTIMIZE_IMPLEMENTATIONS_NOT_POSSIBILITIES",
        "capability_learning_loop": list(CAPABILITY_LEARNING_LOOP),
        "ranked": [
            {
                "rank": i + 1,
                "work_id": row["work_id"],
                "work_type": row["work_type"],
                "benchmark_role": row["benchmark_role"],
                "scheduling_lane": row["scheduling_lane"],
                "open_obligation_ids": row["open_obligation_ids"],
                "constructive_gap_for_open_obligation_ids": row[
                    "constructive_gap_for_open_obligation_ids"
                ],
                "scope_complete_discharge": row["scope_complete_discharge"],
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


def rank_live_work(work: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Canonical primary scheduler entrypoint bound to current authority truth."""
    return rank_work(work, checkpoint_open_obligation_count=_current_open_obligation_count())


_BENEFITS = ("capability", "generalization", "reliability")
_COSTS = ("latency", "compute", "memory", "incremental_spend_usd")


def _metrics(raw: Mapping[str, Any]) -> dict[str, Fraction]:
    return {k: _f(raw.get(k, 0), k) for k in (*_BENEFITS, *_COSTS)}


def _dominates(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    a_contract = _s(a.get("semantic_contract_sha256"))
    b_contract = _s(b.get("semantic_contract_sha256"))
    if a_contract and b_contract and a_contract != b_contract:
        return False
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
                "preserve_candidate_evidence": True,
                "dominated_means_deleted": False,
                "physical_deletion_authority": False,
                "option_preservation_policy": OPTION_PRESERVATION_POLICY,
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
