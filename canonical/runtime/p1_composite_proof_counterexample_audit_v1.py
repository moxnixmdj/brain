"""Executable falsification audit for the candidate P1 composite-proof restoration.

A successful run of this audit means the *candidate restoration is not yet
admissible*. It preserves the immutable V4 and terminal receipts, then checks
whether the proposed proof-role partition actually kills the frozen mutations
assigned to each component.

Two current counterexamples are load-bearing:
1. V4 accepts a case after all visible supporting receipt evidence is erased
   from the causal failure check. The hidden-oracle scorer still passes.
2. The terminal trajectory scorer accepts an otherwise-correct answer after an
   arbitrary unfalsifiable diagnosis field is injected.

No terminal replay or new reality is used.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import contract_native_brain_candidate as terminal_candidate
from canonical.runtime import contract_native_proof_suites as terminal_suite
from canonical.runtime import trajectory_failure_typed_ir_candidate_v4 as v4_candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v4 as v4_proof

ROOT = Path(__file__).resolve().parents[2]
RECONCILIATION = ROOT / "canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json"
SCHEMA = "PROJECT_BRAIN_P1_COMPOSITE_PROOF_COUNTEREXAMPLE_AUDIT_V1"
BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"


def _load() -> dict[str, Any]:
    value = json.loads(RECONCILIATION.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("RECONCILIATION_NOT_OBJECT")
    return value


def v4_dropped_provenance_counterexample() -> dict[str, Any]:
    case = v4_proof.generate_case(
        41001,
        pattern="SINGLE",
        domain="RESEARCH",
        kind="PROVENANCE",
    )
    public = copy.deepcopy(v4_proof.public_task(case))
    erased = 0
    for row in public["task"]["trajectory"]:
        for check in row["checks"]:
            if check.get("pass") is False:
                check["evidence"] = []
                erased += 1

    candidate = v4_candidate.solve(public)
    verdict = v4_proof.score_case(case, candidate)
    return {
        "mutation": "DROP_PROVENANCE_OR_DEPENDENCY_EDGE",
        "mutation_instance": "ERASE_ALL_SUPPORTING_RECEIPTS_ON_FAILED_CHECKS",
        "failed_check_receipt_lists_erased": erased,
        "candidate_supporting_receipts": candidate.get("supporting_receipts"),
        "scorer_pass_after_mutation": verdict.get("pass") is True,
        "verdict": verdict,
        "counterexample_holds": (
            erased > 0
            and candidate.get("supporting_receipts") == []
            and verdict.get("pass") is True
        ),
    }


def terminal_unfalsifiable_diagnosis_counterexample() -> dict[str, Any]:
    case = terminal_suite.generate_case(BEHAVIOR, seed=52001, difficulty=5)
    public = terminal_suite.public_task(case)
    candidate = terminal_candidate.solve(public)
    baseline = terminal_suite.score_case(case, candidate)

    mutated = dict(candidate)
    mutated["diagnosis"] = {
        "claim": "THE_CAUSE_IS_CORRECT_BECAUSE_AN_UNOBSERVABLE_FORCE_SAYS_SO",
        "falsifiable": False,
        "supporting_receipts": [],
    }
    mutated_verdict = terminal_suite.score_case(case, mutated)

    return {
        "mutation": "UNFALSIFIABLE_DIAGNOSIS",
        "baseline_pass": baseline.get("pass") is True,
        "mutated_diagnosis": mutated["diagnosis"],
        "scorer_pass_after_mutation": mutated_verdict.get("pass") is True,
        "verdict": mutated_verdict,
        "counterexample_holds": (
            baseline.get("pass") is True and mutated_verdict.get("pass") is True
        ),
    }


def evaluate(reconciliation: Mapping[str, Any] | None = None) -> dict[str, Any]:
    doc = dict(reconciliation or _load())
    errors: list[str] = []

    if doc.get("behavior_id") != BEHAVIOR:
        errors.append("RECONCILIATION_BEHAVIOR_DRIFT")

    roles = doc.get("mutation_roles")
    if not isinstance(roles, Mapping):
        errors.append("MUTATION_ROLES_MISSING")
        v4_role: list[Any] = []
        terminal_role: list[Any] = []
    else:
        v4_role = roles.get("V4_TYPED_CROSS_DOMAIN_PREFLIGHT") or []
        terminal_role = roles.get("T0_T2_TERMINAL_INTERVENTION_RESCUE") or []
        if "DROP_PROVENANCE_OR_DEPENDENCY_EDGE" not in v4_role:
            errors.append("EXPECTED_DROP_PROVENANCE_MUTATION_NOT_ASSIGNED_TO_V4")
        if "UNFALSIFIABLE_DIAGNOSIS" not in terminal_role:
            errors.append("EXPECTED_UNFALSIFIABLE_DIAGNOSIS_NOT_ASSIGNED_TO_TERMINAL")

    v4_ce = v4_dropped_provenance_counterexample()
    terminal_ce = terminal_unfalsifiable_diagnosis_counterexample()

    if not v4_ce["counterexample_holds"]:
        errors.append("V4_PROVENANCE_COUNTEREXAMPLE_DID_NOT_REPRODUCE")
    if not terminal_ce["counterexample_holds"]:
        errors.append("TERMINAL_DIAGNOSIS_COUNTEREXAMPLE_DID_NOT_REPRODUCE")

    counterexamples_reproduce = (
        v4_ce["counterexample_holds"] and terminal_ce["counterexample_holds"]
    )

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__COMPOSITE_RESTORATION_FALSIFIED__QUARANTINE_MUST_REMAIN"
            if not errors and counterexamples_reproduce
            else "FAIL_CLOSED__AUDIT_INPUT_OR_COUNTEREXAMPLE_DRIFT"
        ),
        "audit_valid": not errors,
        "errors": sorted(set(errors)),
        "behavior_id": BEHAVIOR,
        "candidate_composite_restoration_admissible": False,
        "whole_p1_contract_restored": False,
        "counterexamples": {
            "v4_dropped_provenance": v4_ce,
            "terminal_unfalsifiable_diagnosis": terminal_ce,
        },
        "implications": [
            "V4_CURRENT_SCORER_DOES_NOT_PROVE_FAILURE_CLASS_WITH_SUPPORTING_RECEIPTS_UNDER_DROP_PROVENANCE_MUTATION",
            "TERMINAL_CURRENT_SCORER_DOES_NOT_KILL_UNFALSIFIABLE_DIAGNOSIS_MUTATION",
            "PROPOSED_EXACT_MUTATION_PARTITION_IS_NOT_YET_PROVED",
            "P1_EXECUTION_SCOPE_QUARANTINE_MUST_REMAIN",
            "NO_RECOVERY_ACCEPTANCE_TRANSPORT",
        ],
        "repair_conditions": [
            "V4_SCORER_MUST_REQUIRE_NONEMPTY_CAUSALLY_RELEVANT_SUPPORTING_RECEIPTS_OR_EQUIVALENT_BOUND_EVIDENCE_AND_KILL_DROP_PROVENANCE_MUTATION",
            "UNFALSIFIABLE_DIAGNOSIS_MUTATION_MUST_BE_ASSIGNED_TO_AND_KILLED_BY_A_PREDECLARED_BOUND_COMPONENT",
            "REVERIFY_EXACT_REQUIRED_CHECK_AND_MUTATION_PARTITION_INDEPENDENTLY",
        ],
        "terminal_results_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["audit_valid"] and not out["candidate_composite_restoration_admissible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
