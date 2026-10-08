"""Selected policy-changing semantic truth certificate v1.

Thin fail-closed adapter over the already-owned source-aligned semantic proof
checker. It turns one selected boolean semantic predicate into a pre-commitment
TRUE/FALSE/UNKNOWN observation suitable for the existing Tournament/minimax
information machinery.

It does not prove policy adequacy, target acceptance, U-empty, or terminality.
The checker mints the authoritative predicate ID from the verified source
condition. Caller-supplied predicate labels are preserved only as unauthenticated
metadata and can never inherit semantic truth authority.
"""
from __future__ import annotations

import hashlib
import json
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


def _checked_predicate_id(row: Mapping[str, Any], source_id: str, source_sha256: str) -> str | None:
    """Stable semantic identity from checker-produced source condition, not caller labels.

    The typed-context digest and condition_atom_id vary per observed case, so
    neither can serve as a stable precommitment *predicate* identity.
    """
    if row.get("kind") not in {
        "CERTIFIED_DEFINED_TERM_TYPED_CONDITION",
        "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
    }:
        return None
    atom = row.get("condition_atom_id")
    if not isinstance(atom, str) or not atom:
        return None
    fields = ("defined_term", "field_name", "field_type", "operator", "literal")
    if any(not isinstance(row.get(k), str) or not row[k] for k in fields):
        return None
    # V6 raw-fact receipts carry this field; V5 typed receipts bind the
    # source through verify_proof(source_id=...) without repeating it in-row.
    if "policy_source_id" in row and row.get("policy_source_id") != source_id:
        return None
    descriptor = {"source_id": source_id, "source_sha256": source_sha256,
                  "kind": row["kind"], **{k: row[k] for k in fields}}
    material = json.dumps(descriptor, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8")
    return "source-condition-sha256:" + hashlib.sha256(material).hexdigest()

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
            "predicate_id": None,
            "requested_predicate_id": predicate_id,
            "requested_predicate_id_authority": False,
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
            "predicate_id": None,
            "requested_predicate_id": predicate_id,
            "requested_predicate_id_authority": False,
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

    source_sha256 = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    checked_predicate_id = _checked_predicate_id(row, source_id, source_sha256)
    if checked_predicate_id is None:
        return {
            "schema": SCHEMA,
            "pass": False,
            "status": "UNKNOWN__CHECKED_PREDICATE_ID_UNAVAILABLE",
            "reason": "CHECKER_ACCEPTED_BOOLEAN_WITHOUT_CANONICAL_SOURCE_CONDITION_IDENTITY",
            "predicate_truth": "UNKNOWN",
            "predicate_id": None,
            "requested_predicate_id": predicate_id,
            "requested_predicate_id_authority": False,
            "target_claim_id": target_claim_id,
            "source_id": source_id,
            "source_sha256": source_sha256,
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
        "predicate_id": checked_predicate_id,
        "requested_predicate_id": predicate_id,
        "requested_predicate_id_authority": False,
        "target_claim_id": target_claim_id,
        "predicate_truth": "TRUE" if holds else "FALSE",
        "truthful_precommitment_observation": True,
        "source_id": source_id,
        "source_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "accepted_claim": dict(row),
        "verified_condition_atom_id": row["condition_atom_id"],
        "source_proof": proof,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_empty_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "SEMANTIC_TRUTH_ONLY__SOURCE_AUTHORIZATION_AND_POLICY_ADEQUACY_REMAIN_SEPARATE__"
            "CALLER_PREDICATE_LABEL_IS_NONAUTHORITATIVE__"
            "UNKNOWN_IS_REQUIRED_OUTSIDE_THE_CHECKED_SOURCE_ALIGNED_PROOF_FRAGMENT"
        ),
    }
