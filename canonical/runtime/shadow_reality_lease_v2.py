"""Two-phase shadow reality lease gate.

V2 repairs the V1 preauthorization circularity. A pre-exposure isolation PLAN
may establish only preclaim readiness. Actual case-reveal authority exists only
after a separately verified, durable, one-use claim receipt is presented while
case reveal has still not occurred.

After execution, the old generic isolation theorem is still used as a
post-execution observed receipt. No shadow result earns acceptance by itself.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime.generic_precommit_isolation_theorem_v1 import (
    verify_benchmark_thin_adapter,
    verify_generic_isolation,
)
from canonical.runtime.pre_exposure_isolation_plan_v1 import (
    verify_pre_exposure_plan,
)

SCHEMA = "PROJECT_BRAIN_SHADOW_REALITY_LEASE_V2"
AUTHORITY_SCHEMA = "PROJECT_BRAIN_SHADOW_REALITY_COLLECTION_ACTIVATION_V2"
CLAIM_SCHEMA = "PROJECT_BRAIN_SHADOW_REALITY_ONE_USE_CLAIM_V1"
HEX = set("0123456789abcdef")


def _norm(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _sha256(value: Any) -> bool:
    s = _norm(value)
    return len(s) == 64 and set(s.lower()) <= HEX


def _sha40(value: Any) -> bool:
    s = _norm(value)
    return len(s) == 40 and set(s.lower()) <= HEX


def _receipt(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and isinstance(value.get("path"), str)
        and bool(value.get("path"))
        and _sha40(value.get("git_blob_sha"))
    )


def lease_digest(lease: Mapping[str, Any]) -> str:
    payload = {
        "lease_id": _norm(lease.get("lease_id")),
        "benchmark_id": _norm(lease.get("benchmark_id")),
        "candidate_sha256": _norm(lease.get("candidate_sha256")).lower(),
        "benchmark_contract_sha256": _norm(lease.get("benchmark_contract_sha256")).lower(),
        "population_manifest_sha256": _norm(lease.get("population_manifest_sha256")).lower(),
        "escrow_sink_contract_sha256": _norm(lease.get("escrow_sink_contract_sha256")).lower(),
        "pre_exposure_plan_sha256": _norm(lease.get("pre_exposure_plan_sha256")).lower(),
        "one_use_nonce": _norm(lease.get("one_use_nonce")),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def claim_digest(claim: Mapping[str, Any]) -> str:
    payload = {
        "lease_digest_sha256": _norm(claim.get("lease_digest_sha256")).lower(),
        "one_use_nonce": _norm(claim.get("one_use_nonce")),
        "claim_store_key": _norm(claim.get("claim_store_key")),
        "claim_event_sequence": claim.get("claim_event_sequence"),
        "preflight_event_sequence": claim.get("preflight_event_sequence"),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def verify_activation_receipt(receipt: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if _norm(receipt.get("schema")) != AUTHORITY_SCHEMA:
        reasons.append("SHADOW_ACTIVATION_SCHEMA_MISMATCH")
    required_true = (
        "active",
        "shadow_collection_authority",
        "independent_verification_pass",
        "zero_incremental_spend_only",
        "write_only_escrow_only",
        "two_phase_isolation_protocol_required",
        "durable_one_use_claim_backend_verified",
        "point_of_use_preflight_required",
        "post_execution_isolation_receipt_required",
    )
    for field in required_true:
        if receipt.get(field) is not True:
            reasons.append(f"ACTIVATION_GATE_FALSE:{field}")
    for field in (
        "global_fresh_reality_authority",
        "acceptance_credit_authority",
        "promotion_authority",
    ):
        if receipt.get(field) is not False:
            reasons.append(f"ACTIVATION_MUST_NOT_GRANT:{field}")
    if not _receipt(receipt.get("independent_verification_receipt")):
        reasons.append("ACTIVATION_VERIFICATION_RECEIPT_NOT_CONTENT_ADDRESSED")
    if not _receipt(receipt.get("claim_backend_verification_receipt")):
        reasons.append("CLAIM_BACKEND_VERIFICATION_RECEIPT_NOT_CONTENT_ADDRESSED")
    return not reasons, reasons


def verify_preclaim_readiness(
    lease: Mapping[str, Any],
    pre_exposure_plan: Mapping[str, Any],
    benchmark_adapter: Mapping[str, Any],
    activation_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []

    plan = verify_pre_exposure_plan(pre_exposure_plan)
    if plan.get("pre_exposure_plan_pass") is not True:
        reasons.append("PRE_EXPOSURE_ISOLATION_PLAN_NOT_PROVED")

    adapter = verify_benchmark_thin_adapter(benchmark_adapter)
    if adapter.get("benchmark_thin_adapter_pass") is not True:
        reasons.append("BENCHMARK_THIN_ADAPTER_NOT_PROVED")

    activation_ok, activation_reasons = verify_activation_receipt(activation_receipt)
    if not activation_ok:
        reasons.extend(activation_reasons)

    for field in (
        "candidate_sha256",
        "benchmark_contract_sha256",
        "population_manifest_sha256",
        "escrow_sink_contract_sha256",
        "pre_exposure_plan_sha256",
    ):
        if not _sha256(lease.get(field)):
            reasons.append(f"INVALID_OR_MISSING_{field.upper()}")

    if not _norm(lease.get("lease_id")):
        reasons.append("LEASE_ID_MISSING")
    if not _norm(lease.get("benchmark_id")):
        reasons.append("BENCHMARK_ID_MISSING")
    if not _norm(lease.get("one_use_nonce")):
        reasons.append("ONE_USE_NONCE_MISSING")
    if lease.get("lease_claimed") is not False:
        reasons.append("LEASE_MUST_BE_UNCLAIMED_AT_PRECLAIM_STAGE")
    if lease.get("case_reveal_has_occurred") is not False:
        reasons.append("CASE_REVEAL_MUST_NOT_HAVE_OCCURRED")
    if lease.get("result_exists") is not False:
        reasons.append("RESULT_MUST_NOT_EXIST")

    required_true = (
        "candidate_frozen",
        "candidate_mutation_blocked",
        "unrelated_work_mutation_blocked",
        "zero_incremental_spend_guard_bound",
        "independent_executor_bound",
        "one_use_lease",
        "escrow_write_only",
        "result_read_blocked_until_zero_reality_fixed_point",
        "outputs_bound_to_lease",
        "point_of_use_preflight_required",
        "post_execution_isolation_receipt_required",
    )
    for field in required_true:
        if lease.get(field) is not True:
            reasons.append(f"LEASE_GATE_FALSE:{field}")

    expected = lease_digest(lease)
    if _norm(lease.get("lease_digest_sha256")).lower() != expected:
        reasons.append("LEASE_DIGEST_MISMATCH")

    if _norm(lease.get("pre_exposure_plan_sha256")).lower() != _norm(
        pre_exposure_plan.get("plan_sha256")
    ).lower():
        reasons.append("LEASE_PRE_EXPOSURE_PLAN_BINDING_MISMATCH")

    ready = not reasons
    return {
        "schema": SCHEMA,
        "preclaim_ready": ready,
        "reasons": sorted(set(reasons)),
        "case_reveal_authority": False,
        "one_use_claim_required": True,
        "global_fresh_reality_authority": False,
        "acceptance_credit_authorized": False,
        "promotion_authority": False,
        "execution_authority_beyond_shadow_collection": False,
    }


def verify_one_use_claim(
    claim: Mapping[str, Any],
    lease: Mapping[str, Any],
    *,
    preclaim_ready: bool,
) -> dict[str, Any]:
    reasons: list[str] = []
    if claim.get("schema") != CLAIM_SCHEMA:
        reasons.append("CLAIM_SCHEMA_MISMATCH")
    if preclaim_ready is not True:
        reasons.append("PRECLAIM_READINESS_REQUIRED")
    if claim.get("case_reveal_has_occurred") is not False:
        reasons.append("CLAIM_MUST_PRECEDE_CASE_REVEAL")
    if claim.get("execution_has_started") is not False:
        reasons.append("CLAIM_MUST_PRECEDE_EXECUTION")
    if claim.get("durable_unique_insert_succeeded") is not True:
        reasons.append("DURABLE_UNIQUE_INSERT_NOT_PROVED")
    if claim.get("claim_backend_independently_verified") is not True:
        reasons.append("CLAIM_BACKEND_NOT_INDEPENDENTLY_VERIFIED")
    if claim.get("point_of_use_preflight_pass") is not True:
        reasons.append("POINT_OF_USE_PREFLIGHT_NOT_PASSED")
    if claim.get("claim_store_previously_absent") is not True:
        reasons.append("CLAIM_STORE_PRIOR_ABSENCE_NOT_PROVED")
    if not _receipt(claim.get("claim_backend_receipt")):
        reasons.append("CLAIM_BACKEND_RECEIPT_NOT_CONTENT_ADDRESSED")

    if _norm(claim.get("lease_digest_sha256")).lower() != _norm(
        lease.get("lease_digest_sha256")
    ).lower():
        reasons.append("CLAIM_LEASE_DIGEST_MISMATCH")
    if _norm(claim.get("one_use_nonce")) != _norm(lease.get("one_use_nonce")):
        reasons.append("CLAIM_NONCE_MISMATCH")

    claim_seq = claim.get("claim_event_sequence")
    preflight_seq = claim.get("preflight_event_sequence")
    if (
        isinstance(claim_seq, bool)
        or not isinstance(claim_seq, int)
        or isinstance(preflight_seq, bool)
        or not isinstance(preflight_seq, int)
    ):
        reasons.append("CLAIM_EVENT_SEQUENCE_INVALID")
    elif not preflight_seq < claim_seq:
        reasons.append("CLAIM_MUST_FOLLOW_POINT_OF_USE_PREFLIGHT")

    if _norm(claim.get("claim_digest_sha256")).lower() != claim_digest(claim):
        reasons.append("CLAIM_DIGEST_MISMATCH")

    passed = not reasons
    return {
        "schema": SCHEMA,
        "one_use_claim_pass": passed,
        "reasons": sorted(set(reasons)),
        "case_reveal_authority": passed,
        "shadow_collection_authority": passed,
        "global_fresh_reality_authority": False,
        "acceptance_credit_authorized": False,
        "promotion_authority": False,
        "result_visibility": "WRITE_ONLY_ESCROW" if passed else "BLOCKED",
    }


def verify_post_execution_result(
    *,
    claim_verdict: Mapping[str, Any],
    post_execution_isolation_receipt: Mapping[str, Any],
    output_bound_to_lease: bool,
    result_in_write_only_escrow: bool,
) -> dict[str, Any]:
    post = verify_generic_isolation(post_execution_isolation_receipt)
    valid = bool(
        claim_verdict.get("one_use_claim_pass") is True
        and post.get("generic_isolation_kernel_pass") is True
        and output_bound_to_lease
        and result_in_write_only_escrow
    )
    return {
        "schema": SCHEMA,
        "shadow_result_protocol_valid": valid,
        "post_execution_isolation_pass": post.get("generic_isolation_kernel_pass") is True,
        "eligible_for_future_post_fixed_point_reduction": valid,
        "result_visibility_before_fixed_point": False,
        "global_fresh_reality_authority": False,
        "acceptance_credit_authorized": False,
        "promotion_authority": False,
        "separate_post_fixed_point_predicate_activation_required": True,
    }
