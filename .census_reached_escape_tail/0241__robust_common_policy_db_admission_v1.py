"""Robust D_B admission without full objective identification.

A context cell may enter D_B by either:
A) complete-objective comparator erasure, handled elsewhere; or
B) a Brain-owned deployed policy independently certified adequate in every
   still-possible terminally relevant completion of the cell.

This bridge implements route B. It deliberately does not infer hypothesis-set
completeness or adequacy. Those are authenticated upstream obligations.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_ROBUST_COMMON_POLICY_DB_ADMISSION_V1"

def _fail(reason:str, **detail:Any)->dict[str,Any]:
    out={
        "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
        "db_admission_authorized":False,"u_empty_authorized":False,
        "terminal_authority":False,"terminal_credit_delta":0,
    }
    if detail:
        out["detail"]=detail
    return out

def evaluate(payload:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(payload,Mapping):
        return _fail("PAYLOAD_MAPPING_REQUIRED")

    cell_id=payload.get("cell_id")
    policy_id=payload.get("policy_id")
    if not all(isinstance(x,str) and x.strip() for x in (cell_id,policy_id)):
        return _fail("IDENTITY_BINDING_INVALID")

    if payload.get("cell_scope_sound") is not True:
        return _fail("CELL_SCOPE_NOT_PROVED")
    if payload.get("possibility_set_complete") is not True:
        return _fail("POSSIBILITY_SET_COMPLETENESS_UNPROVED")
    if payload.get("all_load_bearing_terminal_dimensions_bound") is not True:
        return _fail("TERMINAL_DIMENSION_COMPLETENESS_UNPROVED")
    if payload.get("brain_owned_policy_proved") is not True:
        return _fail("BRAIN_OWNERSHIP_UNPROVED")
    if payload.get("deployed_route_exactly_realizes_policy") is not True:
        return _fail("DEPLOYED_ROUTE_REALIZATION_UNPROVED")
    if payload.get("authorized_resource_bound_proved") is not True:
        return _fail("RESOURCE_BOUND_UNPROVED")

    worlds=payload.get("worlds")
    if not isinstance(worlds,Sequence) or isinstance(worlds,(str,bytes)) or not worlds:
        return _fail("WORLDS_REQUIRED")
    seen=set()
    for i,row in enumerate(worlds):
        if not isinstance(row,Mapping):
            return _fail("WORLD_INVALID",index=i)
        wid=row.get("world_id")
        if not isinstance(wid,str) or not wid or wid in seen:
            return _fail("WORLD_ID_INVALID",index=i)
        seen.add(wid)
        if row.get("policy_adequate") is not True:
            return _fail("COMMON_POLICY_NOT_ADEQUATE_IN_WORLD",world_id=wid)
        if row.get("adequacy_independently_verified") is not True:
            return _fail("ADEQUACY_NOT_INDEPENDENTLY_VERIFIED",world_id=wid)
        if row.get("hard_constraints_satisfied") is not True:
            return _fail("HARD_CONSTRAINT_FAILURE",world_id=wid)

    bindings=payload.get("content_bindings")
    if not isinstance(bindings,Mapping) or not bindings:
        return _fail("CONTENT_BINDINGS_REQUIRED")
    if any(not isinstance(k,str) or not k or not isinstance(v,str) or not v for k,v in bindings.items()):
        return _fail("CONTENT_BINDING_INVALID")

    return {
        "schema":SCHEMA,
        "pass":True,
        "status":"PASS__ROBUST_COMMON_POLICY_CELL_ADMISSIBLE_TO_D_B",
        "cell_id":cell_id,
        "policy_id":policy_id,
        "world_count":len(worlds),
        "db_admission_authorized":True,
        "objective_identification_required":False,
        "target_identity_required":False,
        "target_score_required":False,
        "u_empty_authorized":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "boundary":"CELL_ONLY__GLOBAL_U_CLOSURE_REQUIRES_SCOPE_COMPLETE_COVER_OF_ALL_REMAINING_ESCAPE",
    }
