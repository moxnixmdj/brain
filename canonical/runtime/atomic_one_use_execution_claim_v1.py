from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

INPUT_SCHEMA = "PROJECT_BRAIN_ATOMIC_ONE_USE_EXECUTION_CLAIM_INPUT_V1"
OUTPUT_SCHEMA = "PROJECT_BRAIN_ATOMIC_ONE_USE_EXECUTION_CLAIM_OUTPUT_V1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

class AtomicOneUseClaimError(ValueError):
    pass

def _mapping(v: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(v, Mapping):
        raise AtomicOneUseClaimError(field + "_MAPPING_REQUIRED")
    return v

def _text(v: Any, field: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise AtomicOneUseClaimError(field + "_TEXT_REQUIRED")
    return v.strip()

def _sha40(v: Any, field: str) -> str:
    s = _text(v, field).lower()
    if not HEX40.fullmatch(s):
        raise AtomicOneUseClaimError(field + "_HEX40_REQUIRED")
    return s

def _receipt_ref(v: Any, field: str) -> dict[str, str]:
    m = _mapping(v, field)
    return {
        "path": _text(m.get("path"), field + "_PATH"),
        "git_blob_sha": _sha40(m.get("git_blob_sha"), field + "_GIT_BLOB_SHA"),
    }

def execution_lease_digest(lease: Mapping[str, Any]) -> str:
    activation = _receipt_ref(lease.get("activation"), "ACTIVATION")
    candidate = _receipt_ref(lease.get("candidate"), "CANDIDATE")
    scope = _mapping(lease.get("scope"), "SCOPE")
    benchmark_id = _text(scope.get("benchmark_id"), "BENCHMARK_ID")
    target_predicate = _text(scope.get("target_predicate"), "TARGET_PREDICATE")
    execution_kind = _text(scope.get("execution_kind"), "EXECUTION_KIND")
    scope_id = _text(scope.get("scope_id"), "SCOPE_ID")
    max_case_count = scope.get("max_case_count")
    if isinstance(max_case_count, bool) or not isinstance(max_case_count, int) or max_case_count < 0:
        raise AtomicOneUseClaimError("MAX_CASE_COUNT_NONNEGATIVE_INTEGER_REQUIRED")
    new_case_exposure = scope.get("new_case_exposure")
    if not isinstance(new_case_exposure, bool):
        raise AtomicOneUseClaimError("NEW_CASE_EXPOSURE_BOOLEAN_REQUIRED")
    payload = {
        "activation": activation,
        "candidate": candidate,
        "scope": {
            "benchmark_id": benchmark_id,
            "target_predicate": target_predicate,
            "execution_kind": execution_kind,
            "scope_id": scope_id,
            "max_case_count": max_case_count,
            "new_case_exposure": new_case_exposure,
        },
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def expected_claim_ref(digest: str) -> str:
    if not isinstance(digest, str) or not HEX64.fullmatch(digest.lower()):
        raise AtomicOneUseClaimError("LEASE_DIGEST_HEX64_REQUIRED")
    return "refs/heads/claims/one-use/" + digest.lower()

def verify_atomic_one_use_execution_claim(doc: Mapping[str, Any]) -> dict[str, Any]:
    try:
        if not isinstance(doc, Mapping):
            raise AtomicOneUseClaimError("DOCUMENT_MAPPING_REQUIRED")
        if doc.get("schema") != INPUT_SCHEMA:
            raise AtomicOneUseClaimError("SCHEMA_MISMATCH")

        lease = _mapping(doc.get("lease"), "LEASE")
        claim = _mapping(doc.get("claim_receipt"), "CLAIM_RECEIPT")

        digest = execution_lease_digest(lease)
        ref = expected_claim_ref(digest)

        if claim.get("lease_digest_sha256") != digest:
            raise AtomicOneUseClaimError("LEASE_DIGEST_MISMATCH")
        if claim.get("claim_ref") != ref:
            raise AtomicOneUseClaimError("CLAIM_REF_MISMATCH")
        if claim.get("create_http_status") != 201:
            raise AtomicOneUseClaimError("ATOMIC_CREATE_DID_NOT_RETURN_201")
        if claim.get("reference_created") is not True:
            raise AtomicOneUseClaimError("REFERENCE_CREATED_TRUE_REQUIRED")
        if claim.get("response_ref") != ref:
            raise AtomicOneUseClaimError("RESPONSE_REF_MISMATCH")
        response_object_sha = _sha40(claim.get("response_object_sha"), "RESPONSE_OBJECT_SHA")
        expected_target_sha = _sha40(claim.get("expected_target_sha"), "EXPECTED_TARGET_SHA")
        if response_object_sha != expected_target_sha:
            raise AtomicOneUseClaimError("RESPONSE_OBJECT_SHA_TARGET_MISMATCH")
        if claim.get("claim_uniqueness_source") != "ATOMIC_CREATE_RESPONSE":
            raise AtomicOneUseClaimError("CLAIM_UNIQUENESS_SOURCE_INVALID")
        if claim.get("claim_ref_absence_precheck_performed") is not False:
            raise AtomicOneUseClaimError("ABSENCE_PRECHECK_FORBIDDEN")
        for key in (
            "case_read_before_claim",
            "execution_started_before_claim",
            "evaluation_output_exists_before_claim",
        ):
            if claim.get(key) is not False:
                raise AtomicOneUseClaimError(key.upper() + "_FALSE_REQUIRED")

        return {
            "schema": OUTPUT_SCHEMA,
            "status": "PASS__ATOMIC_ONE_USE_EXECUTION_CLAIM__EXACT_LEASE_ONLY",
            "lease_digest_sha256": digest,
            "claim_ref": ref,
            "response_object_sha": response_object_sha,
            "execution_authority": True,
            "authority_scope": "THIS_EXACT_LEASE_ONLY",
            "case_read_authority": True,
            "claim_ref_absence_precheck_required": False,
            "global_fresh_reality_authority": False,
            "promotion_authority": False,
            "acceptance_credit_authorized": False,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
    except AtomicOneUseClaimError as exc:
        return {
            "schema": OUTPUT_SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": [str(exc)],
            "execution_authority": False,
            "authority_scope": "NONE",
            "case_read_authority": False,
            "global_fresh_reality_authority": False,
            "promotion_authority": False,
            "acceptance_credit_authorized": False,
            "family_credit_delta": 0,
            "capability_credit_delta": 0,
            "ownership_credit_delta": 0,
        }
