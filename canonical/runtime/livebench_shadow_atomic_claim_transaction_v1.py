"""Atomic LiveBench shadow claim transaction verifier.

The only transition that may unlock terminal-case reveal is:
  current V3 point-of-use preflight PASS
  + separately verified V2 shadow activation
  + atomic Git-ref create returns 201
  -> reveal authority for THIS exact lease only.

There is intentionally no prior claim-ref absence read. The create response is
the uniqueness linearization point. Duplicate/non-201 results fail closed.

This verifier consumes zero benchmark cases and grants no global fresh-reality,
acceptance, promotion, family, capability, or ownership credit.
"""
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping

from canonical.runtime.livebench_shadow_point_of_use_preflight_v1 import (
    expected_claim_ref,
    verify_point_of_use_preflight,
)
from canonical.runtime.shadow_reality_lease_v2 import verify_activation_receipt

SCHEMA="PROJECT_BRAIN_LIVEBENCH_SHADOW_ATOMIC_CLAIM_TRANSACTION_V1"
CLAIM_SCHEMA="PROJECT_BRAIN_LIVEBENCH_SHADOW_ATOMIC_CLAIM_RECEIPT_V1"
BENCHMARK_ID="LIVEBENCH_IF_2026_06_25"
TARGET_PREDICATE="LIVEBENCH_IF_GE_65_7"
HEX=set("0123456789abcdef")

def _sha40(x: Any) -> bool:
    return isinstance(x,str) and len(x)==40 and set(x.lower()) <= HEX

def preflight_binding_sha256(plan: Mapping[str,Any], receipt: Mapping[str,Any]) -> str:
    payload={"plan_sha256":plan.get("plan_sha256"),"receipt":receipt}
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def verify_atomic_claim_transaction(
    *,
    plan: Mapping[str,Any],
    preflight_receipt: Mapping[str,Any],
    activation_receipt: Mapping[str,Any],
    claim_receipt: Mapping[str,Any],
) -> dict[str,Any]:
    reasons=[]
    pre=verify_point_of_use_preflight(plan,preflight_receipt)
    if pre.get("point_of_use_preflight_pass") is not True:
        reasons.append("POINT_OF_USE_PREFLIGHT_NOT_PASSED")

    activation_ok, activation_reasons=verify_activation_receipt(activation_receipt)
    if not activation_ok:
        reasons.extend(activation_reasons)
    if activation_receipt.get("benchmark_id") != BENCHMARK_ID:
        reasons.append("ACTIVATION_BENCHMARK_ID_MISMATCH")
    if activation_receipt.get("target_predicate") != TARGET_PREDICATE:
        reasons.append("ACTIVATION_TARGET_PREDICATE_MISMATCH")

    if claim_receipt.get("schema") != CLAIM_SCHEMA:
        reasons.append("CLAIM_SCHEMA_MISMATCH")

    lease_digest=preflight_receipt.get("lease_digest_sha256")
    try:
        expected_ref=expected_claim_ref(lease_digest)
    except ValueError:
        expected_ref=""
        reasons.append("INVALID_LEASE_DIGEST_SHA256")

    if claim_receipt.get("claim_ref") != expected_ref:
        reasons.append("CLAIM_REF_MISMATCH")
    if claim_receipt.get("create_http_status") != 201:
        reasons.append("ATOMIC_CLAIM_CREATE_DID_NOT_RETURN_201")
    if claim_receipt.get("reference_created") is not True:
        reasons.append("ATOMIC_CLAIM_REFERENCE_NOT_CREATED")
    if claim_receipt.get("response_ref") != expected_ref:
        reasons.append("ATOMIC_CLAIM_RESPONSE_REF_MISMATCH")
    if not _sha40(claim_receipt.get("response_object_sha")):
        reasons.append("ATOMIC_CLAIM_RESPONSE_OBJECT_SHA_INVALID")

    if claim_receipt.get("preflight_binding_sha256") != preflight_binding_sha256(plan,preflight_receipt):
        reasons.append("CLAIM_PREFLIGHT_BINDING_MISMATCH")

    for field in (
        "case_reveal_has_occurred_before_claim",
        "execution_has_started_before_claim",
        "evaluation_output_exists_before_claim",
    ):
        if claim_receipt.get(field) is not False:
            reasons.append("CLAIM_PRECONDITION_FALSE_GATE_FAILED:"+field)

    if claim_receipt.get("claim_uniqueness_source") != "ATOMIC_CREATE_RESPONSE":
        reasons.append("CLAIM_UNIQUENESS_SOURCE_NOT_ATOMIC_CREATE")

    passed=not reasons
    return {
        "schema":SCHEMA,
        "atomic_claim_transaction_pass":passed,
        "reasons":sorted(set(reasons)),
        "benchmark_id":BENCHMARK_ID,
        "target_predicate":TARGET_PREDICATE,
        "claim_ref":expected_ref,
        "case_reveal_authority":passed,
        "shadow_collection_authority":passed,
        "authority_scope":"THIS_EXACT_LEASE_ONLY" if passed else "NONE",
        "claim_ref_absence_precheck_required":False,
        "terminal_cases_consumed_by_verifier":0,
        "global_fresh_reality_authority":False,
        "acceptance_credit_authorized":False,
        "promotion_authority":False,
        "result_visibility_before_fixed_point":False if passed else None,
    }
