"""Fail-closed gate distinguishing capability transfer from cognition outsourcing."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_CAPABILITY_TRANSFER_OWNERSHIP_GATE_V1"

TRANSFER_METHODS = {
    "DISTILLATION",
    "BEHAVIORAL_IMITATION",
    "SUPERVISED_TRANSFER",
    "PREFERENCE_TRANSFER",
    "SYNTHETIC_DATA_TRAINING",
    "FINE_TUNING_BRAIN_OWNED_SUBSTRATE",
    "CHECKPOINT_OR_TASK_VECTOR_TRANSFER",
    "SPARSE_OR_LOW_RANK_TRANSFER",
    "MODULE_EXPERT_OR_CIRCUIT_EXTRACTION",
    "ALGORITHM_OR_PROCEDURE_RECOVERY",
    "MECHANISTIC_REIMPLEMENTATION",
    "VERIFIED_COMPOSITION",
}

def evaluate(record: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    method = str(record.get("transfer_method") or "").strip()
    if method not in TRANSFER_METHODS:
        errors.append("TRANSFER_METHOD_UNCLASSIFIED")

    required_true = (
        "acquisition_and_deployment_phases_separated",
        "donor_use_confined_to_acquisition",
        "brain_owned_operative_artifact",
        "operative_artifact_content_addressed",
        "applicable_rights_and_provenance_closed",
        "donor_access_disabled_during_qualification",
        "donor_deletion_behavior_preserved",
        "independent_heldout_qualification_pass",
        "heldout_not_used_for_training_selection_or_tuning",
        "causal_ablation_pass",
        "causal_rescue_pass",
        "full_runtime_dependency_inventory_complete",
        "no_answer_leakage",
        "future_use_requires_no_donor_rediscovery",
    )
    for key in required_true:
        if record.get(key) is not True:
            errors.append("REQUIRED_TRUE_MISSING:" + key)

    zero_fields = (
        "donor_runtime_dependency_count",
        "external_model_runtime_dependency_count",
        "online_teacher_call_count",
        "teacher_fallback_path_count",
        "undeclared_runtime_dependency_count",
    )
    for key in zero_fields:
        if record.get(key) != 0:
            errors.append("ZERO_REQUIRED:" + key)

    if record.get("qualification_performed_after_donor_removal") is not True:
        errors.append("QUALIFICATION_NOT_POST_DONOR_REMOVAL")

    if record.get("donor_role") != "ACQUISITION_SOURCE_ONLY":
        errors.append("DONOR_ROLE_NOT_ACQUISITION_ONLY")

    if record.get("operative_solver_role") != "BRAIN_OWNED_DERIVED_MECHANISM":
        errors.append("OPERATIVE_SOLVER_NOT_BRAIN_DERIVED_MECHANISM")

    if record.get("student_or_derived_artifact_distinct_from_donor") is not True:
        errors.append("DERIVED_ARTIFACT_NOT_DISTINCT_FROM_DONOR")

    passed = not errors
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__CAPABILITY_INTERNALIZED__DONOR_ABSENT_AT_RUNTIME"
            if passed else
            "FAIL_CLOSED__COGNITION_OUTSOURCING_OR_UNPROVEN_TRANSFER"
        ),
        "pass": passed,
        "transfer_method": method or None,
        "brain_ownership_credit_allowed": passed,
        "brain_benchmark_credit_allowed": passed,
        "brain_acceptance_credit_allowed": passed,
        "brain_promotion_credit_allowed": passed,
        "brain_terminal_credit_allowed": passed,
        "errors": sorted(set(errors)),
        "rule": "TRANSFER_ALLOWED_ONLY_IF_DONOR_IS_ACQUISITION_ONLY_AND_ABSENT_FROM_QUALIFICATION_AND_DEPLOYMENT",
    }
