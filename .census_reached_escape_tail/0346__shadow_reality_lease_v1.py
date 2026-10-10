#!/usr/bin/env python3
"""Fail-closed proof-carrying lease gate for pre-fixed-point shadow evaluation.

This module may establish only *readiness for escrowed shadow collection* when a
separate active authority receipt is supplied. It never grants acceptance,
promotion, global fresh-reality, capability, family, ownership, or terminal
credit.

The result of a shadow run must remain write-only and unreadable by the frozen
candidate, planner, and zero-reality work until the global zero-reality fixed
point is reached. Even then, a separate predicate-specific independent
reduction/activation is required before any acceptance credit exists.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from canonical.runtime.generic_precommit_isolation_theorem_v1 import (
    verify_benchmark_thin_adapter,
    verify_generic_isolation,
)

SCHEMA = "PROJECT_BRAIN_SHADOW_REALITY_LEASE_V1"
AUTHORITY_SCHEMA = "PROJECT_BRAIN_SHADOW_REALITY_COLLECTION_ACTIVATION_V1"

_HASH_FIELDS = (
    "candidate_sha256",
    "benchmark_contract_sha256",
    "population_manifest_sha256",
    "escrow_sink_contract_sha256",
)

_REQUIRED_TRUE = (
    "candidate_frozen",
    "candidate_mutation_blocked",
    "unrelated_work_mutation_blocked",
    "zero_incremental_spend_guard_pass",
    "independent_executor",
    "one_use_lease",
    "escrow_write_only",
    "result_read_blocked_until_zero_reality_fixed_point",
    "outputs_bound_to_lease",
)


def _norm(x: Any) -> str:
    return " ".join(str(x or "").strip().split())


def _sha256(x: Any) -> bool:
    s = _norm(x)
    return len(s) == 64 and all(c in "0123456789abcdefABCDEF" for c in s)


def lease_digest(lease: Mapping[str, Any]) -> str:
    payload = {
        "lease_id": _norm(lease.get("lease_id")),
        "benchmark_id": _norm(lease.get("benchmark_id")),
        **{k: _norm(lease.get(k)).lower() for k in _HASH_FIELDS},
        "one_use_nonce": _norm(lease.get("one_use_nonce")),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def verify_activation_receipt(receipt: Mapping[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if _norm(receipt.get("schema")) != AUTHORITY_SCHEMA:
        reasons.append("SHADOW_ACTIVATION_SCHEMA_MISMATCH")
    if receipt.get("active") is not True:
        reasons.append("SHADOW_ACTIVATION_NOT_ACTIVE")
    if receipt.get("shadow_collection_authority") is not True:
        reasons.append("SHADOW_COLLECTION_AUTHORITY_NOT_GRANTED")
    if receipt.get("independent_verification_pass") is not True:
        reasons.append("SHADOW_ACTIVATION_NOT_INDEPENDENTLY_VERIFIED")
    if receipt.get("zero_incremental_spend_only") is not True:
        reasons.append("SHADOW_ACTIVATION_ZERO_SPEND_BOUND_MISSING")
    if receipt.get("write_only_escrow_only") is not True:
        reasons.append("SHADOW_ACTIVATION_ESCROW_BOUND_MISSING")
    # This activation is deliberately narrower than global fresh-reality.
    if receipt.get("global_fresh_reality_authority") is not False:
        reasons.append("SHADOW_ACTIVATION_MUST_NOT_GRANT_GLOBAL_FRESH_REALITY")
    if receipt.get("acceptance_credit_authority") is not False:
        reasons.append("SHADOW_ACTIVATION_MUST_NOT_GRANT_ACCEPTANCE_CREDIT")
    if receipt.get("promotion_authority") is not False:
        reasons.append("SHADOW_ACTIVATION_MUST_NOT_GRANT_PROMOTION")
    return not reasons, reasons


def verify_shadow_lease(
    lease: Mapping[str, Any],
    isolation_receipt: Mapping[str, Any],
    benchmark_adapter: Mapping[str, Any],
    activation_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []

    iso = verify_generic_isolation(isolation_receipt)
    if iso.get("generic_isolation_kernel_pass") is not True:
        reasons.append("GENERIC_PRECOMMIT_ISOLATION_NOT_PROVED")

    adapter = verify_benchmark_thin_adapter(benchmark_adapter)
    if adapter.get("benchmark_thin_adapter_pass") is not True:
        reasons.append("BENCHMARK_THIN_ADAPTER_NOT_PROVED")

    activation_ok, activation_reasons = verify_activation_receipt(activation_receipt)
    if not activation_ok:
        reasons.extend(activation_reasons)

    if not _norm(lease.get("lease_id")):
        reasons.append("LEASE_ID_MISSING")
    if not _norm(lease.get("benchmark_id")):
        reasons.append("BENCHMARK_ID_MISSING")
    if not _norm(lease.get("one_use_nonce")):
        reasons.append("ONE_USE_NONCE_MISSING")

    for field in _HASH_FIELDS:
        if not _sha256(lease.get(field)):
            reasons.append(f"INVALID_OR_MISSING_{field.upper()}")

    for field in _REQUIRED_TRUE:
        if lease.get(field) is not True:
            reasons.append(f"LEASE_GATE_FALSE:{field}")

    if lease.get("lease_consumed") is not False:
        reasons.append("LEASE_ALREADY_CONSUMED_OR_STATE_UNKNOWN")

    expected = lease_digest(lease)
    if _norm(lease.get("lease_digest_sha256")).lower() != expected:
        reasons.append("LEASE_DIGEST_MISMATCH")

    # Pre-fixed-point collection is allowed only because result visibility is
    # cryptographically/procedurally separated from the frozen candidate.
    if lease.get("result_visible_to_candidate") is not False:
        reasons.append("RESULT_MUST_NOT_BE_VISIBLE_TO_CANDIDATE")
    if lease.get("result_visible_to_planner") is not False:
        reasons.append("RESULT_MUST_NOT_BE_VISIBLE_TO_PLANNER")
    if lease.get("result_visible_to_zero_reality_work") is not False:
        reasons.append("RESULT_MUST_NOT_BE_VISIBLE_TO_ZERO_REALITY_WORK")

    ready = not reasons
    return {
        "schema": SCHEMA,
        "shadow_collection_ready": ready,
        "reasons": sorted(set(reasons)),
        "generic_isolation_pass": iso.get("generic_isolation_kernel_pass") is True,
        "benchmark_thin_adapter_pass": adapter.get("benchmark_thin_adapter_pass") is True,
        "separate_shadow_activation_pass": activation_ok,
        "shadow_collection_authority": ready,
        "global_fresh_reality_authority": False,
        "acceptance_credit_authorized": False,
        "promotion_authority": False,
        "execution_authority_beyond_shadow_collection": False,
        "result_visibility": "WRITE_ONLY_ESCROW" if ready else "BLOCKED",
        "requires_post_fixed_point_predicate_specific_reduction": True,
    }


def classify_shadow_result_after_fixed_point(
    *,
    zero_reality_fixed_point_reached: bool,
    shadow_lease_passed: bool,
    route_still_required: bool,
    output_bound_to_lease: bool,
    independent_result_verification_pass: bool,
) -> dict[str, Any]:
    eligible = bool(
        zero_reality_fixed_point_reached
        and shadow_lease_passed
        and route_still_required
        and output_bound_to_lease
        and independent_result_verification_pass
    )
    return {
        "schema": SCHEMA,
        "eligible_for_predicate_specific_reduction": eligible,
        "discard_as_dominated_or_stale": bool(
            zero_reality_fixed_point_reached
            and shadow_lease_passed
            and not route_still_required
        ),
        "acceptance_credit_authorized": False,
        "promotion_authority": False,
        "global_fresh_reality_authority": False,
        "separate_predicate_specific_activation_required": True,
    }
