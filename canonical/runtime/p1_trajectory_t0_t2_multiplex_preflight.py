"""Fail-closed prewave verifier for P1 trajectory causal-recovery T0/T2 multiplex binding."""
from __future__ import annotations

import json
from pathlib import Path

BINDING = "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
MANIFEST = "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json"
REQUIRED_ROUTE = "P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF"
REQUIRED_SURFACES = {
    "T0": {"FRONTIERCODE_V1_1", "CURSORBENCH_4_0"},
    "T2": {"RECOVERY_SCOPE_COMPOSITION"},
}
FORBIDDEN_VISIBLE = {
    "HIDDEN_CAUSE_LABEL",
    "REFERENCE_REPAIR_TARGET",
    "HIDDEN_INTERVENTION_OR_RESCUE_RESULT",
    "GOLD_CAUSAL_EQUIVALENCE_CLASS",
    "MUTATION_LABELS_OR_EXPECTED_FAILURE_REASON",
    "POST_FREEZE_CASE_SELECTION_INFORMATION",
}
REQUIRED_CHECKS = {
    "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
    "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
    "NOMINATED_REPAIR_IS_FALSIFIABLE",
    "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
    "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT",
    "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
    "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT",
    "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
}
REQUIRED_MUTATIONS = {
    "SELECT_DOWNSTREAM_SYMPTOM",
    "SELECT_LATER_CORRELATED_STEP",
    "IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT",
    "UNFALSIFIABLE_DIAGNOSIS",
    "REPAIR_TARGET_WITH_NO_RESCUE",
    "FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE",
    "DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN",
    "SWAP_TOOL_OR_AUTHORITY_FAILURE_CLASS",
    "DROP_PROVENANCE_OR_DEPENDENCY_EDGE",
}
REQUIRED_DEPS = (
    "canonical/runtime/trajectory_failure_typed_ir_candidate_v4.py",
    "canonical/runtime/trajectory_failure_typed_ir_proof_v4.py",
    "canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    "canonical/verification/CONTRACT_NATIVE_PROOF_INFORMATION_BOUNDARY_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
    "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json",
    "canonical/governance/TERMINAL_PORTFOLIO_PREWAVE_PROTOCOL_V1.json",
)


def _manifest_has_route(manifest: dict, portfolio: str, surface_id: str) -> bool:
    p = ((manifest.get("portfolios") or {}).get(portfolio) or {})
    for row in p.get("surfaces") or []:
        if row.get("id") == surface_id and REQUIRED_ROUTE in (row.get("proof_routes") or []):
            return True
    return False


def evaluate(root: Path) -> dict:
    errors: list[str] = []
    try:
        binding = json.loads((root / BINDING).read_text(encoding="utf-8"))
        manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "schema": "PROJECT_BRAIN_P1_T0_T2_MULTIPLEX_PREFLIGHT_VERDICT_V1",
            "pass": False,
            "errors": ["INPUT_UNREADABLE:" + type(exc).__name__],
            "execution_authority": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    if binding.get("behavior_id") != "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
        errors.append("BEHAVIOR_ID")
    if binding.get("proof_mode") != "T0_T2_MULTIPLEXED_DETERMINISTIC_INTERVENTION_RESCUE_GATE":
        errors.append("PROOF_MODE")
    if set(binding.get("portfolio_bindings") or []) != {"T0", "T2"}:
        errors.append("PORTFOLIO_BINDING")

    expected_direct = {
        f"{portfolio}/{surface}::{REQUIRED_ROUTE}"
        for portfolio, surfaces in REQUIRED_SURFACES.items()
        for surface in surfaces
    }
    if set(binding.get("direct_surface_bindings") or []) != expected_direct:
        errors.append("DIRECT_SURFACE_BINDINGS")
    for portfolio, surfaces in REQUIRED_SURFACES.items():
        for surface in surfaces:
            if not _manifest_has_route(manifest, portfolio, surface):
                errors.append(f"{portfolio}_{surface}_P1_ROUTE_NOT_BOUND")

            p = ((manifest.get("portfolios") or {}).get(portfolio) or {})
            surface_row = next((row for row in (p.get("surfaces") or []) if row.get("id") == surface), None)
            route_specific = ((surface_row or {}).get("route_specific_evaluators") or {}).get(REQUIRED_ROUTE) or {}
            if (surface_row or {}).get("route_specific_bindings_take_precedence") is not True:
                errors.append(f"{portfolio}_{surface}_P1_ROUTE_SPECIFIC_PRECEDENCE_MISSING")
            if route_specific.get("binding") != BINDING:
                errors.append(f"{portfolio}_{surface}_P1_V4_BINDING_MISSING")
            if route_specific.get("candidate") != "canonical/runtime/trajectory_failure_typed_ir_candidate_v4.py":
                errors.append(f"{portfolio}_{surface}_P1_V4_CANDIDATE_MISSING")
            if route_specific.get("preflight_population") != "canonical/runtime/trajectory_failure_typed_ir_proof_v4.py":
                errors.append(f"{portfolio}_{surface}_P1_V4_PROOF_MISSING")
            if route_specific.get("independent_preflight") != "canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":
                errors.append(f"{portfolio}_{surface}_P1_V4_RECEIPT_MISSING")
            if route_specific.get("generic_contract_native_evaluator_superseded_for_this_route") is not True:
                errors.append(f"{portfolio}_{surface}_GENERIC_P1_EVALUATOR_NOT_SUPERSEDED")

    visible = set(binding.get("candidate_visible_information") or [])
    forbidden = set(binding.get("candidate_must_not_receive") or [])
    if visible & FORBIDDEN_VISIBLE:
        errors.append("HIDDEN_CAUSAL_ORACLE_LEAK")
    if not FORBIDDEN_VISIBLE <= forbidden:
        errors.append("FORBIDDEN_INFORMATION_SET_INCOMPLETE")

    ev = binding.get("evaluator") or {}
    if set(ev.get("required_checks") or []) != REQUIRED_CHECKS:
        errors.append("CHECK_SET")
    if set(ev.get("required_mutations") or []) != REQUIRED_MUTATIONS:
        errors.append("MUTATION_SET")
    if ev.get("role_of_bounded_suite") != "INFORMATION_BOUNDARY_CAUSAL_STRUCTURE_NONIDENTIFIABILITY_AND_DERIVED_REPAIR_TARGET_PREFLIGHT_ONLY__NOT_WHOLE_DOMAIN_TERMINAL_SCORE":
        errors.append("BOUNDED_SUITE_SCOPE_OVERCLAIM")
    if ev.get("mutation_acceptance") != "ALL_APPLICABLE_LOAD_BEARING_P1_MUTATIONS_MUST_BE_REJECTED_OR_CAUSE_PARENT_TERMINAL_ACCEPTANCE_FAILURE":
        errors.append("MUTATION_ACCEPTANCE")

    ta = binding.get("terminal_acceptance") or {}
    if ta.get("prewave_binding_is_terminal_result") is not False:
        errors.append("PREWAVE_RESULT_OVERCLAIM")
    if ta.get("standalone_synthetic_whole_domain_score_forbidden") is not True:
        errors.append("SYNTHETIC_SCOPE_OVERCLAIM")
    if ta.get("terminal_evidence_source") != "THE_FROZEN_T0_AND_T2_TERMINAL_OBSERVATIONS_WITH_DIRECT_P1_INTERVENTION_RESCUE_INSTRUMENTATION":
        errors.append("TERMINAL_EVIDENCE_SOURCE")
    if ta.get("parent_or_direct_surface_credit_only_for_declared_scope") is not True:
        errors.append("SURFACE_SCOPE_INHERITANCE")
    if ta.get("any_load_bearing_p1_failure_blocks_behavior_proof") is not True:
        errors.append("P1_FAILURE_NOT_BLOCKING")
    rule = str(ta.get("proof_rule") or "")
    if "NO_PRIVATE_SCORE_INFERENCE" not in rule:
        errors.append("PRIVATE_SCORE_PROOF_RULE")
    if "NO_CROSS_BEHAVIOR_SCORE_INHERITANCE" not in rule:
        errors.append("CROSS_BEHAVIOR_INHERITANCE")
    if ta.get("no_exact_opus_case_level_comparator_required_for_prewave_admission") is not True:
        errors.append("UNNECESSARY_OPUS_DEPENDENCY_NOT_DELETED")

    scope = binding.get("scope_accounting") or {}
    if scope.get("no_scope_inheritance") is not True:
        errors.append("NO_SCOPE_INHERITANCE_FALSE")
    if set(scope.get("adjacent_contracts_not_inherited") or []) != {
        "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
        "BROWSER_VISUAL_STATE_TO_GROUNDED_ACTION_001",
        "TASK_TO_DELEGATION_GRAPH_001",
        "TOOL_ROUTE_DISCOVERY_AND_SELECTION_001",
    }:
        errors.append("ADJACENT_CONTRACT_ACCOUNTING")

    contamination = binding.get("contamination") or {}
    for key in (
        "post_freeze_case_specific_tuning",
        "case_replacement",
        "result_to_runtime_feedback_during_wave",
        "evaluator_or_threshold_edit_after_first_terminal_result",
        "terminal_case_selection_before_route_freeze",
    ):
        if contamination.get(key) is not False:
            errors.append("CONTAMINATION:" + key)

    if binding.get("prewave_admissible") is not False:
        errors.append("PREMATURE_ADMISSION")
    if binding.get("independent_verification") is not None:
        errors.append("PREMATURE_VERIFICATION_BINDING")
    if binding.get("execution_authority") is not False:
        errors.append("EXECUTION_AUTHORITY")
    if binding.get("terminal_results_observed") != 0 or binding.get("fresh_terminal_evidence_consumed") != 0:
        errors.append("TERMINAL_RESULT_OR_EVIDENCE")
    if binding.get("capability_credit_delta") != 0 or binding.get("family_credit_delta") != 0:
        errors.append("CREDIT_DELTA")

    for rel in REQUIRED_DEPS:
        if not (root / rel).is_file():
            errors.append("DEPENDENCY_MISSING:" + rel)

    return {
        "schema": "PROJECT_BRAIN_P1_T0_T2_MULTIPLEX_PREFLIGHT_VERDICT_V1",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "execution_authority": False,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
