"""Source-aligned semantic proof checker v5.

V5 preserves v4 and adds one explicit-definition denotation primitive:
a named source term may bind to a typed-context field only when the source itself
contains a deterministic explicit definition accepted by
explicit_definition_reference_graph and the definition RHS is exactly one field ID.

The checker recomputes the definition graph, UNLESS scope, field binding, typed
context digest, and exact boolean/decimal condition evaluation. No synonymy,
paraphrase, ontology inference, or world knowledge is trusted.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v4 import verify_proof as verify_v4
from canonical.runtime.certified_defined_term_typed_condition_v1 import (
    evaluate_defined_unless_condition,
)

SCHEMA = "BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V5"


def verify_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str, Any]],
    typed_context: Mapping[str, Any] | None = None,
    expected_typed_context_sha256: str | None = None,
) -> dict[str, Any]:
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["CLAIMS_INVALID"],
            "terminal_authority": False,
        }

    base_claims = []
    defined_claims = []
    seen: set[str] = set()
    errors: list[str] = []
    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            errors.append(f"CLAIM_NOT_OBJECT:{i}")
            continue
        cid = str(claim.get("claim_id") or "").strip()
        if not cid:
            errors.append(f"CLAIM_ID_MISSING:{i}")
            continue
        if cid in seen:
            errors.append(f"CLAIM_ID_DUPLICATE:{cid}")
            continue
        seen.add(cid)
        if claim.get("kind") == "CERTIFIED_DEFINED_TERM_TYPED_CONDITION":
            defined_claims.append(claim)
        else:
            base_claims.append(claim)

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "terminal_authority": False,
        }

    base = verify_v4(
        source_text,
        source_id=source_id,
        claims=base_claims,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
    )
    if base.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["V4_PRIMITIVE_CHECK_FAIL_CLOSED"],
            "base_proof": base,
            "terminal_authority": False,
        }

    accepted = list(base.get("accepted_claims") or [])
    rejected = list(base.get("rejected_claims") or [])
    proved = list(base.get("proved_constraints") or [])

    for claim in defined_claims:
        cid = str(claim["claim_id"])
        if not isinstance(typed_context, Mapping):
            rejected.append({"claim_id": cid, "reason": "TYPED_CONTEXT_REQUIRED"})
            continue
        if not isinstance(expected_typed_context_sha256, str):
            rejected.append({"claim_id": cid, "reason": "EXPECTED_TYPED_CONTEXT_SHA256_REQUIRED"})
            continue

        evaluation = evaluate_defined_unless_condition(
            source_text,
            source_id=source_id,
            typed_context=typed_context,
            expected_typed_context_sha256=expected_typed_context_sha256,
        )
        if evaluation.get("status") not in {"PROVED_TRUE", "PROVED_FALSE"}:
            rejected.append({
                "claim_id": cid,
                "reason": "DEFINED_TERM_TYPED_CONDITION_NOT_PROVED",
                "evaluation_status": evaluation.get("status"),
                "evaluation_reason": evaluation.get("reason"),
                "evaluation_errors": evaluation.get("errors"),
            })
            continue

        claimed_holds = claim.get("condition_holds")
        if not isinstance(claimed_holds, bool):
            rejected.append({"claim_id": cid, "reason": "CONDITION_RESULT_MISSING_OR_INVALID"})
            continue
        if claimed_holds is not evaluation["condition_holds"]:
            rejected.append({
                "claim_id": cid,
                "reason": "CONDITION_RESULT_MISMATCH",
                "claimed": claimed_holds,
                "actual": evaluation["condition_holds"],
            })
            continue

        claimed_term = claim.get("defined_term")
        if claimed_term is not None and claimed_term != evaluation["defined_term"]:
            rejected.append({"claim_id": cid, "reason": "DEFINED_TERM_MISMATCH"})
            continue
        claimed_field = claim.get("field_name")
        if claimed_field is not None and claimed_field != evaluation["field_name"]:
            rejected.append({"claim_id": cid, "reason": "DEFINED_FIELD_MISMATCH"})
            continue

        accepted.append({
            "claim_id": cid,
            "kind": "CERTIFIED_DEFINED_TERM_TYPED_CONDITION",
            "condition_holds": evaluation["condition_holds"],
            "scope_id": evaluation["scope_id"],
            "condition_span": evaluation["condition_span"],
            "condition_text_sha256": evaluation["condition_text_sha256"],
            "defined_term": evaluation["defined_term"],
            "definition_sentence_index": evaluation["definition_sentence_index"],
            "field_name": evaluation["field_name"],
            "field_type": evaluation["field_type"],
            "operator": evaluation["operator"],
            "literal": evaluation["literal"],
            "typed_context_sha256": evaluation["typed_context_sha256"],
            "condition_atom_id": evaluation["condition_atom_id"],
            "constraint": evaluation["proved_constraint"],
        })
        proved.append(evaluation["proved_constraint"])

    return {
        "schema": SCHEMA,
        "status": "PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id": source_id,
        "accepted_claims": accepted,
        "rejected_claims": rejected,
        "proved_constraints": proved,
        "terminal_authority": False,
        "soundness_boundary": (
            "V5_ADDS_ONLY_EXPLICIT_SOURCE_DEFINED_TERM_TO_LITERAL_TYPED_FIELD_DENOTATION;"
            "EXPECTED_TYPED_CONTEXT_DIGEST_AUTHORITY_POLICY_ADEQUACY_AND_NON_EXPLICIT_SEMANTICS_REMAIN_SEPARATE"
        ),
    }
