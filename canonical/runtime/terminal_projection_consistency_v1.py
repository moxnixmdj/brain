"""Fail-closed consistency reducer for Project Brain terminal projections.

This checker grants no capability, family, execution, or promotion credit.
It verifies only that the current derived projections agree with the strongest
current independently verified scope/acceptance authorities.

Current truth after scope reconciliation:
- raw terminal execution receipt remains 3352/3352 PASS;
- P1 whole frozen scope is quarantined, leaving 11/12 whole-scope contracts;
- quarantine propagates to exactly 8 dependent family rows, leaving 11 unaffected
  provisional behavioral family passes;
- Opus55 acceptance is 2/19 closed and 17/19 open;
- atomic acceptance is 7/38 proved and 31/38 unresolved;
- terminal goal remains false.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]

PATHS = {
    "authority": "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "closure": "canonical/governance/TERMINAL_CLOSURE_MANIFEST_V1.json",
    "matrix": "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json",
    "scope_reconciliation": "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json",
    "atomic_bindings": "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
    "p1_propagation": "canonical/verification/TERMINAL_SCOPE_QUARANTINE_PROPAGATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
}

EXPECTED_ACCEPTED = {
    "EXACT_SYMBOLIC_COMPUTATION",
    "LONG_HORIZON_MEMORY_AND_CONTINUITY",
}
EXPECTED_P1_QUARANTINED = {
    "ADVANCED_AGENTIC_CODING",
    "AGENTIC_SCIENTIFIC_RESEARCH",
    "BUSINESS_WORKFLOW_AUTOMATION",
    "COMPLEX_MULTI_TOOL_AGENCY",
    "COMPUTER_AND_BROWSER_USE",
    "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
    "MULTI_CAPABILITY_COMPOSITION",
    "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
}

def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value

def _git_blob_sha(rel: str) -> str:
    data = (ROOT / rel).read_bytes()
    h = hashlib.sha1()
    h.update(f"blob {len(data)}\0".encode())
    h.update(data)
    return h.hexdigest()

def evaluate_documents(
    authority: Mapping[str, Any],
    closure: Mapping[str, Any],
    matrix: Mapping[str, Any],
    scope_reconciliation: Mapping[str, Any],
    atomic_bindings: Mapping[str, Any],
    p1_propagation: Mapping[str, Any],
    actual_blob_shas: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    # Independent acceptance scope reconciliation.
    expected = scope_reconciliation.get("expected_current_reduction")
    if not isinstance(expected, Mapping):
        errors.append("SCOPE_RECONCILIATION_EXPECTED_STATE_MISSING")
        expected = {}
    if expected.get("closed_family_count") != 2:
        errors.append("SCOPE_RECONCILIATION_CLOSED_COUNT_NOT_2")
    if expected.get("open_family_count") != 17:
        errors.append("SCOPE_RECONCILIATION_OPEN_COUNT_NOT_17")
    if set(expected.get("preserved_closed_families") or []) != EXPECTED_ACCEPTED:
        errors.append("SCOPE_RECONCILIATION_CLOSED_SET_MISMATCH")
    if expected.get("terminal_goal_achieved") is not False:
        errors.append("SCOPE_RECONCILIATION_TERMINAL_MUST_BE_FALSE")

    # Current atomic acceptance authority.
    saturation = atomic_bindings.get("saturation")
    if not isinstance(saturation, Mapping):
        errors.append("ATOMIC_BINDING_SATURATION_MISSING")
        saturation = {}
    if saturation.get("proved_predicate_count") != 7:
        errors.append("ATOMIC_PROVED_COUNT_NOT_7")
    if saturation.get("unresolved_predicate_count") != 31:
        errors.append("ATOMIC_UNRESOLVED_COUNT_NOT_31")
    if saturation.get("new_reality_units_consumed") != 0:
        errors.append("ATOMIC_RECONCILIATION_CONSUMED_NEW_REALITY")

    # Independent P1 whole-scope quarantine propagation.
    if p1_propagation.get("status") != (
        "INDEPENDENT_PUBLIC_RUNNER_PASS__P1_WHOLE_SCOPE_QUARANTINE_PROPAGATED__"
        "11_UNAFFECTED_FAMILY_PASSES__8_FAMILY_ROWS_QUARANTINED__ZERO_NEW_REALITY"
    ):
        errors.append("P1_PROPAGATION_NOT_EXACT_INDEPENDENT_PASS")
    if p1_propagation.get("quarantined_behavior_id") != "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001":
        errors.append("P1_QUARANTINED_BEHAVIOR_ID_MISMATCH")
    if set(p1_propagation.get("quarantined_families") or []) != EXPECTED_P1_QUARANTINED:
        errors.append("P1_QUARANTINED_FAMILY_SET_MISMATCH")
    if len(p1_propagation.get("unaffected_behavioral_families") or []) != 11:
        errors.append("P1_UNAFFECTED_FAMILY_COUNT_NOT_11")
    if p1_propagation.get("terminal_results_replayed") != 0:
        errors.append("P1_PROPAGATION_TERMINAL_REPLAY_NONZERO")
    if p1_propagation.get("new_reality_units_consumed") != 0:
        errors.append("P1_PROPAGATION_NEW_REALITY_NONZERO")

    # Single current authority pointer.
    truth = authority.get("truth")
    if not isinstance(truth, Mapping):
        errors.append("AUTHORITY_TRUTH_MISSING")
        truth = {}
    if truth.get("terminal_execution") != "3352/3352_RAW_EXECUTIONS_PASS__IMMUTABLE":
        errors.append("AUTHORITY_RAW_TERMINAL_EXECUTION_MISMATCH")
    if truth.get("contracts") != (
        "11/12_WHOLE_SCOPE_PASS__1/12_P1_WHOLE_SCOPE_QUARANTINED__RAW_NARROW_P1_EVIDENCE_PRESERVED"
    ):
        errors.append("AUTHORITY_WHOLE_SCOPE_CONTRACT_STATE_MISMATCH")
    if truth.get("behavioral_families") != (
        "11/19_UNAFFECTED_PROVISIONAL_BEHAVIORAL_PASS__8/19_P1_DEPENDENT_ROWS_QUARANTINED"
    ):
        errors.append("AUTHORITY_BEHAVIORAL_FAMILY_STATE_MISMATCH")
    if truth.get("opus55_acceptance") != "2/19_PASS__17/19_OPEN":
        errors.append("AUTHORITY_ACCEPTANCE_NOT_2_OF_19")
    if truth.get("achieved") is not False:
        errors.append("AUTHORITY_TERMINAL_GOAL_MUST_REMAIN_FALSE")

    af = authority.get("atomic_acceptance_frontier")
    if not isinstance(af, Mapping):
        errors.append("AUTHORITY_ATOMIC_FRONTIER_MISSING")
        af = {}
    if (af.get("proved"), af.get("unresolved"), af.get("total")) != (7, 31, 38):
        errors.append("AUTHORITY_ATOMIC_FRONTIER_MISMATCH")
    if af.get("authorized_acceptance_case_actions") != []:
        errors.append("AUTHORITY_UNAUTHORIZED_CASE_ACTION_PRESENT")

    # Closure projection.
    if closure.get("behavioral_pass_family_count") != 11:
        errors.append("CLOSURE_UNAFFECTED_BEHAVIORAL_PASS_COUNT_NOT_11")
    if closure.get("behavioral_quarantined_family_count") != 8:
        errors.append("CLOSURE_BEHAVIORAL_QUARANTINE_COUNT_NOT_8")
    counters = closure.get("counters")
    if not isinstance(counters, Mapping):
        errors.append("CLOSURE_COUNTERS_MISSING")
        counters = {}
    if counters.get("unproved_required_behaviors") != 1:
        errors.append("CLOSURE_UNPROVED_REQUIRED_BEHAVIOR_COUNT_NOT_1")
    predicates = closure.get("terminal_predicates")
    if not isinstance(predicates, Mapping):
        errors.append("CLOSURE_TERMINAL_PREDICATES_MISSING")
        predicates = {}
    if predicates.get("every_required_behavior_has_admissible_proof") is not False:
        errors.append("CLOSURE_MUST_FAIL_REQUIRED_BEHAVIOR_PROOF_ON_P1")
    if predicates.get("all_frozen_opus_acceptance_predicates_pass") is not False:
        errors.append("CLOSURE_MUST_NOT_CLAIM_ALL_ACCEPTANCE_PASS")
    if predicates.get("proof_bundle_frozen") is not False:
        errors.append("CLOSURE_PROOF_BUNDLE_MUST_REMAIN_UNFROZEN")
    csum = closure.get("opus55_acceptance_summary")
    if not isinstance(csum, Mapping):
        errors.append("CLOSURE_ACCEPTANCE_SUMMARY_MISSING")
        csum = {}
    if csum.get("calibrated_family_count") != 2 or csum.get("pending_family_count") != 17:
        errors.append("CLOSURE_ACCEPTANCE_SUMMARY_MISMATCH")
    if set(csum.get("calibrated_families") or []) != EXPECTED_ACCEPTED:
        errors.append("CLOSURE_ACCEPTANCE_FAMILY_SET_MISMATCH")
    catomic = csum.get("atomic_predicates")
    if not isinstance(catomic, Mapping) or (
        catomic.get("proved"), catomic.get("unresolved"), catomic.get("total")
    ) != (7, 31, 38):
        errors.append("CLOSURE_ATOMIC_ACCEPTANCE_SUMMARY_MISMATCH")

    rows = closure.get("families")
    if not isinstance(rows, list):
        errors.append("CLOSURE_FAMILIES_MISSING")
        rows = []
    qrows = {
        row.get("id") for row in rows
        if isinstance(row, Mapping)
        and row.get("closure_state") == "P1_WHOLE_SCOPE_QUARANTINED__BEHAVIORAL_PASS_RETRACTED"
    }
    if qrows != EXPECTED_P1_QUARANTINED:
        errors.append("CLOSURE_P1_QUARANTINED_FAMILY_SET_MISMATCH")

    # Ownership matrix projection retains route/internalization status while
    # making current behavioral scope and acceptance summaries explicit.
    mscope = matrix.get("postwave_scope_quarantine_reconciliation")
    if not isinstance(mscope, Mapping):
        errors.append("MATRIX_SCOPE_QUARANTINE_SUMMARY_MISSING")
        mscope = {}
    if mscope.get("unaffected_behavioral_family_pass_count") != 11:
        errors.append("MATRIX_UNAFFECTED_BEHAVIORAL_COUNT_NOT_11")
    if mscope.get("quarantined_behavioral_family_count") != 8:
        errors.append("MATRIX_QUARANTINED_BEHAVIORAL_COUNT_NOT_8")
    macc = matrix.get("postwave_acceptance_summary")
    if not isinstance(macc, Mapping):
        errors.append("MATRIX_ACCEPTANCE_SUMMARY_MISSING")
        macc = {}
    if macc.get("calibrated_family_count") != 2 or macc.get("pending_acceptance_family_count") != 17:
        errors.append("MATRIX_ACCEPTANCE_SUMMARY_MISMATCH")
    if set(macc.get("calibrated_families") or []) != EXPECTED_ACCEPTED:
        errors.append("MATRIX_ACCEPTANCE_FAMILY_SET_MISMATCH")
    matomic = macc.get("atomic_acceptance")
    if not isinstance(matomic, Mapping) or (
        matomic.get("proved"), matomic.get("unresolved"), matomic.get("total")
    ) != (7, 31, 38):
        errors.append("MATRIX_ATOMIC_ACCEPTANCE_SUMMARY_MISMATCH")

    mrows = matrix.get("rows")
    if not isinstance(mrows, list):
        errors.append("MATRIX_ROWS_MISSING")
        mrows = []
    mq = {
        row.get("family") for row in mrows
        if isinstance(row, Mapping)
        and row.get("current_behavioral_scope_state") ==
            "P1_WHOLE_SCOPE_QUARANTINED__PROVISIONAL_BEHAVIORAL_FAMILY_PASS_RETRACTED"
    }
    if mq != EXPECTED_P1_QUARANTINED:
        errors.append("MATRIX_P1_QUARANTINED_FAMILY_SET_MISMATCH")

    # Current authority must point to exact current projection blobs.
    if actual_blob_shas is not None:
        sources = authority.get("sources")
        if not isinstance(sources, Mapping):
            errors.append("AUTHORITY_SOURCES_MISSING")
            sources = {}
        pointer_expectations = {
            "terminal_closure_manifest": PATHS["closure"],
            "ownership_matrix": PATHS["matrix"],
            "acceptance_predicate_evidence_bindings_reconciled": PATHS["atomic_bindings"],
            "p1_scope_quarantine_propagation": PATHS["p1_propagation"],
        }
        for key, rel in pointer_expectations.items():
            row = sources.get(key)
            if not isinstance(row, Mapping):
                errors.append("AUTHORITY_SOURCE_MISSING:" + key)
                continue
            if row.get("path") != rel:
                errors.append("AUTHORITY_SOURCE_PATH_MISMATCH:" + key)
            if row.get("git_blob_sha") != actual_blob_shas.get(rel):
                errors.append("AUTHORITY_SOURCE_BLOB_MISMATCH:" + key)

    unique = sorted(set(errors))
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_PROJECTION_CONSISTENCY_VERDICT_V2",
        "status": "PASS" if not unique else "FAIL_CLOSED",
        "pass": not unique,
        "errors": unique,
        "raw_terminal_execution_passes": 3352,
        "whole_scope_contract_passes": 11,
        "whole_scope_contract_quarantined": 1,
        "unaffected_behavioral_family_passes": 11,
        "p1_dependent_behavioral_families_quarantined": 8,
        "acceptance_closed_families": 2,
        "acceptance_open_families": 17,
        "atomic_predicates_proved": 7,
        "atomic_predicates_unresolved": 31,
        "authorized_acceptance_case_actions": 0,
        "terminal_goal_achieved": False,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
        "execution_authority": False,
        "rule": (
            "DERIVED_PROJECTIONS_MUST_AGREE_WITH_CURRENT_SCOPE_COMPLETE_ACCEPTANCE_AND_P1_QUARANTINE_AUTHORITIES__"
            "RAW_EXECUTION_SUCCESS_MAY_NOT_OVERRIDE_WHOLE_SCOPE_SEMANTIC_QUARANTINE__"
            "ALL_CURRENT_AUTHORITY_HASH_POINTERS_MUST_RESOLVE__NO_PROMOTION_CREDIT"
        ),
    }

def evaluate_live() -> dict[str, Any]:
    docs = {key: _load(rel) for key, rel in PATHS.items()}
    shas = {rel: _git_blob_sha(rel) for rel in PATHS.values()}
    return evaluate_documents(
        docs["authority"],
        docs["closure"],
        docs["matrix"],
        docs["scope_reconciliation"],
        docs["atomic_bindings"],
        docs["p1_propagation"],
        shas,
    )

def main() -> int:
    out = evaluate_live()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
