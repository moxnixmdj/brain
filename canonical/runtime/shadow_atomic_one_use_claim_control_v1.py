"""Atomic create-as-proof one-use claim control for shadow evaluation."""
from __future__ import annotations
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_SHADOW_ATOMIC_ONE_USE_CLAIM_CONTROL_V1"
HEX=set("0123456789abcdef")

def _sha256(x: Any) -> bool:
    return isinstance(x,str) and len(x)==64 and set(x.lower()) <= HEX

def expected_claim_ref(lease_digest_sha256: str) -> str:
    if not _sha256(lease_digest_sha256):
        raise ValueError("INVALID_LEASE_DIGEST_SHA256")
    return "refs/heads/shadow-claims/"+lease_digest_sha256.lower()

def verify_atomic_claim_event(receipt: Mapping[str,Any]) -> dict[str,Any]:
    reasons=[]
    digest=receipt.get("lease_digest_sha256")
    try:
        expected=expected_claim_ref(digest)
    except ValueError:
        expected=""
        reasons.append("INVALID_LEASE_DIGEST_SHA256")
    if receipt.get("claim_ref") != expected:
        reasons.append("CLAIM_REF_NOT_DERIVED_FROM_LEASE_DIGEST")
    if receipt.get("atomic_create_attempted") is not True:
        reasons.append("ATOMIC_CREATE_NOT_ATTEMPTED")
    if receipt.get("atomic_create_succeeded") is not True:
        reasons.append("ATOMIC_CREATE_DID_NOT_SUCCEED")
    if receipt.get("create_http_status") not in (200,201):
        reasons.append("ATOMIC_CREATE_SUCCESS_STATUS_NOT_BOUND")
    if receipt.get("reference_already_exists") is True:
        reasons.append("REFERENCE_ALREADY_EXISTS")
    if receipt.get("case_reveal_before_claim") is not False:
        reasons.append("CASE_REVEAL_OCCURRED_BEFORE_CLAIM")
    if receipt.get("execution_started_before_claim") is not False:
        reasons.append("EXECUTION_STARTED_BEFORE_CLAIM")
    if receipt.get("claim_response_bound_to_exact_ref") is not True:
        reasons.append("CLAIM_RESPONSE_NOT_BOUND_TO_EXACT_REF")
    if receipt.get("claim_response_bound_to_exact_lease") is not True:
        reasons.append("CLAIM_RESPONSE_NOT_BOUND_TO_EXACT_LEASE")
    passed=not reasons
    return {
        "schema":SCHEMA,
        "atomic_one_use_claim_pass":passed,
        "expected_claim_ref":expected,
        "reasons":sorted(set(reasons)),
        "prior_absence_observation_required":False,
        "atomic_create_success_is_ownership_event":True,
        "terminal_cases_consumed":0,
        "case_reveal_authority":False,
        "shadow_collection_authority":False,
        "fresh_reality_authority":False,
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_credit_authorized":False,
    }

def classify_failed_create(receipt: Mapping[str,Any]) -> str:
    if receipt.get("atomic_create_succeeded") is True:
        return "CLAIM_CREATED"
    status=receipt.get("create_http_status")
    msg=str(receipt.get("create_error") or "").lower()
    if status==422 and ("already exists" in msg or receipt.get("reference_already_exists") is True):
        return "REPLAY_OR_DUPLICATE_REJECTED"
    return "CREATE_FAILED_CLOSED"
