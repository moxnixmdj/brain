"""Orthogonal deontic extension for the current source-aligned semantic stack.

All non-DEONTIC_RULE claims and every current v6 input are delegated unchanged to
source_aligned_semantic_proof_v6. The only additional primitive is a narrow,
source-certified explicit deontic rule.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence
from canonical.runtime.source_aligned_semantic_proof_v6 import verify_proof as verify_v6
from canonical.runtime.certified_deontic_rule_fragment_v1 import parse_deontic_rule

SCHEMA = "BRAIN_SOURCE_ALIGNED_DEONTIC_EXTENSION_V1"

def _atom(parsed: Mapping[str, Any]) -> str:
    scope = parsed.get("scope")
    scope_id = scope.get("scope_id") if isinstance(scope, Mapping) else "UNSCOPED"
    return (
        f"DEONTIC_RULE::{parsed['rule_id']}::{parsed['relation']}::"
        f"{parsed['subject_text_sha256']}::{parsed['action_text_sha256']}::{scope_id}"
    )

def verify_proof(
    source_text: str, *, source_id: str, claims: Sequence[Mapping[str, Any]],
    typed_context: Mapping[str, Any] | None = None,
    expected_typed_context_sha256: str | None = None,
    fact_source: str | bytes | None = None,
    fact_source_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["CLAIMS_INVALID"], "terminal_authority": False}
    base, deontic, seen, errors = [], [], set(), []
    for i, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            errors.append(f"CLAIM_NOT_OBJECT:{i}"); continue
        cid = str(claim.get("claim_id") or "").strip()
        if not cid:
            errors.append(f"CLAIM_ID_MISSING:{i}"); continue
        if cid in seen:
            errors.append(f"CLAIM_ID_DUPLICATE:{cid}"); continue
        seen.add(cid)
        (deontic if claim.get("kind") == "DEONTIC_RULE" else base).append(claim)
    if errors:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": sorted(set(errors)), "terminal_authority": False}

    prior = verify_v6(
        source_text, source_id=source_id, claims=base,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
        fact_source=fact_source, fact_source_id=fact_source_id,
    )
    if prior.get("status") == "FAIL_CLOSED":
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["V6_PRIMITIVE_CHECK_FAIL_CLOSED"],
                "base_proof": prior, "terminal_authority": False}

    accepted = list(prior.get("accepted_claims") or [])
    rejected = list(prior.get("rejected_claims") or [])
    proved = list(prior.get("proved_constraints") or [])
    parsed = parse_deontic_rule(source_text, source=source_id)

    for claim in deontic:
        cid = str(claim["claim_id"])
        if parsed.get("status") != "PARSED":
            rejected.append({"claim_id": cid, "reason": "SOURCE_DEONTIC_RULE_NOT_CERTIFIED",
                             "parse_status": parsed.get("status"), "parse_reason": parsed.get("reason")})
            continue
        scope = parsed.get("scope")
        expected = {
            "rule_id": parsed["rule_id"], "relation": parsed["relation"],
            "subject_span": parsed["subject_span"], "action_span": parsed["action_span"],
            "scope_id": scope.get("scope_id") if isinstance(scope, Mapping) else None,
            "scope_relation": scope.get("relation") if isinstance(scope, Mapping) else None,
            "condition_span": scope.get("condition_span") if isinstance(scope, Mapping) else None,
        }
        claimed = {k: claim.get(k) for k in expected}
        if claimed != expected:
            rejected.append({"claim_id": cid, "reason": "DEONTIC_CLAIM_MISMATCH",
                             "expected": expected, "claimed": claimed})
            continue
        constraint = {"op": "ATOM", "id": _atom(parsed)}
        accepted.append({
            "claim_id": cid, "kind": "DEONTIC_RULE", **expected,
            "subject_text_sha256": parsed["subject_text_sha256"],
            "action_text_sha256": parsed["action_text_sha256"],
            "condition_text_sha256": scope.get("condition_text_sha256") if isinstance(scope, Mapping) else None,
            "constraint": constraint,
        })
        proved.append(constraint)

    return {
        "schema": SCHEMA,
        "status": "PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id": source_id, "accepted_claims": accepted, "rejected_claims": rejected,
        "proved_constraints": proved, "terminal_authority": False,
        "soundness_boundary": (
            "DELEGATES_CURRENT_V6_UNCHANGED_AND_ADDS_ONLY_CONTROLLED_EXPLICIT_DEONTIC_STRUCTURE;"
            "SOURCE_AUTHORITY_REFERENCE_RESOLUTION_DOMAIN_MAPPING_IMPLICIT_APPLICABILITY_MATERIALITY_AND_POLICY_ADEQUACY_REMAIN_SEPARATE"
        ),
    }
