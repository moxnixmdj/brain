"""Goal-bound observable policy-cover selection for R2 V2."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import general_adequate_decision_controller_v1 as v1
from canonical.runtime.observable_policy_cover_executor_v1 import evaluate as evaluate_cover

SCHEMA="PROJECT_BRAIN_R2_POLICY_COVER_SELECTION_V1"
ROOT=Path(__file__).resolve().parents[2]


def _fail(status:str, reason:str, **extra:Any)->dict[str,Any]:
    return {
        "schema":SCHEMA,"status":status,"pass":False,"reason":reason,
        "semantic_acceptance_complete":False,
        "actual_goal_satisfaction_verified":False,
        "terminal_authority":False,"terminal_credit_delta":0,**extra,
    }


def run(request:Mapping[str,Any], *, repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root) if repo_root is not None else ROOT
    if not isinstance(request,Mapping):
        return _fail("FAIL_CLOSED","REQUEST_NOT_OBJECT")
    task_id=str(request.get("task_id") or "").strip()
    goal=str(request.get("goal") or "").strip()
    decision=request.get("decision_payload")
    if not task_id or not goal or not isinstance(decision,Mapping):
        return _fail("FAIL_CLOSED","TASK_GOAL_AND_DECISION_PAYLOAD_REQUIRED")
    cfg=decision.get("observable_policy_cover")
    if not isinstance(cfg,Mapping) or set(cfg)-{"problem","cover_binding"}:
        return _fail("FAIL_CLOSED","OBSERVABLE_POLICY_COVER_CONFIG_INVALID")

    raw=v1.compile_contract(
        goal,source_id="user",routing_target_effects=["decision.adequate_action"]
    )
    if raw.get("pass") is not True:
        return _fail("FAIL_CLOSED","LOSSLESS_RAW_GOAL_CONTRACT_FAILED",raw_contract=raw)

    goal_binding=v1._authenticate_goal_binding(
        request.get("goal_to_decision_binding"),
        goal=goal,decision_payload=decision,repo_root=root,
    )
    if goal_binding.get("pass") is not True:
        return _fail(
            str(goal_binding.get("status") or "OPEN__GOAL_TO_DECISION_BINDING_REQUIRED"),
            "GOAL_TO_DECISION_CONTEXT_NOT_AUTHENTICATED",
            task_id=task_id,goal=goal,raw_contract=raw,
            next_required_edge="AUTHENTICATED_GOAL_TO_DECISION_CONTEXT",
            goal_to_decision_binding=goal_binding,
        )

    cover=evaluate_cover(
        {
            "problem":cfg.get("problem"),
            "cover_binding":cfg.get("cover_binding"),
            "observation_bindings_by_discriminator_id":request.get(
                "policy_cover_observation_bindings",{}
            ),
            "max_observations":request.get("max_policy_cover_observations",64),
        },
        repo_root=root,
    )
    if cover.get("pass") is not True:
        next_edge=(
            "AUTHENTICATED_SELECTED_POLICY_CHANGING_OBSERVATION"
            if isinstance(cover.get("next_observation_request"),Mapping)
            else "AUTHENTICATED_OBSERVABLE_POLICY_COVER"
        )
        return _fail(
            str(cover.get("status") or "OPEN__OBSERVABLE_POLICY_COVER_UNRESOLVED"),
            str(cover.get("reason") or "POLICY_COVER_SELECTION_UNRESOLVED"),
            task_id=task_id,goal=goal,raw_contract=raw,
            goal_to_decision_binding=goal_binding,
            decision_result=cover,next_required_edge=next_edge,
            next_observation_request=cover.get("next_observation_request"),
        )

    pid=cover.get("selected_policy_id")
    if not isinstance(pid,str) or not pid:
        return _fail("FAIL_CLOSED","SELECTED_POLICY_ID_INVALID")
    return {
        "schema":SCHEMA,
        "status":"PASS__GOAL_BOUND_OBSERVABLE_POLICY_SELECTED",
        "pass":True,
        "task_id":task_id,
        "goal":goal,
        "goal_sha256":sha256(goal.encode("utf-8")).hexdigest(),
        "raw_contract":raw,
        "goal_to_decision_binding":goal_binding,
        "selected_policy_id":pid,
        "decision_result":{
            "pass":True,
            "status":"PASS__R2_AUTHENTICATED_OBSERVABLE_POLICY_COVER",
            "route":"OBSERVABLE_POLICY_COVER_EXECUTOR_V1",
            "selected_policy_id":pid,
            "policy_cover_result":cover,
        },
        "semantic_acceptance_complete":False,
        "actual_goal_satisfaction_verified":False,
        "terminal_authority":False,
        "terminal_credit_delta":0,
    }
