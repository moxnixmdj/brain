"""Source-aligned semantic proof checker V7.

V7 preserves V6 and adds one narrow independently recomputed primitive:
CERTIFIED_EFFECT_TARGET_SCOPE.

The primitive is accepted only when the exact source contains one valid
"Effect targets only: ..." declaration recognized by the Brain-owned parser,
and the caller's claimed target set exactly matches that parse.

This proves only the document's explicit declared target scope. It does not
prove the specific effects on those targets, raw-language completeness, or
policy adequacy.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v6 import verify_proof as verify_v6
from canonical.runtime.certified_effect_target_scope_v1 import parse_effect_target_scope
from canonical.runtime.certified_effect_id_inventory_v1 import parse_effect_id_inventories

SCHEMA="BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V7"


def _scope_atom(source_id:str,scope_id:str,target_ids:Sequence[str])->str:
    return (
        "EFFECT_TARGET_SCOPE::"
        + source_id
        + "::"
        + scope_id
        + "::"
        + ",".join(target_ids)
    )


def _inventory_atom(
    source_id:str,
    inventory_id:str,
    target_id:str,
    effect_ids:Sequence[str],
)->str:
    return (
        "EFFECT_ID_INVENTORY::"
        + source_id
        + "::"
        + inventory_id
        + "::"
        + target_id
        + "::"
        + ",".join(effect_ids)
    )


def verify_proof(
    source_text:str,
    *,
    source_id:str,
    claims:Sequence[Mapping[str,Any]],
    typed_context:Mapping[str,Any]|None=None,
    expected_typed_context_sha256:str|None=None,
    fact_source:str|bytes|None=None,
    fact_source_id:str|None=None,
)->dict[str,Any]:
    if not isinstance(claims,Sequence) or isinstance(claims,(str,bytes)):
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "errors":["CLAIMS_INVALID"],
            "terminal_authority":False,
        }

    base_claims=[]
    scope_claims=[]
    inventory_claims=[]
    seen=set()
    errors=[]
    for i,claim in enumerate(claims):
        if not isinstance(claim,Mapping):
            errors.append(f"CLAIM_NOT_OBJECT:{i}")
            continue
        cid=str(claim.get("claim_id") or "").strip()
        if not cid:
            errors.append(f"CLAIM_ID_MISSING:{i}")
            continue
        if cid in seen:
            errors.append(f"CLAIM_ID_DUPLICATE:{cid}")
            continue
        seen.add(cid)
        if claim.get("kind")=="CERTIFIED_EFFECT_TARGET_SCOPE":
            scope_claims.append(claim)
        elif claim.get("kind")=="CERTIFIED_EFFECT_ID_INVENTORY":
            inventory_claims.append(claim)
        else:
            base_claims.append(claim)

    if errors:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "errors":sorted(set(errors)),
            "terminal_authority":False,
        }

    base=verify_v6(
        source_text,
        source_id=source_id,
        claims=base_claims,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
        fact_source=fact_source,
        fact_source_id=fact_source_id,
    )
    if base.get("status")=="FAIL_CLOSED":
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "errors":["V6_PRIMITIVE_CHECK_FAIL_CLOSED"],
            "base_proof":base,
            "terminal_authority":False,
        }

    accepted=list(base.get("accepted_claims") or [])
    rejected=list(base.get("rejected_claims") or [])
    proved=list(base.get("proved_constraints") or [])

    parsed=parse_effect_target_scope(source_text,source=source_id)
    parsed_inventories=parse_effect_id_inventories(source_text,source=source_id)
    inventory_by_target={
        row["target_id"]:row
        for row in (parsed_inventories.get("inventories") or [])
        if isinstance(row,Mapping)
    }

    for claim in scope_claims:
        cid=str(claim["claim_id"])
        if parsed.get("status")!="PARSED":
            rejected.append({
                "claim_id":cid,
                "reason":"EFFECT_TARGET_SCOPE_NOT_CERTIFIABLY_PARSED",
                "scope_status":parsed.get("status"),
                "scope_reason":parsed.get("reason"),
            })
            continue

        p=parsed["parse"]
        raw=claim.get("target_ids")
        if (
            not isinstance(raw,Sequence)
            or isinstance(raw,(str,bytes))
            or any(not isinstance(x,str) or not x.strip() for x in raw)
        ):
            rejected.append({
                "claim_id":cid,
                "reason":"TARGET_IDS_INVALID",
            })
            continue

        claimed=sorted(x.strip() for x in raw)
        if len(claimed)!=len(set(claimed)):
            rejected.append({
                "claim_id":cid,
                "reason":"TARGET_IDS_DUPLICATE",
            })
            continue

        expected=list(p["target_ids"])
        if claimed!=expected:
            rejected.append({
                "claim_id":cid,
                "reason":"EFFECT_TARGET_SCOPE_MISMATCH",
                "expected":expected,
                "claimed":claimed,
            })
            continue

        constraint={
            "op":"ATOM",
            "id":_scope_atom(source_id,str(p["scope_id"]),expected),
        }
        accepted.append({
            "claim_id":cid,
            "kind":"CERTIFIED_EFFECT_TARGET_SCOPE",
            "scope_id":p["scope_id"],
            "target_ids":expected,
            "source_span":list(p["source_span"]),
            "source_text_sha256":p["source_text_sha256"],
            "constraint":constraint,
        })
        proved.append(constraint)

    for claim in inventory_claims:
        cid=str(claim["claim_id"])
        target=str(claim.get("target_id") or "").strip()
        if not target:
            rejected.append({
                "claim_id":cid,
                "reason":"TARGET_ID_INVALID",
            })
            continue
        row=inventory_by_target.get(target)
        if row is None:
            rejected.append({
                "claim_id":cid,
                "reason":"EFFECT_ID_INVENTORY_NOT_CERTIFIABLY_PARSED",
                "target_id":target,
                "inventory_status":parsed_inventories.get("status"),
                "inventory_reason":parsed_inventories.get("reason"),
            })
            continue

        raw=claim.get("effect_ids")
        if (
            not isinstance(raw,Sequence)
            or isinstance(raw,(str,bytes))
            or any(not isinstance(x,str) or not x.strip() for x in raw)
        ):
            rejected.append({
                "claim_id":cid,
                "reason":"EFFECT_IDS_INVALID",
            })
            continue
        claimed=sorted(x.strip() for x in raw)
        if len(claimed)!=len(set(claimed)):
            rejected.append({
                "claim_id":cid,
                "reason":"EFFECT_IDS_DUPLICATE",
            })
            continue
        expected=list(row["effect_ids"])
        if claimed!=expected:
            rejected.append({
                "claim_id":cid,
                "reason":"EFFECT_ID_INVENTORY_MISMATCH",
                "expected":expected,
                "claimed":claimed,
            })
            continue

        constraint={
            "op":"ATOM",
            "id":_inventory_atom(
                source_id,
                str(row["inventory_id"]),
                target,
                expected,
            ),
        }
        accepted.append({
            "claim_id":cid,
            "kind":"CERTIFIED_EFFECT_ID_INVENTORY",
            "inventory_id":row["inventory_id"],
            "target_id":target,
            "effect_ids":expected,
            "source_span":list(row["source_span"]),
            "source_text_sha256":row["source_text_sha256"],
            "constraint":constraint,
        })
        proved.append(constraint)

    return {
        "schema":SCHEMA,
        "status":"PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id":source_id,
        "accepted_claims":accepted,
        "rejected_claims":rejected,
        "proved_constraints":proved,
        "terminal_authority":False,
        "soundness_boundary":(
            "V7_CERTIFIES_ONLY_EXPLICIT_DECLARED_EFFECT_TARGET_SETS_AND_EFFECT_ID_INVENTORIES;"
            "EFFECT_VALUES_CLASSES_CONDITIONS_AND_UNSTRUCTURED_RAW_LANGUAGE_COMPLETENESS_REMAIN_UNPROVED"
        ),
    }
