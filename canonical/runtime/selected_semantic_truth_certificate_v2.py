"""Selected policy-changing semantic truth certificate v2.

V2 preserves the V1 source-aligned boolean condition path and extends the
trusted checker with the already-owned controlled deontic source fragment.

A DEONTIC_RULE can certify only the positive proposition that the exact
source-bound required/prohibited rule is present with the checked relation,
subject/action spans, and optional checked scope. Failure to prove that exact
rule remains UNKNOWN. V2 never infers a negative rule from absence.

No source authorization, policy adequacy, D_B/U, or terminal authority is
minted by this adapter.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_deontic_extension_v1 import verify_proof

SCHEMA = "PROJECT_BRAIN_SELECTED_SEMANTIC_TRUTH_CERTIFICATE_V2"


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


def _checked_predicate_id(
    row: Mapping[str, Any],
    source_id: str,
    source_sha256: str,
) -> str | None:
    kind = row.get("kind")

    if kind in {
        "CERTIFIED_DEFINED_TERM_TYPED_CONDITION",
        "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
    }:
        atom = row.get("condition_atom_id")
        if not isinstance(atom, str) or not atom:
            return None
        fields = ("defined_term", "field_name", "field_type", "operator", "literal")
        if any(not isinstance(row.get(k), str) or not row[k] for k in fields):
            return None
        if "policy_source_id" in row and row.get("policy_source_id") != source_id:
            return None
        descriptor = {
            "source_id": source_id,
            "source_sha256": source_sha256,
            "kind": kind,
            **{k: row[k] for k in fields},
        }
        material = json.dumps(
            descriptor,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return "source-condition-sha256:" + hashlib.sha256(material).hexdigest()

    if kind == "DEONTIC_RULE":
        fields = (
            "rule_id",
            "relation",
            "subject_text_sha256",
            "action_text_sha256",
        )
        if any(not isinstance(row.get(k), str) or not row[k] for k in fields):
            return None
        relation = row.get("relation")
        if relation not in {"REQUIRED", "PROHIBITED"}:
            return None
        constraint = row.get("constraint")
        if (
            not isinstance(constraint, Mapping)
            or constraint.get("op") != "ATOM"
            or not isinstance(constraint.get("id"), str)
            or not constraint["id"]
        ):
            return None
        descriptor = {
            "source_id": source_id,
            "source_sha256": source_sha256,
            "kind": kind,
            **{k: row[k] for k in fields},
            "scope_id": row.get("scope_id"),
            "scope_relation": row.get("scope_relation"),
            "condition_span": row.get("condition_span"),
            "verified_constraint_atom_id": constraint["id"],
        }
        material = json.dumps(
            descriptor,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return "source-deontic-rule-sha256:" + hashlib.sha256(material).hexdigest()

    return None


def _unknown(
    *,
    status: str,
    reason: str,
    predicate_id: str,
    target_claim_id: str,
    source_id: str,
    source_sha256: str,
    **detail: Any,
) -> dict[str, Any]:
    out = {
        "schema": SCHEMA,
        "pass": False,
        "status": status,
        "reason": reason,
        "predicate_id": None,
        "requested_predicate_id": predicate_id,
        "requested_predicate_id_authority": False,
        "target_claim_id": target_claim_id,
        "predicate_truth": "UNKNOWN",
        "source_id": source_id,
        "source_sha256": source_sha256,
        "truthful_precommitment_observation": False,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_empty_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
    }
    out.update(detail)
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

    source_sha256 = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
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
        row
        for row in (proof.get("accepted_claims") or [])
        if isinstance(row, Mapping) and row.get("claim_id") == target_claim_id
    ]
    if len(accepted) != 1:
        return _unknown(
            status="UNKNOWN__SELECTED_PREDICATE_NOT_PROVED",
            reason="TARGET_CLAIM_NOT_UNIQUELY_ACCEPTED",
            predicate_id=predicate_id,
            target_claim_id=target_claim_id,
            source_id=source_id,
            source_sha256=source_sha256,
            source_proof=proof,
        )

    row = accepted[0]
    checked_predicate_id = _checked_predicate_id(row, source_id, source_sha256)
    if checked_predicate_id is None:
        return _unknown(
            status="UNKNOWN__CHECKED_PREDICATE_ID_UNAVAILABLE",
            reason="CHECKER_ACCEPTED_CLAIM_WITHOUT_CANONICAL_SOURCE_PREDICATE_IDENTITY",
            predicate_id=predicate_id,
            target_claim_id=target_claim_id,
            source_id=source_id,
            source_sha256=source_sha256,
            accepted_claim=dict(row),
            source_proof=proof,
        )

    kind = row.get("kind")
    if kind == "DEONTIC_RULE":
        constraint = row["constraint"]
        holds = True
        verified_atom_id = constraint["id"]
        truth_basis = "EXACT_SOURCE_BOUND_DEONTIC_RULE_PRESENCE"
    else:
        holds = row.get("condition_holds")
        if not isinstance(holds, bool):
            return _unknown(
                status="UNKNOWN__ACCEPTED_CLAIM_NOT_BOOLEAN",
                reason="TARGET_CLAIM_HAS_NO_VERIFIED_BOOLEAN_TRUTH_VALUE",
                predicate_id=predicate_id,
                target_claim_id=target_claim_id,
                source_id=source_id,
                source_sha256=source_sha256,
                accepted_claim=dict(row),
                source_proof=proof,
            )
        verified_atom_id = row.get("condition_atom_id")
        if not isinstance(verified_atom_id, str) or not verified_atom_id:
            return _unknown(
                status="UNKNOWN__VERIFIED_ATOM_ID_UNAVAILABLE",
                reason="BOOLEAN_CLAIM_HAS_NO_VERIFIED_ATOM_ID",
                predicate_id=predicate_id,
                target_claim_id=target_claim_id,
                source_id=source_id,
                source_sha256=source_sha256,
                accepted_claim=dict(row),
                source_proof=proof,
            )
        truth_basis = "VERIFIED_SOURCE_ALIGNED_BOOLEAN_CONDITION"

    return {
        "schema": SCHEMA,
        "pass": True,
        "status": (
            "PASS__SELECTED_SEMANTIC_PREDICATE_PROVED_TRUE"
            if holds
            else "PASS__SELECTED_SEMANTIC_PREDICATE_PROVED_FALSE"
        ),
        "predicate_id": checked_predicate_id,
        "requested_predicate_id": predicate_id,
        "requested_predicate_id_authority": False,
        "target_claim_id": target_claim_id,
        "predicate_truth": "TRUE" if holds else "FALSE",
        "truthful_precommitment_observation": True,
        "truth_basis": truth_basis,
        "source_id": source_id,
        "source_sha256": source_sha256,
        "accepted_claim": dict(row),
        "verified_condition_atom_id": verified_atom_id,
        "source_proof": proof,
        "policy_adequacy_authority": False,
        "db_admission_authority": False,
        "u_empty_authority": False,
        "terminal_authority": False,
        "terminal_credit_delta": 0,
        "boundary": (
            "SEMANTIC_TRUTH_ONLY__SOURCE_AUTHORIZATION_AND_POLICY_ADEQUACY_REMAIN_SEPARATE__"
            "CALLER_PREDICATE_LABEL_IS_NONAUTHORITATIVE__"
            "DEONTIC_RULES_CERTIFY_POSITIVE_EXACT_RULE_PRESENCE_ONLY__"
            "ABSENCE_OR_MISMATCH_REMAINS_UNKNOWN__"
            "UNKNOWN_IS_REQUIRED_OUTSIDE_THE_CHECKED_SOURCE_ALIGNED_PROOF_FRAGMENT"
        ),
    }


def run(args: Mapping[str, Any] | None = None, root: Any = None) -> dict[str, Any]:
    del root
    return evaluate(args or {})
