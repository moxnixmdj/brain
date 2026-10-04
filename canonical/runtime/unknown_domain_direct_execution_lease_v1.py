"""Deterministic execution-lease compiler for Unknown-Domain direct production.

This closes a one-use ambiguity in the frozen production precommit: the claim
key is sha256(exact_execution_lease), but the exact lease object and byte
serialization were not frozen there. This module defines both deterministically.

It grants no execution, fresh-reality, promotion, or acceptance authority.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_V1"
TARGET="UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
CLAIM_PREFIX="refs/heads/unknown-domain-direct-claims/"
HEX=set("0123456789abcdef")

AUTHORIZED_LEAVES=[
    "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS",
    "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE",
]

BOUND_COMPONENTS={
    "canonical/governance/UNKNOWN_DOMAIN_DIRECT_PREDICATE_LOCAL_ACTIVATION_V1.json":"337bb7ee777e8b0f7f6340f395ca6c50e466594c",
    "canonical/verification/UNKNOWN_DOMAIN_V2_FINAL_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"93353244a5a0a6a7ef2e1e0a3a1bbedb63cef3ec",
    "canonical/governance/UNKNOWN_DOMAIN_DIRECT_PRODUCTION_PRECOMMIT_V1.json":"ddf55f3e54ef6af89a95395075441742cb124258",
    "canonical/verification/UNKNOWN_DOMAIN_DIRECT_CANDIDATE_V2_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json":"36452412fb60ce38405f139111eba98b5cebc040",
    "canonical/runtime/unknown_domain_direct_candidate_v1.py":"a2a77269a8175ce315b466035049da0f761b8734",
    "canonical/runtime/unknown_domain_direct_candidate_v2.py":"4470716f95a559a700e461262df909ae19a41651",
    "canonical/runtime/unknown_domain_direct_hidden_generator_v2.py":"d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "canonical/runtime/unknown_domain_direct_hidden_scorer_v1.py":"e8cf5d1b5d311644725a751c15e6235958fb587d",
    "canonical/runtime/unknown_domain_direct_execution_harness_v1.py":"04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}

PRODUCTION_BUDGET={
    "production_populations_allowed":1,
    "production_cases_allowed":27,
    "max_transfer_probes_per_case":2,
    "replay_allowed":False,
    "replacement_allowed":False,
    "post_result_tuning_allowed":False,
}

RESOURCE_BOUNDARY={
    "persistent_learned_bytes":0,
    "external_frontier_model_calls":0,
    "external_learned_capability_calls":0,
    "incremental_spend_usd":0,
}

EXPECTED_DIGEST_SHA256="244d3ff682959cc90dee51890784b4cb7ad6844946f0fe1bc8e7126c43b0bfdb"

def build_execution_lease() -> dict[str,Any]:
    return {
        "schema":SCHEMA,
        "target_predicate":TARGET,
        "authorized_leaves":list(AUTHORIZED_LEAVES),
        "production_budget":dict(PRODUCTION_BUDGET),
        "resource_boundary":dict(RESOURCE_BOUNDARY),
        "bound_components":dict(BOUND_COMPONENTS),
    }

def canonical_lease_bytes(lease: Mapping[str,Any]) -> bytes:
    if not isinstance(lease,Mapping):
        raise ValueError("LEASE_INVALID")
    return json.dumps(
        lease,
        sort_keys=True,
        separators=(",",":"),
        ensure_ascii=False,
    ).encode("utf-8")

def lease_digest_sha256(lease: Mapping[str,Any]) -> str:
    return hashlib.sha256(canonical_lease_bytes(lease)).hexdigest()

def expected_claim_ref(digest_sha256: str) -> str:
    if not isinstance(digest_sha256,str) or len(digest_sha256)!=64 or set(digest_sha256.lower()) > HEX:
        raise ValueError("INVALID_LEASE_DIGEST_SHA256")
    return CLAIM_PREFIX + digest_sha256.lower()

def verify_execution_lease(lease: Mapping[str,Any]) -> dict[str,Any]:
    reasons=[]
    if dict(lease) != build_execution_lease():
        reasons.append("LEASE_NOT_EXACT_FROZEN_OBJECT")
    digest=lease_digest_sha256(lease)
    if digest != EXPECTED_DIGEST_SHA256:
        reasons.append("LEASE_DIGEST_MISMATCH")
    return {
        "schema":"PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_VERIFICATION_V1",
        "pass":not reasons,
        "reasons":reasons,
        "lease_digest_sha256":digest,
        "claim_ref":expected_claim_ref(digest),
        "execution_authority":False,
        "fresh_reality_authority":False,
        "promotion_authority":False,
        "acceptance_credit":False,
    }
