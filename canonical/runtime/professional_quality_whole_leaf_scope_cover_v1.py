"""Claim-bound whole-leaf scope-cover verifier V1.

Composes an independently verified whole-leaf domain-equivalence claim with the
existing universal scope-closure compiler. It proves only scope completeness for
that exact claim. Property truth and all quality/acceptance authority remain
separate and false.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.universal_scope_closure_compiler_v1 import (
    UNIVERSAL,
    evaluate as evaluate_scope,
)

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_COVER_V1"
CLAIM_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_CLAIM_SCOPE_V1"
CLAIM_VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_CLAIM_SCOPE_VERIFY_V1"
CERT_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_CERTIFICATE_V2"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "scope_complete": False,
        "leaf_property_truth_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
        **extra,
    }


def expected_scope_certificate(claim_id: str, claim_verify_blob: str) -> dict[str, Any]:
    if not isinstance(claim_id, str) or len(claim_id) != 64:
        raise ValueError("CLAIM_ID_INVALID")
    if not isinstance(claim_verify_blob, str) or len(claim_verify_blob) != 40:
        raise ValueError("CLAIM_VERIFY_BLOB_INVALID")
    return {
        "id": "PQ_WHOLE_LEAF_SCOPE::" + claim_id,
        "target_scope_id": "scope://professional-quality/whole-leaf/" + claim_id,
        "claim_id": claim_id,
        "basis": UNIVERSAL,
        "verified": True,
        "independent": True,
        "scope_relation": "EXACT",
        "formal_completeness": True,
        "all_admissible_target_inputs_proved": True,
        "premise_set_id": "claim-domain-equivalence:" + claim_verify_blob,
    }


def evaluate(
    *,
    claim_scope: Mapping[str, Any],
    claim_verification: Mapping[str, Any],
    certificate: Mapping[str, Any],
    claim_scope_blob: str,
    claim_verification_blob: str,
) -> dict[str, Any]:
    if not all(isinstance(x, Mapping) for x in (claim_scope, claim_verification, certificate)):
        return _fail("INPUT_NOT_MAPPING")
    if claim_scope.get("schema") != CLAIM_SCOPE_SCHEMA:
        return _fail("CLAIM_SCOPE_SCHEMA_INVALID")
    if claim_verification.get("schema") != CLAIM_VERIFY_SCHEMA:
        return _fail("CLAIM_VERIFY_SCHEMA_INVALID")
    if certificate.get("schema") != CERT_SCHEMA:
        return _fail("CERT_SCHEMA_INVALID")

    leaf_id = claim_scope.get("leaf_id")
    claim = claim_scope.get("claim")
    if not isinstance(leaf_id, str) or not leaf_id:
        return _fail("LEAF_ID_REQUIRED")
    if not isinstance(claim, Mapping):
        return _fail("CLAIM_REQUIRED")
    claim_id = claim.get("claim_id")
    if not isinstance(claim_id, str) or len(claim_id) != 64:
        return _fail("CLAIM_ID_INVALID")

    if claim_verification.get("status", "").startswith("PASS__") is not True:
        return _fail("CLAIM_VERIFY_NOT_PASS")
    if claim_verification.get("leaf_id") != leaf_id or claim_verification.get("claim_id") != claim_id:
        return _fail("CLAIM_VERIFY_IDENTITY_MISMATCH")
    if claim_verification.get("claim_scope_git_blob_sha") != claim_scope_blob:
        return _fail("CLAIM_VERIFY_SCOPE_BLOB_MISMATCH")
    if claim_verification.get("whole_leaf_domain_equivalence_proved") is not True:
        return _fail("WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED")
    replay = claim_verification.get("independent_replay")
    if not isinstance(replay, Mapping) or replay.get("pass") is not True:
        return _fail("INDEPENDENT_DOMAIN_REPLAY_REQUIRED")

    if certificate.get("leaf_id") != leaf_id or certificate.get("claim_id") != claim_id:
        return _fail("CERT_IDENTITY_MISMATCH")
    if certificate.get("claim_scope_git_blob_sha") != claim_scope_blob:
        return _fail("CERT_CLAIM_SCOPE_BLOB_MISMATCH")
    if certificate.get("claim_verification_git_blob_sha") != claim_verification_blob:
        return _fail("CERT_CLAIM_VERIFY_BLOB_MISMATCH")

    for field in (
        "semantic_truth_authority", "execution_authority", "quality_authority",
        "acceptance_authority", "promotion_authority", "terminal_authority",
    ):
        if certificate.get(field) is not False:
            return _fail("CERT_SELF_AUTHORITY_FORBIDDEN:" + field)
    if certificate.get("terminal_credit_delta") != 0:
        return _fail("CERT_TERMINAL_CREDIT_FORBIDDEN")

    expected = expected_scope_certificate(claim_id, claim_verification_blob)
    observed = certificate.get("scope_certificate")
    if observed != expected:
        return _fail("SCOPE_CERTIFICATE_NOT_EXACT")

    scope = evaluate_scope(observed)
    if scope.get("scope_complete") is not True:
        return _fail("UNIVERSAL_SCOPE_COMPILER_REJECTED", scope_verdict=scope)
    if scope.get("basis") != UNIVERSAL:
        return _fail("SCOPE_BASIS_INVALID")

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__CLAIM_BOUND_UNIVERSAL_WHOLE_LEAF_SCOPE_COVER__PROPERTY_TRUTH_SEPARATE",
        "leaf_id": leaf_id,
        "claim_id": claim_id,
        "claim_scope_git_blob_sha": claim_scope_blob,
        "claim_verification_git_blob_sha": claim_verification_blob,
        "scope_complete": True,
        "verified_basis": UNIVERSAL,
        "proof_basis": "INDEPENDENT_WHOLE_DOMAIN_EQUIVALENCE_PLUS_EXACT_UNIVERSAL_SCOPE_COMPILER",
        "leaf_property_truth_authority": False,
        "semantic_truth_authority": False,
        "execution_authority": False,
        "quality_authority": False,
        "acceptance_authority": False,
        "promotion_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "incremental_spend_usd": 0,
    }
