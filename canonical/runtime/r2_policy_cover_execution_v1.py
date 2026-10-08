"""Execute one authenticated R2 policy-cover selection."""
from __future__ import annotations
from pathlib import Path
from typing import Any, Callable, Mapping
from canonical.runtime import general_adequate_decision_controller_v1 as v1
from canonical.runtime.r2_policy_cover_selection_v1 import SCHEMA as SEL

SCHEMA="PROJECT_BRAIN_R2_POLICY_COVER_EXECUTION_V1"
ROOT=Path(__file__).resolve().parents[2]

def run(request:Mapping[str,Any], selection:Mapping[str,Any], *,
        repo_root:str|Path|None=None,
        proposal_provider:Callable[...,Mapping[str,Any]|None]|None=None,
        capability_expander:Callable[...,Mapping[str,Any]|None]|None=None)->dict[str,Any]:
    root=Path(repo_root) if repo_root is not None else ROOT
    if not isinstance(selection,Mapping) or selection.get("schema")!=SEL or selection.get("pass") is not True:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "reason":"AUTHENTICATED_POLICY_COVER_SELECTION_REQUIRED",
                "terminal_authority":False,"terminal_credit_delta":0}
    pid=selection.get("selected_policy_id")
    problem=request.get("execution_problem") if isinstance(request,Mapping) else None
    if not isinstance(pid,str) or not pid:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "reason":"SELECTED_POLICY_ID_INVALID",
                "terminal_authority":False,"terminal_credit_delta":0}
    if not isinstance(problem,Mapping):
        return {"schema":SCHEMA,"status":"OPEN__ADEQUATE_POLICY_REALIZATION_REQUIRED","pass":False,
                "next_required_edge":"AUTHENTICATED_SELECTED_POLICY_TO_EXECUTION_BINDING",
                "selection":selection,"terminal_authority":False,"terminal_credit_delta":0}
    binding=v1._authenticate_policy_execution_binding(
        request.get("policy_execution_binding"),selected_policy_id=pid,
        execution_problem=problem,repo_root=root)
    if binding.get("pass") is not True:
        return {"schema":SCHEMA,
                "status":str(binding.get("status") or "OPEN__POLICY_EXECUTION_BINDING_REQUIRED"),
                "pass":False,
                "next_required_edge":"AUTHENTICATED_SELECTED_POLICY_TO_EXECUTION_BINDING",
                "selection":selection,"policy_execution_binding":binding,
                "terminal_authority":False,"terminal_credit_delta":0}
    execution=v1.run_universal(
        problem,repo_root=root,
        episode_id=str(request.get("episode_id") or selection.get("task_id")),
        scope_id=str(request.get("scope_id") or "r2-policy-cover-v1"),
        proposal_provider=proposal_provider,capability_expander=capability_expander)
    if execution.get("pass") is not True:
        return {"schema":SCHEMA,"status":"OPEN__SELECTED_ADEQUATE_POLICY_EXECUTION_UNRESOLVED",
                "pass":False,
                "next_required_edge":"UNIVERSAL_SOLVER_EXACT_NEXT_REQUIRED_INPUT_OR_CAPABILITY",
                "selection":selection,"policy_execution_binding":binding,
                "execution_result":execution,"terminal_authority":False,"terminal_credit_delta":0}
    return {"schema":SCHEMA,"status":"PASS__SELECTED_POLICY_COVER_EXECUTION_VERIFIED","pass":True,
            "selection":selection,"selected_policy_id":pid,
            "policy_execution_binding":binding,"execution_result":execution,
            "terminal_authority":False,"terminal_credit_delta":0}
