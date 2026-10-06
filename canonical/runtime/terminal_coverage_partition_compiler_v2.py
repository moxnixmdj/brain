from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from canonical.runtime.terminal_frontier_factorizer_v2 import (
    ATOMIC,
    META,
    EXTERNAL_RESULT_ATOMS,
)

ROUTES = ("J", "G", "T", "D", "U")

ASTRA_CAPABILITY_TARGETS = (
    "END_TO_END_COMPUTER_WORK",
    "RESEARCH_AND_KNOWLEDGE_ACQUISITION",
    "SOFTWARE_ENGINEERING",
    "PROFESSIONAL_WORK",
    "SCIENCE_AND_REASONING",
    "JUDGMENT_AND_SCOPE",
    "LONG_HORIZON_CONTINUITY",
    "DYNAMIC_TOOL_ORCHESTRATION",
)


class CoveragePartitionError(RuntimeError):
    pass


@dataclass(frozen=True)
class Classification:
    route: str
    status: str
    reason: str
    terminal_credit: bool = False


def _true(row: Mapping[str, Any], key: str) -> bool:
    return row.get(key) is True


def _all_true(row: Mapping[str, Any], keys: tuple[str, ...]) -> bool:
    return all(_true(row, key) for key in keys)


def classify_one(
    item_id: str,
    evidence: Mapping[str, Any] | None = None,
    *,
    external_result_candidate: bool = False,
) -> Classification:
    row = evidence or {}

    j_keys = (
        "complete_semantics_verified",
        "joint_optimum_verified",
        "hard_constraints_verified",
        "brain_owned_verified",
        "independent_verification_verified",
    )
    if _all_true(row, j_keys):
        return Classification(
            "J",
            "PROVED_ROUTE_CANDIDATE",
            "JOINT_OPTIMUM_AND_COMPLETE_SEMANTICS_VERIFIED",
        )

    g_keys = (
        "generator_verified",
        "brain_transfer_verified",
        "target_transfer_verified",
        "utility_pullback_verified",
        "hard_constraints_transfer_verified",
        "ownership_transfer_verified",
        "independent_verification_verified",
    )
    if _all_true(row, g_keys):
        return Classification(
            "G",
            "PROVED_ROUTE_CANDIDATE",
            "CONTEXT_GENERATOR_TRANSFER_PREMISES_VERIFIED",
        )

    t_keys = (
        "brain_ge_astra_verified",
        "astra_ge_opus55_verified",
        "same_context_verified",
        "same_evaluator_verified",
        "same_tool_policy_verified",
        "same_hard_constraints_verified",
        "distribution_aware_order_verified",
        "transitivity_verified",
        "brain_owned_verified",
        "astra_absent_from_brain_execution_verified",
        "independent_verification_verified",
    )
    if _all_true(row, t_keys):
        return Classification(
            "T",
            "PROVED_ROUTE_CANDIDATE",
            "EXACT_MATCHED_BRAIN_GE_ASTRA_GE_OPUS55_TRANSITIVITY_VERIFIED",
        )

    if _true(row, "direct_evidence_verified"):
        return Classification(
            "D",
            "PROVED_ROUTE_CANDIDATE",
            "EXACT_DIRECT_TARGET_OR_EVALUATOR_EVIDENCE_VERIFIED",
        )
    if external_result_candidate:
        return Classification(
            "D",
            "SCHEDULING_CANDIDATE__NO_CREDIT",
            "CURRENT_FACTORIZER_MARKS_EXTERNAL_RESULT_OR_ACCESS",
        )

    return Classification(
        "U",
        "UNRESOLVED_FAIL_CLOSED",
        "NO_SOUND_J_G_T_OR_DIRECT_EVIDENCE_CERTIFICATE",
    )


def compile_partition(
    evidence_by_item: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence_by_item = evidence_by_item or {}
    obligations = tuple(ATOMIC) + tuple(META)

    unknown = sorted(
        set(evidence_by_item) - set(obligations) - set(ASTRA_CAPABILITY_TARGETS)
    )
    if unknown:
        raise CoveragePartitionError("UNKNOWN_ITEMS:" + ",".join(unknown))

    classifications: dict[str, dict[str, Any]] = {}
    route_counts = {route: 0 for route in ROUTES}

    for item_id in obligations:
        c = classify_one(
            item_id,
            evidence_by_item.get(item_id),
            external_result_candidate=item_id in EXTERNAL_RESULT_ATOMS,
        )
        classifications[item_id] = {
            "route": c.route,
            "status": c.status,
            "reason": c.reason,
            "terminal_credit": c.terminal_credit,
        }
        route_counts[c.route] += 1

    calibration: dict[str, dict[str, Any]] = {}
    for item_id in ASTRA_CAPABILITY_TARGETS:
        c = classify_one(item_id, evidence_by_item.get(item_id))
        calibration[item_id] = {
            "route": c.route,
            "status": c.status,
            "reason": c.reason,
            "terminal_credit": False,
            "role": "ASTRA_CALIBRATION_TARGET_NOT_TERMINAL_OBLIGATION",
        }

    expected_obligation_count=len(obligations)
    if len(classifications) != expected_obligation_count:
        raise CoveragePartitionError(
            f"TRUTH_OBLIGATION_COUNT_DRIFT:{len(classifications)}"
        )

    proved_route_candidates = sorted(
        item_id
        for item_id, row in classifications.items()
        if row["status"] == "PROVED_ROUTE_CANDIDATE"
    )

    return {
        "status": (
            f"PASS__{expected_obligation_count}_CURRENT_TRUTH_OBLIGATIONS__"
            "FALSIFICATION_FIRST_ROUTING__ZERO_AUTOMATIC_CREDIT"
        ),
        "truth_obligation_count": len(classifications),
        "astra_calibration_target_count": len(calibration),
        "route_counts": route_counts,
        "classifications": classifications,
        "astra_calibration_targets": calibration,
        "proved_route_candidates": proved_route_candidates,
        "truth_obligations_deleted": 3,
        "truth_obligations_closed_by_routing_alone": 0,
        "terminal_credit_delta": 0,
        "ownership_credit_delta": 0,
        "astra_access_rule": (
            "SPEND_ONLY_AFTER_J_AND_G_FAIL_AND_ONLY_FOR_ASTRA_EXCLUSIVE_"
            "MAXIMALLY_DISCRIMINATING_BEHAVIORAL_INFORMATION"
        ),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(compile_partition(), indent=2, sort_keys=True))
