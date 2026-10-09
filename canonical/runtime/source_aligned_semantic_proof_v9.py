"""Source-aligned semantic proof checker V9.

V9 preserves V8 and adds one narrow compositional primitive:
CERTIFIED_DOCUMENT_EFFECT_DIMENSION.

Each accepted claim binds exactly one effect dimension to one exact source span
recomputed by the Brain-owned parser. This permits monotone partial refinement:
a proved class does not certify value, timing, conditions, target, or
supersession.

Unrecognized prose and rejected claims remain unproved.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v8 import verify_proof as verify_v8
from canonical.runtime.certified_document_effect_dimension_v1 import parse_effect_dimensions

SCHEMA="BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V9"


def _atom(source_id:str,dimension_id:str,effect_id:str,dimension:str)->str:
    return (
        "DOCUMENT_EFFECT_DIMENSION::"+source_id+"::"+dimension_id+"::"
        +effect_id+"::"+dimension
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
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["CLAIMS_INVALID"],"terminal_authority":False,
        }

    base_claims=[]; dimension_claims=[]; seen=set(); errors=[]
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
        if claim.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_DIMENSION":
            dimension_claims.append(claim)
        else:
            base_claims.append(claim)

    if errors:
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":sorted(set(errors)),"terminal_authority":False,
        }

    base=verify_v8(
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
            "errors":["V8_PRIMITIVE_CHECK_FAIL_CLOSED"],
            "base_proof":base,"terminal_authority":False,
        }

    accepted=list(base.get("accepted_claims") or [])
    rejected=list(base.get("rejected_claims") or [])
    proved=list(base.get("proved_constraints") or [])

    parsed=parse_effect_dimensions(source_text,source=source_id)
    by_key={
        (row["effect_id"],row["dimension"]):row
        for row in (parsed.get("dimensions") or [])
        if isinstance(row,Mapping)
    }

    for claim in dimension_claims:
        cid=str(claim["claim_id"])
        eid=str(claim.get("effect_id") or "").strip()
        dim=str(claim.get("dimension") or "").strip()
        if not eid or not dim:
            rejected.append({
                "claim_id":cid,
                "reason":"EFFECT_ID_OR_DIMENSION_INVALID",
            })
            continue

        row=by_key.get((eid,dim))
        if row is None:
            rejected.append({
                "claim_id":cid,
                "reason":"DOCUMENT_EFFECT_DIMENSION_NOT_CERTIFIABLY_PARSED",
                "effect_id":eid,
                "dimension":dim,
                "parse_status":parsed.get("status"),
                "parse_reason":parsed.get("reason"),
            })
            continue

        if claim.get("value")!=row["value"]:
            rejected.append({
                "claim_id":cid,
                "reason":"DOCUMENT_EFFECT_DIMENSION_MISMATCH",
                "effect_id":eid,
                "dimension":dim,
                "expected":row["value"],
                "claimed":claim.get("value"),
            })
            continue

        constraint={
            "op":"ATOM",
            "id":_atom(
                source_id,
                str(row["dimension_id"]),
                eid,
                dim,
            ),
        }
        accepted.append({
            "claim_id":cid,
            "kind":"CERTIFIED_DOCUMENT_EFFECT_DIMENSION",
            "dimension_id":row["dimension_id"],
            "effect_id":eid,
            "dimension":dim,
            "value":row["value"],
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
            "V9_CERTIFIES_ONLY_EXPLICIT_SINGLE_EFFECT_DIMENSIONS_ON_EXACT_SOURCE_SPANS;"
            "NO_SINGLE_DIMENSION_CERTIFIES_OTHER_RELATION_FIELDS_OR_GLOBAL_PROSE_COMPLETENESS"
        ),
    }
