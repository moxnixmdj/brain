"""Source-aligned semantic proof checker V9.

V9 preserves V8 and adds:
    CERTIFIED_DOCUMENT_EFFECT_FIELD

A field claim is accepted only when the exact source contains a canonical
"Effect field: <json>" line for the same effect_id, semantic field and exact
normalized value.

Accepted fields carry exact source spans and hashes. This proves only the
individual coordinate. Cross-field consistency and effect completeness remain
the semantic lattice's job.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v8 import verify_proof as verify_v8
from canonical.runtime.certified_document_effect_field_v1 import parse_effect_fields

SCHEMA="BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V9"


def _field_atom(
    source_id:str,
    field_id:str,
    effect_id:str,
    field:str,
)->str:
    return (
        "DOCUMENT_EFFECT_FIELD::"+source_id+"::"+field_id+"::"
        +effect_id+"::"+field
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
    field_claims=[]
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
            errors.append("CLAIM_ID_DUPLICATE:"+cid)
            continue
        seen.add(cid)
        if claim.get("kind")=="CERTIFIED_DOCUMENT_EFFECT_FIELD":
            field_claims.append(claim)
        else:
            base_claims.append(claim)

    if errors:
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "errors":sorted(set(errors)),
            "terminal_authority":False,
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
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "errors":["V8_PRIMITIVE_CHECK_FAIL_CLOSED"],
            "base_proof":base,
            "terminal_authority":False,
        }

    accepted=list(base.get("accepted_claims") or [])
    rejected=list(base.get("rejected_claims") or [])
    proved=list(base.get("proved_constraints") or [])

    parsed=parse_effect_fields(source_text,source=source_id)
    by_slot={
        (str(row["effect_id"]),str(row["field"])):row
        for row in (parsed.get("fields") or [])
        if isinstance(row,Mapping)
    }

    for claim in field_claims:
        cid=str(claim["claim_id"])
        if set(claim)!={"claim_id","kind","effect_id","field","value"}:
            rejected.append({
                "claim_id":cid,
                "reason":"DOCUMENT_EFFECT_FIELD_CLAIM_FIELD_SET_INVALID",
            })
            continue
        eid=str(claim.get("effect_id") or "").strip()
        field=str(claim.get("field") or "").strip()
        row=by_slot.get((eid,field))
        if row is None:
            rejected.append({
                "claim_id":cid,
                "reason":"DOCUMENT_EFFECT_FIELD_NOT_CERTIFIABLY_PARSED",
                "effect_id":eid or None,
                "field":field or None,
                "parse_status":parsed.get("status"),
                "parse_reason":parsed.get("reason"),
            })
            continue
        if claim.get("value")!=row.get("value"):
            rejected.append({
                "claim_id":cid,
                "reason":"DOCUMENT_EFFECT_FIELD_VALUE_MISMATCH",
                "effect_id":eid,
                "field":field,
                "expected":row.get("value"),
                "claimed":claim.get("value"),
            })
            continue

        constraint={
            "op":"ATOM",
            "id":_field_atom(
                source_id,
                str(row["field_id"]),
                eid,
                field,
            ),
        }
        accepted.append({
            "claim_id":cid,
            "kind":"CERTIFIED_DOCUMENT_EFFECT_FIELD",
            "field_id":row["field_id"],
            "effect_id":eid,
            "field":field,
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
            "V9_CERTIFIES_ONLY_EXPLICIT_CANONICAL_EFFECT_FIELDS_AND_ALL_V8_"
            "PRIMITIVES;CROSS_FIELD_CONSISTENCY_COMPLETENESS_AND_UNRECOGNIZED_"
            "PROSE_SEMANTICS_REMAIN_UNPROVED"
        ),
    }
