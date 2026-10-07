from __future__ import annotations
from typing import Any, Mapping
from canonical.runtime.universal_verified_adaptive_solver_v1 import (
    BUILTIN_VERIFIERS, PROPOSAL_FREE_VERIFIERS, _normalize_caps,
)

SCHEMA="PROJECT_BRAIN_PROPOSAL_GENERATION_OWNERSHIP_GATE_V1"

def classify(problem: Mapping[str,Any])->dict[str,Any]:
    try:
        caps=_normalize_caps(problem)
    except Exception as exc:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "errors":[type(exc).__name__+":"+str(exc)],"terminal_authority":False}
    rows=[]; dependent=[]; free=[]; effect=[]
    for cid,cap in sorted(caps.items()):
        action=cap["action"]
        action_type=str(action.get("type") or "")
        if action_type=="verified_effect_tool":
            vid=str(action.get("pre_verifier_id") or "")
            dep="EFFECT_TOOL_ROUTE_REQUIRES_SEPARATE_EXECUTOR_OWNERSHIP_ANALYSIS"
            effect.append(cid)
        else:
            vid=str(action.get("verifier_id") or "")
            if vid in PROPOSAL_FREE_VERIFIERS:
                dep="PROPOSAL_FREE_VERIFIER_ROUTE"; free.append(cid)
            else:
                dep="CALLER_PROPOSAL_REQUIRED_BY_SOLVER_CORE"; dependent.append(cid)
        rows.append({"capability_id":cid,"action_type":action_type,
                     "verifier_id":vid,"proposal_dependency":dep})
    return {
        "schema":SCHEMA,"status":"CLASSIFIED","pass":True,
        "builtin_verifier_registry":sorted(BUILTIN_VERIFIERS),
        "proposal_free_verifiers":sorted(PROPOSAL_FREE_VERIFIERS),
        "capabilities":rows,
        "proposal_dependent_capability_ids":dependent,
        "proposal_free_capability_ids":free,
        "effect_tool_capability_ids":effect,
        "solver_core_alone_generates_all_required_proposals":not dependent and not effect,
        "ownership_rule":"PROPOSAL_DEPENDENT_EDGES_REQUIRE_A_BRAIN_OWNED_VERIFIED_GENERATOR_OR_EXACT_PROPOSAL_FREE_CONSTRUCTOR",
        "terminal_authority":False,"capability_credit_delta":0,"ownership_credit_delta":0,
    }
