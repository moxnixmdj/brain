"""Fail-closed P1 whole-scope restoration reducer.

This reducer grants no Opus-5.5 acceptance, family ownership, or capability credit.
It only answers whether the independently verified P1 quarantine cause has been
fully discharged by combining the pre-existing V7 proof frontier with the new
independently adjudicated failure-semantics transport receipt.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]

BINDING = ROOT / "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
V7_CURRENT = ROOT / "canonical/verification/P1_V7_CURRENT_MAIN_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
V7_PROVENANCE = ROOT / "canonical/verification/P1_V7_PROVENANCE_AND_MINIMUM_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
V6 = ROOT / "canonical/verification/P1_TYPED_CAUSAL_INTERVENTION_V6_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
SCOPE_AUDIT = ROOT / "canonical/verification/P1_TERMINAL_EXECUTION_SCOPE_AUDIT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
POSTWAVE = ROOT / "canonical/verification/TERMINAL_V3_POSTWAVE_CONTRACT_AND_FAMILY_REDUCTION_20261002_V1.json"
QUARANTINE_PROPAGATION = ROOT / "canonical/verification/TERMINAL_SCOPE_QUARANTINE_PROPAGATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
REGISTRY = ROOT / "canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V1.json"
TRANSPORT = ROOT / "canonical/verification/P1_PUBLIC_RECOVERY_RESULT_INDEPENDENT_ADJUDICATION_20261003_V1.json"

BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
EXPECTED_TRANSPORT_REQUIREMENTS = {
    "P1_FAILURE_SEMANTICS_TRANSPORT_CURSORBENCH",
    "P1_FAILURE_SEMANTICS_TRANSPORT_FRONTIERCODE",
    "P1_FAILURE_SEMANTICS_TRANSPORT_RECOVERY_SCOPE_COMPOSITION",
}
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
EXPECTED_MUTATIONS = {
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
EXPECTED_QUARANTINED_FAMILIES = {
    "ADVANCED_AGENTIC_CODING",
    "AGENTIC_SCIENTIFIC_RESEARCH",
    "BUSINESS_WORKFLOW_AUTOMATION",
    "COMPLEX_MULTI_TOOL_AGENCY",
    "COMPUTER_AND_BROWSER_USE",
    "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
    "MULTI_CAPABILITY_COMPOSITION",
    "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(str(path) + ":NOT_OBJECT")
    return value


def _error(errors: list[str], cond: bool, code: str) -> None:
    if not cond:
        errors.append(code)


def evaluate(
    *,
    binding: Mapping[str, Any] | None = None,
    v7_current: Mapping[str, Any] | None = None,
    v7_provenance: Mapping[str, Any] | None = None,
    v6: Mapping[str, Any] | None = None,
    scope_audit: Mapping[str, Any] | None = None,
    postwave: Mapping[str, Any] | None = None,
    quarantine: Mapping[str, Any] | None = None,
    registry: Mapping[str, Any] | None = None,
    transport: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    binding = copy.deepcopy(dict(binding or load(BINDING)))
    v7_current = copy.deepcopy(dict(v7_current or load(V7_CURRENT)))
    v7_provenance = copy.deepcopy(dict(v7_provenance or load(V7_PROVENANCE)))
    v6 = copy.deepcopy(dict(v6 or load(V6)))
    scope_audit = copy.deepcopy(dict(scope_audit or load(SCOPE_AUDIT)))
    postwave = copy.deepcopy(dict(postwave or load(POSTWAVE)))
    quarantine = copy.deepcopy(dict(quarantine or load(QUARANTINE_PROPAGATION)))
    registry = copy.deepcopy(dict(registry or load(REGISTRY)))
    transport = copy.deepcopy(dict(transport or load(TRANSPORT)))

    errors: list[str] = []

    _error(errors, binding.get("behavior_id") == BEHAVIOR, "BINDING_BEHAVIOR")
    evaluator = binding.get("evaluator") or {}
    _error(errors, set(evaluator.get("required_checks") or []) == EXPECTED_REQUIRED_CHECKS, "FROZEN_REQUIRED_CHECK_SET")
    _error(errors, set(evaluator.get("required_mutations") or []) == EXPECTED_MUTATIONS, "FROZEN_MUTATION_SET")
    _error(
        errors,
        set(binding.get("direct_surface_bindings") or []) == {
            "T0/FRONTIERCODE_V1_1::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
            "T0/CURSORBENCH_4_0::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
            "T2/RECOVERY_SCOPE_COMPOSITION::P1_CAUSAL_FAILURE_LOCALIZATION_DIRECT_PROOF",
        },
        "FROZEN_DIRECT_SURFACE_SET",
    )
    term = binding.get("terminal_acceptance") or {}
    _error(errors, term.get("standalone_synthetic_whole_domain_score_forbidden") is True, "SYNTHETIC_WHOLE_DOMAIN_GUARD")
    _error(errors, term.get("parent_or_direct_surface_credit_only_for_declared_scope") is True, "DECLARED_SCOPE_GUARD")
    _error(errors, term.get("any_load_bearing_p1_failure_blocks_behavior_proof") is True, "LOAD_BEARING_FAILURE_GUARD")

    _error(
        errors,
        str(v6.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),
        "V6_NOT_INDEPENDENT_PASS",
    )
    vv6 = v6.get("verified") or {}
    for key in (
        "scope_first_class",
        "provenance_erasure_killed",
        "unbound_output_killed",
        "partial_interaction_repair_killed",
        "symptom_only_repair_killed",
        "fake_repair_string_killed",
        "hidden_oracle_isolated",
        "rescue_depends_on_candidate_visible_trajectory_semantics",
    ):
        _error(errors, vv6.get(key) is True, "V6_PROPERTY:" + key)
    _error(errors, vv6.get("cross_product_cases") == 192, "V6_CASE_COUNT")
    _error(errors, vv6.get("forward_causal_rescues") == 144, "V6_RESCUE_COUNT")
    _error(errors, vv6.get("ambiguous_abstentions") == 48, "V6_ABSTENTION_COUNT")

    _error(
        errors,
        str(v7_current.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),
        "V7_NOT_INDEPENDENT_PASS",
    )
    v7props = set(v7_current.get("verified_properties") or [])
    for required in (
        "INHERITED_V6_192_CASE_SUITE_PRESERVED",
        "DERIVED_ONLY_FAILURE_IS_NOT_PROMOTED_TO_CAUSAL_ROOT",
        "SERIAL_DIRECT_COFAULT_RETAINS_BOTH_DIRECT_REPAIRS",
        "PARTIAL_SERIAL_REPAIR_DOES_NOT_RESCUE",
        "FAILURE_SEMANTICS_IS_LOAD_BEARING",
        "INVALID_FAILURE_SEMANTICS_FAILS_CLOSED",
    ):
        _error(errors, required in v7props, "V7_PROPERTY:" + required)
    _error(
        errors,
        set(v7_current.get("remaining_open") or []) == {
            "V7_DIRECT_SURFACE_SCOPE_TRANSPORT_TO_ALL_FROZEN_P1_SURFACES",
            "P1_COMPOSITE_RESTORATION",
            "P1_QUARANTINE_REMOVAL",
        },
        "V7_REMAINING_OPEN_DRIFT",
    )

    _error(
        errors,
        str(v7_provenance.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),
        "V7_PROVENANCE_NOT_INDEPENDENT_PASS",
    )
    vp = v7_provenance.get("result") or {}
    _error(errors, vp.get("provenance_mutation_closed_under_current_v7") is True, "PROVENANCE_MUTATION_OPEN")
    _error(
        errors,
        vp.get("remaining_p1_information_residual") == "FAILURE_SEMANTICS_TRANSPORT_TO_THREE_FROZEN_DIRECT_SURFACES",
        "PRETRANSPORT_RESIDUAL_NOT_EXACT",
    )
    _error(errors, vp.get("exact_minimum_reality") is True, "MINIMUM_REALITY_NOT_EXACT")
    _error(errors, vp.get("selected_observation") == "P1_SHARED_SOURCE_BOUND_FAILURE_SEMANTICS_BATCH", "SELECTED_OBSERVATION")
    _error(errors, vp.get("minimum_new_reality_units") == 1, "MINIMUM_REALITY_NOT_ONE")

    _error(
        errors,
        str(scope_audit.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),
        "SCOPE_AUDIT_NOT_PASS",
    )
    _error(errors, scope_audit.get("scope_mismatch_proved") is True, "ORIGINAL_SCOPE_MISMATCH_NOT_PROVED")
    _error(errors, scope_audit.get("preserved_narrow_execution_evidence") is True, "NARROW_EVIDENCE_NOT_PRESERVED")
    _error(errors, scope_audit.get("broad_p1_transport_admissible") is False, "OLD_BROAD_TRANSPORT_NOT_QUARANTINED")

    _error(
        errors,
        str(transport.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),
        "NEW_TRANSPORT_NOT_INDEPENDENT_PASS",
    )
    tr = transport.get("result") or {}
    acct = transport.get("accounting") or {}
    _error(errors, tr.get("p1_failure_semantics_transport_pass") is True, "NEW_TRANSPORT_FAIL")
    _error(
        errors,
        set(tr.get("transport_requirements_discharged") or []) == EXPECTED_TRANSPORT_REQUIREMENTS,
        "TRANSPORT_REQUIREMENT_SET",
    )
    _error(errors, tr.get("cases") == 192 and tr.get("passes") == 192 and tr.get("failures") == 0, "TRANSPORT_192_OF_192")
    _error(errors, tr.get("surface_count") == 3 and tr.get("passes_per_surface") == 64, "TRANSPORT_SURFACE_COUNTS")
    _error(errors, tr.get("both_failure_semantics_classes_present_every_case") is True, "TRANSPORT_SEMANTICS_CLASSES")
    _error(errors, tr.get("v7_intervention_scorer_all_pass") is True, "TRANSPORT_V7_SCORER")
    _error(errors, tr.get("source_native_rescue_scorer_all_pass") is True, "TRANSPORT_SOURCE_SCORER")
    _error(errors, acct.get("fresh_reality_units_consumed") == 1, "TRANSPORT_REALITY_COUNT")
    _error(errors, acct.get("terminal_v3_replayed") == 0, "TRANSPORT_TERMINAL_REPLAY")
    _error(errors, acct.get("incremental_spend_usd") == 0, "TRANSPORT_SPEND")

    contract = postwave.get("contract_verdict") or {}
    family = postwave.get("family_verdict") or {}
    _error(errors, contract.get("valid") is True and contract.get("contract_pass_count") == 12, "SOURCE_12_CONTRACTS")
    _error(errors, BEHAVIOR in set(contract.get("passed_contracts") or []), "SOURCE_P1_PASS_ABSENT")
    _error(errors, family.get("valid") is True and family.get("family_pass_count") == 19, "SOURCE_19_FAMILIES")

    _error(
        errors,
        str(quarantine.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),
        "QUARANTINE_PROPAGATION_NOT_PASS",
    )
    quarantined = set(quarantine.get("quarantined_families") or [])
    _error(errors, quarantined == EXPECTED_QUARANTINED_FAMILIES, "QUARANTINED_FAMILY_SET")

    fmap = registry.get("family_to_residual_contracts") or {}
    mapped = {
        name for name, contracts in fmap.items()
        if isinstance(contracts, list) and BEHAVIOR in contracts
    }
    _error(errors, mapped == EXPECTED_QUARANTINED_FAMILIES, "REGISTRY_P1_FAMILY_MAPPING")

    unique = sorted(set(errors))
    restored = not unique
    return {
        "schema": "PROJECT_BRAIN_P1_SCOPE_RESTORATION_V8_VERDICT",
        "status": (
            "PASS__P1_WHOLE_FROZEN_SCOPE_RESTORED__12_OF_12_CONTRACTS__19_OF_19_PROVISIONAL_BEHAVIORAL_ROWS__ZERO_OPUS55_ACCEPTANCE_CREDIT"
            if restored else "FAIL_CLOSED"
        ),
        "pass": restored,
        "errors": unique,
        "behavior_id": BEHAVIOR,
        "proof_composition": {
            "prior_scope_mismatch_preserved": bool(scope_audit.get("scope_mismatch_proved")),
            "v6_forward_causal_envelope_pass": str(v6.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),
            "v7_current_hardening_pass": str(v7_current.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"),
            "v7_provenance_mutation_closed": bool(vp.get("provenance_mutation_closed_under_current_v7")),
            "pretransport_residual_exactly_failure_semantics_transport": (
                vp.get("remaining_p1_information_residual")
                == "FAILURE_SEMANTICS_TRANSPORT_TO_THREE_FROZEN_DIRECT_SURFACES"
            ),
            "new_failure_semantics_transport_pass": bool(tr.get("p1_failure_semantics_transport_pass")),
        },
        "transport_requirements_discharged": sorted(EXPECTED_TRANSPORT_REQUIREMENTS) if restored else [],
        "whole_p1_contract_restored": restored,
        "p1_scope_quarantine_clearable": restored,
        "contract_accounting": {
            "whole_scope_pass_count": 12 if restored else 11,
            "whole_scope_quarantined_count": 0 if restored else 1,
        },
        "behavioral_family_accounting": {
            "provisional_behavioral_pass_count": 19 if restored else 11,
            "quarantined_family_count": 0 if restored else 8,
            "reactivated_families": sorted(EXPECTED_QUARANTINED_FAMILIES) if restored else [],
        },
        "source_fresh_reality_units_consumed": 1,
        "restoration_new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "opus55_acceptance_credit_delta": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "rule": (
            "RESTORE_ONLY_THE_SCOPE_QUARANTINE_CAUSED_BY_THE_PROVED_P1_EXECUTION_SCOPE_MISMATCH__"
            "DO_NOT_INFER_OPUS55_ACCEPTANCE_OR_FULL_FAMILY_OWNERSHIP_FROM_BEHAVIORAL_RESTORATION"
        ),
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
