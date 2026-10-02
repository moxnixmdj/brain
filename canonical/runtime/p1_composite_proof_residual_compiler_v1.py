"""Compile the exact residual of the frozen P1 composite proof.

This compiler is deliberately asymmetric: it can prove that a proposed proof-role
partition is complete, but it does not upgrade semantic obligations merely because
a role document names them. Each obligation must have machine evidence in the
predeclared V4 preflight or the actually executed terminal scorer.

Zero capability/family credit is granted here.
"""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_P1_COMPOSITE_PROOF_RESIDUAL_COMPILER_V1"
BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"

CHECK_MECHANISM_RECEIPTS = "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS"
CHECK_NONIDENT = "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE"
CHECK_CLASS_FAMILY = "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT"
CHECK_MULTISTEP = "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM"
CHECK_LOCALIZE = "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE"
CHECK_FALSIFIABLE = "NOMINATED_REPAIR_IS_FALSIFIABLE"
CHECK_RESCUE = "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE"
CHECK_SYMPTOM = "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT"

V4_EXPLICIT_CLASSES = {
    "AUTHORITY", "SCHEMA", "PROVENANCE", "INVARIANT",
    "STATE_TRANSITION", "TOOL_CONTRACT", "DEPENDENCY",
}
V4_REQUIRED_PATTERNS = {"SINGLE", "DELAYED", "INTERACTION", "AMBIGUOUS"}
V4_REQUIRED_DOMAINS = {"BROWSER", "FILESYSTEM", "TOOL_API", "ARTIFACT", "RESEARCH", "CODE"}

EXPLICIT_V4_TEST_MARKERS = {
    "test_full_cross_product_suite",
    "test_visible_repair_target_injection_cannot_control_candidate",
    "test_wrong_repair_target_is_rejected_by_hidden_oracle",
    "test_hidden_oracle_changes_do_not_enter_public_payload",
    "test_downstream_symptom_is_not_selected",
    "test_nonidentifiable_case_abstains",
    "test_interaction_preserves_both_roots_and_repairs",
}

MUT_FORCE_UNIQUE = "FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE"
MUT_SELECT_DOWNSTREAM = "SELECT_DOWNSTREAM_SYMPTOM"
MUT_SELECT_LATER = "SELECT_LATER_CORRELATED_STEP"
MUT_REPAIR_NO_RESCUE = "REPAIR_TARGET_WITH_NO_RESCUE"
MUT_IGNORE_AUTH = "IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT"
MUT_DROP_PREDECESSOR = "DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN"
MUT_SWAP_CLASS = "SWAP_TOOL_OR_AUTHORITY_FAILURE_CLASS"
MUT_DROP_EDGE = "DROP_PROVENANCE_OR_DEPENDENCY_EDGE"
MUT_UNFALSIFIABLE = "UNFALSIFIABLE_DIAGNOSIS"


def _fail(errors: list[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": "FAIL_CLOSED_INPUT_DRIFT",
        "pass": False,
        "errors": sorted(set(errors)),
        "proved_checks": [],
        "partial_checks": [],
        "open_checks": [],
        "proved_mutations": [],
        "open_mutations": [],
        "whole_p1_contract_restored": False,
        "recovery_transport_authorized": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
    }


def _partition_exact(required: set[str], roles: Mapping[str, Any] | None) -> tuple[bool, set[str], set[str]]:
    if not isinstance(roles, Mapping) or not roles:
        return False, set(), set()
    seen: set[str] = set()
    overlap: set[str] = set()
    for values in roles.values():
        if not isinstance(values, list):
            return False, set(), set()
        vals = set(values)
        overlap |= seen & vals
        seen |= vals
    return seen == required and not overlap, seen, overlap


def evaluate(
    *,
    binding: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
    v4_verification: Mapping[str, Any],
    v4_candidate_source: str,
    v4_proof_source: str,
    v4_tests_source: str,
    terminal_scope_audit: Mapping[str, Any],
    terminal_suite_source: str,
) -> dict[str, Any]:
    e: list[str] = []

    if binding.get("behavior_id") != BEHAVIOR:
        e.append("BINDING_BEHAVIOR_DRIFT")
    evaluator = binding.get("evaluator")
    if not isinstance(evaluator, Mapping):
        e.append("BINDING_EVALUATOR_MISSING")
        required_checks: set[str] = set()
        required_mutations: set[str] = set()
    else:
        required_checks = set(evaluator.get("required_checks") or [])
        required_mutations = set(evaluator.get("required_mutations") or [])
        if evaluator.get("typed_cross_domain_scope_role") != (
            "CROSS_DOMAIN_MECHANISM_CAUSAL_PATTERN_INFORMATION_SAFE_PREFLIGHT__"
            "TERMINAL_RESCUE_JUDGMENT_REMAINS_INSIDE_FROZEN_T0_T2_OBSERVATIONS"
        ):
            e.append("V4_ROLE_NOT_PREDECLARED_IN_FROZEN_BINDING")
        if evaluator.get("typed_cross_domain_independent_preflight") != (
            "canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
        ):
            e.append("V4_VERIFICATION_NOT_BOUND_PREWAVE")

    if reconciliation.get("behavior_id") != BEHAVIOR:
        e.append("RECONCILIATION_BEHAVIOR_DRIFT")
    checks_exact, check_seen, check_overlap = _partition_exact(
        required_checks, reconciliation.get("proof_roles")
    )
    mutations_exact, mutation_seen, mutation_overlap = _partition_exact(
        required_mutations, reconciliation.get("mutation_roles")
    )
    if not checks_exact:
        e.append("PROPOSED_CHECK_PARTITION_NOT_EXACT")
    if not mutations_exact:
        e.append("PROPOSED_MUTATION_PARTITION_NOT_EXACT")

    status = str(v4_verification.get("status") or "")
    if not status.startswith("INDEPENDENT_PASS__EXACT_IMPORTED_PUBLIC_RUNNER_BYTES__168_TYPED_CROSS_DOMAIN_CASE_MATRIX"):
        e.append("V4_INDEPENDENT_VERIFICATION_DRIFT")
    verified = v4_verification.get("verified")
    if not isinstance(verified, Mapping):
        e.append("V4_VERIFIED_SECTION_MISSING")
        verified = {}
    if set(verified.get("normalized_domains") or []) != V4_REQUIRED_DOMAINS:
        e.append("V4_DOMAIN_COVERAGE_DRIFT")
    if set(verified.get("mechanism_classes") or []) != V4_EXPLICIT_CLASSES:
        e.append("V4_MECHANISM_CLASS_COVERAGE_DRIFT")
    if set(verified.get("causal_patterns") or []) != V4_REQUIRED_PATTERNS:
        e.append("V4_CAUSAL_PATTERN_COVERAGE_DRIFT")
    if int(verified.get("cross_product_case_count") or 0) != 168:
        e.append("V4_CASE_COUNT_DRIFT")
    if verified.get("hidden_oracle_not_candidate_visible") is not True:
        e.append("V4_HIDDEN_ORACLE_BOUNDARY_DRIFT")
    if verified.get("falsifiable_repair_targets_scored_against_hidden_oracle") is not True:
        e.append("V4_REPAIR_ORACLE_DRIFT")

    # Exact source-shape facts. These establish what the frozen V4 mechanism does,
    # not what we wish it did.
    for marker in EXPLICIT_V4_TEST_MARKERS:
        if ("def " + marker) not in v4_tests_source:
            e.append("V4_TEST_MARKER_MISSING:" + marker)
    for token in ('"SINGLE"', '"DELAYED"', '"INTERACTION"', '"AMBIGUOUS"'):
        if token not in v4_proof_source:
            e.append("V4_PATTERN_SOURCE_MISSING:" + token)
    if '"supporting_receipts": d["supporting_receipts"]' not in v4_candidate_source:
        e.append("V4_RECEIPT_OUTPUT_DATAFLOW_MISSING")
    if 'evidence = sorted({e for x in checks for e in x["evidence"]})' not in v4_candidate_source:
        e.append("V4_VISIBLE_RECEIPT_DERIVATION_MISSING")
    if 'candidate.get("supporting_receipts")' in v4_proof_source:
        e.append("V4_SCORER_SHAPE_UNEXPECTED__UPDATE_RESIDUAL_LOGIC")

    audit_status = str(terminal_scope_audit.get("status") or "")
    if audit_status != "FAIL_CLOSED__EXECUTED_P1_TERMINAL_INSTRUMENTATION_NARROWER_THAN_FROZEN_P1_BINDING":
        e.append("TERMINAL_SCOPE_AUDIT_DRIFT")
    if terminal_scope_audit.get("scope_mismatch_proved") is not True:
        e.append("TERMINAL_SCOPE_MISMATCH_NOT_PROVED")
    scored = set(((terminal_scope_audit.get("executed_route") or {}).get("candidate_output_keys_scored") or []))
    if scored != {"cause_step", "repair_id", "evidence_steps"}:
        e.append("TERMINAL_SCORER_KEYS_DRIFT")
    for token in (
        'candidate.get("cause_step")',
        'candidate.get("repair_id")',
        '"RESCUE_FAILED"',
        '"CAUSAL_EVIDENCE_MISSING"',
    ):
        if token not in terminal_suite_source:
            e.append("TERMINAL_SCORER_TOKEN_MISSING:" + token)

    if e:
        return _fail(e)

    proved_checks = {
        CHECK_NONIDENT,
        CHECK_MULTISTEP,
        CHECK_LOCALIZE,
        CHECK_FALSIFIABLE,
        CHECK_RESCUE,
        CHECK_SYMPTOM,
    }

    # Mechanism classification itself is exact across the V4 matrix and the Brain
    # candidate deterministically carries visible check evidence into receipts.
    # However, the independent V4 scorer does not score supporting_receipts. Keep
    # this partial until an independent static/dataflow proof is bound.
    partial_checks = {
        CHECK_MECHANISM_RECEIPTS: [
            "MECHANISM_CLASS_IS_HIDDEN_ORACLE_SCORED_ACROSS_168_CASES",
            "BRAIN_CANDIDATE_DERIVES_SUPPORTING_RECEIPTS_FROM_VISIBLE_FAILED_CHECK_EVIDENCE",
            "INDEPENDENT_V4_SCORER_DOES_NOT_VALIDATE_SUPPORTING_RECEIPTS_FIELD",
        ],
        CHECK_CLASS_FAMILY: [
            "AUTHORITY_PROVENANCE_DEPENDENCY_ARE_EXPLICIT_V4_MECHANISM_CLASSES",
            "SCOPE_HAS_NO_EXPLICIT_FROZEN_CLASS_OR_MACHINE_BINDING_TO_AUTHORITY_OR_SCHEMA",
            "TOOL_STATE_HAS_NO_EXPLICIT_FROZEN_CLASS_OR_MACHINE_BINDING_TO_STATE_TRANSITION_OR_TOOL_CONTRACT",
        ],
    }
    open_checks = sorted(required_checks - proved_checks)

    # Only mutations directly exercised by existing tests/scorers are credited here.
    # Output-shape implications are not silently upgraded to mutation execution.
    proved_mutations = {
        MUT_FORCE_UNIQUE,
        MUT_SELECT_DOWNSTREAM,
        MUT_SELECT_LATER,
        MUT_REPAIR_NO_RESCUE,
    }
    open_mutations = sorted(required_mutations - proved_mutations)

    exact_residual = {
        "semantic": {
            CHECK_MECHANISM_RECEIPTS: {
                "gap": "INDEPENDENT_SCORER_DOES_NOT_SCORE_SUPPORTING_RECEIPTS",
                "minimum_zero_reality_discharge": "STATIC_OR_METAMORPHIC_PROOF_THAT_THE_FROZEN_CANDIDATE_OUTPUT_RECEIPTS_ARE_EXACTLY_VISIBLE_FAILED_CHECK_EVIDENCE_AND_CANNOT_BE_DROPPED_OR_FABRICATED",
            },
            CHECK_CLASS_FAMILY: {
                "gap": "SCOPE_AND_TOOL_STATE_SUBSEMANTICS_HAVE_NO_EXPLICIT_MACHINE_BINDING_IN_V4_ONTOLOGY",
                "minimum_zero_reality_discharge": "CONTENT_ADDRESSED_EXPLICIT_EQUIVALENCE_OR_SEPARATE_EXISTING_WITNESS_FOR_SCOPE_AND_TOOL_STATE__NO_NAME_BASED_MAPPING",
            },
        },
        "mutations": {
            m: {"gap": "NO_EXPLICIT_EXECUTED_FAIL_CLOSED_MUTATION_RECEIPT_IN_BOUND_V4_OR_TERMINAL_TESTS"}
            for m in open_mutations
        },
    }

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_COMPOSITE_RESIDUAL_COMPILED__WHOLE_P1_STILL_QUARANTINED",
        "pass": True,
        "errors": [],
        "required_check_count": len(required_checks),
        "required_mutation_count": len(required_mutations),
        "check_partition_exact": checks_exact,
        "mutation_partition_exact": mutations_exact,
        "proved_checks": sorted(proved_checks),
        "partial_checks": partial_checks,
        "open_checks": open_checks,
        "proved_mutations": sorted(proved_mutations),
        "open_mutations": open_mutations,
        "exact_residual": exact_residual,
        "whole_p1_contract_restored": False,
        "recovery_transport_authorized": False,
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
        "next": "DISCHARGE_ONLY_THE_EXACT_RESIDUAL_WITH_ZERO_REALITY_STATIC_OR_METAMORPHIC_PROOFS__KEEP_SCOPE_AND_TOOL_STATE_FAIL_CLOSED_UNLESS_EXPLICITLY_BOUND",
    }
