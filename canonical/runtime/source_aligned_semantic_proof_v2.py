"""Source-aligned semantic proof checker v2.

V2 preserves the v1 primitive checker and adds one certified structural primitive:
scope relations from canonical.runtime.certified_scope_fragment_v1.

The caller may propose a scope fact, but the checker recomputes the full structural
parse from the raw source and admits the claim only on exact agreement. This still
does not prove the denotation or domain meaning of either scoped clause.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v1 import verify_proof as verify_v1
from canonical.runtime.certified_scope_fragment_v1 import parse_scope

SCHEMA = "BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V2"


def _scope_atom(p: Mapping[str, Any]) -> str:
    return (
        f"SCOPE_RELATION::{p['scope_id']}::{p['relation']}::"
        f"{p['left_role']}::{p['right_role']}"
    )


def verify_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["CLAIMS_INVALID"],
            "terminal_authority": False,
        }

    seen: set[str] = set()
    errors: list[str] = []
    base_claims: list[Mapping[str, Any]] = []
    scope_claims: list[Mapping[str, Any]] = []
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
        if claim.get("kind") == "SCOPE_RELATION":
            scope_claims.append(claim)
        else:
            base_claims.append(claim)

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "terminal_authority": False,
        }

    base = verify_v1(source_text, source_id=source_id, claims=base_claims)
    if base.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["V1_PRIMITIVE_CHECK_FAIL_CLOSED"],
            "base_proof": base,
            "terminal_authority": False,
        }

    accepted = list(base.get("accepted_claims") or [])
    rejected = list(base.get("rejected_claims") or [])
    proved = list(base.get("proved_constraints") or [])

    parsed = parse_scope(source_text, source=source_id)
    p = parsed.get("parse") if parsed.get("status") == "PARSED" else None

    for claim in scope_claims:
        cid = str(claim["claim_id"])
        if not isinstance(p, Mapping):
            rejected.append({
                "claim_id": cid,
                "reason": "SOURCE_SCOPE_NOT_CERTIFIED_BY_V1_FRAGMENT",
                "scope_parse_status": parsed.get("status"),
                "scope_parse_reason": parsed.get("reason"),
            })
            continue

        expected = {
            "scope_id": p["scope_id"],
            "relation": p["relation"],
            "operator_id": p["operator_id"],
            "left_role": p["left_role"],
            "left_span": p["left_span"],
            "right_role": p["right_role"],
            "right_span": p["right_span"],
        }
        claimed = {
            "scope_id": claim.get("scope_id"),
            "relation": claim.get("relation"),
            "operator_id": claim.get("operator_id"),
            "left_role": claim.get("left_role"),
            "left_span": claim.get("left_span"),
            "right_role": claim.get("right_role"),
            "right_span": claim.get("right_span"),
        }
        if claimed != expected:
            rejected.append({
                "claim_id": cid,
                "reason": "SCOPE_CLAIM_MISMATCH",
                "expected": expected,
                "claimed": claimed,
            })
            continue

        constraint = {"op": "ATOM", "id": _scope_atom(p)}
        accepted.append({
            "claim_id": cid,
            "kind": "SCOPE_RELATION",
            **expected,
            "left_text_sha256": p["left_text_sha256"],
            "right_text_sha256": p["right_text_sha256"],
            "constraint": constraint,
        })
        proved.append(constraint)

    return {
        "schema": SCHEMA,
        "status": "PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id": source_id,
        "accepted_claims": accepted,
        "rejected_claims": rejected,
        "proved_constraints": proved,
        "proved_constraint_ids": [c["id"] for c in proved],
        "scope_parse": parsed,
        "terminal_authority": False,
        "soundness_boundary": (
            "V2_ADDS_ONLY_STRUCTURAL_SCOPE_FOR_THE_CERTIFIED_FRAGMENT;"
            "CLAUSE_DENOTATION_REFERENCE_RESOLUTION_DOMAIN_MEANING_AND_POLICY_ADEQUACY_REMAIN_UNPROVED"
        ),
    }
