"""Source-aligned semantic proof checker V14.

V13 preserves V12 and adds independent recovery for claims entailed by the
bounded compositional complete-effect sentence grammar.

Autofill/proposal has zero authority. A claim is recovered only when this layer
reparses the exact source sentence and obtains the identical inventory/field
coordinate.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from canonical.runtime.source_aligned_semantic_proof_v14_registry_base import verify_proof as verify_v12
from canonical.runtime.certified_compositional_natural_effect_clause_v1 import (
    parse_compositional_effect_clauses,
)

SCHEMA="BRAIN_SOURCE_ALIGNED_SEMANTIC_PROOF_V14"


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

    return {
        "schema":SCHEMA,
        "status":"PROOF_CHECKED" if not rejected else "PROOF_CHECKED_WITH_REJECTIONS",
        "source_id":source_id,
        "accepted_claims":accepted,
        "rejected_claims":rejected,
        "proved_constraints":proved,
        "compositional_clause_parse_status":parsed.get("status"),
        "compositional_clause_parse_reason":parsed.get("reason"),
        "terminal_authority":False,
        "soundness_boundary":(
            "V14_PRESERVES_V13_COMPOSITIONAL_CLAUSE_RECOVERY_AND_ADDS_REGISTRY_V2_NONEXPLICIT_IMPLICATION_CLOSURE;"
            "AUTOFILL_HAS_ZERO_AUTHORITY_AND_EVERY_RECOVERED_COORDINATE_IS_REPARSED_FROM_EXACT_SOURCE;"
            "UNRECOGNIZED_PROSE_REMAINS_TOP"
        ),
    }
