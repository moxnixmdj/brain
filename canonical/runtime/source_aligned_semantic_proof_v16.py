"""Source-aligned semantic proof checker V16.

V13 preserves V12 and adds independent recovery for claims entailed by the
bounded compositional complete-effect sentence grammar.

Autofill/proposal has zero authority. A claim is recovered only when this layer
reparses the exact source sentence and obtains the identical inventory/field
coordinate.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v15_registry_base import verify_proof as verify_v12
from canonical.runtime.certified_compositional_natural_effect_clause_v1 import (
    parse_compositional_effect_clauses,
)
from canonical.runtime.certified_multi_effect_natural_clause_v1 import (
    parse_multi_effect_clauses,
)

SCHEMA="BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V16"


def _constraint(source_id:str,clause_id:str,kind:str,slot:str)->dict[str,Any]:
    return {
        "op":"ATOM",
        "id":"COMPOSITIONAL_EFFECT_CLAUSE::"+source_id+"::"+clause_id+"::"+kind+"::"+slot,
    }


def _match(claim:Mapping[str,Any],clauses:Sequence[Mapping[str,Any]]):
    kind=claim.get("kind")
    for row in clauses:
        effect=row.get("effect")
        inventory=row.get("inventory")
        if not isinstance(effect,Mapping) or not isinstance(inventory,Mapping):
            continue
        if kind=="CERTIFIED_EFFECT_ID_INVENTORY":
            if set(claim)!={"claim_id","kind","target_id","effect_ids"}:
                return None
            if (
                claim.get("target_id")==inventory.get("target_id")
                and list(claim.get("effect_ids") or [])==list(inventory.get("effect_ids") or [])
            ):
                return row
        elif kind=="CERTIFIED_DOCUMENT_EFFECT_FIELD":
            if set(claim)!={"claim_id","kind","effect_id","field","value"}:
                return None
            field=str(claim.get("field") or "")
            if (
                claim.get("effect_id")==effect.get("effect_id")
                and field in effect
                and claim.get("value")==effect.get(field)
            ):
                return row
    return None



def _match_multi(claim:Mapping[str,Any],groups:Sequence[Mapping[str,Any]]):
    kind=claim.get("kind")
    for group in groups:
        inv=group.get("inventory")
        effects=group.get("effects")
        if not isinstance(inv,Mapping) or not isinstance(effects,Sequence):
            continue
        if kind=="CERTIFIED_EFFECT_ID_INVENTORY":
            if set(claim)!={"claim_id","kind","target_id","effect_ids"}:
                return None
            if (
                claim.get("target_id")==inv.get("target_id")
                and list(claim.get("effect_ids") or [])==list(inv.get("effect_ids") or [])
            ):
                return ("inventory",group,None)
        elif kind=="CERTIFIED_DOCUMENT_EFFECT_FIELD":
            if set(claim)!={"claim_id","kind","effect_id","field","value"}:
                return None
            for item in effects:
                effect=item.get("effect") if isinstance(item,Mapping) else None
                if not isinstance(effect,Mapping):
                    continue
                field=str(claim.get("field") or "")
                if (
                    claim.get("effect_id")==effect.get("effect_id")
                    and field in effect
                    and claim.get("value")==effect.get(field)
                ):
                    return ("field",group,item)
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
    relation_verifier:Callable[[Mapping[str,Any]],Mapping[str,Any]|None]|None=None,
)->dict[str,Any]:
    if not isinstance(claims,Sequence) or isinstance(claims,(str,bytes)):
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":["CLAIMS_INVALID"],"terminal_authority":False,
        }

    base=verify_v12(
        source_text,
        source_id=source_id,
        claims=claims,
        typed_context=typed_context,
        expected_typed_context_sha256=expected_typed_context_sha256,
        fact_source=fact_source,
        fact_source_id=fact_source_id,
        relation_verifier=relation_verifier,
    )
    if base.get("status")=="FAIL_CLOSED":
        inherited=[
            str(x) for x in (base.get("errors") or [])
            if isinstance(x,str) and x
        ]
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED",
            "errors":sorted(set(["V12_PRIMITIVE_CHECK_FAIL_CLOSED"]+inherited)),
            "base_proof":base,"terminal_authority":False,
        }

    parsed=parse_compositional_effect_clauses(source_text,source=source_id)
    clauses=[x for x in (parsed.get("clauses") or []) if isinstance(x,Mapping)]

    accepted=list(base.get("accepted_claims") or [])
    rejected=list(base.get("rejected_claims") or [])
    proved=list(base.get("proved_constraints") or [])
    accepted_ids={str(x.get("claim_id") or "") for x in accepted if isinstance(x,Mapping)}
    originals={
        str(x.get("claim_id") or ""):x
        for x in claims
        if isinstance(x,Mapping) and str(x.get("claim_id") or "")
    }
    recovered=set()

    if parsed.get("status")=="PARSED":
        for cid,claim in originals.items():
            if cid in accepted_ids:
                continue
            row=_match(claim,clauses)
            if row is None:
                continue
            kind=str(claim.get("kind") or "")
            if kind=="CERTIFIED_EFFECT_ID_INVENTORY":
                slot="inventory:"+str(claim.get("target_id") or "")
                payload={
                    "claim_id":cid,
                    "kind":kind,
                    "target_id":claim.get("target_id"),
                    "effect_ids":list(claim.get("effect_ids") or []),
                }
            elif kind=="CERTIFIED_DOCUMENT_EFFECT_FIELD":
                slot=str(claim.get("effect_id") or "")+":"+str(claim.get("field") or "")
                payload={
                    "claim_id":cid,
                    "kind":kind,
                    "effect_id":claim.get("effect_id"),
                    "field":claim.get("field"),
                    "value":claim.get("value"),
                }
            else:
                continue
            atom=_constraint(source_id,str(row.get("clause_id") or ""),kind,slot)
            payload.update({
                "compositional_clause_id":row.get("clause_id"),
                "source_span_chars":list(row.get("source_span_chars") or []),
                "source_span_bytes":list(row.get("source_span_bytes") or []),
                "source_text_sha256":row.get("source_text_sha256"),
                "constraint":atom,
                "proof_primitive":"COMPOSITIONAL_NATURAL_EFFECT_CLAUSE_V1",
            })
            if kind=="CERTIFIED_DOCUMENT_EFFECT_FIELD":
                payload["field_id"]="COMP-FIELD-"+str(row.get("clause_id") or "")[-24:]
            accepted.append(payload)
            proved.append(atom)
            recovered.add(cid)

    if recovered:
        rejected=[
            x for x in rejected
            if not (isinstance(x,Mapping) and str(x.get("claim_id") or "") in recovered)
        ]


    multi=parse_multi_effect_clauses(source_text,source=source_id)
    groups=[x for x in (multi.get("groups") or []) if isinstance(x,Mapping)]
    recovered_multi=set()
    if multi.get("status")=="PARSED":
        for cid,claim in originals.items():
            if cid in accepted_ids or cid in recovered:
                continue
            matched=_match_multi(claim,groups)
            if matched is None:
                continue
            mode,group,item=matched
            kind=str(claim.get("kind") or "")
            if kind=="CERTIFIED_EFFECT_ID_INVENTORY":
                payload={
                    "claim_id":cid,
                    "kind":kind,
                    "target_id":claim.get("target_id"),
                    "effect_ids":list(claim.get("effect_ids") or []),
                    "group_id":group.get("group_id"),
                    "source_span_chars":list(group.get("header_source_span_chars") or []),
                    "source_span_bytes":list(group.get("header_source_span_bytes") or []),
                    "source_text_sha256":group.get("header_source_text_sha256"),
                    "proof_primitive":"MULTI_EFFECT_NATURAL_CLAUSE_V1",
                }
                slot="inventory:"+str(claim.get("target_id") or "")
            else:
                payload={
                    "claim_id":cid,
                    "kind":kind,
                    "effect_id":claim.get("effect_id"),
                    "field":claim.get("field"),
                    "value":claim.get("value"),
                    "group_id":group.get("group_id"),
                    "source_span_chars":list(item.get("body_source_span_chars") or []),
                    "source_span_bytes":list(item.get("body_source_span_bytes") or []),
                    "source_text_sha256":item.get("body_source_text_sha256"),
                    "proof_primitive":"MULTI_EFFECT_NATURAL_CLAUSE_V1",
                }
                slot=str(claim.get("effect_id") or "")+":"+str(claim.get("field") or "")
                payload["field_id"]="MULTI-FIELD-"+str(group.get("group_id") or "")[-24:]+"-"+str(claim.get("effect_id") or "")+"-"+str(claim.get("field") or "")
            atom=_constraint(source_id,str(group.get("group_id") or ""),kind,slot)
            payload["constraint"]=atom
            accepted.append(payload)
            proved.append(atom)
            recovered_multi.add(cid)

    if recovered_multi:
        rejected=[
            x for x in rejected
            if not (isinstance(x,Mapping) and str(x.get("claim_id") or "") in recovered_multi)
        ]

    return {
        "schema":SCHEMA,
        "status":"PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id":source_id,
        "accepted_claims":accepted,
        "rejected_claims":rejected,
        "proved_constraints":proved,
        "compositional_clause_parse_status":parsed.get("status"),
        "compositional_clause_parse_reason":parsed.get("reason"),
        "multi_effect_clause_parse_status":multi.get("status"),
        "multi_effect_clause_parse_reason":multi.get("reason"),
        "terminal_authority":False,
        "soundness_boundary":(
            "V16_PRESERVES_V15_AND_ADDS_COMPLETE_MULTI_EFFECT_SET_RECOVERY;"
            "AUTOFILL_HAS_ZERO_AUTHORITY_AND_EVERY_RECOVERED_COORDINATE_IS_REPARSED_FROM_EXACT_SOURCE;"
            "UNRECOGNIZED_PROSE_REMAINS_TOP"
        ),
    }
