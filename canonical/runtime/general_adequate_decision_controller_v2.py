"""R2 adequate-decision controller V2.

Preserves V1 exactly unless decision_payload explicitly contains
observable_policy_cover. That explicit route composes authenticated cover
selection, verified execution, and independent actual-goal acceptance.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Mapping

from canonical.runtime import general_adequate_decision_controller_v1 as v1
from canonical.runtime.r2_policy_cover_selection_v1 import run as select_cover
from canonical.runtime.r2_policy_cover_execution_v1 import run as execute_cover
from canonical.runtime.r2_policy_cover_acceptance_gate_v1 import evaluate as accept_cover

SCHEMA="PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_CONTROLLER_V2"
ROOT=Path(__file__).resolve().parents[2]


def run(
    request:Mapping[str,Any], *,
    repo_root:str|Path|None=None,
    information_provider:Callable[[Mapping[str,Any],int],Mapping[str,Any]|None]|None=None,
    proposal_provider:Callable[...,Mapping[str,Any]|None]|None=None,
    capability_expander:Callable[...,Mapping[str,Any]|None]|None=None,
)->dict[str,Any]:
    root=Path(repo_root) if repo_root is not None else ROOT
    decision=request.get("decision_payload") if isinstance(request,Mapping) else None
    if not isinstance(decision,Mapping) or "observable_policy_cover" not in decision:
        out=v1.run(
            request,repo_root=root,information_provider=information_provider,
            proposal_provider=proposal_provider,capability_expander=capability_expander)
        if isinstance(out,Mapping):
            out=deepcopy(dict(out)); out["r2_v2_route"]="V1_PRESERVED"
        return out

    selected=select_cover(request,repo_root=root)
    if selected.get("pass") is not True:
        return {"schema":SCHEMA,"r2_v2_route":"OBSERVABLE_POLICY_COVER",**dict(selected)}

    executed=execute_cover(
        request,selected,repo_root=root,
        proposal_provider=proposal_provider,capability_expander=capability_expander)
    if executed.get("pass") is not True:
        return {"schema":SCHEMA,"r2_v2_route":"OBSERVABLE_POLICY_COVER",**dict(executed)}

    accepted=accept_cover(request,executed,repo_root=root)
    if accepted.get("pass") is not True:
        return {"schema":SCHEMA,"r2_v2_route":"OBSERVABLE_POLICY_COVER",**dict(accepted)}

    sel=executed["selection"]
    raw=sel.get("raw_contract") or {}
    return {
        "schema":SCHEMA,
        "status":"PASS__GOAL_BOUND_POLICY_COVER_EXECUTED_AND_ACCEPTANCE_VERIFIED",
        "pass":True,
        "task_id":sel.get("task_id"),
        "goal_sha256":sel.get("goal_sha256"),
        "raw_task_contract_sha256":raw.get("task_contract_sha256"),
        "raw_source_coverage_complete":raw.get("nonwhitespace_source_coverage_complete"),
        "goal_to_decision_binding":sel.get("goal_to_decision_binding"),
        "decision_result":sel.get("decision_result"),
        "selected_policy_id":executed.get("selected_policy_id"),
        "policy_execution_binding":executed.get("policy_execution_binding"),
        "execution_result":executed.get("execution_result"),
        "realization":accepted.get("realization"),
        "goal_satisfaction_binding":accepted.get("acceptance"),
        "semantic_acceptance_complete":True,
        "actual_goal_satisfaction_verified":True,
        "r2_v2_route":"OBSERVABLE_POLICY_COVER",
        "terminal_authority":False,
        "terminal_credit_delta":0,
        "incremental_spend_usd":0,
    }
