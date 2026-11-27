"""Compile the P1 terminal-scope quarantine against existing typed V4 evidence.

Zero-reality proof compression only. This module cannot promote P1 or recovery.
Only content-addressed, independently verified live evidence may shrink the
residual. There are intentionally no caller-supplied proof override knobs.
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
) -> dict[str, Any]:
    errors: list[str] = []
    audit = dict(audit_result or p1_audit.evaluate())
    v4 = dict(v4_verification or _load(V4_VERIFICATION))

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
    verified_kinds = set(verified.get("mechanism_classes") or [])
    code_kinds = set(candidate_v4.ALLOWED_KINDS)

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
    if verified_kinds != code_kinds:
        errors.append("V4_VERIFIED_KIND_SET_DOES_NOT_MATCH_LIVE_CANDIDATE")

    # Recompute the already-spent deterministic prewave V4 matrix. This is
    # receipt validation, not fresh terminal evidence.
    cases = proof_v4.suite_cases()
    case_failures: list[str] = []
    status_counts: dict[str, int] = {}
    mechanism_observations: dict[str, int] = {}
    for case in cases:
        oracle = case.get("_oracle") or {}
        expected_status = str(oracle.get("status"))
        status_counts[expected_status] = status_counts.get(expected_status, 0) + 1
        for mechanisms in (oracle.get("mechanisms") or {}).values():
            for kind in mechanisms:
                mechanism_observations[str(kind)] = mechanism_observations.get(str(kind), 0) + 1
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
            "new_reality_units_consumed": 0,
        }

    discharged = set(DIRECT_V4_DISCHARGE)
    covered_class_kinds = FULL_CLASS_REQUIREMENT & verified_kinds
    missing_class_kinds = FULL_CLASS_REQUIREMENT - verified_kinds
    if not missing_class_kinds:
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
            "disposition": "SEARCH_EXISTING_SCOPE_TYPED_P1_RECEIPT_BEFORE_ANY_NEW_OBSERVATION",
        })

    # The independent V4 receipt proves repair-target identity against its hidden
    # oracle. It contains no verified post-intervention terminal-rescue field.
    # Terminal V3 does have rescue, but only inside its audited narrow linear
    # single-cause envelope, so that fact may not be inherited into V4 scope.
    heterogeneous_rescue_verified = (
        verified.get("heterogeneous_post_intervention_terminal_rescue_verified") is True
    )
    if not heterogeneous_rescue_verified:
        residuals.append({
            "id": "P1_HETEROGENEOUS_INTERVENTION_RESCUE",
            "reason": "V4_SCORES_REPAIR_TARGET_IDENTITY_BUT_HAS_NO_INDEPENDENT_POST_INTERVENTION_TERMINAL_RESCUE_RECEIPT",
            "covered_by_terminal_v3": "LINEAR_SINGLE_CAUSE_ENVELOPE_ONLY",
            "new_reality_required": False,
            "disposition": "SEARCH_EXISTING_HETEROGENEOUS_INTERVENTION_RESCUE_RECEIPT_BEFORE_ANY_NEW_OBSERVATION",
        })

    unresolved_missing_semantics = sorted(MISSING_FROM_TERMINAL_SCORER - discharged)
    prewave_residuals_exhausted = not residuals and not unresolved_missing_semantics

    # This compiler is deliberately prewave-only. The frozen P1 binding forbids
    # standalone synthetic whole-domain terminal credit and requires direct P1
    # intervention/rescue evidence inside the frozen T0/T2 observations.
    # Therefore exhausting V4/prewave residual semantics can never, by itself,
    # clear the terminal P1 scope quarantine. A separate terminal-evidence
    # reconciler must prove that frozen requirement.
    can_clear = False

    return {
        "schema": SCHEMA,
        "status": (
            "PASS__V4_PREFLIGHT_RESIDUAL_EXHAUSTED__TERMINAL_QUARANTINE_REMAINS"
            if prewave_residuals_exhausted
            else "PASS__V4_COMPRESSES_P1_SCOPE_QUARANTINE_TO_EXACT_RESIDUAL"
        ),
        "pass": True,
        "errors": [],
        "source_scope_mismatch_proved": True,
        "v4_independent_verification": V4_VERIFICATION,
        "v4_recomputed_case_count": len(cases),
        "v4_case_failures": case_failures,
        "v4_status_counts": status_counts,
        "v4_mechanism_observations": mechanism_observations,
        "terminal_missing_semantics": sorted(MISSING_FROM_TERMINAL_SCORER),
        "semantics_discharged_by_existing_v4": sorted(discharged),
        "unresolved_terminal_missing_semantics": unresolved_missing_semantics,
        "class_coverage": {
            "required": sorted(FULL_CLASS_REQUIREMENT),
            "covered_by_v4": sorted(covered_class_kinds),
            "missing_from_v4": sorted(missing_class_kinds),
        },
        "heterogeneous_post_intervention_terminal_rescue_verified": heterogeneous_rescue_verified,
        "residual_obligations": residuals,
        "prewave_residuals_exhausted": prewave_residuals_exhausted,
        "can_clear_p1_scope_quarantine": can_clear,
        "terminal_clearance_requires": (
            "FROZEN_T0_T2_DIRECT_P1_INTERVENTION_RESCUE_EVIDENCE__"
            "STANDALONE_SYNTHETIC_WHOLE_DOMAIN_SCORE_FORBIDDEN"
        ),
        "next": (
            "REQUIRE_FROZEN_T0_T2_DIRECT_P1_INTERVENTION_RESCUE_EVIDENCE_BEFORE_QUARANTINE_CLEARANCE"
            if prewave_residuals_exhausted
            else
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
