"""Fail-closed cognition provenance gate for ownership promotion."""
from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime.capability_transfer_ownership_gate_v1 import evaluate as evaluate_transfer

SCHEMA = "PROJECT_BRAIN_OWNERSHIP_PROMOTION_COGNITION_PROVENANCE_GATE_V1"
CLASSES = {"NONE", "K1_INFORMATION_ONLY", "K2_TRANSFER_DERIVED", "K3_RUNTIME_COGNITION"}

def evaluate(row: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    cls = row.get("external_contribution_classification")
    if cls not in CLASSES:
        errors.append("EXTERNAL_CONTRIBUTION_CLASSIFICATION_MISSING_OR_INVALID")
    elif cls == "K3_RUNTIME_COGNITION":
        errors.append("RUNTIME_COGNITION_PROVIDER_FORBIDDEN")
    elif cls == "K2_TRANSFER_DERIVED":
        rec = row.get("capability_transfer_record")
        if not isinstance(rec, Mapping):
            errors.append("K2_TRANSFER_RECORD_REQUIRED")
        else:
            verdict = evaluate_transfer(rec)
            if verdict.get("pass") is not True:
                errors.append("K2_TRANSFER_GATE_NOT_PASSED")
    elif cls == "K1_INFORMATION_ONLY":
        if row.get("external_knowledge_non_authoritative") is not True:
            errors.append("K1_EXTERNAL_KNOWLEDGE_NOT_PROVEN_NON_AUTHORITATIVE")
        if row.get("external_knowledge_target_solving_policy_or_answer") is not False:
            errors.append("K1_TARGET_SOLVING_COGNITION_NOT_EXCLUDED")
    elif cls == "NONE":
        provenance = row.get("acquisition_donor_provenance")
        if isinstance(provenance, Mapping) and provenance.get("used") is True:
            errors.append("NONE_CLASS_CONTRADICTS_DONOR_PROVENANCE")
        if row.get("external_runtime_cognition") is True:
            errors.append("NONE_CLASS_CONTRADICTS_RUNTIME_COGNITION")
    passed = not errors
    return {
        "schema": SCHEMA,
        "status": "PASS__PROVENANCE_CLASSIFIED_AND_OWNERSHIP_ADMISSIBLE" if passed else "FAIL_CLOSED__PROVENANCE_OR_COGNITION_BOUNDARY",
        "pass": passed,
        "classification": cls if cls in CLASSES else None,
        "errors": sorted(set(errors)),
        "promotion_authority": False,
        "ownership_credit_delta": 0,
        "terminal_credit_delta": 0,
    }
