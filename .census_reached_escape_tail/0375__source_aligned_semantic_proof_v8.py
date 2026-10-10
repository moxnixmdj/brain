"""Source-aligned semantic proof checker V8.

V8 preserves V7 and adds one narrow positive primitive:
CERTIFIED_DOCUMENT_EFFECT_RELATION.

A claim is accepted only when the exact source contains a canonical
"Effect relation: <json>" line parsed by the Brain-owned relation parser and
the claimed complete effect relation exactly equals that source parse.

This does not prove that unrecognized prose is inert or that all document
effects were enumerated.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v7 import verify_proof as verify_v7
from canonical.runtime.certified_document_effect_relation_v1 import parse_effect_relations

SCHEMA="BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V8"


def _relation_atom(source_id:str,relation_id:str,effect_id:str)->str:
    return "DOCUMENT_EFFECT_RELATION::"+source_id+"::"+relation_id+"::"+effect_id


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
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["CLAIMS_INVALID"],"terminal_authority":False,
        }

    base_claims=[]; relation_claims=[]; seen=set(); errors=[]
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
        if claim.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_RELATION":
            relation_claims.append(claim)
        else:
            base_claims.append(claim)

    if errors:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":sorted(set(errors)),"terminal_authority":False,
        }

    base=verify_v7(
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
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["V7_PRIMITIVE_CHECK_FAIL_CLOSED"],
            "base_proof":base,"terminal_authority":False,
        }

    accepted=list(base.get("accepted_claims") or [])
    rejected=list(base.get("rejected_claims") or [])
    proved=list(base.get("proved_constraints") or [])

    parsed=parse_effect_relations(source_text,source=source_id)
    by_id={
        row["effect"]["effect_id"]:row
        for row in (parsed.get("relations") or [])
        if isinstance(row,Mapping)
    }

    for claim in relation_claims:
        cid=str(claim["claim_id"])
        effect=claim.get("effect")
        if not isinstance(effect,Mapping):
            rejected.append({"claim_id":cid,"reason":"EFFECT_RELATION_CLAIM_INVALID"})
            continue
        eid=str(effect.get("effect_id") or "").strip()
        row=by_id.get(eid)
        if row is None:
            rejected.append({
                "claim_id":cid,
                "reason":"DOCUMENT_EFFECT_RELATION_NOT_CERTIFIABLY_PARSED",
                "effect_id":eid or None,
                "parse_status":parsed.get("status"),
                "parse_reason":parsed.get("reason"),
            })
            continue
        expected_semantics={
            key:value for key,value in row["effect"].items()
            if key!="source_locator"
        }
        if dict(effect)!=expected_semantics:
            rejected.append({
                "claim_id":cid,
                "reason":"DOCUMENT_EFFECT_RELATION_MISMATCH",
                "effect_id":eid,
                "expected":expected_semantics,
                "claimed":dict(effect),
            })
            continue

        constraint={
            "op":"ATOM",
            "id":_relation_atom(source_id,str(row["relation_id"]),eid),
        }
        accepted.append({
            "claim_id":cid,
            "kind":"CERTIFIED_DOCUMENT_EFFECT_RELATION",
            "relation_id":row["relation_id"],
            "effect":row["effect"],
            "source_span_chars":list(row["source_span_chars"]),
            "source_span_bytes":list(row["source_span_bytes"]),
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
            "V8_CERTIFIES_ONLY_EXPLICIT_CANONICAL_COMPLETE_DOCUMENT_EFFECT_RELATION_LINES;"
            "UNRECOGNIZED_PROSE_EFFECT_COMPLETENESS_REFERENCE_RESOLUTION_AND_POLICY_ADEQUACY_REMAIN_UNPROVED"
        ),
    }
