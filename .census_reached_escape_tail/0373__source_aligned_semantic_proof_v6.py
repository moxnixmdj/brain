"""Source-aligned semantic proof checker v6.

V6 preserves v5 and adds a raw-fact-source defined-term primitive. For this path,
the caller does not supply a typed context or expected digest. The checker compiles
the typed context from exact raw fact-source bytes, binds an explicit source
definition to the literal field ID, evaluates the controlled UNLESS condition,
and admits only the recomputed result.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v5 import verify_proof as verify_v5
from canonical.runtime.certified_defined_term_raw_typed_condition_v2 import (
    evaluate_defined_unless_condition_from_raw_facts,
)

SCHEMA = "BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V6"


def verify_proof(
    source_text: str,
    *,
    source_id: str,
    claims: Sequence[Mapping[str, Any]],
    typed_context: Mapping[str, Any] | None = None,
    expected_typed_context_sha256: str | None = None,
    fact_source: str | bytes | None = None,
    fact_source_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["CLAIMS_INVALID"],
            "terminal_authority": False,
        }

    base_claims = []
    raw_fact_claims = []
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
        if claim.get("kind") == "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION":
            raw_fact_claims.append(claim)
        else:
            base_claims.append(claim)

    if errors:
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": sorted(set(errors)),
            "terminal_authority": False,
        }

    base = verify_v5(
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
            "errors": ["V5_PRIMITIVE_CHECK_FAIL_CLOSED"],
            "base_proof": base,
            "terminal_authority": False,
        }

    accepted = list(base.get("accepted_claims") or [])
    rejected = list(base.get("rejected_claims") or [])
    proved = list(base.get("proved_constraints") or [])

    for claim in raw_fact_claims:
        cid = str(claim["claim_id"])
        if not isinstance(fact_source, (str, bytes)):
            rejected.append({"claim_id": cid, "reason": "RAW_FACT_SOURCE_REQUIRED"})
            continue
        if not isinstance(fact_source_id, str) or not fact_source_id.strip():
            rejected.append({"claim_id": cid, "reason": "FACT_SOURCE_ID_REQUIRED"})
            continue

        evaluation = evaluate_defined_unless_condition_from_raw_facts(
            source_text,
            policy_source_id=source_id,
            fact_source=fact_source,
            fact_source_id=fact_source_id,
        )
        if evaluation.get("status") not in {"PROVED_TRUE", "PROVED_FALSE"}:
            rejected.append({
                "claim_id": cid,
                "reason": "RAW_FACT_DEFINED_TERM_CONDITION_NOT_PROVED",
                "evaluation_status": evaluation.get("status"),
                "evaluation_reason": evaluation.get("reason"),
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

        accepted.append({
            "claim_id": cid,
            "kind": "CERTIFIED_DEFINED_TERM_RAW_TYPED_CONDITION",
            "condition_holds": evaluation["condition_holds"],
            "defined_term": evaluation["defined_term"],
            "field_name": evaluation["field_name"],
            "field_type": evaluation["field_type"],
            "operator": evaluation["operator"],
            "literal": evaluation["literal"],
            "condition_atom_id": evaluation["condition_atom_id"],
            "policy_source_id": source_id,
            "fact_source_id": evaluation["fact_source_id"],
            "fact_source_sha256": evaluation["fact_source_sha256"],
            "typed_context_sha256": evaluation["typed_context_sha256"],
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
            "V6_REMOVES_CALLER_SUPPLIED_TYPED_CONTEXT_HASH_FROM_THE_RAW_FACT_SUBREGION;"
            "UPSTREAM_SOURCE_AUTHORIZATION_AND_POLICY_ADEQUACY_REMAIN_SEPARATE"
        ),
    }
