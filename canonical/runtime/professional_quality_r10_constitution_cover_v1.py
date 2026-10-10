"""Completeness check for the R10 decision constitution decomposition.

This verifier proves only that every governing law in the conservative R10
constitution is assigned to an executable structural proof slot or the
detected-defect enforcement guard, and that the guard's known R10 defeater set
matches the canonical R10 challenge catalog.

It does NOT prove underlying evidence truth, detector completeness, whole-leaf
property truth, quality, acceptance, promotion, or terminal completion.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime import professional_quality_r10_execution_guard_v1 as guard
from canonical.runtime import professional_quality_r10_proof_slot_verifier_v1 as slots

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_CONSTITUTION_COVER_V1"
ROOT_ID = "R10_ANALYSIS_DECISION"
LEAF_ID = "PQ::R10_ANALYSIS_DECISION::EXECUTION"
CLAIM_ID = guard.CLAIM_ID
CONSTITUTION_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_DECISION_CONSTITUTION_V1"

EXPECTED_ROOT_CONTRACT = (
    "Freeze or robustify admissible analysis, aggregation, compensation, risk "
    "and normative policy; preserve Pareto/incomparability structure and model "
    "multiplicity rather than selecting convenient scalarizations after outcomes are known."
)

LAW_TO_MECHANISM = {
    "target_and_constraints": (
        "SLOT", "target_and_hard_constraints_frozen",
    ),
    "decision_state": (
        "SLOT", "decision_state_lossless",
    ),
    "uncertainty": (
        "SLOT", "uncertainty_semantics_typed",
    ),
    "aggregation": (
        "SLOT", "aggregation_and_risk_policy_precommitted",
    ),
    "risk": (
        "SLOT", "aggregation_and_risk_policy_precommitted",
    ),
    "veto": (
        "SLOT", "veto_constraints_preserved",
    ),
    "multiplicity": (
        "SLOT", "model_or_analysis_multiplicity_resolved_or_escalated",
    ),
    "evidence_packet": (
        "SLOT", "evidence_packet_complete",
    ),
    "stopping": (
        "SLOT", "stopping_rule_precommitted",
    ),
    "absolute_floor": (
        "SLOT", "absolute_floor_not_inferred_from_weak_baseline",
    ),
    "defeaters": (
        "GUARD", "DETECTED_DEFEATER_AND_NEAR_MISS_ENFORCEMENT",
    ),
}


def _base(status: str, passed: bool) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "pass": passed,
        "root_id": ROOT_ID,
        "leaf_id": LEAF_ID,
        "claim_id": CLAIM_ID,
        "constitution_decomposition_complete": passed,
        "underlying_fact_truth_authority": False,
        "detection_completeness_proved": False,
        "whole_leaf_property_truth_proved": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }


def _r10_root(manifest: Mapping[str, Any]) -> Mapping[str, Any] | None:
    roots = manifest.get("roots")
    if not isinstance(roots, list):
        return None
    matches = [
        row for row in roots
        if isinstance(row, Mapping) and row.get("root_id") == ROOT_ID
    ]
    return matches[0] if len(matches) == 1 else None


def _catalog_r10_ids(catalog: Mapping[str, Any]) -> set[str]:
    rows = catalog.get("defeaters")
    if not isinstance(rows, list):
        rows = catalog.get("attack_classes")
    if not isinstance(rows, list):
        rows = catalog.get("nodes")
    if not isinstance(rows, list):
        rows = catalog.get("challenges")
    if not isinstance(rows, list):
        return set()
    out: set[str] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        ids = row.get("root_ids")
        if not isinstance(ids, list):
            ids = row.get("target_root_ids")
        if ROOT_ID in (ids or []):
            did = row.get("id")
            if isinstance(did, str) and did:
                out.add(did)
    return out


def evaluate(
    *,
    constitution: Mapping[str, Any],
    manifest: Mapping[str, Any],
    defeater_catalog: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    if constitution.get("schema") != CONSTITUTION_SCHEMA:
        errors.append("CONSTITUTION_SCHEMA_INVALID")
    if constitution.get("root_id") != ROOT_ID:
        errors.append("CONSTITUTION_ROOT_MISMATCH")
    if constitution.get("leaf_id") != LEAF_ID:
        errors.append("CONSTITUTION_LEAF_MISMATCH")
    if constitution.get("claim_id") != CLAIM_ID:
        errors.append("CONSTITUTION_CLAIM_MISMATCH")

    root = _r10_root(manifest)
    if root is None:
        errors.append("R10_ROOT_NOT_UNIQUE_IN_MANIFEST")
    else:
        if root.get("contract") != EXPECTED_ROOT_CONTRACT:
            errors.append("R10_ROOT_CONTRACT_DRIFT")
        execution = root.get("execution_leaf")
        if not isinstance(execution, Mapping) or execution.get("id") != LEAF_ID:
            errors.append("R10_EXECUTION_LEAF_DRIFT")

    laws = constitution.get("governing_laws")
    if not isinstance(laws, Mapping):
        errors.append("CONSTITUTION_GOVERNING_LAWS_INVALID")
        laws = {}

    law_keys = set(laws)
    expected_law_keys = set(LAW_TO_MECHANISM)
    missing_laws = sorted(expected_law_keys - law_keys)
    extra_laws = sorted(law_keys - expected_law_keys)
    if missing_laws:
        errors.append("CONSTITUTION_LAW_MISSING")
    if extra_laws:
        errors.append("CONSTITUTION_LAW_UNMAPPED")

    slot_names = set(slots.REQUIRED_SLOTS)
    mapped_slots = {
        target
        for kind, target in LAW_TO_MECHANISM.values()
        if kind == "SLOT"
    }
    missing_slot_implementation = sorted(mapped_slots - slot_names)
    orphan_slots = sorted(slot_names - mapped_slots)
    if missing_slot_implementation:
        errors.append("MAPPED_SLOT_NOT_IMPLEMENTED")
    if orphan_slots:
        errors.append("IMPLEMENTED_SLOT_NOT_JUSTIFIED_BY_CONSTITUTION")

    if slots.CLAIM_ID != CLAIM_ID or slots.ROOT_ID != ROOT_ID or slots.LEAF_ID != LEAF_ID:
        errors.append("SLOT_VERIFIER_SCOPE_DRIFT")
    if guard.CLAIM_ID != CLAIM_ID or guard.ROOT_ID != ROOT_ID or guard.LEAF_ID != LEAF_ID:
        errors.append("GUARD_SCOPE_DRIFT")

    catalog_ids = _catalog_r10_ids(defeater_catalog)
    guard_ids = set(guard.KNOWN_R10_DEFEATERS)
    missing_guard_defeaters = sorted(catalog_ids - guard_ids)
    foreign_guard_defeaters = sorted(guard_ids - catalog_ids)
    if missing_guard_defeaters:
        errors.append("CATALOG_R10_DEFEATER_NOT_ENFORCED")
    if foreign_guard_defeaters:
        errors.append("GUARD_R10_DEFEATER_NOT_IN_CANONICAL_CATALOG")

    profile_signal_classes = set(guard.NEAR_MISS_TO_TRIGGER)
    if not profile_signal_classes:
        errors.append("NEAR_MISS_ENFORCEMENT_EMPTY")

    passed = not errors
    return {
        **_base(
            (
                "PASS__R10_CONSTITUTION_FULLY_MAPPED_TO_STRUCTURAL_SLOTS_AND_"
                "DETECTED_DEFEATER_ENFORCEMENT"
                if passed
                else "FAIL_CLOSED__R10_CONSTITUTION_DECOMPOSITION_GAP"
            ),
            passed,
        ),
        "errors": errors,
        "governing_law_count": len(law_keys),
        "mapped_governing_law_count": len(expected_law_keys & law_keys),
        "proof_slot_count": len(slot_names),
        "mapped_proof_slot_count": len(mapped_slots & slot_names),
        "catalog_r10_defeater_count": len(catalog_ids),
        "guard_r10_defeater_count": len(guard_ids),
        "near_miss_signal_class_count": len(profile_signal_classes),
        "missing_laws": missing_laws,
        "extra_unmapped_laws": extra_laws,
        "missing_slot_implementation": missing_slot_implementation,
        "orphan_slots": orphan_slots,
        "missing_guard_defeaters": missing_guard_defeaters,
        "foreign_guard_defeaters": foreign_guard_defeaters,
        "law_to_mechanism": {
            key: {"kind": value[0], "mechanism": value[1]}
            for key, value in LAW_TO_MECHANISM.items()
        },
        "remaining_residual": (
            "UNDERLYING_SLOT_EVIDENCE_TRUTH_AND_CROSS_ROOT_DETECTOR_COMPLETENESS"
            if passed
            else "REPAIR_CONSTITUTION_DECOMPOSITION_BEFORE_FACT_TRUTH_WORK"
        ),
    }
