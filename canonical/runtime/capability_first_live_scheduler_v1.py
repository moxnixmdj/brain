"""Fail-closed live wrapper for the capability-first scheduler.

The core V1 scheduler remains a planning/scoring primitive.  This wrapper is
the only intended live entrypoint: it rejects arbitrary or heterogeneous score
numbers unless every candidate is bound to one complete, independently
verified, dimensionless calibration/frontier contract.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
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
ROOT = Path(__file__).resolve().parents[2]
CURRENT_FRONTIER_PATH = ROOT / "canonical/governance/CURRENT_LIVE_WORK_FRONTIER.json"


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


def _git_blob_sha(path: Path) -> str:
    raw = path.read_bytes()
    return sha1(
        b"blob " + str(len(raw)).encode("ascii") + bytes([0]) + raw
    ).hexdigest()


def validate_current_frontier(
    work: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
    *,
    frontier_path: Path = CURRENT_FRONTIER_PATH,
) -> dict[str, Any]:
    try:
        frontier = json.loads(frontier_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LiveSchedulerContractError("CURRENT_LIVE_WORK_FRONTIER_UNAVAILABLE") from exc

    expected_frontier_id = _s(frontier.get("frontier_id"))
    if not expected_frontier_id:
        raise LiveSchedulerContractError("CURRENT_LIVE_WORK_FRONTIER_ID_MISSING")
    if _s(contract.get("frontier_id")) != expected_frontier_id:
        raise LiveSchedulerContractError("LIVE_WORK_FRONTIER_NOT_CURRENT")

    source_set = frontier.get("scope", {}).get("source_set")
    if not isinstance(source_set, list) or not source_set:
        raise LiveSchedulerContractError("CURRENT_LIVE_WORK_FRONTIER_SOURCE_SET_MISSING")

    stale: list[str] = []
    for row in source_set:
        if not isinstance(row, Mapping):
            raise LiveSchedulerContractError("CURRENT_LIVE_WORK_FRONTIER_SOURCE_SET_INVALID")
        rel = _s(row.get("path"))
        expected_sha = _s(row.get("git_blob_sha"))
        if not rel or not expected_sha:
            raise LiveSchedulerContractError("CURRENT_LIVE_WORK_FRONTIER_SOURCE_BINDING_INVALID")
        source = ROOT / rel
        if not source.is_file() or _git_blob_sha(source) != expected_sha:
            stale.append(rel)
    if stale:
        raise LiveSchedulerContractError(
            "LIVE_WORK_FRONTIER_STALE:" + ",".join(sorted(stale))
        )

    candidates = frontier.get("candidates")
    if not isinstance(candidates, list):
        raise LiveSchedulerContractError("CURRENT_LIVE_WORK_FRONTIER_CANDIDATES_INVALID")
    expected_ids: set[str] = set()
    for row in candidates:
        if not isinstance(row, Mapping):
            raise LiveSchedulerContractError("CURRENT_LIVE_WORK_FRONTIER_CANDIDATES_INVALID")
        work_id = _s(row.get("work_id"))
        if not work_id:
            raise LiveSchedulerContractError("CURRENT_LIVE_WORK_FRONTIER_CANDIDATE_ID_MISSING")
        if _s(row.get("score_state")).startswith("INELIGIBLE_"):
            continue
        expected_ids.add(work_id)

    supplied_ids = {_s(row.get("work_id")) for row in work}
    if supplied_ids != expected_ids:
        missing = sorted(expected_ids - supplied_ids)
        extra = sorted(supplied_ids - expected_ids)
        raise LiveSchedulerContractError(
            "LIVE_WORK_FRONTIER_CANDIDATE_SET_MISMATCH:"
            + "missing="
            + ",".join(missing)
            + ";extra="
            + ",".join(extra)
        )

    live_selection = frontier.get("live_selection")
    if not isinstance(live_selection, Mapping) or live_selection.get("authorized") is not True:
        raise LiveSchedulerContractError("LIVE_WORK_FRONTIER_SELECTION_NOT_AUTHORIZED")

    return {
        "frontier_id": expected_frontier_id,
        "source_count": len(source_set),
        "eligible_candidate_count": len(expected_ids),
        "currentness_verified": True,
    }


def rank_live_work(work: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    contract = validate_live_score_contract(work)
    frontier = validate_current_frontier(work, contract)
    out = core.rank_work(
        work,
        checkpoint_open_obligation_count=core._current_open_obligation_count(),
    )
    out["schema"] = SCHEMA
    out["live_score_contract_verified"] = True
    out["live_score_contract"] = contract
    out["live_frontier_currentness"] = frontier
    out["live_ranking_semantics"] = (
        "ONLY_COMMON_DIMENSIONLESS_EVIDENCE_BOUND_COMPLETE_FRONTIER_SCORES_RANK"
    )
    return out
