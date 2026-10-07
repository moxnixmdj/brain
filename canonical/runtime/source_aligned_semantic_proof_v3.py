"""Source-aligned semantic proof checker v3.

V3 extends v2 with one additional one-sided primitive: an exact-source
controlled deontic rule. The deontic parser keeps subject/action/condition as
opaque source spans and proves only REQUIRED/PROHIBITED structure plus certified
conditional scope. Unsupported language remains unresolved.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v2 import verify_proof as verify_v2
from canonical.runtime.certified_deontic_rule_fragment_v1 import parse_deontic_rule

SCHEMA = "BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V3"


def _atom(p: Mapping[str, Any]) -> str:
    scope = p.get("scope")
    scope_id = scope.get("scope_id") if isinstance(scope, Mapping) else "UNSCOPED"
    return (
        f"DEONTIC_RULE::{p['rule_id']}::{p['relation']}::"
        f"{p['subject_text_sha256']}::{p['action_text_sha256']}::{scope_id}"
    )


def verify_proof(source_text: str, *, source_id: str, claims: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": ["CLAIMS_INVALID"], "terminal_authority": False}

    deontic_claims = []
    base_claims = []
    seen = set()
    errors = []
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
        if claim.get("kind") == "DEONTIC_RULE":
            deontic_claims.append(claim)
        else:
            base_claims.append(claim)
    if errors:
        return {"schema": SCHEMA, "status": "FAIL_CLOSED", "errors": sorted(set(errors)), "terminal_authority": False}

    base = verify_v2(source_text, source_id=source_id, claims=base_claims)
    if base.get("status") == "FAIL_CLOSED":
        return {
            "schema": SCHEMA,
            "status": "FAIL_CLOSED",
            "errors": ["V2_PRIMITIVE_CHECK_FAIL_CLOSED"],
            "base_proof": base,
            "terminal_authority": False,
        }

    accepted = list(base.get("accepted_claims") or [])
    rejected = list(base.get("rejected_claims") or [])
    proved = list(base.get("proved_constraints") or [])
    parsed = parse_deontic_rule(source_text, source=source_id)

    for claim in deontic_claims:
        cid = str(claim["claim_id"])
        if parsed.get("status") != "PARSED":
            rejected.append({
                "claim_id": cid,
                "reason": "SOURCE_DEONTIC_RULE_NOT_CERTIFIED",
                "parse_status": parsed.get("status"),
                "parse_reason": parsed.get("reason"),
            })
            continue

        scope = parsed.get("scope")
        expected = {
            "rule_id": parsed["rule_id"],
            "relation": parsed["relation"],
            "subject_span": parsed["subject_span"],
            "action_span": parsed["action_span"],
            "scope_id": scope.get("scope_id") if isinstance(scope, Mapping) else None,
            "scope_relation": scope.get("relation") if isinstance(scope, Mapping) else None,
            "condition_span": scope.get("condition_span") if isinstance(scope, Mapping) else None,
        }
        claimed = {k: claim.get(k) for k in expected}
        if claimed != expected:
            rejected.append({
                "claim_id": cid,
                "reason": "DEONTIC_CLAIM_MISMATCH",
                "expected": expected,
                "claimed": claimed,
            })
            continue

        constraint = {"op": "ATOM", "id": _atom(parsed)}
        accepted.append({
            "claim_id": cid,
            "kind": "DEONTIC_RULE",
            **expected,
            "subject_text_sha256": parsed["subject_text_sha256"],
            "action_text_sha256": parsed["action_text_sha256"],
            "condition_text_sha256": scope.get("condition_text_sha256") if isinstance(scope, Mapping) else None,
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
        "deontic_parse": parsed,
        "terminal_authority": False,
        "soundness_boundary": (
            "V3_PROVES_ONLY_EXPLICIT_CONTROLLED_DEONTIC_STRUCTURE_AND_EXACT_SOURCE_SPANS;"
            "REFERENCE_RESOLUTION_DOMAIN_CLASSIFICATION_IMPLICIT_APPLICABILITY_MATERIALITY_AND_POLICY_ADEQUACY_REMAIN_SEPARATE"
        ),
    }
