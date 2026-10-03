"""Post-delegation terminal projection consistency verifier V3.

This verifier treats the older 2/19 absolute-dominance reconciliation as an
immutable baseline, then admits only independently verified, content-addressed
terminal deltas.  It currently composes exactly one such delta: the verified
delegation universal-scope closure.

It grants no capability, family, execution, or promotion credit.  Its purpose is
to prevent stale control-plane counters from rejecting valid verified progress,
while also preventing an authority file from inventing progress that lacks the
bound independent receipts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]

PATHS = {
    "authority": "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json",
    "baseline_scope": "canonical/governance/ABSOLUTE_DOMINANCE_SCOPE_COMPLETENESS_RECONCILIATION_V1.json",
    "atomic_bindings": "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json",
    "delegation_scope": "canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "delegation_reduction": "canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
    "p1_propagation": "canonical/verification/TERMINAL_SCOPE_QUARANTINE_PROPAGATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
}

BASELINE_ACCEPTED = {
    "EXACT_SYMBOLIC_COMPUTATION",
    "LONG_HORIZON_MEMORY_AND_CONTINUITY",
}
DELEGATION_DELTA = {"SUBAGENT_DELEGATION_AND_COORDINATION"}
P1_QUARANTINED = {
    "ADVANCED_AGENTIC_CODING",
    "AGENTIC_SCIENTIFIC_RESEARCH",
    "BUSINESS_WORKFLOW_AUTOMATION",
    "COMPLEX_MULTI_TOOL_AGENCY",
    "COMPUTER_AND_BROWSER_USE",
    "INSTRUCTION_FOLLOWING_SCOPE_AND_JUDGMENT",
    "MULTI_CAPABILITY_COMPOSITION",
    "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
}
DELEGATION_PREDICATE = "DELEGATION_TERMINAL_SUCCESS_NONINFERIOR"


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


def _claim(bindings: Mapping[str, Any], predicate_id: str) -> Mapping[str, Any] | None:
    rows = bindings.get("claims")
    if not isinstance(rows, list):
        return None
    for row in rows:
        if isinstance(row, Mapping) and row.get("predicate_id") == predicate_id:
            return row
    return None


def evaluate_documents(
    authority: Mapping[str, Any],
    baseline_scope: Mapping[str, Any],
    atomic_bindings: Mapping[str, Any],
    delegation_scope: Mapping[str, Any],
    delegation_reduction: Mapping[str, Any],
    p1_propagation: Mapping[str, Any],
    actual_blob_shas: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []

    # 1) Immutable pre-delegation baseline.
    baseline = baseline_scope.get("expected_current_reduction")
    if not isinstance(baseline, Mapping):
        errors.append("BASELINE_SCOPE_REDUCTION_MISSING")
        baseline = {}
    if baseline.get("closed_family_count") != 2:
        errors.append("BASELINE_CLOSED_COUNT_NOT_2")
    if baseline.get("open_family_count") != 17:
        errors.append("BASELINE_OPEN_COUNT_NOT_17")
    if set(baseline.get("preserved_closed_families") or []) != BASELINE_ACCEPTED:
        errors.append("BASELINE_ACCEPTED_SET_MISMATCH")
    if baseline.get("terminal_goal_achieved") is not False:
        errors.append("BASELINE_TERMINAL_MUST_BE_FALSE")

    # 2) Independently verified universal delegation scope proof.
    ds_status = str(delegation_scope.get("status") or "")
    if not ds_status.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("DELEGATION_SCOPE_NOT_INDEPENDENT_PASS")
    if delegation_scope.get("target_predicate") != DELEGATION_PREDICATE:
        errors.append("DELEGATION_SCOPE_TARGET_MISMATCH")
    verified = set(delegation_scope.get("verified") or [])
    for item in {
        "UNIVERSAL_SCOPE_PROVED_TRUE",
        "BASIS_KIND_UNIVERSAL_FORMAL_SCOPE_PROOF",
        "NO_EMPIRICAL_GENERALIZATION",
        "ZERO_TERMINAL_REPLAY_AND_ZERO_NEW_REALITY",
    }:
        if item not in verified:
            errors.append("DELEGATION_SCOPE_VERIFIED_FACT_MISSING:" + item)
    if delegation_scope.get("new_reality_units_consumed") != 0:
        errors.append("DELEGATION_SCOPE_CONSUMED_NEW_REALITY")
    if delegation_scope.get("terminal_results_replayed") != 0:
        errors.append("DELEGATION_SCOPE_REPLAYED_TERMINAL_RESULTS")

    # 3) Independent reduction may add exactly one family to the baseline.
    dr_status = str(delegation_reduction.get("status") or "")
    if not dr_status.startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("DELEGATION_REDUCTION_NOT_INDEPENDENT_PASS")
    vr = delegation_reduction.get("verified_result")
    if not isinstance(vr, Mapping):
        errors.append("DELEGATION_REDUCTION_RESULT_MISSING")
        vr = {}
    if vr.get("family_count") != 19:
        errors.append("DELEGATION_REDUCTION_FAMILY_COUNT_NOT_19")
    if vr.get("closed_family_count") != 3 or vr.get("open_family_count") != 16:
        errors.append("DELEGATION_REDUCTION_COUNTS_MISMATCH")
    if set(vr.get("preserved_closed_families") or []) != BASELINE_ACCEPTED:
        errors.append("DELEGATION_REDUCTION_BASELINE_SET_MISMATCH")
    if set(vr.get("newly_closed_families") or []) != DELEGATION_DELTA:
        errors.append("DELEGATION_REDUCTION_DELTA_SET_MISMATCH")
    if vr.get("scope_completeness_basis") != "UNIVERSAL_FORMAL_SCOPE_PROOF":
        errors.append("DELEGATION_REDUCTION_SCOPE_BASIS_MISMATCH")
    if delegation_reduction.get("new_reality_units_consumed") != 0:
        errors.append("DELEGATION_REDUCTION_CONSUMED_NEW_REALITY")
    if delegation_reduction.get("terminal_results_replayed") != 0:
        errors.append("DELEGATION_REDUCTION_REPLAYED_TERMINAL_RESULTS")

    current_accepted = BASELINE_ACCEPTED | DELEGATION_DELTA
    expected_closed = len(current_accepted)
    expected_open = 19 - expected_closed

    # 4) Atomic ledger must contain exactly the independently admitted predicate delta.
    sat = atomic_bindings.get("saturation")
    if not isinstance(sat, Mapping):
        errors.append("ATOMIC_SATURATION_MISSING")
        sat = {}
    if sat.get("proved_predicate_count") != 8:
        errors.append("ATOMIC_PROVED_COUNT_NOT_8")
    if sat.get("unresolved_predicate_count") != 30:
        errors.append("ATOMIC_UNRESOLVED_COUNT_NOT_30")
    if sat.get("new_reality_units_consumed") != 0:
        errors.append("ATOMIC_RECONCILIATION_CONSUMED_NEW_REALITY")
    claim = _claim(atomic_bindings, DELEGATION_PREDICATE)
    if claim is None:
        errors.append("DELEGATION_ATOMIC_CLAIM_MISSING")
        claim = {}
    if claim.get("state") != "PROVED":
        errors.append("DELEGATION_ATOMIC_CLAIM_NOT_PROVED")
    if claim.get("family") != "SUBAGENT_DELEGATION_AND_COORDINATION":
        errors.append("DELEGATION_ATOMIC_FAMILY_MISMATCH")
    if claim.get("source_path") != PATHS["delegation_reduction"]:
        errors.append("DELEGATION_ATOMIC_SOURCE_PATH_MISMATCH")
    if claim.get("scope_complete") is not True:
        errors.append("DELEGATION_ATOMIC_SCOPE_NOT_COMPLETE")

    # 5) P1 quarantine remains orthogonal and unchanged.
    if p1_propagation.get("status") != (
        "INDEPENDENT_PUBLIC_RUNNER_PASS__P1_WHOLE_SCOPE_QUARANTINE_PROPAGATED__"
        "11_UNAFFECTED_FAMILY_PASSES__8_FAMILY_ROWS_QUARANTINED__ZERO_NEW_REALITY"
    ):
        errors.append("P1_PROPAGATION_NOT_EXACT_INDEPENDENT_PASS")
    if set(p1_propagation.get("quarantined_families") or []) != P1_QUARANTINED:
        errors.append("P1_QUARANTINED_FAMILY_SET_MISMATCH")
    if p1_propagation.get("new_reality_units_consumed") != 0:
        errors.append("P1_PROPAGATION_NEW_REALITY_NONZERO")

    # 6) Live authority must equal baseline + independently verified delta.
    truth = authority.get("truth")
    if not isinstance(truth, Mapping):
        errors.append("AUTHORITY_TRUTH_MISSING")
        truth = {}
    if truth.get("terminal_execution") != "3352/3352_RAW_EXECUTIONS_PASS__IMMUTABLE":
        errors.append("AUTHORITY_RAW_TERMINAL_EXECUTION_MISMATCH")
    if truth.get("contracts") != (
        "11/12_WHOLE_SCOPE_PASS__1/12_P1_WHOLE_SCOPE_QUARANTINED__RAW_NARROW_P1_EVIDENCE_PRESERVED"
    ):
        errors.append("AUTHORITY_CONTRACT_STATE_MISMATCH")
    if truth.get("behavioral_families") != (
        "11/19_UNAFFECTED_PROVISIONAL_BEHAVIORAL_PASS__8/19_P1_DEPENDENT_ROWS_QUARANTINED"
    ):
        errors.append("AUTHORITY_BEHAVIORAL_STATE_MISMATCH")
    expected_acceptance = f"{expected_closed}/19_PASS__{expected_open}/19_OPEN"
    if truth.get("opus55_acceptance") != expected_acceptance:
        errors.append("AUTHORITY_ACCEPTANCE_MISMATCH")
    if truth.get("achieved") is not False:
        errors.append("AUTHORITY_TERMINAL_GOAL_MUST_REMAIN_FALSE")

    af = authority.get("atomic_acceptance_frontier")
    if not isinstance(af, Mapping):
        errors.append("AUTHORITY_ATOMIC_FRONTIER_MISSING")
        af = {}
    if (af.get("proved"), af.get("unresolved"), af.get("total")) != (8, 30, 38):
        errors.append("AUTHORITY_ATOMIC_FRONTIER_MISMATCH")
    if af.get("authorized_acceptance_case_actions") != []:
        errors.append("AUTHORITY_UNAUTHORIZED_CASE_ACTION_PRESENT")
    if af.get("source") != PATHS["atomic_bindings"]:
        errors.append("AUTHORITY_ATOMIC_SOURCE_PATH_MISMATCH")

    integ = authority.get("integrator_reconciliation_20261002_current")
    if not isinstance(integ, Mapping):
        errors.append("AUTHORITY_CURRENT_RECONCILIATION_MISSING")
        integ = {}
    if integ.get("family_acceptance") != "3_OF_19_CLOSED__16_OPEN":
        errors.append("AUTHORITY_CURRENT_FAMILY_RECONCILIATION_MISMATCH")
    if integ.get("atomic_acceptance") != "8_OF_38_PROVED__30_UNRESOLVED":
        errors.append("AUTHORITY_CURRENT_ATOMIC_RECONCILIATION_MISMATCH")
    if set(integ.get("preserved_closed_families") or []) != current_accepted:
        errors.append("AUTHORITY_CURRENT_ACCEPTED_SET_MISMATCH")

    # 7) Every current delta pointer must be content-addressed to the exact live blob.
    if actual_blob_shas is not None:
        sources = authority.get("sources")
        if not isinstance(sources, Mapping):
            errors.append("AUTHORITY_SOURCES_MISSING")
            sources = {}
        pointer_expectations = {
            "acceptance_predicate_evidence_bindings_reconciled": PATHS["atomic_bindings"],
            "delegation_v4_universal_scope_verification": PATHS["delegation_scope"],
            "delegation_acceptance_reduction": PATHS["delegation_reduction"],
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

        if af.get("source_git_blob_sha") != actual_blob_shas.get(PATHS["atomic_bindings"]):
            errors.append("AUTHORITY_ATOMIC_SOURCE_BLOB_MISMATCH")

        exact_inputs = delegation_reduction.get("exact_brain_inputs")
        if not isinstance(exact_inputs, Mapping):
            errors.append("DELEGATION_REDUCTION_EXACT_INPUTS_MISSING")
            exact_inputs = {}
        if exact_inputs.get(PATHS["delegation_scope"]) != actual_blob_shas.get(PATHS["delegation_scope"]):
            errors.append("DELEGATION_REDUCTION_SCOPE_BLOB_BINDING_MISMATCH")

        if claim.get("source_sha") != actual_blob_shas.get(PATHS["delegation_reduction"]):
            errors.append("DELEGATION_ATOMIC_SOURCE_BLOB_MISMATCH")

    unique = sorted(set(errors))
    return {
        "schema": "PROJECT_BRAIN_TERMINAL_PROJECTION_CONSISTENCY_VERDICT_V3",
        "status": "PASS" if not unique else "FAIL_CLOSED",
        "pass": not unique,
        "errors": unique,
        "baseline_accepted_families": sorted(BASELINE_ACCEPTED),
        "verified_delta_families": sorted(DELEGATION_DELTA),
        "current_accepted_families": sorted(current_accepted),
        "acceptance_closed_families": expected_closed,
        "acceptance_open_families": expected_open,
        "atomic_predicates_proved": 8,
        "atomic_predicates_unresolved": 30,
        "terminal_goal_achieved": False,
        "new_reality_units_consumed": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
        "execution_authority": False,
        "rule": (
            "CURRENT_PROJECTION_EQUALS_IMMUTABLE_VERIFIED_BASELINE_PLUS_EXACT_CONTENT_ADDRESSED_"
            "INDEPENDENTLY_VERIFIED_DELTAS__NO_DELTA_WITHOUT_SCOPE_COMPLETE_RECEIPT__NO_STALE_COUNTER_OVERRIDE"
        ),
    }


def evaluate_live() -> dict[str, Any]:
    docs = {key: _load(rel) for key, rel in PATHS.items()}
    shas = {rel: _git_blob_sha(rel) for rel in PATHS.values()}
    return evaluate_documents(
        docs["authority"],
        docs["baseline_scope"],
        docs["atomic_bindings"],
        docs["delegation_scope"],
        docs["delegation_reduction"],
        docs["p1_propagation"],
        shas,
    )


def main() -> int:
    out = evaluate_live()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
