"""Compile the P1 terminal-scope quarantine against existing typed V4 evidence.

This is a zero-reality proof compressor.  It does not promote P1 or recovery.
It asks exactly which semantics missing from the actually executed terminal P1
scorer are already discharged by the independently verified typed V4 route, and
which obligations still survive.

The compiler deliberately refuses to treat repair-target correctness as
intervention/rescue evidence.  That distinction is load-bearing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import p1_terminal_execution_scope_audit_v1 as p1_audit
from canonical.runtime import trajectory_failure_typed_ir_candidate_v4 as candidate_v4
from canonical.runtime import trajectory_failure_typed_ir_proof_v4 as proof_v4

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_P1_V4_SCOPE_SAFE_RESIDUAL_DISCHARGE_V1"
V4_VERIFICATION = "canonical/verification/TRAJECTORY_TYPED_IR_V4_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

MISSING_FROM_TERMINAL_SCORER = {
    "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
    "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
    "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT",
    "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
}

FULL_CLASS_REQUIREMENT = {
    "AUTHORITY",
    "SCOPE",
    "TOOL_CONTRACT",
    "STATE_TRANSITION",
    "PROVENANCE",
    "DEPENDENCY",
}

DIRECT_V4_DISCHARGE = {
    "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
    "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
    "MULTISTEP_OR_DELAYED_CAUSAL_INTERACTIONS_ARE_NOT_REDUCED_TO_FIRST_VISIBLE_SYMPTOM",
}


def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value


def evaluate(
    *,
    audit_result: Mapping[str, Any] | None = None,
    v4_verification: Mapping[str, Any] | None = None,
    v4_kinds: set[str] | None = None,
    rescue_intervention_verified: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    audit = dict(audit_result or p1_audit.evaluate())
    v4 = dict(v4_verification or _load(V4_VERIFICATION))
    kinds = set(v4_kinds if v4_kinds is not None else candidate_v4.ALLOWED_KINDS)

    if audit.get("audit_valid") is not True or audit.get("scope_mismatch_proved") is not True:
        errors.append("P1_SCOPE_MISMATCH_AUDIT_NOT_PROVED")

    missing = set(audit.get("frozen_required_checks_not_evaluated_by_executed_scorer") or [])
    if missing != MISSING_FROM_TERMINAL_SCORER:
        errors.append("P1_MISSING_SEMANTIC_SET_DRIFT")

    if not str(v4.get("status", "")).startswith("INDEPENDENT_PASS__"):
        errors.append("V4_NOT_INDEPENDENTLY_VERIFIED")
    verified = v4.get("verified")
    if not isinstance(verified, Mapping):
        errors.append("V4_VERIFIED_BLOCK_MISSING")
        verified = {}

    expected_domains = {"BROWSER", "FILESYSTEM", "TOOL_API", "ARTIFACT", "RESEARCH", "CODE"}
    expected_patterns = {"SINGLE", "DELAYED", "INTERACTION", "AMBIGUOUS"}
    if set(verified.get("normalized_domains") or []) != expected_domains:
        errors.append("V4_DOMAIN_COVERAGE_DRIFT")
    if set(verified.get("causal_patterns") or []) != expected_patterns:
        errors.append("V4_CAUSAL_PATTERN_COVERAGE_DRIFT")
    if int(verified.get("cross_product_case_count") or -1) != 168:
        errors.append("V4_CASE_MATRIX_DRIFT")
    if verified.get("hidden_oracle_not_candidate_visible") is not True:
        errors.append("V4_ORACLE_ISOLATION_NOT_PROVED")
    if verified.get("falsifiable_repair_targets_scored_against_hidden_oracle") is not True:
        errors.append("V4_REPAIR_TARGET_SCORING_NOT_PROVED")

    # Recompute only the already-spent deterministic prewave V4 matrix.  This is
    # receipt validation, not fresh terminal evidence.
    cases = proof_v4.suite_cases()
    case_failures: list[str] = []
    pattern_counts: dict[str, int] = {}
    kind_counts: dict[str, int] = {}
    for case in cases:
        oracle = case.get("_oracle") or {}
        task = case.get("task") or {}
        pattern = str(oracle.get("status"))
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        for mechanisms in (oracle.get("mechanisms") or {}).values():
            for kind in mechanisms:
                kind_counts[str(kind)] = kind_counts.get(str(kind), 0) + 1
        out = candidate_v4.solve(proof_v4.public_task(case))
        scored = proof_v4.score_case(case, out)
        if scored.get("pass") is not True:
            case_failures.append(str(case.get("seed")))
    if len(cases) != 168 or case_failures:
        errors.append("V4_MATRIX_RECOMPUTE_FAIL")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": sorted(set(errors)),
            "can_clear_p1_scope_quarantine": False,
            "promotion_authority": False,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "fresh_terminal_evidence_consumed": 0,
        }

    discharged = set(DIRECT_V4_DISCHARGE)
    covered_class_kinds = FULL_CLASS_REQUIREMENT & kinds
    missing_class_kinds = FULL_CLASS_REQUIREMENT - kinds
    class_semantic_fully_discharged = not missing_class_kinds
    if class_semantic_fully_discharged:
        discharged.add(
            "AUTHORITY_SCOPE_TOOL_STATE_PROVENANCE_AND_DEPENDENCY_FAILURE_CLASSES_ARE_LOAD_BEARING_WHEN_PRESENT"
        )

    residuals: list[dict[str, Any]] = []
    if missing_class_kinds:
        residuals.append({
            "id": "P1_EXPLICIT_SCOPE_FAILURE_CLASS",
            "reason": "V4_TYPED_IR_HAS_NO_EXPLICIT_SCOPE_FAILURE_KIND",
            "missing_kinds": sorted(missing_class_kinds),
            "covered_kinds": sorted(covered_class_kinds),
            "new_reality_required": False,
            "disposition": "SEARCH_EXISTING_SCOPE_TYPED_P1_RECEIPT_OR_ADD_SCOPE_KIND_TO_A_FUTURE_PREDECLARED_ROUTE",
        })

    # V4 proves that a nominated repair target matches its hidden oracle.  It
    # does not execute the intervention and observe terminal rescue.  Terminal
    # V3 did execute a narrow linear/single-cause rescue suite, but that cannot
    # be inherited across V4's heterogeneous delayed/interaction envelope.
    if not rescue_intervention_verified:
        residuals.append({
            "id": "P1_HETEROGENEOUS_INTERVENTION_RESCUE",
            "reason": "V4_SCORES_REPAIR_TARGET_IDENTITY_BUT_DOES_NOT_MACHINE_VERIFY_POST_INTERVENTION_TERMINAL_RESCUE",
            "covered_by_terminal_v3": "LINEAR_SINGLE_CAUSE_ENVELOPE_ONLY",
            "new_reality_required": False,
            "disposition": "SEARCH_EXISTING_HETEROGENEOUS_INTERVENTION_RESCUE_RECEIPT_BEFORE_AUTHORIZING_NEW_OBSERVATION",
        })

    unresolved_missing_semantics = sorted(MISSING_FROM_TERMINAL_SCORER - discharged)
    can_clear = not residuals and not unresolved_missing_semantics

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__V4_COMPRESSES_P1_SCOPE_QUARANTINE_TO_EXACT_RESIDUAL"
            if not can_clear
            else "PASS__P1_SCOPE_QUARANTINE_CLEARABLE_CANDIDATE"
        ),
        "pass": True,
        "errors": [],
        "source_scope_mismatch_proved": True,
        "v4_independent_verification": V4_VERIFICATION,
        "v4_recomputed_case_count": len(cases),
        "v4_case_failures": case_failures,
        "v4_pattern_counts": pattern_counts,
        "v4_mechanism_observations": kind_counts,
        "terminal_missing_semantics": sorted(MISSING_FROM_TERMINAL_SCORER),
        "semantics_discharged_by_existing_v4": sorted(discharged),
        "unresolved_terminal_missing_semantics": unresolved_missing_semantics,
        "class_coverage": {
            "required": sorted(FULL_CLASS_REQUIREMENT),
            "covered_by_v4": sorted(covered_class_kinds),
            "missing_from_v4": sorted(missing_class_kinds),
        },
        "residual_obligations": residuals,
        "can_clear_p1_scope_quarantine": can_clear,
        "next": (
            "SEARCH_EXISTING_P1_SCOPE_FAILURE_AND_HETEROGENEOUS_INTERVENTION_RESCUE_RECEIPTS__"
            "ONLY_IF_ABSENT_FREEZE_THE_MINIMUM_TWO_OBLIGATION_ROUTE_BEFORE_ANY_NEW_REALITY"
        ),
        "fresh_terminal_evidence_consumed": 0,
        "new_reality_units_consumed": 0,
        "terminal_results_replayed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "promotion_authority": False,
    }


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
