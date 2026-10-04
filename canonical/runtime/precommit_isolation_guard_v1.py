#!/usr/bin/env python3
"""Mechanical guard for precommit-isolated evaluation receipts.

Passing this guard is NECESSARY, never sufficient, for relaxing any existing
fresh-reality gate. Benchmark-specific semantic proof and independent
activation remain mandatory.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SCHEMA = "PROJECT_BRAIN_PRECOMMIT_ISOLATION_GUARD_V1"
HASH_FIELDS = (
    "candidate_sha256",
    "harness_sha256",
    "scorer_sha256",
    "environment_sha256",
    "policy_sha256",
)


def _is_sha256(x: Any) -> bool:
    s = str(x or "")
    return len(s) == 64 and all(c in "0123456789abcdefABCDEF" for c in s)


def commitment_digest(receipt: Mapping[str, Any]) -> str:
    obj = {k: str(receipt.get(k, "")).lower() for k in HASH_FIELDS}
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def verify_precommit_isolation_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    for field in HASH_FIELDS:
        if not _is_sha256(receipt.get(field)):
            reasons.append(f"INVALID_{field.upper()}")

    declared = str(receipt.get("commitment_sha256", "")).lower()
    if declared != commitment_digest(receipt):
        reasons.append("COMMITMENT_DIGEST_MISMATCH")

    if receipt.get("commitment_recorded_before_case_reveal") is not True:
        reasons.append("COMMITMENT_NOT_PROVED_BEFORE_CASE_REVEAL")
    if receipt.get("independent_executor") is not True:
        reasons.append("INDEPENDENT_EXECUTOR_NOT_PROVED")
    if receipt.get("candidate_immutable_during_execution") is not True:
        reasons.append("CANDIDATE_IMMUTABILITY_NOT_PROVED")
    if receipt.get("no_adaptive_state_channel") is not True:
        reasons.append("ADAPTIVE_STATE_CHANNEL_NOT_EXCLUDED")
    if receipt.get("outputs_bound_to_commitment") is not True:
        reasons.append("OUTPUTS_NOT_BOUND_TO_COMMITMENT")
    if receipt.get("benchmark_protocol_comparability_verified") is not True:
        reasons.append("BENCHMARK_PROTOCOL_COMPARABILITY_NOT_VERIFIED")

    observed = str(receipt.get("observed_candidate_sha256", "")).lower()
    committed = str(receipt.get("candidate_sha256", "")).lower()
    if observed != committed:
        reasons.append("EXECUTED_CANDIDATE_DIFFERS_FROM_COMMITTED_CANDIDATE")

    passed = not reasons
    return {
        "schema": SCHEMA,
        "mechanical_isolation_gate_pass": passed,
        "reasons": reasons,
        "fresh_reality_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "requires_benchmark_specific_semantic_proof": True,
        "requires_independent_activation": True,
    }
