"""Deterministic one-use execution lease for Unknown-Domain direct production.

The lease identity is intentionally nonce-free.  A mutable nonce, timestamp, or
run label would let the same frozen execution tuple mint a second claim key,
which would defeat the one-use production invariant.

The digest binds only the exact qualified/activated execution tuple, its fixed
production budget, and the fixed claim backend namespace.  Therefore one exact
tuple has exactly one admissible claim ref.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

TARGET = "UNKNOWN_DOMAIN_UNCOVERED_TRANSFER_AUDIT"
AUTHORIZED_LEAVES = (
    "CALIBRATED_UNKNOWN_OR_ABSTENTION_ON_NONIDENTIFIABLE_OR_UNDERSPECIFIED_VARIANTS",
    "CROSS_DOMAIN_TRANSFER_OUTSIDE_MYSTERYMECHANISM_TASK_STRUCTURE",
)
CLAIM_REPOSITORY = "moxnixmdj/verification-capsule-runner"
CLAIM_NAMESPACE = "refs/heads/unknown-domain-direct-claims/"
ACTIVATION_BLOB = "337bb7ee777e8b0f7f6340f395ca6c50e466594c"
QUALIFICATION_RECEIPT_BLOB = "36452412fb60ce38405f139111eba98b5cebc040"
PRODUCTION_PRECOMMIT_BLOB = "ddf55f3e54ef6af89a95395075441742cb124258"
EXACT_SUBJECTS = {
    "candidate_v1": "a2a77269a8175ce315b466035049da0f761b8734",
    "candidate_v2": "4470716f95a559a700e461262df909ae19a41651",
    "generator_v1": "f974a4594c78e74693c7ba5a19f131dfa481b937",
    "generator_v2": "d077028c9bde534dc4bc6eb0d1f776341f9d59f8",
    "hidden_scorer": "e8cf5d1b5d311644725a751c15e6235958fb587d",
    "execution_harness": "04fe06f4eed081c4cb6197b12f2d92bd396aeafd",
}
HEX = set("0123456789abcdef")


class UnknownDomainExecutionLeaseError(ValueError):
    pass


def _sha40(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 40 and set(value.lower()) <= HEX


def canonical_lease_payload() -> dict[str, Any]:
    return {
        "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_V1",
        "target_predicate": TARGET,
        "authorized_leaves": list(AUTHORIZED_LEAVES),
        "activation_git_blob_sha": ACTIVATION_BLOB,
        "qualification_receipt_git_blob_sha": QUALIFICATION_RECEIPT_BLOB,
        "production_precommit_git_blob_sha": PRODUCTION_PRECOMMIT_BLOB,
        "exact_execution_subject": dict(sorted(EXACT_SUBJECTS.items())),
        "claim_repository": CLAIM_REPOSITORY,
        "claim_namespace": CLAIM_NAMESPACE,
        "production_budget": {
            "production_populations_allowed": 1,
            "production_cases_allowed": 27,
            "max_transfer_probes_per_case": 2,
            "replay_allowed": False,
            "replacement_allowed": False,
            "post_result_tuning_allowed": False,
        },
        "resource_boundary": {
            "persistent_learned_bytes": 0,
            "external_frontier_model_calls": 0,
            "external_learned_capability_calls": 0,
            "incremental_spend_usd": 0,
        },
        "global_fresh_reality": False,
    }


def lease_digest_sha256(payload: Mapping[str, Any] | None = None) -> str:
    obj = canonical_lease_payload() if payload is None else dict(payload)
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def expected_claim_ref(payload: Mapping[str, Any] | None = None) -> str:
    return CLAIM_NAMESPACE + lease_digest_sha256(payload)


def verify_point_of_use_state(state: Mapping[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if not isinstance(state, Mapping):
        reasons.append("STATE_INVALID")
        state = {}

    if state.get("target_predicate") != TARGET:
        reasons.append("TARGET_PREDICATE_MISMATCH")
    leaves = state.get("authorized_leaves")
    if not isinstance(leaves, list) or tuple(sorted(map(str, leaves))) != AUTHORIZED_LEAVES:
        reasons.append("AUTHORIZED_LEAF_SET_MISMATCH")
    if state.get("activation_git_blob_sha") != ACTIVATION_BLOB:
        reasons.append("ACTIVATION_BLOB_MISMATCH")
    if state.get("qualification_receipt_git_blob_sha") != QUALIFICATION_RECEIPT_BLOB:
        reasons.append("QUALIFICATION_RECEIPT_BLOB_MISMATCH")
    if state.get("production_precommit_git_blob_sha") != PRODUCTION_PRECOMMIT_BLOB:
        reasons.append("PRODUCTION_PRECOMMIT_BLOB_MISMATCH")

    subjects = state.get("exact_execution_subject")
    if not isinstance(subjects, Mapping) or dict(subjects) != EXACT_SUBJECTS:
        reasons.append("EXACT_EXECUTION_SUBJECT_MISMATCH")
    else:
        for value in subjects.values():
            if not _sha40(value):
                reasons.append("EXACT_EXECUTION_SUBJECT_SHA_INVALID")

    required_true = (
        "qualification_independent_pass",
        "activation_independent_pass",
        "exact_subject_blobs_rechecked",
    )
    for field in required_true:
        if state.get(field) is not True:
            reasons.append("REQUIRED_TRUE_GATE_FAILED:" + field)

    exact_zero = (
        "production_cases_consumed",
        "production_populations_generated",
        "persistent_learned_bytes",
        "external_frontier_model_calls",
        "external_learned_capability_calls",
        "incremental_spend_usd",
    )
    for field in exact_zero:
        if state.get(field) != 0:
            reasons.append("REQUIRED_ZERO_GATE_FAILED:" + field)

    required_false = (
        "production_beacon_generated",
        "candidate_mutated_after_qualification",
        "global_fresh_reality",
        "execution_started",
    )
    for field in required_false:
        if state.get(field) is not False:
            reasons.append("REQUIRED_FALSE_GATE_FAILED:" + field)

    passed = not reasons
    payload = canonical_lease_payload()
    digest = lease_digest_sha256(payload)
    return {
        "schema": "PROJECT_BRAIN_UNKNOWN_DOMAIN_DIRECT_EXECUTION_LEASE_PREFLIGHT_V1",
        "ready_for_atomic_claim_only": passed,
        "reasons": sorted(set(reasons)),
        "lease": payload if passed else None,
        "lease_digest_sha256": digest if passed else None,
        "claim_ref": CLAIM_NAMESPACE + digest if passed else None,
        "claim_repository": CLAIM_REPOSITORY if passed else None,
        "claim_uniqueness_source": "ATOMIC_FIRST_CREATE_RESPONSE",
        "claim_ref_absence_precheck_required": False,
        "case_generation_authority": False,
        "execution_authority": False,
        "promotion_authority": False,
        "acceptance_credit": False,
    }
