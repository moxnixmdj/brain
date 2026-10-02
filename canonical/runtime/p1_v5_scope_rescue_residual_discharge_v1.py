"""Fail-closed P1 V5 residual discharge compiler.

This compiler can eliminate the two residual obligations emitted by the verified
P1 V4 compressor only when an independent public-runner receipt proves the exact
V5 bytes and all required scope/rescue counts. It grants no family/capability
credit and does not itself rewrite terminal authority.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "PROJECT_BRAIN_P1_V5_SCOPE_RESCUE_RESIDUAL_DISCHARGE_V1"
SOURCE = "canonical/governance/P1_V4_SCOPE_SAFE_RESIDUAL_DISCHARGE_ACTIVATION_V1.json"
V5_RECEIPT = "canonical/verification/P1_TYPED_TRAJECTORY_V5_SCOPE_RESCUE_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json"

EXPECTED_RESIDUALS = {
    "P1_EXPLICIT_SCOPE_FAILURE_CLASS",
    "P1_HETEROGENEOUS_INTERVENTION_RESCUE",
}
EXPECTED_BLOBS = {
    "candidate": "aabac3cc36684862f5fb2388a9a281daa30c24a6",
    "proof": "bfc0421bd39796d0e0a7434e475fd1d0d7f17774",
    "tests": "7ad1c7fc2e7e5a083501ce8b9034899bce581ee4",
    "governance": "f1d82765760e5ffe8a016e1fc6e943a9467bfc64",
}
REQUIRED_VERIFIED = {
    "EXACT_BRAIN_V5_BLOB_IDENTITIES_PASS",
    "ALL_192_TYPED_CROSS_DOMAIN_CASES_PASS",
    "SCOPE_FIRST_CLASS_NOT_AUTHORITY_ALIAS",
    "ALL_144_NONAMBIGUOUS_POST_INTERVENTION_RESCUES_PASS",
    "DELAYED_SCOPE_RESCUE_PASS",
    "SYMPTOM_ONLY_REPAIRS_DO_NOT_RESCUE",
    "INTERACTION_REQUIRES_COMPLETE_JOINT_REPAIR_SET",
    "AMBIGUOUS_CASES_PRESERVE_NONIDENTIFIABILITY",
    "HIDDEN_ORACLE_NOT_CANDIDATE_VISIBLE",
}

def _load(rel: str) -> dict[str, Any]:
    value = json.loads((ROOT / rel).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(rel + ":NOT_OBJECT")
    return value

def evaluate(
    *,
    source: Mapping[str, Any] | None = None,
    verification: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    src = dict(source or _load(SOURCE))
    ver = dict(verification or _load(V5_RECEIPT))

    exact = src.get("exact_residual_after_existing_v4")
    if not isinstance(exact, list):
        errors.append("SOURCE_RESIDUAL_LIST_MISSING")
        source_ids: set[str] = set()
    else:
        source_ids = {
            str(x.get("id"))
            for x in exact
            if isinstance(x, Mapping) and isinstance(x.get("id"), str)
        }
    if source_ids != EXPECTED_RESIDUALS:
        errors.append("SOURCE_RESIDUAL_SET_DRIFT")

    if not str(ver.get("status", "")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS__"):
        errors.append("V5_NOT_INDEPENDENT_PUBLIC_RUNNER_PASS")

    blobs = ver.get("exact_brain_blobs")
    if not isinstance(blobs, Mapping):
        errors.append("V5_EXACT_BLOBS_MISSING")
    else:
        for key, expected in EXPECTED_BLOBS.items():
            if blobs.get(key) != expected:
                errors.append(f"V5_BLOB_MISMATCH:{key}")

    verified = ver.get("verified")
    verified_set = set(verified) if isinstance(verified, list) and all(isinstance(x, str) for x in verified) else set()
    missing_verified = sorted(REQUIRED_VERIFIED - verified_set)
    if missing_verified:
        errors.append("V5_REQUIRED_VERIFIED_FACTS_MISSING:" + ",".join(missing_verified))

    result = ver.get("result")
    if not isinstance(result, Mapping):
        errors.append("V5_RESULT_MISSING")
        result = {}
    expected_counts = {
        "case_count": 192,
        "machine_checked_rescues": 144,
        "interaction_joint_rescues": 48,
        "primary_scope_cases": 24,
        "scope_delayed_cases": 6,
        "scope_interaction_cases": 6,
    }
    for key, expected in expected_counts.items():
        if result.get(key) != expected:
            errors.append(f"V5_RESULT_COUNT_MISMATCH:{key}")

    if ver.get("terminal_results_replayed") not in (0, None):
        errors.append("TERMINAL_REPLAY_NONZERO")
    if ver.get("fresh_terminal_evidence_consumed") not in (0, None):
        errors.append("FRESH_TERMINAL_EVIDENCE_NONZERO")
    if ver.get("new_reality_units_consumed") not in (0, None):
        errors.append("NEW_REALITY_NONZERO")
    if ver.get("capability_credit_delta") not in (0, None) or ver.get("family_credit_delta") not in (0, None):
        errors.append("UPSTREAM_RECEIPT_CREDIT_NONZERO")

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "pass": False,
            "errors": sorted(set(errors)),
            "source_residuals": sorted(source_ids),
            "residual_obligations_after_v5": sorted(EXPECTED_RESIDUALS),
            "can_clear_p1_scope_quarantine_candidate": False,
            "terminal_results_replayed": 0,
            "fresh_terminal_evidence_consumed": 0,
            "new_reality_units_consumed": 0,
            "capability_credit_delta": 0,
            "family_credit_delta": 0,
            "execution_authority": False,
            "promotion_authority": False,
        }

    return {
        "schema": SCHEMA,
        "status": "PASS__EXACT_TWO_P1_V4_RESIDUALS_DISCHARGED_BY_INDEPENDENT_V5_SCOPE_RESCUE_PROOF__ZERO_CREDIT",
        "pass": True,
        "errors": [],
        "source_residuals": sorted(source_ids),
        "discharged_by_v5": sorted(EXPECTED_RESIDUALS),
        "residual_obligations_after_v5": [],
        "can_clear_p1_scope_quarantine_candidate": True,
        "proof": {
            "scope_failure_class": "EXPLICIT_FIRST_CLASS_SCOPE_CHECK_IN_192_CASE_TYPED_MATRIX",
            "heterogeneous_intervention_rescue": "144_MACHINE_CHECKED_NONAMBIGUOUS_RESCUES_ACROSS_SIX_DOMAINS_EIGHT_MECHANISM_CLASSES_AND_SINGLE_DELAYED_INTERACTION_PATTERNS",
            "interaction_negative_control": "48_INTERACTION_CASES_REQUIRE_COMPLETE_JOINT_REPAIR_SET",
            "symptom_negative_control": "SYMPTOM_ONLY_REPAIRS_NEVER_RESCUE",
        },
        "next": "INDEPENDENTLY_VERIFY_THIS_REDUCER__THEN_RECOMPUTE_P1_QUARANTINE_AND_ATOMIC_ACCEPTANCE_FIXED_POINT_FROM_CURRENT_AUTHORITY__NO_INHERITED_FAMILY_CREDIT",
        "terminal_results_replayed": 0,
        "fresh_terminal_evidence_consumed": 0,
        "new_reality_units_consumed": 0,
        "incremental_spend_usd": 0,
        "capability_credit_delta": 0,
        "family_credit_delta": 0,
        "execution_authority": False,
        "promotion_authority": False,
    }

if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, sort_keys=True))
