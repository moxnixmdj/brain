from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_p1_router_v2 as v2
from canonical.runtime import professional_artifact_hard_defect_preflight_v1 as hard_gate

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V3"
PROFILE_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_V2"
HARD_STEP="RUN_FROZEN_SOURCE_OR_POLICY_BOUND_HARD_DEFECT_PREFLIGHT_WHEN_SUPPORTED"
TRIGGER_ROOTS=v2.TRIGGER_ROOTS
STEP_STATES=v2.STEP_STATES

def _base(status:str)->dict[str,Any]:
    return {
        "schema":SCHEMA,
        "status":status,
        "quality_judgment_authority":False,
        "semantic_truth_authority":False,
        "execution_authority":False,
        "new_root_authority":False,
        "acceptance_authority":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "capability_credit_delta":0,
        "incremental_spend_usd":0,
    }

def _fail(reason:str,**extra:Any)->dict[str,Any]:
    return {**_base("FAIL_CLOSED"),"reason":reason,**extra}

def _profile(repo_root:str|Path|None)->dict[str,Any]:
    root=Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    p=root/"canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V2.json"
    data=json.loads(p.read_text())
    if data.get("schema")!=PROFILE_SCHEMA:
        raise ValueError("PROFILE_SCHEMA_INVALID")
    return data

def _delegate_v2(state:Mapping[str,Any],repo_root:str|Path|None)->dict[str,Any]:
    out=dict(v2.route(state,repo_root=repo_root))
    out["schema"]=SCHEMA
    out["delegated_router_schema"]=v2.SCHEMA
    out["artifact_preflight_applied"]=False
    out["artifact_preflight_result"]=None
    return out

def route(state:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
    if not isinstance(state,Mapping):
        return _fail("STATE_NOT_OBJECT")

    request=state.get("artifact_preflight_request")
    if request is None:
        return _delegate_v2(state,repo_root)
    if not isinstance(request,Mapping):
        return _fail("ARTIFACT_PREFLIGHT_REQUEST_NOT_OBJECT")

    try:
        profile=_profile(repo_root)
    except Exception as exc:
        return _fail("PROFILE_LOAD_OR_SCHEMA_FAILURE:"+type(exc).__name__)

    steps=list(profile.get("steps") or [])
    declared=set(profile.get("escalation_triggers") or [])
    if (
        not steps
        or HARD_STEP not in steps
        or declared!=set(TRIGGER_ROOTS)
    ):
        return _fail("PROFILE_ROUTER_CONTRACT_DRIFT")

    triggers=state.get("detected_triggers",[])
    if not isinstance(triggers,list) or not all(isinstance(x,str) and x for x in triggers):
        return _fail("DETECTED_TRIGGERS_INVALID")
    unknown=sorted(set(triggers)-declared)
    if unknown:
        return _fail("UNKNOWN_ESCALATION_TRIGGER",unknown_triggers=unknown)

    results=state.get("step_results",{})
    if not isinstance(results,Mapping):
        return _fail("STEP_RESULTS_NOT_OBJECT")
    if HARD_STEP in results:
        return _fail("ARTIFACT_PREFLIGHT_STEP_CALLER_SELF_CERTIFICATION_FORBIDDEN")
    unknown_steps=sorted(set(results)-set(steps))
    if unknown_steps:
        return _fail("UNKNOWN_P1_STEP",unknown_steps=unknown_steps)
    invalid={k:v for k,v in results.items() if v not in STEP_STATES}
    if invalid:
        return _fail("STEP_RESULT_STATE_INVALID",invalid_step_states=invalid)

    preflight=hard_gate.verify(request)
    effective_results=dict(results)
    effective_results[HARD_STEP]="PASS" if preflight.get("pass") is True else "FAIL"

    failed=[s for s in steps if effective_results.get(s)=="FAIL"]
    unresolved=[
        s for s in steps
        if effective_results.get(s,"NOT_RUN") in {"OPEN","NOT_RUN"}
    ]
    shared={
        "artifact_preflight_applied":True,
        "artifact_preflight_result":preflight,
        "artifact_preflight_self_certified":False,
    }
    if failed:
        return {
            **_base("ABSTAIN__P1_HARD_FAILURE"),
            **shared,
            "route":"ABSTAIN",
            "blocking_steps":failed,
        }
    if unresolved:
        return {
            **_base("ABSTAIN__P1_INCOMPLETE"),
            **shared,
            "route":"ABSTAIN",
            "blocking_steps":unresolved,
        }

    unmapped=state.get("unmapped_material_false_certification_path")
    rep=state.get("unmapped_path_representation")
    if unmapped not in {None,False,True}:
        return _fail("UNMAPPED_PATH_FLAG_INVALID",**shared)
    if rep not in {None,"EXISTING_ROOTS","UNREPRESENTABLE","UNKNOWN"}:
        return _fail("UNMAPPED_PATH_REPRESENTATION_INVALID",**shared)
    if unmapped is True and rep in {None,"UNKNOWN"}:
        return {
            **_base("ABSTAIN__UNMAPPED_PATH_REPRESENTATION_UNKNOWN"),
            **shared,
            "route":"ABSTAIN",
        }
    if unmapped is True and rep=="UNREPRESENTABLE":
        return {
            **_base("ESCALATE__NEW_ROOT_CANDIDATE_REQUIRES_PROOF"),
            **shared,
            "route":"ARCHITECTURE_REVIEW",
            "new_root_candidate":True,
        }

    unique=sorted(set(triggers))
    roots=sorted({root for trigger in unique for root in TRIGGER_ROOTS[trigger]})
    if unique:
        return {
            **_base("ROUTE__ESCALATE_EXISTING_ASSURANCE_ROOTS"),
            **shared,
            "route":"ESCALATE",
            "detected_triggers":unique,
            "escalation_root_ids":roots,
            "new_root_candidate":False,
        }
    return {
        **_base("ROUTE__P1_ORDINARY_WITH_ARTIFACT_PREFLIGHT"),
        **shared,
        "route":"P1",
        "detected_triggers":[],
        "escalation_root_ids":[],
        "profile_steps":steps,
    }
