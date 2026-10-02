"""Fail-closed prewave verifier for P3 grounded-synthesis T1/T3 multiplex binding."""
from __future__ import annotations

import json
from pathlib import Path

BINDING = "canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json"
MANIFEST = "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json"
REQUIRED_ROUTE = "P3_EVIDENCE_AUDIENCE_SYNTHESIS_DIRECT_PROOF"
REQUIRED_SURFACES = {
    "T1": {"GDPVAL_AA_V2_1", "AA_BRIEFCASE_V1_1", "FINANCE_ACCOUNTING_INDEX", "FINANCE_AGENT_V2"},
    "T3": {"UNKNOWN_DOMAIN_SYNTHESIS"},
}
FORBIDDEN_VISIBLE = {
    "HIDDEN_VERIFIER",
    "HIDDEN_CLAIM_SUPPORT_GRAPH",
    "HIDDEN_DECISION_RELEVANCE_LABELS",
    "GOLD_CLAIM_SELECTION",
    "GOLD_OR_REFERENCE_SYNTHESIS",
    "MUTATION_LABELS_OR_EXPECTED_FAILURE_REASON",
    "POST_FREEZE_CASE_SELECTION_INFORMATION",
}
REQUIRED_CHECKS = {
    "ZERO_UNSUPPORTED_MATERIAL_CLAIMS",
    "ALL_REQUIRED_CLAIMS_OR_DECISION_REQUIREMENTS_COVERED",
    "PROVENANCE_PRESERVED_FOR_MATERIAL_CLAIMS",
    "MATERIAL_CONFLICT_AND_UNCERTAINTY_PRESERVED",
    "NO_DECISION_RELEVANT_EVIDENCE_DROPPED_UNDER_COMPRESSION",
    "AUDIENCE_AND_FORMAT_CONSTRAINTS_PASS",
    "IRRELEVANT_EVIDENCE_EXCLUDED_WITHOUT_DELETING_REQUIRED_SUPPORT",
}
REQUIRED_MUTATIONS = {
    "UNSUPPORTED_CLAIM",
    "DELETE_REQUIRED_SUPPORT",
    "COLLAPSE_CONFLICT_TO_SINGLE_ASSERTION",
    "DROP_MATERIAL_UNCERTAINTY",
    "ADD_IRRELEVANT_DETAIL_UNDER_BUDGET",
    "DELETE_DECISION_RELEVANT_EVIDENCE",
    "AUDIENCE_FORMAT_MISMATCH",
    "PROVENANCE_SWAP_OR_DROP",
}
REQUIRED_DEPS = (
    "canonical/runtime/p3_information_safe_candidate_v3.py",
    "canonical/runtime/p3_information_safe_proof_suite_v3.py",
    "canonical/verification/P3_INFORMATION_SAFE_V3_PREFLIGHT_VERIFICATION_20261002_V1.json",
    "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json",
    "canonical/governance/TERMINAL_PORTFOLIO_PREWAVE_PROTOCOL_V1.json",
    "canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json",
    "canonical/governance/CONTRACT_NATIVE_ABSOLUTE_PROOF_SUITES_V1.json",
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
            "schema": "PROJECT_BRAIN_P3_T1_T3_MULTIPLEX_PREFLIGHT_VERDICT_V1",
            "pass": False,
            "errors": ["INPUT_UNREADABLE:" + type(exc).__name__],
            "execution_authority": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
        }

    if binding.get("behavior_id") != "EVIDENCE_TO_AUDIENCE_SYNTHESIS_001":
        errors.append("BEHAVIOR_ID")
    if binding.get("proof_mode") != "T1_T3_MULTIPLEXED_DIRECT_GROUNDED_SYNTHESIS_GATE":
        errors.append("PROOF_MODE")
    if set(binding.get("portfolio_bindings") or []) != {"T1", "T3"}:
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
                errors.append(f"{portfolio}_{surface}_P3_ROUTE_NOT_BOUND")

    visible = set(binding.get("candidate_visible_information") or [])
    forbidden = set(binding.get("candidate_must_not_receive") or [])
    if visible & FORBIDDEN_VISIBLE:
        errors.append("HIDDEN_ORACLE_LEAK")
    if not FORBIDDEN_VISIBLE <= forbidden:
        errors.append("FORBIDDEN_INFORMATION_SET_INCOMPLETE")

    ev = binding.get("evaluator") or {}
    if set(ev.get("required_checks") or []) != REQUIRED_CHECKS:
        errors.append("CHECK_SET")
    if set(ev.get("required_mutations") or []) != REQUIRED_MUTATIONS:
        errors.append("MUTATION_SET")
    if ev.get("role_of_bounded_suite") != "INFORMATION_BOUNDARY_AND_MUTATION_PREFLIGHT_ONLY__NOT_WHOLE_DOMAIN_TERMINAL_SCORE":
        errors.append("BOUNDED_SUITE_SCOPE_OVERCLAIM")
    if ev.get("mutation_acceptance") != "ALL_APPLICABLE_LOAD_BEARING_P3_MUTATIONS_MUST_BE_DETECTED_OR_CAUSE_PARENT_TERMINAL_ACCEPTANCE_FAILURE":
        errors.append("MUTATION_ACCEPTANCE")

    ta = binding.get("terminal_acceptance") or {}
    if ta.get("prewave_binding_is_terminal_result") is not False:
        errors.append("PREWAVE_RESULT_OVERCLAIM")
    if ta.get("standalone_synthetic_whole_domain_score_forbidden") is not True:
        errors.append("SYNTHETIC_SCOPE_OVERCLAIM")
    if ta.get("terminal_evidence_source") != "THE_FROZEN_T1_AND_T3_TERMINAL_OBSERVATIONS_WITH_DIRECT_P3_INSTRUMENTATION":
        errors.append("TERMINAL_EVIDENCE_SOURCE")
    if ta.get("public_or_parent_surface_credit_only_for_declared_scope") is not True:
        errors.append("SURFACE_SCOPE_INHERITANCE")
    if ta.get("any_load_bearing_p3_failure_blocks_behavior_proof") is not True:
        errors.append("P3_FAILURE_NOT_BLOCKING")
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
    adjacent = set(scope.get("adjacent_contracts_not_inherited") or [])
    if adjacent != {
        "SPECIFICATION_TO_INDEPENDENT_ACCEPTANCE_MODEL_001",
        "PROFESSIONAL_ARTIFACT_PLAN_AND_QUALITY_JUDGMENT_001",
        "ITERATIVE_RESEARCH_EVIDENCE_CONTROL_001",
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
        "schema": "PROJECT_BRAIN_P3_T1_T3_MULTIPLEX_PREFLIGHT_VERDICT_V1",
        "pass": not errors,
        "errors": sorted(set(errors)),
        "execution_authority": False,
        "terminal_results_observed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
    }
