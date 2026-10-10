"""Independent semantic verifier for professional whole-leaf scope certificates.

This checker validates only scope-cover authority. It requires a separately
verified whole-leaf domain-equivalence receipt and an exact claim-bound universal
scope certificate. It never grants leaf property truth or downstream authority.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical.runtime.universal_scope_closure_compiler_v1 import (
    UNIVERSAL,
    evaluate as evaluate_scope,
)

SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_CERTIFICATE_SEMANTIC_V1"
CLAIM_SCOPE_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_CLAIM_SCOPE_V1"
CLAIM_VERIFY_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_CLAIM_SCOPE_VERIFY_V1"
CERT_SCHEMA = "PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_CERTIFICATE_V2"


def _fail(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "whole_leaf_scope_complete": False,
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


def evaluate(
    claim_scope: Mapping[str, Any],
    claim_verification: Mapping[str, Any],
    certificate: Mapping[str, Any],
    *,
    claim_scope_blob: str,
    claim_verification_blob: str,
    claim_verification_path: str,
) -> dict[str, Any]:
    if not all(isinstance(x, Mapping) for x in (claim_scope, claim_verification, certificate)):
        return _fail("INPUT_NOT_MAPPING")
    if claim_scope.get("schema") != CLAIM_SCOPE_SCHEMA:
        return _fail("CLAIM_SCOPE_SCHEMA_INVALID")
    if claim_verification.get("schema") != CLAIM_VERIFY_SCHEMA:
        return _fail("CLAIM_VERIFICATION_SCHEMA_INVALID")
    if not str(claim_verification.get("status") or "").startswith("PASS__"):
        return _fail("CLAIM_VERIFICATION_NOT_PASS")
    if claim_verification.get("whole_leaf_domain_equivalence_proved") is not True:
        return _fail("WHOLE_LEAF_DOMAIN_EQUIVALENCE_REQUIRED")

    claim = claim_scope.get("claim")
    if not isinstance(claim, Mapping):
        return _fail("CLAIM_REQUIRED")
    claim_id = claim.get("claim_id")
    leaf_id = claim_scope.get("leaf_id")
    if not isinstance(claim_id, str) or len(claim_id) != 64:
        return _fail("CLAIM_ID_INVALID")
    if not isinstance(leaf_id, str) or not leaf_id:
        return _fail("LEAF_ID_INVALID")
    if claim_verification.get("leaf_id") != leaf_id:
        return _fail("CLAIM_VERIFICATION_LEAF_MISMATCH")
    if claim_verification.get("claim_id") != claim_id:
        return _fail("CLAIM_VERIFICATION_CLAIM_MISMATCH")
    if claim_verification.get("claim_scope_git_blob_sha") != claim_scope_blob:
        return _fail("CLAIM_VERIFICATION_SCOPE_BLOB_MISMATCH")

    if certificate.get("schema") != CERT_SCHEMA:
        return _fail("CERTIFICATE_SCHEMA_INVALID")
    if certificate.get("leaf_id") != leaf_id or certificate.get("claim_id") != claim_id:
        return _fail("CERTIFICATE_IDENTITY_MISMATCH")
    if certificate.get("claim_scope_git_blob_sha") != claim_scope_blob:
        return _fail("CERTIFICATE_SCOPE_BLOB_MISMATCH")

    expected_evidence = {
        "path": claim_verification_path,
        "git_blob_sha": claim_verification_blob,
    }
    refs = certificate.get("evidence_refs")
    if not isinstance(refs, list) or expected_evidence not in refs:
        return _fail("CLAIM_VERIFICATION_EVIDENCE_REF_REQUIRED")

    for field in (
        "semantic_truth_authority", "execution_authority", "quality_authority",
        "acceptance_authority", "promotion_authority", "terminal_authority",
    ):
        if certificate.get(field) is not False:
            return _fail("CERTIFICATE_AUTHORITY_OVERCLAIM:" + field)
    if certificate.get("terminal_credit_delta") != 0:
        return _fail("CERTIFICATE_TERMINAL_CREDIT_FORBIDDEN")

    scope_certificate = certificate.get("scope_certificate")
    if not isinstance(scope_certificate, Mapping):
        return _fail("SCOPE_CERTIFICATE_REQUIRED")
    expected_target = "scope://professional-quality/whole-leaf/" + claim_id
    if scope_certificate.get("target_scope_id") != expected_target:
        return _fail("SCOPE_TARGET_MISMATCH")
    if scope_certificate.get("claim_id") != claim_id:
        return _fail("SCOPE_CLAIM_ID_MISMATCH")
    if scope_certificate.get("basis") != UNIVERSAL:
        return _fail("UNIVERSAL_FORMAL_SCOPE_PROOF_REQUIRED")
    expected_premise = "claim-verification:" + claim_verification_blob
    if scope_certificate.get("premise_set_id") != expected_premise:
        return _fail("PREMISE_SET_NOT_BOUND_TO_CLAIM_VERIFICATION")

    scope_out = evaluate_scope(scope_certificate)
    if scope_out.get("scope_complete") is not True:
        return _fail("UNIVERSAL_SCOPE_COMPILER_REJECTED", scope_verdict=scope_out)

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__CLAIM_BOUND_UNIVERSAL_WHOLE_LEAF_SCOPE_COVER",
        "leaf_id": leaf_id,
        "claim_id": claim_id,
        "whole_leaf_scope_complete": True,
        "scope_basis": UNIVERSAL,
        "claim_verification_git_blob_sha": claim_verification_blob,
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
