"""Fail-closed runtime guard for Brain-credited cognition paths.

This guard is intentionally small and deterministic. It verifies that the
canonical ownership/transfer boundary, runtime model-planner kill switch, and
the executable acceptance/transfer gates still enforce zero external model
cognition before any live, promotion, or terminal credit path proceeds.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.acceptance_capability_source_gate_v2 import (
    evaluate as evaluate_acceptance_source,
)
from canonical.runtime.capability_transfer_ownership_gate_v1 import (
    evaluate as evaluate_capability_transfer,
)

SCHEMA = "PROJECT_BRAIN_RUNTIME_COGNITION_CREDIT_GUARD_V1"
ROOT = Path(__file__).resolve().parents[2]

REQUIRED_LAWS = (
    "canonical/laws/GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.md",
    "canonical/laws/CAPABILITY_TRANSFER_VS_COGNITION_OUTSOURCING_LAW_V1.md",
    "canonical/laws/EXTERNAL_KNOWLEDGE_CAPABILITY_TRANSFER_RUNTIME_COGNITION_BOUNDARY_LAW_V1.md",
    "canonical/laws/WHITE_BOX_CAPABILITY_HARVESTING_LAW_V3.md",
)

REQUIRED_TRUE = (
    "external_model_cognition_in_brain_credit_producer_path_forbidden",
    "model_assisted_execution_never_brain_capability_proof",
    "runtime_cognition_provenance_required_for_all_brain_credit",
    "unknown_cognition_provenance_fails_closed",
    "local_open_weight_self_hosted_or_content_addressed_model_still_counts_as_model_dependency",
    "benchmark_credit_requires_zero_external_model_cognition_dependencies",
    "capability_transfer_vs_cognition_outsourcing_law_required",
    "capability_transfer_ownership_gate_required",
    "donor_deletion_protocol_required_for_all_donor_derived_promotions",
    "distillation_allowed_only_as_acquisition_time_transfer",
    "teacher_or_donor_runtime_cognition_forbidden",
    "teacher_fallback_rerank_critique_online_planning_forbidden",
    "copied_or_rehosted_teacher_is_not_transfer",
    "post_donor_removal_heldout_qualification_required",
    "all_donor_derived_promotions_require_zero_external_model_runtime_dependencies",
    "donor_provenance_must_persist_across_verified_episodes",
    "donor_derived_skill_candidate_requires_exact_candidate_bound_transfer_record",
    "donor_derived_skill_verifier_must_not_run_before_transfer_gate_pass",
    "transfer_gate_pass_never_grants_reuse_by_itself",
    "donor_derived_skill_requires_independent_skill_verification_after_transfer_gate",
    "temporal_provenance_laundering_forbidden",
    "external_contribution_three_way_classification_required",
    "external_knowledge_must_be_non_authoritative_observation_or_evidence",
    "external_knowledge_target_solving_policy_or_answer_forbidden",
    "acquisition_donor_must_remain_transfer_gated_until_donor_deletion",
    "runtime_cognition_provider_forbidden_regardless_of_label_hosting_or_cost",
    "ambiguous_external_contribution_classification_fails_closed",
    "runtime_external_cognition_lock_verifier_required",
    "python_startup_model_planner_kill_switch_required",
    "runtime_cognition_credit_guard_required",
    "runtime_cognition_credit_guard_fail_closed_before_credit",
    "runtime_cognition_credit_guard_live_execution_binding_required",
    "runtime_cognition_credit_guard_self_improvement_binding_required",
    "runtime_cognition_credit_guard_terminal_closure_binding_required",
    "runtime_cognition_credit_guard_ownership_promotion_binding_required",
    "runtime_cognition_credit_guard_final_cleanroom_binding_required",
    "runtime_cognition_credit_guard_kstar_promotion_binding_required",
    "runtime_cognition_credit_guard_global_ownership_binding_required",
    "local_runner_for_cognition_governance_forbidden",
)

REQUIRED_PATHS = {
    "runtime_cognition_credit_guard_path": "canonical/runtime/runtime_cognition_credit_guard_v1.py",
    "runtime_cognition_credit_guard_verification_path": "canonical/verification/RUNTIME_COGNITION_CREDIT_GUARD_REMOTE_VERIFY_20261011_V1.json",
}

REQUIRED_BINDINGS = {
    "canonical/runtime/live_integrated_brain_v1.py": 2,
    "canonical/runtime/autonomous_verified_self_improvement_v1.py": 3,
    "canonical/runtime/terminal_closure_reducer.py": 2,
    "canonical/runtime/ownership_promotion_compiler_v1.py": 1,
    "canonical/runtime/final_terminal_cleanroom_gate_v1.py": 1,
    "canonical/runtime/terminal_global_ownership_postconditions_reducer_v1.py": 1,
    "canonical/runtime/terminal_kstar_promotion_bridge_v1.py": 1,
}

REQUIRED_PRECEDENCE = [
    "TARGET_SOLVING_COGNITION=>K3_FORBIDDEN",
    "DONOR_DERIVED_LEARNED_MECHANISM=>K2_TRANSFER_GATED",
    "SOURCE_BOUND_NON_AUTHORITATIVE_FACT_OR_EVIDENCE=>K1_INFORMATION_ONLY",
]


def _owned_no_model_route() -> dict[str, Any]:
    return {
        "benchmark_harness_zero_cost": True,
        "scorer_frozen": True,
        "brain_candidate_bound": True,
        "brain_owned_operative_configuration": True,
        "configuration_materially_constrains_execution": True,
        "capability_package_contains_configuration": True,
        "promotion_evaluates_brain_configured_system": True,
        "external_hidden_target_capability_provider": False,
        "ownership_claim_relies_on_model_standalone_superiority": False,
        "future_use_requires_capability_rediscovery": False,
        "model_role": "NONE",
        "model_dependency_count": 0,
        "incremental_spend_usd": 0,
    }


def _valid_transfer() -> dict[str, Any]:
    return {
        "transfer_method": "DISTILLATION",
        "acquisition_and_deployment_phases_separated": True,
        "donor_use_confined_to_acquisition": True,
        "brain_owned_operative_artifact": True,
        "operative_artifact_content_addressed": True,
        "applicable_rights_and_provenance_closed": True,
        "donor_access_disabled_during_qualification": True,
        "donor_deletion_behavior_preserved": True,
        "independent_heldout_qualification_pass": True,
        "heldout_not_used_for_training_selection_or_tuning": True,
        "causal_ablation_pass": True,
        "causal_rescue_pass": True,
        "full_runtime_dependency_inventory_complete": True,
        "no_answer_leakage": True,
        "future_use_requires_no_donor_rediscovery": True,
        "donor_runtime_dependency_count": 0,
        "external_model_runtime_dependency_count": 0,
        "online_teacher_call_count": 0,
        "teacher_fallback_path_count": 0,
        "undeclared_runtime_dependency_count": 0,
        "qualification_performed_after_donor_removal": True,
        "donor_role": "ACQUISITION_SOURCE_ONLY",
        "operative_solver_role": "BRAIN_OWNED_DERIVED_MECHANISM",
        "student_or_derived_artifact_distinct_from_donor": True,
    }


def evaluate_materials(
    pointer: Mapping[str, Any],
    startup_text: str,
    astra_runtime_text: str,
    binding_sources: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    mandatory = pointer.get("mandatory_laws")
    if not isinstance(mandatory, list):
        errors.append("MANDATORY_LAWS_INVALID")
        mandatory = []
    for law in REQUIRED_LAWS:
        if law not in mandatory:
            errors.append("MANDATORY_LAW_MISSING:" + law)

    boot = pointer.get("boot_requirements")
    if not isinstance(boot, Mapping):
        errors.append("BOOT_REQUIREMENTS_INVALID")
        boot = {}
    for key in REQUIRED_TRUE:
        if boot.get(key) is not True:
            errors.append("BOOT_REQUIREMENT_NOT_TRUE:" + key)
    if boot.get("external_contribution_classification_precedence") != REQUIRED_PRECEDENCE:
        errors.append("EXTERNAL_CONTRIBUTION_PRECEDENCE_WEAKENED")
    for key, expected in REQUIRED_PATHS.items():
        if boot.get(key) != expected:
            errors.append("BOOT_PATH_MISMATCH:" + key)
    current_frontier = pointer.get("current_frontier")
    current_frontier = current_frontier if isinstance(current_frontier, Mapping) else {}
    harvest = current_frontier.get("white_box_capability_harvest")
    harvest = harvest if isinstance(harvest, Mapping) else {}
    execution_governance = pointer.get("execution_governance")
    execution_governance = execution_governance if isinstance(execution_governance, Mapping) else {}
    mission_lock = pointer.get("mission_lock")
    mission_lock = mission_lock if isinstance(mission_lock, Mapping) else {}

    nested_expected = (
        ("CURRENT_FRONTIER_MISSION_LOCK", current_frontier.get("frontier_capability_mission_lock_path"), "canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V10.md"),
        ("CURRENT_FRONTIER_HARVEST_LAW", harvest.get("law_path"), "canonical/laws/WHITE_BOX_CAPABILITY_HARVESTING_LAW_V3.md"),
        ("CURRENT_FRONTIER_CAPSULE_SCHEMA", harvest.get("capsule_schema_path"), "canonical/governance/WHITE_BOX_CAPABILITY_CAPSULE_SCHEMA_V3.json"),
        ("EXECUTION_MISSION_LOCK", execution_governance.get("capability_realization_mission_lock"), "canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V10.md"),
        ("EXECUTION_FRONTIER_MISSION_LOCK", execution_governance.get("frontier_capability_mission_lock"), "canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V10.md"),
        ("EXECUTION_HARVEST_LAW", execution_governance.get("white_box_capability_harvesting_law"), "canonical/laws/WHITE_BOX_CAPABILITY_HARVESTING_LAW_V3.md"),
        ("EXECUTION_CAPSULE_SCHEMA", execution_governance.get("white_box_capability_capsule_schema"), "canonical/governance/WHITE_BOX_CAPABILITY_CAPSULE_SCHEMA_V3.json"),
        ("MISSION_AUTHORITY", mission_lock.get("authority_path"), "canonical/laws/FRONTIER_KNOWLEDGE_CAPABILITY_INTERNALIZATION_MISSION_LOCK_V10.md"),
        ("MISSION_MODEL_OWNERSHIP_LAW", mission_lock.get("model_substrate_law"), "canonical/laws/GENERAL_COGNITION_SUBSTRATE_AND_CAPABILITY_OWNERSHIP_LAW_V4.md"),
        ("MISSION_TRANSFER_BOUNDARY_LAW", mission_lock.get("capability_transfer_boundary_law"), "canonical/laws/CAPABILITY_TRANSFER_VS_COGNITION_OUTSOURCING_LAW_V1.md"),
        ("MISSION_EXTERNAL_CONTRIBUTION_BOUNDARY_LAW", mission_lock.get("external_contribution_boundary_law"), "canonical/laws/EXTERNAL_KNOWLEDGE_CAPABILITY_TRANSFER_RUNTIME_COGNITION_BOUNDARY_LAW_V1.md"),
        ("MISSION_HARVEST_LAW", mission_lock.get("white_box_harvesting_law"), "canonical/laws/WHITE_BOX_CAPABILITY_HARVESTING_LAW_V3.md"),
        ("MISSION_CAPSULE_SCHEMA", mission_lock.get("capability_capsule_schema"), "canonical/governance/WHITE_BOX_CAPABILITY_CAPSULE_SCHEMA_V3.json"),
    )
    for label, actual, expected in nested_expected:
        if actual != expected:
            errors.append("STALE_OR_CONTRADICTORY_POINTER_AUTHORITY:" + label)

    if "MODEL_BASED" in str(execution_governance.get("frontier_comparison_rule") or ""):
        errors.append("STALE_MODEL_BASED_FRONTIER_COMPARISON_RULE")
    if mission_lock.get("general_computation_substrate") != "NON_MODEL_GENERAL_COMPUTATION_MAY_BE_EXTERNAL__TARGET_SOLVING_MODEL_COGNITION_FORBIDDEN_IN_CREDITED_PRODUCER_PATH":
        errors.append("MISSION_GENERAL_COMPUTATION_SUBSTRATE_BOUNDARY_INVALID")

    if binding_sources is not None:
        for path, minimum_calls in REQUIRED_BINDINGS.items():
            source = binding_sources.get(path)
            if not isinstance(source, str):
                errors.append("COGNITION_GUARD_BINDING_SOURCE_MISSING:" + path)
                continue
            if "runtime_cognition_credit_guard_v1" not in source:
                errors.append("COGNITION_GUARD_IMPORT_MISSING:" + path)
            if source.count("assert_credit_path_cognition_governance(") < minimum_calls:
                errors.append("COGNITION_GUARD_CALL_COUNT_WEAKENED:" + path)

    if "ASTRA_DISABLE_MODEL_PLANNER" not in startup_text:
        errors.append("STARTUP_MODEL_PLANNER_KILL_SWITCH_MISSING")
    if not any(token in startup_text for token in ("='1'", '="1"', '= "1"', "= '1'")):
        errors.append("STARTUP_MODEL_PLANNER_KILL_SWITCH_NOT_ONE")

    marker = "def _planner_post(prompt, timeout_s=20):"
    try:
        start = astra_runtime_text.index(marker)
        window = astra_runtime_text[start:start + 900]
    except ValueError:
        window = ""
        errors.append("ASTRA_MODEL_PLANNER_ENTRYPOINT_NOT_FOUND")
    if "ASTRA_DISABLE_MODEL_PLANNER" not in window:
        errors.append("ASTRA_RUNTIME_KILL_SWITCH_CHECK_MISSING")
    if "MODEL_PLANNER_DISABLED_BY_POLICY" not in window:
        errors.append("ASTRA_RUNTIME_FAIL_CLOSED_SIGNAL_MISSING")

    clean_acceptance = evaluate_acceptance_source(_owned_no_model_route())
    if clean_acceptance.get("pass") is not True:
        errors.append("ACCEPTANCE_GATE_REJECTS_CLEAN_ZERO_MODEL_ROUTE")
    poisoned_acceptance = _owned_no_model_route()
    poisoned_acceptance["model_role"] = "GENERAL_COGNITION_SUBSTRATE"
    poisoned_acceptance["model_dependency_count"] = 1
    rejected = evaluate_acceptance_source(poisoned_acceptance)
    if rejected.get("pass") is not False:
        errors.append("ACCEPTANCE_GATE_ALLOWS_EXTERNAL_MODEL_COGNITION")
    if "EXTERNAL_MODEL_COGNITION_DEPENDENCY_FORBIDDEN" not in (rejected.get("errors") or []):
        errors.append("ACCEPTANCE_GATE_MODEL_DEPENDENCY_REJECTION_MISSING")

    clean_transfer = evaluate_capability_transfer(_valid_transfer())
    if clean_transfer.get("pass") is not True:
        errors.append("TRANSFER_GATE_REJECTS_CLEAN_POST_DONOR_TRANSFER")
    poisoned_transfer = deepcopy(_valid_transfer())
    poisoned_transfer["online_teacher_call_count"] = 1
    poisoned_transfer["donor_runtime_dependency_count"] = 1
    transfer_rejected = evaluate_capability_transfer(poisoned_transfer)
    if transfer_rejected.get("pass") is not False:
        errors.append("TRANSFER_GATE_ALLOWS_RUNTIME_TEACHER")
    if transfer_rejected.get("brain_terminal_credit_allowed") is not False:
        errors.append("TRANSFER_GATE_RUNTIME_TEACHER_TERMINAL_CREDIT_NOT_ZERO")

    return {
        "schema": SCHEMA,
        "status": "PASS__COGNITION_GOVERNANCE_INTACT" if not errors else "FAIL_CLOSED__COGNITION_GOVERNANCE_WEAKENED",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "external_model_runtime_cognition_credit_authority": False,
        "distillation_transfer_requires_post_donor_removal_qualification": True,
        "terminal_authority": False,
    }


def evaluate_repository(root: str | Path | None = None) -> dict[str, Any]:
    base = Path(root).resolve() if root is not None else ROOT
    try:
        pointer = json.loads((base / "canonical/CANONICAL_POINTER.json").read_text(encoding="utf-8"))
        startup = (base / "sitecustomize.py").read_text(encoding="utf-8")
        runtime = (base / "canonical/runtime/astra_runtime.py").read_text(encoding="utf-8")
        bindings = {
            path: (base / path).read_text(encoding="utf-8")
            for path in REQUIRED_BINDINGS
        }
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__COGNITION_GOVERNANCE_UNREADABLE",
            "pass": False,
            "errors": [type(exc).__name__ + ":" + str(exc)],
            "external_model_runtime_cognition_credit_authority": False,
            "terminal_authority": False,
        }
    if not isinstance(pointer, Mapping):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED__COGNITION_GOVERNANCE_POINTER_INVALID",
            "pass": False,
            "errors": ["CANONICAL_POINTER_NOT_OBJECT"],
            "external_model_runtime_cognition_credit_authority": False,
            "terminal_authority": False,
        }
    return evaluate_materials(pointer, startup, runtime, bindings)


def assert_credit_path_cognition_governance(root: str | Path | None = None) -> dict[str, Any]:
    result = evaluate_repository(root)
    if result.get("pass") is not True:
        raise RuntimeError(
            "COGNITION_GOVERNANCE_FAIL_CLOSED:"
            + ",".join(str(x) for x in (result.get("errors") or []))
        )
    return result


if __name__ == "__main__":
    result = evaluate_repository()
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["pass"] else 1)
