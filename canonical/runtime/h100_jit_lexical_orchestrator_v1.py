"""Deterministic JIT lexical source orchestrator for H100."""
from __future__ import annotations
from typing import Any, Mapping, Sequence

from canonical.runtime import h100_oewn_lexical_acquisition_v1 as oewn
from canonical.runtime import h100_lexical_source_fallback_v1 as fallback

SCHEMA="PROJECT_BRAIN_H100_JIT_LEXICAL_ORCHESTRATOR_V1"

class JITLexicalOrchestratorError(ValueError):
    pass

def resolve(
    *,
    term:Any,
    context:Any=None,
    oewn_knowledge:Mapping[str,Any]|None=None,
    source_records:Sequence[Mapping[str,Any]]|None=None,
)->dict[str,Any]:
    attempts=[]
    successes=[]

    if oewn_knowledge is not None:
        out=oewn.resolve_lexical_role(term,context,oewn_knowledge)
        attempts.append({"route":"OEWN_REAL_LEXICAL","status":out.get("status"),"role":out.get("role")})
        if out.get("status")=="ROLE_IDENTIFIED" and out.get("role") in {"INPUT","TARGET"}:
            successes.append(("OEWN_REAL_LEXICAL",str(out["role"])))

    if source_records is not None:
        out=fallback.resolve_source_relations(term,source_records)
        attempts.append({"route":"LEXICAL_SOURCE_FALLBACK","status":out.get("status"),"role":out.get("role")})
        if out.get("status")=="ROLE_IDENTIFIED" and out.get("role") in {"INPUT","TARGET"}:
            successes.append(("LEXICAL_SOURCE_FALLBACK",str(out["role"])))

    roles={role for _,role in successes}
    if len(roles)==1:
        role=next(iter(roles))
        return {
            "schema":SCHEMA,
            "status":"ROLE_IDENTIFIED",
            "role":role,
            "successful_routes":[route for route,r in successes if r==role],
            "route_attempts":attempts,
            "persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
        }
    if len(roles)>1:
        return {
            "schema":SCHEMA,
            "status":"ABSTAIN_SOURCE_ROLE_CONFLICT",
            "role":None,
            "successful_routes":[route for route,_ in successes],
            "route_attempts":attempts,
            "persistent_learned_bytes":0,
            "external_learned_capability_calls":0,
        }
    return {
        "schema":SCHEMA,
        "status":"ABSTAIN_NO_VERIFIED_LEXICAL_ROLE",
        "role":None,
        "successful_routes":[],
        "route_attempts":attempts,
        "persistent_learned_bytes":0,
        "external_learned_capability_calls":0,
    }
