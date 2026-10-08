"""R2 policy-cover execution V2.

Never trusts a caller-supplied selection receipt. It recomputes authenticated
selection from the original request before any effectful execution.
"""
from pathlib import Path
from typing import Mapping
from canonical.runtime import general_adequate_decision_controller_v1 as v1
from canonical.runtime.r2_policy_cover_selection_v1 import run as select_cover
SCHEMA="PROJECT_BRAIN_R2_POLICY_COVER_EXECUTION_V2"
ROOT=Path(__file__).resolve().parents[2]

def run(request,*,repo_root=None,proposal_provider=None,capability_expander=None):
    root=Path(repo_root) if repo_root is not None else ROOT
    if not isinstance(request,Mapping):
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "reason":"REQUEST_NOT_OBJECT","terminal_authority":False}
    selection=select_cover(request,repo_root=root)
    if selection.get("pass") is not True:
        out=dict(selection); out["schema"]=SCHEMA; out["execution_authority"]=False
        return out
    pid=selection.get("selected_policy_id")
    problem=request.get("execution_problem")
    if not isinstance(pid,str) or not pid:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
                "reason":"SELECTED_POLICY_ID_INVALID","terminal_authority":False}
    if not isinstance(problem,Mapping):
        return {"schema":SCHEMA,"status":"OPEN__ADEQUATE_POLICY_REALIZATION_REQUIRED","pass":False,
                "selection":selection,
                "next_required_edge":"AUTHENTICATED_SELECTED_POLICY_TO_EXECUTION_BINDING",
                "terminal_authority":False}
    binding=v1._authenticate_policy_execution_binding(
        request.get("policy_execution_binding"),selected_policy_id=pid,
        execution_problem=problem,repo_root=root)
    if binding.get("pass") is not True:
        return {"schema":SCHEMA,
                "status":str(binding.get("status") or "OPEN__POLICY_EXECUTION_BINDING_REQUIRED"),
                "pass":False,"selection":selection,"policy_execution_binding":binding,
                "next_required_edge":"AUTHENTICATED_SELECTED_POLICY_TO_EXECUTION_BINDING",
                "terminal_authority":False}
    execution=v1.run_universal(
        problem,repo_root=root,
        episode_id=str(request.get("episode_id") or selection.get("task_id")),
        scope_id=str(request.get("scope_id") or "r2-policy-cover-v2"),
        proposal_provider=proposal_provider,capability_expander=capability_expander)
    if execution.get("pass") is not True:
        return {"schema":SCHEMA,"status":"OPEN__SELECTED_ADEQUATE_POLICY_EXECUTION_UNRESOLVED",
                "pass":False,"selection":selection,"policy_execution_binding":binding,
                "execution_result":execution,
                "next_required_edge":"UNIVERSAL_SOLVER_EXACT_NEXT_REQUIRED_INPUT_OR_CAPABILITY",
                "terminal_authority":False}
    return {"schema":SCHEMA,"status":"PASS__SELECTED_POLICY_COVER_EXECUTION_VERIFIED",
            "pass":True,"selection":selection,"selected_policy_id":pid,
            "policy_execution_binding":binding,"execution_result":execution,
            "execution_authority":True,"terminal_authority":False,"terminal_credit_delta":0}
