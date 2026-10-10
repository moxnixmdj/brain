"""Source-proof to D_B positive-admission bridge.

This composes the existing proof-carrying semantic refinement with deployed
Brain-route evidence. It deliberately does not enumerate or claim completeness
of an interpretation set. The semantic state is a sound over-approximation:
missing source facts leave more models alive.

A cell is admitted only when the selected Brain-owned policy's authenticated
adequacy condition is entailed across every model of that over-approximation.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

from canonical.runtime.proof_carrying_semantic_refinement_v6 import resolve_from_source_proof

SCHEMA="PROJECT_BRAIN_SOURCE_POSITIVE_ADEQUACY_DB_ADMISSION_V1"

def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "db_admission_authorized":False,"interpretation_set_enumeration_required":False,
        "u_empty_authorized":False,"terminal_authority":False,"terminal_credit_delta":0,
    }
    if detail:
        out["detail"]=detail
    return out

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    cell_id=payload.get("cell_id")
    policy_id=payload.get("selected_policy_id")
    if not all(isinstance(x,str) and x.strip() for x in (cell_id,policy_id)):
        return _fail("CELL_OR_POLICY_ID_INVALID")

    for field in (
        "cell_scope_sound",
        "brain_owned_policy_proved",
        "deployed_route_exactly_realizes_policy",
        "authorized_resource_bound_proved",
    ):
        if payload.get(field) is not True:
            return _fail("REQUIRED_ROUTE_PREMISE_UNPROVED:"+field)

    source_text=payload.get("source_text")
    source_id=payload.get("source_id")
    claims=payload.get("claims",[])
    decision_basis=payload.get("decision_basis")
    policy_conditions=payload.get("policy_conditions")
    adequacy=payload.get("policy_adequacy_bindings")
    if not isinstance(source_text,str) or not source_text:
        return _fail("SOURCE_TEXT_REQUIRED")
    if not isinstance(source_id,str) or not source_id:
        return _fail("SOURCE_ID_REQUIRED")
    if not isinstance(claims,Sequence) or isinstance(claims,(str,bytes)):
        return _fail("CLAIMS_SEQUENCE_REQUIRED")
    if not isinstance(decision_basis,Sequence) or isinstance(decision_basis,(str,bytes)) or not decision_basis:
        return _fail("DECISION_BASIS_REQUIRED")
    if not isinstance(policy_conditions,Mapping) or policy_id not in policy_conditions:
        return _fail("SELECTED_POLICY_CONDITION_REQUIRED")
    if not isinstance(adequacy,Mapping) or policy_id not in adequacy:
        return _fail("SELECTED_POLICY_ADEQUACY_BINDING_REQUIRED")

    result=resolve_from_source_proof(
        source_text,
        source_id=source_id,
        claims=claims,
        decision_basis=decision_basis,
        policy_conditions=policy_conditions,
        typed_context=payload.get("typed_context"),
        expected_typed_context_sha256=payload.get("expected_typed_context_sha256"),
        fact_source=payload.get("fact_source"),
        fact_source_id=payload.get("fact_source_id"),
        policy_adequacy_bindings=adequacy,
    )
    if result.get("status")!="COMMON_POLICY_CERTIFIED":
        return {
            "schema":SCHEMA,
            "pass":False,
            "status":"UNRESOLVED__POSITIVE_ADEQUACY_NOT_ENTAILED",
            "cell_id":cell_id,
            "selected_policy_id":policy_id,
            "refinement":result,
            "db_admission_authorized":False,
            "interpretation_set_enumeration_required":False,
            "u_empty_authorized":False,
            "terminal_authority":False,
            "terminal_credit_delta":0,
        }

    certified=set(result.get("certified_common_policies") or [])
    if policy_id not in certified:
        return _fail("DECLARED_POLICY_NOT_CERTIFIED",certified=sorted(certified))

    bindings=payload.get("content_bindings")
    if not isinstance(bindings,Mapping) or not bindings:
        return _fail("CONTENT_BINDINGS_REQUIRED")
    if any(not isinstance(k,str) or not k or not isinstance(v,str) or not v for k,v in bindings.items()):
        return _fail("CONTENT_BINDING_INVALID")

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__SOURCE_PROVED_POSITIVE_ADEQUACY_CELL_ADMISSIBLE_TO_D_B",
        "cell_id":cell_id,
        "selected_policy_id":policy_id,
        "db_admission_authorized":True,
        "interpretation_set_enumeration_required":False,
        "exact_interpretation_set_completeness_required":False,
        "semantic_overapproximation_used":True,
        "source_refinement":result,
        "u_empty_authorized":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "boundary":"CELL_ONLY__GLOBAL_U_CLOSURE_REQUIRES_SCOPE_COMPLETE_UNION_OF_SOUND_D_B_ADMISSIONS",
    }
