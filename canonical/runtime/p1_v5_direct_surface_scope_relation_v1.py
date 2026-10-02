"""Fail-closed P1 V5 direct-surface scope relation compiler.

This proves only the relation between V5 and the frozen P1 causal-localization
contract role delegated by the three declared terminal surfaces. It never claims
that V5 covers an entire benchmark/surface, and it grants no terminal,
capability, family, execution, or promotion credit.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_P1_V5_DIRECT_SURFACE_SCOPE_RELATION_V1"

BINDING = "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
PORTFOLIOS = "canonical/governance/TERMINAL_PORTFOLIO_BINDING_MANIFESTS_V1.json"
FOUR_CONTRACTS = "canonical/governance/FOUR_UNCOVERED_BEHAVIORAL_PROOF_CONTRACTS_V1.json"
ABSOLUTE_SUITES = "canonical/governance/CONTRACT_NATIVE_ABSOLUTE_PROOF_SUITES_V1.json"
NATIVE_ROUTES = "canonical/governance/CONTRACT_NATIVE_PRIVATE_SURFACE_PROOF_ROUTES_V1.json"
V5 = "canonical/governance/P1_TYPED_INTERVENTION_ENVELOPE_V5.json"
V5_VERIFY = "canonical/verification/P1_TYPED_INTERVENTION_ENVELOPE_V5_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
ROUTE = "P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF"
EXPECTED_SURFACES = {
    "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF": ("T0", "FRONTIERCODE_V1_1", "P1-V5-SCOPE-FRONTIERCODE-V1"),
    "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF": ("T0", "CURSORBENCH_4_0", "P1-V5-SCOPE-CURSORBENCH-V1"),
    "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF": ("T2", "RECOVERY_SCOPE_COMPOSITION", "P1-V5-SCOPE-RECOVERY-COMPOSITION-V1"),
}
EXPECTED_OUTPUTS = {
    "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_STEP",
    "FAILURE_CLASS_WITH_SUPPORTING_RECEIPTS",
    "FALSIFIABLE_REPAIR_TARGET",
}
EXPECTED_ORACLES = {
    "GROUND_TRUTH_INJECTED_CAUSE_OR_INDEPENDENT_INTERVENTION_ESTABLISHES_CAUSAL_STEP",
    "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME",
    "SYMPTOM_ONLY_REPAIR_DOES_NOT_RESCUE_WHERE_COUNTEREXAMPLE_DECLARED",
    "NONIDENTIFIABLE_OBSERVATIONAL_CASE_RETURNS_AMBIGUITY_OR_INFORMATION_REQUEST",
}
EXPECTED_MUTATIONS = {
    "SELECT_DOWNSTREAM_SYMPTOM",
    "SELECT_LATER_CORRELATED_STEP",
    "IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT",
    "UNFALSIFIABLE_DIAGNOSIS",
    "REPAIR_TARGET_WITH_NO_RESCUE",
    "FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE",
}
EXPECTED_KINDS = {
    "AUTHORITY", "SCOPE", "SCHEMA", "PROVENANCE", "INVARIANT",
    "STATE_TRANSITION", "TOOL_CONTRACT", "DEPENDENCY",
}
EXPECTED_PATTERNS = {"SINGLE", "DELAYED", "INTERACTION", "AMBIGUOUS"}
EXPECTED_NORMALIZATION_BOUNDARY = "TASK_SPECIFIC_RAW_LOGS_SCREENSHOTS_TOOL_OUTPUTS_AND_ARTIFACT_EVENTS_MAY_BE_NORMALIZED_TO_THE_CANONICAL_TRAJECTORY_IR_BY_OWNED_DETERMINISTIC_OR_SEPARATELY_PROVEN_UPSTREAM_COMPONENTS"
EXPECTED_OWNED_BEHAVIOR = "FAILED_EXECUTION_TRAJECTORY_TO_EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_CLASS_AND_FALSIFIABLE_REPAIR_TARGET_WITH_INTERVENTION_RESCUE_EVIDENCE"
EXPECTED_REQUIRED_CHECKS = {
    "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE",
    "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
    "NOMINATED_REPAIR_IS_FALSIFIABLE",
    "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE",
    "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT",
    "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
    "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT",
    "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
}
EXPECTED_REQUIRED_MUTATIONS = {
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
EXPECTED_V5_BLOBS = {
    "canonical/runtime/trajectory_failure_typed_ir_candidate_v5.py": "2a8613ddac7402c7e6d2f349f9d3c32d3fb95e1d",
    "canonical/runtime/trajectory_failure_typed_ir_proof_v5.py": "3fc600a8176dac250219e3d98b92cf93d8fceef5",
    "canonical/tests/test_trajectory_failure_typed_ir_v5.py": "abc87ada119e42b720af5fb0f472816df975bc25",
    "canonical/governance/P1_TYPED_INTERVENTION_ENVELOPE_V5.json": "26cd9f4c626d4754200c64c3f298383580d67c14",
}
CHECK_EVIDENCE = {
    "EARLIEST_OR_CRITICAL_CAUSAL_FAILURE_LOCALIZATION_MATCHES_HIDDEN_INTERVENTION_ORACLE": {"V5_192_TYPED_CROSS_PRODUCT", "ALL_CAUSAL_PATTERNS"},
    "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS": {"ALL_MECHANISM_CLASSES", "VISIBLE_RECEIPT_SUPPORT_REQUIRED"},
    "NOMINATED_REPAIR_IS_FALSIFIABLE": {"UNFALSIFIABLE_OUTPUT_KILLED"},
    "NOMINATED_REPAIR_RESCUES_TERMINAL_OUTCOME_WHEN_CAUSE_IS_IDENTIFIABLE": {"HETEROGENEOUS_RESCUE_VERIFIED"},
    "SYMPTOM_ONLY_OR_COMPETING_REPAIR_DOES_NOT_RECEIVE_CAUSAL_CREDIT": {"SYMPTOM_NONRESCUE_VERIFIED"},
    "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE": {"AMBIGUITY_ABSTENTION_VERIFIED"},
    "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT": {"ALL_MECHANISM_CLASSES", "EXPLICIT_SCOPE_FIRST_CLASS"},
    "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM": {"ALL_CAUSAL_PATTERNS", "PARTIAL_INTERACTION_NONRESCUE_VERIFIED"},
}
MUTATION_EVIDENCE = {
    "SELECT_DOWNSTREAM_SYMPTOM": {"SYMPTOM_NONRESCUE_VERIFIED"},
    "SELECT_LATER_CORRELATED_STEP": {"ALL_CAUSAL_PATTERNS", "V5_192_TYPED_CROSS_PRODUCT"},
    "IGNORE_VIOLATED_AUTHORITY_OR_INVARIANT": {"ALL_MECHANISM_CLASSES"},
    "UNFALSIFIABLE_DIAGNOSIS": {"UNFALSIFIABLE_OUTPUT_KILLED"},
    "REPAIR_TARGET_WITH_NO_RESCUE": {"HETEROGENEOUS_RESCUE_VERIFIED"},
    "FORCE_UNIQUE_CAUSE_ON_NONIDENTIFIABLE_TRACE": {"AMBIGUITY_ABSTENTION_VERIFIED"},
    "DROP_CAUSAL_PREDECESSOR_IN_MULTI_STEP_CHAIN": {"ALL_CAUSAL_PATTERNS", "HETEROGENEOUS_RESCUE_VERIFIED"},
    "SWAP_TOOL_OR_AUTHORITY_FAILURE_CLASS": {"ALL_MECHANISM_CLASSES"},
    "DROP_PROVENANCE_OR_DEPENDENCY_EDGE": {"DROP_PROVENANCE_KILLED", "VISIBLE_RECEIPT_SUPPORT_REQUIRED"},
}
REQUIRED_V5_RULES = {
    "SCOPE_IS_FIRST_CLASS_NOT_ALIAS_OF_AUTHORITY",
    "FAILED_CAUSAL_CHECK_REQUIRES_NONEMPTY_VISIBLE_SUPPORTING_RECEIPTS",
    "HIDDEN_CAUSAL_AND_INTERVENTION_STATE_NEVER_ENTERS_CANDIDATE_PAYLOAD",
    "NOMINATED_ROOT_REPAIR_MUST_RESCUE_HIDDEN_TERMINAL_MODEL",
    "DOWNSTREAM_SYMPTOM_REPAIR_MUST_NOT_RESCUE",
    "CONJUNCTIVE_INTERACTION_REQUIRES_ALL_ROOT_REPAIRS",
    "AMBIGUOUS_ALTERNATIVES_MUST_NOT_FORCE_UNIQUE_CAUSE",
    "EXTRA_UNBOUND_DIAGNOSIS_FIELDS_ARE_REJECTED",
}


def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value


def _one(rows: Any, predicate, error: str) -> Mapping[str, Any] | None:
    if not isinstance(rows, list):
        return None
    found = [x for x in rows if isinstance(x, Mapping) and predicate(x)]
    if len(found) != 1:
        return None
    return found[0]


def _surface(portfolios: Mapping[str, Any], portfolio: str, surface: str) -> Mapping[str, Any] | None:
    ps = portfolios.get("portfolios")
    if not isinstance(ps, Mapping):
        return None
    p = ps.get(portfolio)
    if not isinstance(p, Mapping):
        return None
    return _one(p.get("surfaces"), lambda x: x.get("id") == surface, "surface")


def evaluate(
    *,
    binding: Mapping[str, Any] | None = None,
    portfolios: Mapping[str, Any] | None = None,
    four_contracts: Mapping[str, Any] | None = None,
    absolute_suites: Mapping[str, Any] | None = None,
    native_routes: Mapping[str, Any] | None = None,
    v5: Mapping[str, Any] | None = None,
    v5_verify: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    b = dict(binding or _load(BINDING))
    p = dict(portfolios or _load(PORTFOLIOS))
    fc = dict(four_contracts or _load(FOUR_CONTRACTS))
    a = dict(absolute_suites or _load(ABSOLUTE_SUITES))
    nr = dict(native_routes or _load(NATIVE_ROUTES))
    v = dict(v5 or _load(V5))
    vv = dict(v5_verify or _load(V5_VERIFY))
    errors: list[str] = []

    if b.get("behavior_id") != BEHAVIOR:
        errors.append("P1_BINDING_BEHAVIOR_DRIFT")
    if set(b.get("direct_surface_bindings") or []) != set(EXPECTED_SURFACES):
        errors.append("P1_DECLARED_DIRECT_SURFACE_SET_DRIFT")
    decomposition = b.get("decomposition") or {}
    if decomposition.get("owned_behavior") != EXPECTED_OWNED_BEHAVIOR:
        errors.append("P1_OWNED_BEHAVIOR_BOUNDARY_DRIFT")
    if decomposition.get("normalization_boundary") != EXPECTED_NORMALIZATION_BOUNDARY:
        errors.append("P1_NORMALIZATION_BOUNDARY_DRIFT")
    terminal = b.get("terminal_acceptance") or {}
    if terminal.get("standalone_synthetic_whole_domain_score_forbidden") is not True:
        errors.append("SYNTHETIC_TERMINAL_SCORE_FIREWALL_MISSING")
    if terminal.get("parent_or_direct_surface_credit_only_for_declared_scope") is not True:
        errors.append("DECLARED_SCOPE_CREDIT_FIREWALL_MISSING")
    if b.get("terminal_results_observed") != 0:
        errors.append("P1_BINDING_ALREADY_OBSERVED_TERMINAL_RESULT")
    evaluator = b.get("evaluator") or {}
    if set(evaluator.get("required_checks") or []) != EXPECTED_REQUIRED_CHECKS:
        errors.append("P1_FULL_REQUIRED_CHECK_SET_DRIFT")
    if set(evaluator.get("required_mutations") or []) != EXPECTED_REQUIRED_MUTATIONS:
        errors.append("P1_FULL_REQUIRED_MUTATION_SET_DRIFT")

    obligation = _one(
        fc.get("obligations"),
        lambda x: x.get("route_id") == ROUTE and x.get("behavior_id") == BEHAVIOR,
        "obligation",
    )
    if obligation is None:
        errors.append("FROZEN_P1_DIRECT_PROOF_OBLIGATION_MISSING")
    else:
        if set(obligation.get("portfolios") or []) != {"T0", "T2"}:
            errors.append("P1_CONTRACT_PORTFOLIO_SCOPE_DRIFT")

    suite = _one(
        a.get("suites"),
        lambda x: x.get("id") == "P1_TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_DIRECT"
        and x.get("behavior_id") == BEHAVIOR,
        "suite",
    )
    if suite is None:
        errors.append("P1_ABSOLUTE_SUITE_MISSING")
    else:
        if set(suite.get("required_outputs") or []) != EXPECTED_OUTPUTS:
            errors.append("P1_REQUIRED_OUTPUT_SET_DRIFT")
        if set(suite.get("oracle") or []) != EXPECTED_ORACLES:
            errors.append("P1_ORACLE_SET_DRIFT")
        if set(suite.get("mutations") or []) != EXPECTED_MUTATIONS:
            errors.append("P1_MUTATION_SET_DRIFT")

    route = _one(
        nr.get("routes"),
        lambda x: x.get("id") == "DIRECT_TRAJECTORY_CAUSAL_CONTRACT_SUITE",
        "native route",
    )
    if route is None:
        errors.append("P1_CONTRACT_NATIVE_ROUTE_MISSING")
    else:
        if set(route.get("covers") or []) != {BEHAVIOR}:
            errors.append("P1_CONTRACT_NATIVE_COVERAGE_DRIFT")
        for key in ("zero_cost", "executable", "independent_oracle", "scope_mapping_frozen", "contamination_boundary_frozen"):
            if route.get(key) is not True:
                errors.append("P1_CONTRACT_NATIVE_ROUTE_" + key.upper() + "_FALSE")
        if route.get("blocked") is not False:
            errors.append("P1_CONTRACT_NATIVE_ROUTE_BLOCKED")

    surface_relations: list[dict[str, Any]] = []
    for binding_id, (portfolio_id, surface_id, claim_id) in EXPECTED_SURFACES.items():
        s = _surface(p, portfolio_id, surface_id)
        if s is None:
            errors.append("DECLARED_SURFACE_MISSING:" + binding_id)
            continue
        if ROUTE not in set(s.get("proof_routes") or []):
            errors.append("P1_ROUTE_NOT_BOUND_TO_SURFACE:" + binding_id)
            continue
        if s.get("direct_proof_contracts") != FOUR_CONTRACTS:
            errors.append("P1_SURFACE_CONTRACT_POINTER_DRIFT:" + binding_id)
            continue
        evaluator = s.get("evaluator")
        if evaluator != "canonical/governance/CONTRACT_NATIVE_PRIVATE_SURFACE_PROOF_ROUTES_V1.json":
            errors.append("P1_SURFACE_EVALUATOR_DRIFT:" + binding_id)
            continue
        surface_relations.append({
            "binding": binding_id,
            "claim_id": claim_id,
            "relation": "SUPERSET",
            "relation_scope": "UNRESOLVED_SEMANTICS_WITHIN_EXACT_FROZEN_P1_CONTRACT_ROLE_ONLY",
            "behavior_id": BEHAVIOR,
            "route_id": ROUTE,
            "full_surface_superset_claim": False,
        })

    if not str(vv.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"):
        errors.append("V5_INDEPENDENT_VERIFICATION_MISSING")
    if vv.get("behavior_id") != BEHAVIOR:
        errors.append("V5_VERIFICATION_BEHAVIOR_DRIFT")
    if dict(vv.get("exact_brain_blobs") or {}) != EXPECTED_V5_BLOBS:
        errors.append("V5_VERIFIED_BLOB_SET_DRIFT")
    verified = vv.get("verified") or {}
    verified_ids: set[str] = set()
    if int(verified.get("typed_case_count") or -1) == 192:
        verified_ids.add("V5_192_TYPED_CROSS_PRODUCT")
    if set(verified.get("mechanism_classes") or []) == EXPECTED_KINDS:
        verified_ids.add("ALL_MECHANISM_CLASSES")
    if set(verified.get("causal_patterns") or []) == EXPECTED_PATTERNS:
        verified_ids.add("ALL_CAUSAL_PATTERNS")
    if int(verified.get("explicit_scope_case_count") or -1) == 24 and "SCOPE" in set(verified.get("mechanism_classes") or []):
        verified_ids.add("EXPLICIT_SCOPE_FIRST_CLASS")
    if int(verified.get("identifiable_or_interaction_rescue_count") or -1) == 144:
        verified_ids.add("HETEROGENEOUS_RESCUE_VERIFIED")
    if verified.get("symptom_only_repair_does_not_rescue") is True:
        verified_ids.add("SYMPTOM_NONRESCUE_VERIFIED")
    if verified.get("partial_interaction_repair_does_not_rescue") is True:
        verified_ids.add("PARTIAL_INTERACTION_NONRESCUE_VERIFIED")
    if verified.get("ambiguous_cases_do_not_force_unique_cause") is True:
        verified_ids.add("AMBIGUITY_ABSTENTION_VERIFIED")
    if verified.get("drop_provenance_mutation_killed") is True:
        verified_ids.add("DROP_PROVENANCE_KILLED")
    if verified.get("unfalsifiable_output_injection_killed") is True:
        verified_ids.add("UNFALSIFIABLE_OUTPUT_KILLED")
    if verified.get("hidden_intervention_state_candidate_visible") is False:
        verified_ids.add("HIDDEN_GOLD_ISOLATED")
    if "FAILED_CAUSAL_CHECK_REQUIRES_NONEMPTY_VISIBLE_SUPPORTING_RECEIPTS" in set(v.get("hard_rules") or []):
        verified_ids.add("VISIBLE_RECEIPT_SUPPORT_REQUIRED")
    if set(CHECK_EVIDENCE) != EXPECTED_REQUIRED_CHECKS:
        errors.append("P1_CHECK_EVIDENCE_MAP_INCOMPLETE")
    if set(MUTATION_EVIDENCE) != EXPECTED_REQUIRED_MUTATIONS:
        errors.append("P1_MUTATION_EVIDENCE_MAP_INCOMPLETE")
    for req, evidence_ids in CHECK_EVIDENCE.items():
        missing = set(evidence_ids) - verified_ids
        if missing:
            errors.append("P1_REQUIRED_CHECK_UNVERIFIED:" + req + ":" + ",".join(sorted(missing)))
    for req, evidence_ids in MUTATION_EVIDENCE.items():
        missing = set(evidence_ids) - verified_ids
        if missing:
            errors.append("P1_REQUIRED_MUTATION_UNVERIFIED:" + req + ":" + ",".join(sorted(missing)))

    if v.get("behavior_id") != BEHAVIOR:
        errors.append("V5_BEHAVIOR_DRIFT")
    scope = v.get("scope") or {}
    if set(scope.get("domains") or []) != {"BROWSER", "FILESYSTEM", "TOOL_API", "ARTIFACT", "RESEARCH", "CODE"}:
        errors.append("V5_DOMAIN_SET_DRIFT")
    if set(scope.get("mechanism_classes") or []) != EXPECTED_KINDS:
        errors.append("V5_MECHANISM_SET_DRIFT")
    if set(scope.get("causal_patterns") or []) != EXPECTED_PATTERNS:
        errors.append("V5_PATTERN_SET_DRIFT")
    if int(scope.get("cross_product_case_count") or -1) != 192:
        errors.append("V5_CASE_COUNT_DRIFT")
    if not REQUIRED_V5_RULES.issubset(set(v.get("hard_rules") or [])):
        errors.append("V5_REQUIRED_RESIDUAL_RULE_MISSING")
    if set(v.get("residuals_targeted") or []) != {
        "P1_EXPLICIT_SCOPE_FAILURE_CLASS",
        "P1_HETEROGENEOUS_INTERVENTION_RESCUE",
    }:
        errors.append("V5_RESIDUAL_TARGET_SET_DRIFT")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "all_declared_p1_surface_relations_exact_or_superset": False,
            "v5_is_superset_carrier_for_frozen_p1_residual_role": False,
            "full_surface_superset_claim": False,
            "terminal_surface_proof_complete": False,
            "can_clear_p1_scope_quarantine": False,
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    residual_semantics = {
        "EXPLICIT_SCOPE_FAILURE_FIRST_CLASS",
        "HETEROGENEOUS_DELAYED_AND_INTERACTION_RESCUE",
        "SYMPTOM_ONLY_AND_INCOMPLETE_REPAIR_NONRESCUE",
        "HIDDEN_CAUSE_AND_RESCUE_GOLD_ISOLATION",
        "NONIDENTIFIABILITY_PRESERVATION",
        "VISIBLE_RECEIPT_SUPPORT_FOR_FAILURE_CLASS",
        "FALSIFIABLE_REPAIR_ONLY",
    }
    return {
        "schema": SCHEMA,
        "status": "PASS__V5_SUPERSET_OF_FROZEN_P1_RESIDUAL_ROLE_ON_ALL_THREE_DECLARED_SURFACES__NOT_TERMINAL_PROOF",
        "errors": [],
        "behavior_id": BEHAVIOR,
        "route_id": ROUTE,
        "surface_relations": surface_relations,
        "all_declared_p1_surface_relations_exact_or_superset": len(surface_relations) == 3,
        "v5_relation": "SUPERSET",
        "v5_is_superset_carrier_for_frozen_p1_residual_role": True,
        "residual_semantics_carried": sorted(residual_semantics),
        "full_frozen_p1_required_checks_mapped": sorted(EXPECTED_REQUIRED_CHECKS),
        "full_frozen_p1_required_mutations_mapped": sorted(EXPECTED_REQUIRED_MUTATIONS),
        "verified_evidence_ids": sorted(verified_ids),
        "anti_overclaim": {
            "full_surface_superset_claim": False,
            "private_benchmark_score_reproduction_claim": False,
            "adjacent_contract_inheritance": False,
            "terminal_surface_proof_complete": False,
            "reason": "THE_THREE_SURFACES_DELEGATE_A_FROZEN_P1_ROLE; V5_SUPERSETS_THE_OPEN_P1_RESIDUAL_SEMANTICS_ONLY. OTHER_SURFACE_CONTRACTS_AND_TERMINAL_POPULATION_ACCEPTANCE_REMAIN SEPARATE.",
        },
        "full_surface_superset_claim": False,
        "terminal_surface_proof_complete": False,
        "can_clear_p1_scope_quarantine": False,
        "next": "INDEPENDENTLY_VERIFY_EXACT_V5_AND_THIS_SCOPE_RELATION__THEN_FREEZE_AND_EXECUTE_ONLY_THE_MINIMUM_P1_TERMINAL_DIRECT_PROOF_CUT_REQUIRED_BY_THE_EXISTING_BINDING",
        "terminal_results_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
