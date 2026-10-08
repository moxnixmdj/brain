"""Selected policy-changing semantic truth certificate v1.

Thin fail-closed adapter over the already-owned source-aligned semantic proof
checker. It turns one selected boolean semantic predicate into a pre-commitment
TRUE/FALSE/UNKNOWN observation suitable for the existing Tournament/minimax
information machinery.

It does not prove policy adequacy, target acceptance, U-empty, or terminality.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v6 import verify_proof

SCHEMA = "PROJECT_BRAIN_SELECTED_SEMANTIC_TRUTH_CERTIFICATE_V1"


def _fail(reason: str, **detail: Any) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": "FAIL_CLOSED",
        "reason": reason,
        "predicate_truth": "UNKNOWN",
        "truthful_precommitment_observation": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_empty_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    if detail:
        out["detail"] = detail
    return out


def evaluate(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    predicate_id = payload.get("predicate_id")
    target_claim_id = payload.get("target_claim_id")
    source_text = payload.get("source_text")
    source_id = payload.get("source_id")
    claims = payload.get("claims")

    if not isinstance(predicate_id, str) or not predicate_id.strip():
        return _fail("PREDICATE_ID_REQUIRED")
    if not isinstance(target_claim_id, str) or not target_claim_id.strip():
        return _fail("TARGET_CLAIM_ID_REQUIRED")
    if not isinstance(source_text, str) or not source_text:
        return _fail("SOURCE_TEXT_REQUIRED")
    if not isinstance(source_id, str) or not source_id.strip():
        return _fail("SOURCE_ID_REQUIRED")
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return _fail("CLAIMS_SEQUENCE_REQUIRED")

    proof = verify_proof(
        source_text,
        source_id=source_id,
        claims=claims,
        typed_context=payload.get("typed_context"),
        expected_typed_context_sha256=payload.get("expected_typed_context_sha256"),
        fact_source=payload.get("fact_source"),
        fact_source_id=payload.get("fact_source_id"),
    )

    if proof.get("status") == "FAIL_CLOSED":
        return _fail("SOURCE_PROOF_FAIL_CLOSED", source_proof=proof)

    accepted = [
        row for row in (proof.get("accepted_claims") or [])
        if isinstance(row, Mapping) and row.get("claim_id") == target_claim_id
    ]
    if len(accepted) != 1:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNKNOWN__SELECTED_PREDICATE_NOT_PROVED",
            "reason": "TARGET_CLAIM_NOT_UNIQUELY_ACCEPTED",
            "predicate_id": predicate_id,
            "target_claim_id": target_claim_id,
            "predicate_truth": "UNKNOWN",
            "source_id": source_id,
            "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "source_proof": proof,
            "truthful_precommitment_observation": False,
            "policy_adequacy_authority": False,
            "db_admission_authority": False,
            "u_empty_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    row = accepted[0]
    holds = row.get("condition_holds")
    if not isinstance(holds, bool):
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNKNOWN__ACCEPTED_CLAIM_NOT_BOOLEAN",
            "reason": "TARGET_CLAIM_HAS_NO_VERIFIED_BOOLEAN_TRUTH_VALUE",
            "predicate_id": predicate_id,
            "target_claim_id": target_claim_id,
            "predicate_truth": "UNKNOWN",
            "accepted_claim": dict(row),
            "source_id": source_id,
            "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "truthful_precommitment_observation": False,
            "policy_adequacy_authority": False,
            "db_admission_authority": False,
            "u_empty_authority": False,
            "terminal_authority": False,
            "terminal_credit_delta": 0,
        }

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": "PASS__SELECTED_SEMANTIC_PREDICATE_PROVED_TRUE" if holds else "PASS__SELECTED_SEMANTIC_PREDICATE_PROVED_FALSE",
        "predicate_id": predicate_id,
        "target_claim_id": target_claim_id,
        "predicate_truth": "TRUE" if holds else "FALSE",
        "truthful_precommitment_observation": True,
        "source_id": source_id,
        "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "accepted_claim": dict(row),
        "source_proof": proof,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_empty_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "SEMANTIC_TRUTH_ONLY__SOURCE_AUTHORIZATION_AND_POLICY_ADEQUACY_REMAIN_SEPARATE__"
            "UNKNOWN_IS_REQUIRED_OUTSIDE_THE_CHECKED_SOURCE_ALIGNED_PROOF_FRAGMENT"
        ),
    }
