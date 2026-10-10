"""Fail-closed live wrapper for the capability-first scheduler.

The core V1 scheduler remains a planning/scoring primitive.  This wrapper is
the only intended live entrypoint: it rejects arbitrary or heterogeneous score
numbers unless every candidate is bound to one complete, independently
verified, dimensionless calibration/frontier contract.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime import capability_first_scheduler_v1 as core


SCHEMA = "PROJECT_BRAIN_CAPABILITY_FIRST_LIVE_SCHEDULER_V1"
LIVE_SCORE_FIELDS = (
    "expected_capability_gain_lcb",
    "expected_efficiency_gain_lcb",
    "expected_reliability_gain_lcb",
    "reuse_breadth_lcb",
    "generalization_lcb",
    "success_probability_lcb",
    "wall_clock_cost_ub",
    "compute_cost_ub",
    "memory_cost_ub",
    "complexity_cost_ub",
)
LIVE_SCORE_CONTRACT_SCALE = "COMMON_DIMENSIONLESS_MISSION_UTILITY_RESOURCE_SCALE_V1"


class LiveSchedulerContractError(ValueError):
    pass


def _s(value: Any) -> str:
    return " ".join(str(value or "").split())


def validate_live_score_contract(work: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not work:
        raise LiveSchedulerContractError("LIVE_WORK_FRONTIER_EMPTY")

    calibration_ids: set[str] = set()
    frontier_ids: set[str] = set()
    verification_refs: set[str] = set()

    for raw in work:
        work_id = _s(raw.get("work_id"))
        if not work_id:
            raise LiveSchedulerContractError("WORK_ID_REQUIRED")

        contract = raw.get("live_score_contract")
        if not isinstance(contract, Mapping):
            raise LiveSchedulerContractError("LIVE_SCORE_CONTRACT_REQUIRED:" + work_id)
        if contract.get("dimensionless_normalized") is not True:
            raise LiveSchedulerContractError(
                "LIVE_SCORE_CONTRACT_NOT_DIMENSIONLESS:" + work_id
            )
        if _s(contract.get("scale")) != LIVE_SCORE_CONTRACT_SCALE:
            raise LiveSchedulerContractError(
                "LIVE_SCORE_CONTRACT_SCALE_INVALID:" + work_id
            )

        calibration_id = _s(contract.get("calibration_id"))
        frontier_id = _s(contract.get("frontier_id"))
        calibration_evidence = _s(contract.get("calibration_evidence_ref"))
        frontier_evidence = _s(contract.get("frontier_completeness_evidence_ref"))
        independent_verification = _s(contract.get("independent_verification_ref"))

        if not calibration_id:
            raise LiveSchedulerContractError(
                "LIVE_SCORE_CALIBRATION_ID_REQUIRED:" + work_id
            )
        if not frontier_id:
            raise LiveSchedulerContractError("LIVE_WORK_FRONTIER_ID_REQUIRED:" + work_id)
        if not calibration_evidence:
            raise LiveSchedulerContractError(
                "LIVE_SCORE_CALIBRATION_EVIDENCE_REQUIRED:" + work_id
            )
        if contract.get("frontier_complete") is not True or not frontier_evidence:
            raise LiveSchedulerContractError(
                "LIVE_WORK_FRONTIER_COMPLETENESS_EVIDENCE_REQUIRED:" + work_id
            )
        if not independent_verification:
            raise LiveSchedulerContractError(
                "LIVE_SCORE_INDEPENDENT_VERIFICATION_REQUIRED:" + work_id
            )

        metric_evidence = contract.get("metric_evidence")
        if not isinstance(metric_evidence, Mapping):
            raise LiveSchedulerContractError(
                "LIVE_SCORE_METRIC_EVIDENCE_REQUIRED:" + work_id
            )
        missing = [
            field for field in LIVE_SCORE_FIELDS if not _s(metric_evidence.get(field))
        ]
        if missing:
            raise LiveSchedulerContractError(
                "LIVE_SCORE_METRIC_EVIDENCE_MISSING:"
                + work_id
                + ":"
                + ",".join(missing)
            )

        for field in LIVE_SCORE_FIELDS:
            core._f(raw.get(field, 0), field)
        success = core._f(
            raw.get("success_probability_lcb", 0),
            "success_probability_lcb",
        )
        if success > 1:
            raise LiveSchedulerContractError("SUCCESS_PROBABILITY_LCB_GT_ONE")

        calibration_ids.add(calibration_id)
        frontier_ids.add(frontier_id)
        verification_refs.add(independent_verification)

    if len(calibration_ids) != 1:
        raise LiveSchedulerContractError("LIVE_SCORE_CALIBRATION_MISMATCH")
    if len(frontier_ids) != 1:
        raise LiveSchedulerContractError("LIVE_WORK_FRONTIER_MISMATCH")
    if len(verification_refs) != 1:
        raise LiveSchedulerContractError("LIVE_SCORE_VERIFICATION_MISMATCH")

    return {
        "calibration_id": next(iter(calibration_ids)),
        "frontier_id": next(iter(frontier_ids)),
        "independent_verification_ref": next(iter(verification_refs)),
        "scale": LIVE_SCORE_CONTRACT_SCALE,
    }


def rank_live_work(work: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    contract = validate_live_score_contract(work)
    out = core.rank_work(
        work,
        checkpoint_open_obligation_count=core._current_open_obligation_count(),
    )
    out["schema"] = SCHEMA
    out["live_score_contract_verified"] = True
    out["live_score_contract"] = contract
    out["live_ranking_semantics"] = (
        "ONLY_COMMON_DIMENSIONLESS_EVIDENCE_BOUND_COMPLETE_FRONTIER_SCORES_RANK"
    )
    return out
