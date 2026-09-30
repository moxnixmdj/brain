#!/usr/bin/env python3
"""Bind a decomposed broad objective to qualified source primitives.

This bridge is deliberately narrow. It executes only the SOURCE_DISCOVERY role
with already-qualified model-independent primitives and verifies candidate
provenance. It never upgrades retrievability or DOI identity into authority,
primary-source status, relevance, evidence sufficiency, or a final answer.
"""
from __future__ import annotations

SCHEMA="PROJECT_BRAIN_BROAD_OBJECTIVE_SOURCE_ROLE_BINDING_V1"

class BroadObjectiveRoleBindingError(RuntimeError):
    pass

def run(goal,decomposition,source_discovery,provenance_verifier,*,limit=8,timeout=15):
    if not isinstance(decomposition,dict) or decomposition.get("status")!="DECOMPOSED":
        raise BroadObjectiveRoleBindingError("DECOMPOSED_BROAD_OBJECTIVE_REQUIRED")
    roles=decomposition.get("roles") or []
    source_roles=[r for r in roles if isinstance(r,dict) and r.get("role")=="SOURCE_DISCOVERY"]
    if len(source_roles)!=1:
        raise BroadObjectiveRoleBindingError("EXACTLY_ONE_SOURCE_DISCOVERY_ROLE_REQUIRED")
    limit=max(1,min(int(limit),12))
    timeout=max(2,min(int(timeout),30))
    discovered=source_discovery.discover(str(goal or ""),limit=limit,timeout=timeout)
    candidates=list((discovered or {}).get("candidates") or [])[:limit]
    checks=[]
    verified=[]
    for candidate in candidates:
        result=provenance_verifier.verify(candidate,timeout=timeout)
        checks.append({
            "candidate":candidate,
            "verification":result,
        })
        if (result or {}).get("status") in {
            "BIBLIOGRAPHIC_PROVENANCE_VERIFIED",
            "RETRIEVAL_PROVENANCE_VERIFIED",
        }:
            verified.append({
                "candidate":candidate,
                "verification":result,
            })
    status="SOURCE_PROVENANCE_READY" if verified else "SOURCE_PROVENANCE_UNAVAILABLE"
    remaining=[str(r.get("role")) for r in roles if isinstance(r,dict) and r.get("role")!="SOURCE_DISCOVERY"]
    return {
        "schema":SCHEMA,
        "status":status,
        "objective":str(goal or "").strip(),
        "source_discovery_role_status":"EXECUTED",
        "candidate_discovery_status":(discovered or {}).get("status"),
        "candidate_count":len(candidates),
        "provenance_verified_count":len(verified),
        "candidate_checks":checks,
        "remaining_roles":remaining,
        "next_required_capability":"MODEL_INDEPENDENT_SOURCE_AUTHORITY_PRIMARY_EVIDENCE_AND_RELEVANCE_VERIFICATION",
        "authority_status":"UNVERIFIED",
        "primary_source_status":"UNVERIFIED",
        "relevance_status":"UNVERIFIED",
        "evidence_sufficiency_status":"UNVERIFIED",
        "final_answer_status":"NOT_ATTEMPTED",
        "model_dependency_count":0,
        "incremental_spend_usd":0,
    }
