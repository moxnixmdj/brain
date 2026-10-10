"""Source-aligned semantic proof checker v4.

V4 preserves v3 and adds a narrow certified source-to-typed-condition primitive for
single-UNLESS controlled clauses. The caller may propose whether the exception
condition holds; the checker recomputes the source scope, literal field/operator,
content-addressed typed context, and exact boolean/decimal evaluation.

Unsupported prose remains unproved. This module has no terminal authority.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v3 import verify_proof as verify_v3
from canonical.runtime.certified_typed_unless_condition_v1 import evaluate_unless_condition

SCHEMA = "BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V4"


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
    condition_claims = []
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
        if claim.get("kind") == "CERTIFIED_TYPED_UNLESS_CONDITION":
            condition_claims.append(claim)
        else:
            base_claims.append(claim)

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "terminal_authority": False,
        }

    base = verify_v3(
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
            "errors": ["V3_PRIMITIVE_CHECK_FAIL_CLOSED"],
            "base_proof": base,
            "terminal_authority": False,
        }

    accepted = list(base.get("accepted_claims") or [])
    rejected = list(base.get("rejected_claims") or [])
    proved = list(base.get("proved_constraints") or [])

    for claim in condition_claims:
        cid = str(claim["claim_id"])
        if not isinstance(typed_context, Mapping):
            rejected.append({"claim_id": cid, "reason": "TYPED_CONTEXT_REQUIRED"})
            continue
        if not isinstance(expected_typed_context_sha256, str):
            rejected.append({"claim_id": cid, "reason": "EXPECTED_TYPED_CONTEXT_SHA256_REQUIRED"})
            continue

        evaluation = evaluate_unless_condition(
            source_text,
            source_id=source_id,
            typed_context=typed_context,
            expected_typed_context_sha256=expected_typed_context_sha256,
        )
        if evaluation.get("status") not in {"PROVED_TRUE", "PROVED_FALSE"}:
            rejected.append({
                "claim_id": cid,
                "reason": "CONTROLLED_CONDITION_NOT_PROVED",
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

        expected_atom_id = claim.get("condition_atom_id")
        if expected_atom_id is not None and expected_atom_id != evaluation["condition_atom_id"]:
            rejected.append({
                "claim_id": cid,
                "reason": "CONDITION_ATOM_ID_MISMATCH",
            })
            continue

        accepted.append({
            "claim_id": cid,
            "kind": "CERTIFIED_TYPED_UNLESS_CONDITION",
            "condition_holds": evaluation["condition_holds"],
            "scope_id": evaluation["scope_id"],
            "condition_span": evaluation["condition_span"],
            "condition_text_sha256": evaluation["condition_text_sha256"],
            "schema_id": evaluation["schema_id"],
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
            "V4_ADDS_ONLY_SINGLE_UNLESS_CONTROLLED_FIELD_CONDITIONS_WITH_LITERAL_FIELD_NAMES"
            "_CONTENT_ADDRESSED_TYPED_CONTEXT_AND_EXACT_BOOLEAN_OR_DECIMAL_EVALUATION;"
            "GENERAL_REFERENCE_DOMAIN_SEMANTICS_AND_TYPED_CONTEXT_AUTHORITY_REMAIN_OUTSIDE"
        ),
    }
