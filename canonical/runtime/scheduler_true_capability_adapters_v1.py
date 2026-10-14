"""True-capability adapters for the schedulers (canonical/laws/TRUE_CAPABILITY_TEST_LAW_V1.md).

The schedulers themselves are byte-pinned by governance records, so the pure
adapters that turn a described instance into calls on their public functions
live here instead of inside them.  No scheduling logic is in this file.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import authenticated_pareto_scheduler_v1 as _auth
from canonical.runtime import capability_first_scheduler_v1 as _core


def _s(x: Any) -> str:
    return " ".join(str(x or "").split())


def solve_ranking(instance: Mapping[str, Any]) -> dict[str, Any]:
    """CAPABILITY_FIRST_RANKING_V1: rank the instance's work list with rank_work."""
    try:
        result = _core.rank_work(
            [dict(w) for w in instance["work"]],
            checkpoint_open_obligation_count=instance["checkpoint_open_obligation_count"],
        )
    except _core.CapabilityFirstSchedulerError as exc:
        return {"status": "REJECTED", "reason": str(exc)}
    return {
        "status": "OK",
        "ranked": [
            {
                "rank": row["rank"],
                "work_id": row["work_id"],
                "eligibility": row["eligibility"],
                "priority_score": row["priority_score"],
                "checkpoint_audit_score": row["checkpoint_audit_score"],
            }
            for row in result["ranked"]
        ],
        "checkpoint_audit_active": result["checkpoint_audit_active"],
        "planning_only": result["planning_only"],
        "execution_authority": result["execution_authority"],
        "credit_deltas": [
            result["acceptance_credit_delta"],
            result["capability_credit_delta"],
            result["ownership_credit_delta"],
            result["terminal_credit_delta"],
        ],
    }


def solve_frontier(instance: Mapping[str, Any]) -> dict[str, Any]:
    """PARETO_FRONTIER_UPDATE_V1: fold the candidates into an initially empty frontier."""
    frontier: list[Mapping[str, Any]] = []
    steps: list[dict[str, Any]] = []
    for candidate in instance["candidates"]:
        try:
            out = _core.update_pareto_frontier(frontier, dict(candidate))
        except _core.CapabilityFirstSchedulerError as exc:
            steps.append({"status": "REJECTED", "reason": str(exc)})
            continue
        steps.append({
            "status": "OK",
            "admitted": bool(out["admitted"]),
            "reason": out["reason"],
            "dominated_by": out.get("dominated_by"),
            "removed": sorted(out.get("removed_dominated", [])),
            "frontier_ids": [_s(x.get("capability_id")) for x in out["frontier"]],
            "physical_deletion_authority": out.get("physical_deletion_authority"),
            "dominated_means_deleted": out.get("dominated_means_deleted"),
        })
        frontier = out["frontier"]
    return {"steps": steps, "final_frontier_ids": [_s(x.get("capability_id")) for x in frontier]}


def solve_schedule(instance: Mapping[str, Any]) -> dict[str, Any]:
    """AUTHENTICATED_PARETO_SCHEDULE_V1: compile the receipt-bound nondominated set."""
    out = _auth.compile_schedule([dict(c) for c in instance["candidates"]])
    return {
        "pass": bool(out.get("pass")),
        "reason": out.get("reason"),
        "candidate_id": out.get("candidate_id"),
        "nondominated_candidate_ids": list(out.get("nondominated_candidate_ids", [])),
        "dominated_by": {k: list(v) for k, v in (out.get("dominated_by") or {}).items()},
        "schedule_authority": out.get("schedule_authority"),
        "promotion_authority": out.get("promotion_authority"),
        "terminal_authority": out.get("terminal_authority"),
        "terminal_credit_delta": out.get("terminal_credit_delta"),
        "incremental_spend_usd": out.get("incremental_spend_usd"),
    }
