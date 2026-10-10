"""Source-aligned semantic proof checker V10.

V10 preserves V9 and adds source verification for the bounded natural-effect
clause grammar. The claim vocabulary is unchanged:
  CERTIFIED_EFFECT_TARGET_SCOPE
  CERTIFIED_EFFECT_ID_INVENTORY
  CERTIFIED_DOCUMENT_EFFECT_FIELD

A claim rejected by V9 may be recovered only when an exact bounded-natural
source clause independently parses to the same semantic claim. Natural-clause
proof never replaces a contradictory accepted claim and never certifies
unrecognized prose.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v9 import verify_proof as verify_v9
from canonical.runtime.certified_bounded_natural_effect_clause_v1 import (
    parse_natural_effect_clauses,
)

SCHEMA="BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V10"


def _canon(v:Any)->str:
    return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)


def _atom(source_id:str,clause_id:str,claim_kind:str,slot:str)->dict[str,Any]:
    return {
        "op":"ATOM",
        "id":"NATURAL_EFFECT_CLAUSE::"+source_id+"::"+clause_id+"::"+claim_kind+"::"+slot,
    }


def _natural_match(
    claim:Mapping[str,Any],
    clauses:Sequence[Mapping[str,Any]],
)->Mapping[str,Any]|None:
    kind=claim.get("kind")
    if kind=="CERTIFIED_EFFECT_TARGET_SCOPE":
        if set(claim)!={"claim_id","kind","target_ids"}:
            return None
        expected=list(claim.get("target_ids") or [])
        for row in clauses:
            if row.get("kind")=="TARGET_SCOPE" and row.get("target_ids")==expected:
                return row
        return None

    if kind=="CERTIFIED_EFFECT_ID_INVENTORY":
        if set(claim)!={"claim_id","kind","target_id","effect_ids"}:
            return None
        target=claim.get("target_id")
        ids=list(claim.get("effect_ids") or [])
        for row in clauses:
            if (
                row.get("kind")=="INVENTORY"
                and row.get("target_id")==target
                and row.get("effect_ids")==ids
            ):
                return row
        return None

    if kind=="CERTIFIED_DOCUMENT_EFFECT_FIELD":
        if set(claim)!={"claim_id","kind","effect_id","field","value"}:
            return None
        for row in clauses:
            if (
                row.get("kind")=="FIELD"
                and row.get("effect_id")==claim.get("effect_id")
                and row.get("field")==claim.get("field")
                and row.get("value")==claim.get("value")
            ):
                return row
        return None

    return None


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

    base=verify_v9(
        source_text,
        source_id=source_id,
        claims=claims,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
        fact_source=fact_source,
        fact_source_id=fact_source_id,
    )
    if base.get("status")=="FAIL_CLOSED":
        return {
            "schema":SCHEMA,
            "status":"FAIL_CLOSED",
            "errors":["V9_PRIMITIVE_CHECK_FAIL_CLOSED"],
            "base_proof":base,
            "terminal_authority":False,
        }

    parsed=parse_natural_effect_clauses(source_text,source=source_id)
    clauses=[
        x for x in (parsed.get("clauses") or [])
        if isinstance(x,Mapping)
    ]

    accepted=list(base.get("accepted_claims") or [])
    accepted_ids={
        str(x.get("claim_id") or "")
        for x in accepted
        if isinstance(x,Mapping)
    }
    rejected=list(base.get("rejected_claims") or [])
    proved=list(base.get("proved_constraints") or [])

    original_by_id={}
    for claim in claims:
        if isinstance(claim,Mapping):
            cid=str(claim.get("claim_id") or "")
            if cid:
                original_by_id[cid]=claim

    recovered_ids=set()
    if parsed.get("status")=="PARSED":
        for cid,claim in original_by_id.items():
            if cid in accepted_ids:
                continue
            row=_natural_match(claim,clauses)
            if row is None:
                continue

            kind=str(claim.get("kind") or "")
            if kind=="CERTIFIED_EFFECT_TARGET_SCOPE":
                slot="scope"
                payload={
                    "claim_id":cid,
                    "kind":kind,
                    "target_ids":list(claim.get("target_ids") or []),
                }
            elif kind=="CERTIFIED_EFFECT_ID_INVENTORY":
                slot="inventory:"+str(claim.get("target_id") or "")
                payload={
                    "claim_id":cid,
                    "kind":kind,
                    "target_id":claim.get("target_id"),
                    "effect_ids":list(claim.get("effect_ids") or []),
                }
            elif kind=="CERTIFIED_DOCUMENT_EFFECT_FIELD":
                slot=(
                    str(claim.get("effect_id") or "")
                    +":"+str(claim.get("field") or "")
                )
                payload={
                    "claim_id":cid,
                    "kind":kind,
                    "effect_id":claim.get("effect_id"),
                    "field":claim.get("field"),
                    "value":claim.get("value"),
                }
            else:
                continue

            constraint=_atom(
                source_id,
                str(row.get("clause_id") or ""),
                kind,
                slot,
            )
            payload.update({
                "natural_clause_id":row.get("clause_id"),
                "source_span_chars":list(row.get("source_span_chars") or []),
                "source_span_bytes":list(row.get("source_span_bytes") or []),
                "source_text_sha256":row.get("source_text_sha256"),
                "constraint":constraint,
                "proof_primitive":"BOUNDED_NATURAL_EFFECT_CLAUSE_V1",
            })
            accepted.append(payload)
            proved.append(constraint)
            recovered_ids.add(cid)

    if recovered_ids:
        rejected=[
            row for row in rejected
            if not (
                isinstance(row,Mapping)
                and str(row.get("claim_id") or "") in recovered_ids
            )
        ]

    return {
        "schema":SCHEMA,
        "status":"PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id":source_id,
        "accepted_claims":accepted,
        "rejected_claims":rejected,
        "proved_constraints":proved,
        "natural_clause_parse_status":parsed.get("status"),
        "natural_clause_parse_reason":parsed.get("reason"),
        "terminal_authority":False,
        "soundness_boundary":(
            "V10_ADDS_ONLY_THE_BOUNDED_UNAMBIGUOUS_NATURAL_EFFECT_CLAUSE_GRAMMAR;"
            "UNRECOGNIZED_OR_AMBIGUOUS_PROSE_REMAINS_UNPROVED_AND_CANNOT_NARROW_TOP"
        ),
    }
