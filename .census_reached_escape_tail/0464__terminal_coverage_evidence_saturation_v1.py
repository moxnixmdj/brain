from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.terminal_coverage_partition_compiler_v1 import (
    compile_partition,
)

J_KEYS = (
    "complete_semantics_verified",
    "joint_optimum_verified",
    "hard_constraints_verified",
    "brain_owned_verified",
    "independent_verification_verified",
)


def complete_j_fixture() -> dict[str, bool]:
    return {key: True for key in J_KEYS}


def empty_evidence_countermodel(item_id: str = "AGENCY_MATCHED_SUCCESS_NONINFERIOR") -> dict[str, Any]:
    baseline = compile_partition()
    with_j = compile_partition({item_id: complete_j_fixture()})
    return {
        "item_id": item_id,
        "baseline_route": baseline["classifications"][item_id]["route"],
        "with_complete_j_route": with_j["classifications"][item_id]["route"],
        "baseline_j_count": baseline["route_counts"]["J"],
        "with_j_count": with_j["route_counts"]["J"],
        "empty_evidence_proves_no_j_certificate_exists": False,
        "countermodel_valid": (
            baseline["classifications"][item_id]["route"] != "J"
            and with_j["classifications"][item_id]["route"] == "J"
            and baseline["route_counts"]["J"] == 0
            and with_j["route_counts"]["J"] == 1
        ),
    }


def coverage_projection_truth_status(
    *,
    evidence_by_item: Mapping[str, Mapping[str, Any]] | None,
    scan_state_by_item: Mapping[str, str] | None,
) -> dict[str, Any]:
    compiled = compile_partition(evidence_by_item or {})
    scan_state_by_item = scan_state_by_item or {}
    allowed = {
        "UNSCANNED",
        "PARTIAL",
        "SATURATED_NO_BOUND_CERTIFICATE",
        "BOUND_CERTIFICATE_FOUND",
    }
    invalid = sorted(
        f"{item}:{state}"
        for item, state in scan_state_by_item.items()
        if state not in allowed
    )
    if invalid:
        raise ValueError("INVALID_SCAN_STATE:" + ",".join(invalid))

    obligations = tuple(compiled["classifications"])
    missing_scan = sorted(x for x in obligations if x not in scan_state_by_item)
    saturated = not missing_scan and all(
        scan_state_by_item[x] in {
            "SATURATED_NO_BOUND_CERTIFICATE",
            "BOUND_CERTIFICATE_FOUND",
        }
        for x in obligations
    )
    return {
        "compiled": compiled,
        "scan_complete_for_all_32": saturated,
        "missing_scan_items": missing_scan,
        "negative_route_counts_are_exhaustive_current_evidence_claim": saturated,
        "status": (
            "SATURATED_CURRENT_EVIDENCE_PROJECTION"
            if saturated
            else "BASELINE_OR_PARTIAL_EVIDENCE_PROJECTION"
        ),
        "terminal_credit": False,
    }
