"""Fail-closed verifier for the frozen P1 composite proof-role reconciliation.

The frozen P1 binding was composite before the terminal wave:
- typed V4 supplied cross-domain mechanism/causal-pattern preflight semantics;
- T0/T2 supplied terminal intervention/rescue judgments.

This verifier proves only that the corrected role partition is exactly supported
by those predeclared, content-addressed sources. It does not replay terminal
evidence and does not itself lift the quarantine.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.p1_terminal_execution_scope_audit_v1 import evaluate as scope_audit
from canonical.runtime import trajectory_failure_typed_ir_candidate_v4 as v4_candidate
from canonical.runtime import trajectory_failure_typed_ir_proof_v4 as v4_proof

ROOT = Path(__file__).resolve().parents[2]
CANDIDATE = ROOT / "canonical/governance/P1_COMPOSITE_PROOF_ROLE_RECONCILIATION_V1.json"
P1_BINDING = ROOT / "canonical/governance/P1_TRAJECTORY_T0_T2_MULTIPLEX_TERMINAL_BINDING_V1.json"
V4_RECEIPT = ROOT / "canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"
V4_PROOF = ROOT / "canonical/runtime/trajectory_failure_typed_ir_proof_v4.py"
V4_TESTS = ROOT / "canonical/tests/test_trajectory_failure_typed_ir_v4.py"
PARENT_BINDING = ROOT / "canonical/governance/TERMINAL_PARENT_PORTFOLIO_RUNNER_BINDING_V1.json"
EXECUTED_SUITE = ROOT / "canonical/runtime/contract_native_proof_suites.py"
TERMINAL_WAVE = ROOT / "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json"
SCOPE_AUDIT = ROOT / "canonical/runtime/p1_terminal_execution_scope_audit_v1.py"
QUARANTINE = ROOT / "canonical/governance/P1_TERMINAL_EXECUTION_SCOPE_MISMATCH_QUARANTINE_V1.json"

BEHAVIOR = "TRAJECTORY_CRITICAL_FAILURE_LOCALIZATION_001"
SCHEMA = "PROJECT_BRAIN_P1_COMPOSITE_PROOF_ROLE_VERDICT_V1"

AUTHORITY_KEYS = {
    "p1_binding": P1_BINDING,
    "v4_independent_preflight": V4_RECEIPT,
    "v4_proof": V4_PROOF,
    "v4_tests": V4_TESTS,
    "parent_binding": PARENT_BINDING,
    "executed_suite": EXECUTED_SUITE,
    "terminal_wave": TERMINAL_WAVE,
    "scope_audit": SCOPE_AUDIT,
    "quarantine": QUARANTINE,
}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(str(path) + ":NOT_OBJECT")
    return value


def blob(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _flatten_partition(partition: Mapping[str, Any], errors: list[str], label: str) -> tuple[set[str], dict[str, set[str]]]:
    by_role: dict[str, set[str]] = {}
    seen: set[str] = set()
    for role, values in partition.items():
        if not isinstance(role, str) or not isinstance(values, list) or any(not isinstance(x, str) for x in values):
            errors.append(label + "_PARTITION_MALFORMED")
            continue
        s = set(values)
        if len(s) != len(values):
            errors.append(label + "_DUPLICATE_WITHIN_ROLE:" + role)
        overlap = seen & s
        if overlap:
            errors.append(label + "_CROSS_ROLE_OVERLAP:" + ",".join(sorted(overlap)))
        seen |= s
        by_role[role] = s
    return seen, by_role


def _v4_drop_provenance_counterexample() -> dict[str, Any]:
    """Execute the frozen DROP_PROVENANCE mutation against the exact V4 scorer.

    A role assignment is not proof. If erasing all visible supporting receipts
    still produces a passing scorer verdict, the assigned mutation is not killed
    and P1 quarantine cannot lift.
    """
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
    holds = (
        erased > 0
        and candidate.get("supporting_receipts") == []
        and verdict.get("pass") is True
    )
    return {
        "mutation": "DROP_PROVENANCE_OR_DEPENDENCY_EDGE",
        "mutation_instance": "ERASE_ALL_SUPPORTING_RECEIPTS_ON_FAILED_CHECKS",
        "failed_check_receipt_lists_erased": erased,
        "candidate_supporting_receipts": candidate.get("supporting_receipts"),
        "scorer_pass_after_mutation": verdict.get("pass") is True,
        "counterexample_holds": holds,
        "verdict": verdict,
    }



def _v4_unfalsifiable_diagnosis_counterexample() -> dict[str, Any]:
    """Execute the reassigned UNFALSIFIABLE_DIAGNOSIS mutation against V4.

    Moving a mutation between proof roles is not a kill. If V4's exact scorer
    accepts an otherwise-correct output after injection of an explicitly
    unfalsifiable diagnosis with no supporting receipts, the mutation survives
    and quarantine cannot lift.
    """
    case = v4_proof.generate_case(
        41002,
        pattern="SINGLE",
        domain="RESEARCH",
        kind="AUTHORITY",
    )
    public = copy.deepcopy(v4_proof.public_task(case))
    candidate = v4_candidate.solve(public)
    baseline = v4_proof.score_case(case, candidate)

    mutated = dict(candidate)
    mutated["diagnosis"] = {
        "claim": "THE_CAUSE_IS_CORRECT_BECAUSE_AN_UNOBSERVABLE_FORCE_SAYS_SO",
        "falsifiable": False,
        "supporting_receipts": [],
    }
    verdict = v4_proof.score_case(case, mutated)
    holds = baseline.get("pass") is True and verdict.get("pass") is True
    return {
        "mutation": "UNFALSIFIABLE_DIAGNOSIS",
        "mutation_instance": "INJECT_EXPLICIT_UNFALSIFIABLE_DIAGNOSIS_WITH_ZERO_RECEIPTS",
        "baseline_pass": baseline.get("pass") is True,
        "scorer_pass_after_mutation": verdict.get("pass") is True,
        "mutated_diagnosis": mutated["diagnosis"],
        "counterexample_holds": holds,
        "verdict": verdict,
    }


def evaluate(candidate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    errors: list[str] = []
    candidate = copy.deepcopy(dict(candidate)) if candidate is not None else load(CANDIDATE)
    binding = load(P1_BINDING)
    v4_receipt = load(V4_RECEIPT)
    terminal = load(TERMINAL_WAVE)

    if candidate.get("behavior_id") != BEHAVIOR or binding.get("behavior_id") != BEHAVIOR:
        errors.append("BEHAVIOR_ID_MISMATCH")

    auth = candidate.get("authority")
    if not isinstance(auth, Mapping):
        errors.append("CANDIDATE_AUTHORITY_MISSING")
        auth = {}
    for key, path in AUTHORITY_KEYS.items():
        row = auth.get(key)
        rel = str(path.relative_to(ROOT))
        if not isinstance(row, Mapping):
            errors.append("AUTHORITY_ROW_MISSING:" + key)
            continue
        if row.get("path") != rel:
            errors.append("AUTHORITY_PATH_MISMATCH:" + key)
        if row.get("git_blob_sha") != blob(path):
            errors.append("AUTHORITY_BLOB_MISMATCH:" + key)

    evaluator = binding.get("evaluator") if isinstance(binding.get("evaluator"), Mapping) else {}
    required_checks = set(evaluator.get("required_checks") or [])
    required_mutations = set(evaluator.get("required_mutations") or [])
    if not required_checks or not required_mutations:
        errors.append("FROZEN_BINDING_REQUIRED_SETS_MISSING")

    proof_roles = candidate.get("proof_roles")
    if not isinstance(proof_roles, Mapping):
        proof_roles = {}
        errors.append("PROOF_ROLES_MISSING")
    all_checks, checks_by_role = _flatten_partition(proof_roles, errors, "CHECK")
    if all_checks != required_checks:
        errors.append("CHECK_PARTITION_NOT_EXACT_FROZEN_SET")

    mutation_roles = candidate.get("mutation_roles")
    if not isinstance(mutation_roles, Mapping):
        mutation_roles = {}
        errors.append("MUTATION_ROLES_MISSING")
    all_mutations, mutations_by_role = _flatten_partition(mutation_roles, errors, "MUTATION")
    if all_mutations != required_mutations:
        errors.append("MUTATION_PARTITION_NOT_EXACT_FROZEN_SET")

    audit = scope_audit()
    if audit.get("audit_valid") is not True or audit.get("scope_mismatch_proved") is not True:
        errors.append("SCOPE_AUDIT_NOT_VALID_PROVED_MISMATCH")
    missing_checks = set(audit.get("frozen_required_checks_not_evaluated_by_executed_scorer") or [])
    v4_checks = checks_by_role.get("V4_TYPED_CROSS_DOMAIN_PREFLIGHT", set())
    terminal_checks = checks_by_role.get("T0_T2_TERMINAL_INTERVENTION_RESCUE", set())
    if v4_checks != missing_checks:
        errors.append("V4_CHECK_ROLE_NOT_EXACT_SCOPE_AUDIT_RESIDUAL")
    if terminal_checks != required_checks - missing_checks:
        errors.append("TERMINAL_CHECK_ROLE_NOT_EXACT_COMPLEMENT")

    # V4 exact independent source and operational semantics.
    if "INDEPENDENT_PASS" not in str(v4_receipt.get("status", "")):
        errors.append("V4_RECEIPT_NOT_INDEPENDENT_PASS")
    exact = v4_receipt.get("exact_brain_blobs") if isinstance(v4_receipt.get("exact_brain_blobs"), Mapping) else {}
    if exact.get("proof") != blob(V4_PROOF) or exact.get("tests") != blob(V4_TESTS):
        errors.append("V4_RECEIPT_BLOB_DRIFT")
    verified = v4_receipt.get("verified") if isinstance(v4_receipt.get("verified"), Mapping) else {}
    if verified.get("cross_product_case_count") != 168:
        errors.append("V4_CASE_COUNT_NOT_168")
    if verified.get("hidden_oracle_not_candidate_visible") is not True:
        errors.append("V4_HIDDEN_ORACLE_BOUNDARY_NOT_PROVED")
    if verified.get("falsifiable_repair_targets_scored_against_hidden_oracle") is not True:
        errors.append("V4_FALSIFIABLE_REPAIR_TARGET_NOT_PROVED")

    proof_src = V4_PROOF.read_text(encoding="utf-8")
    tests_src = V4_TESTS.read_text(encoding="utf-8")
    required_v4_literals = [
        'KINDS=("AUTHORITY","SCHEMA","PROVENANCE","INVARIANT","STATE_TRANSITION","TOOL_CONTRACT","DEPENDENCY")',
        '("SINGLE","DELAYED","INTERACTION","AMBIGUOUS")',
        "NONIDENTIFIABILITY_OVERCLAIM",
        "FALSIFIABLE_REPAIR_TARGET_WRONG",
    ]
    for lit in required_v4_literals:
        if lit not in proof_src:
            errors.append("V4_OPERATIONAL_LITERAL_MISSING:" + lit)
    for name in [
        "test_wrong_repair_target_is_rejected_by_hidden_oracle",
        "test_nonidentifiable_case_abstains",
        "test_interaction_preserves_both_roots_and_repairs",
        "test_downstream_symptom_is_not_selected",
    ]:
        if name not in tests_src:
            errors.append("V4_TEST_SEMANTIC_MISSING:" + name)

    # Load-bearing adversarial check: an assigned mutation must actually be
    # killed by its assigned scorer. Static role/literal presence is insufficient.
    v4_provenance_counterexample = _v4_drop_provenance_counterexample()
    if v4_provenance_counterexample["counterexample_holds"]:
        errors.append("V4_DROP_PROVENANCE_MUTATION_SURVIVES_SCORER")

    # The corrected mutation role gives V4 the unfalsifiable-diagnosis mutation.
    v4_mut = mutations_by_role.get("V4_TYPED_CROSS_DOMAIN_PREFLIGHT", set())
    term_mut = mutations_by_role.get("T0_T2_TERMINAL_INTERVENTION_RESCUE", set())
    if "UNFALSIFIABLE_DIAGNOSIS" not in v4_mut:
        errors.append("UNFALSIFIABLE_DIAGNOSIS_NOT_ASSIGNED_TO_V4_HIDDEN_ORACLE_PROOF")
    if "UNFALSIFIABLE_DIAGNOSIS" in term_mut:
        errors.append("UNFALSIFIABLE_DIAGNOSIS_STILL_ASSIGNED_TO_NARROW_TERMINAL_SCORER")

    v4_diagnosis_counterexample = _v4_unfalsifiable_diagnosis_counterexample()
    if v4_diagnosis_counterexample["counterexample_holds"]:
        errors.append("V4_UNFALSIFIABLE_DIAGNOSIS_MUTATION_SURVIVES_SCORER")

    suite_src = EXECUTED_SUITE.read_text(encoding="utf-8")
    for lit in ["CAUSE_STEP_WRONG", "REPAIR_TARGET_WRONG", "CAUSAL_EVIDENCE_MISSING", "RESCUE_FAILED"]:
        if lit not in suite_src:
            errors.append("TERMINAL_SCORER_LITERAL_MISSING:" + lit)

    parent = (((terminal.get("reduction_input") or {}).get("wave") or {}).get("parent_portfolio_receipts") or {})
    for portfolio in ("T0", "T2"):
        hits = [x for x in parent.get(portfolio, []) if isinstance(x, Mapping) and x.get("behavior_id") == BEHAVIOR]
        if len(hits) != 1:
            errors.append(portfolio + "_P1_RECEIPT_COUNT")
            continue
        row = hits[0]
        for key in ("load_bearing", "direct_instrumentation_pass", "parent_terminal_acceptance_pass"):
            if row.get(key) is not True:
                errors.append(portfolio + "_P1_" + key.upper() + "_NOT_TRUE")
        for key in ("case_replaced", "result_to_runtime_feedback", "tuning_replay"):
            if row.get(key) is not False:
                errors.append(portfolio + "_P1_" + key.upper() + "_NOT_FALSE")

    unique = sorted(set(errors))
    return {
        "schema": SCHEMA,
        "status": (
            "PASS__COMPOSITE_P1_PROOF_ROLE_PARTITION_SUPPORTED__QUARANTINE_LIFT_ELIGIBLE_PENDING_INDEPENDENT_VERIFICATION"
            if not unique else "FAIL_CLOSED"
        ),
        "pass": not unique,
        "errors": unique,
        "behavior_id": BEHAVIOR,
        "required_check_count": len(required_checks),
        "required_mutation_count": len(required_mutations),
        "v4_check_count": len(v4_checks),
        "terminal_check_count": len(terminal_checks),
        "v4_mutation_count": len(v4_mut),
        "terminal_mutation_count": len(term_mut),
        "quarantine_lift_eligible": not unique,
        "v4_drop_provenance_counterexample": v4_provenance_counterexample,
        "v4_unfalsifiable_diagnosis_counterexample": v4_diagnosis_counterexample,
        "quarantine_resolved": False,
        "terminal_results_replayed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
        "rule": (
            "PASS_REQUIRES_PREDECLARED_COMPOSITE_ROLE_SUPPORT_AND_EXECUTABLE_KILL_OF_ASSIGNED_LOAD_BEARING_MUTATIONS__"
            "A_SURVIVING_ASSIGNED_MUTATION_BLOCKS_QUARANTINE_LIFT__"
            "QUARANTINE_MAY_LIFT_ONLY_AFTER_INDEPENDENT_EXACT_BLOB_REVERIFICATION__"
            "RECOVERY_ACCEPTANCE_TRANSPORT_REMAINS_SEPARATE"
        ),
    }


def main() -> int:
    out = evaluate()
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
