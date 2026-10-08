"""Final actual-goal acceptance gate for R2 policy-cover execution."""
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import general_adequate_decision_controller_v1 as v1
from canonical.runtime.r2_policy_cover_execution_v1 import SCHEMA as EXEC

SCHEMA="PROJECT_BRAIN_R2_POLICY_COVER_ACCEPTANCE_GATE_V1"
ROOT=Path(__file__).resolve().parents[2]

def evaluate(request:Mapping[str,Any], executed:Mapping[str,Any], *,
             repo_root:str|Path|None=None)->dict[str,Any]:
    root=Path(repo_root) if repo_root is not None else ROOT
    if not isinstance(executed,Mapping) or executed.get("schema")!=EXEC or executed.get("pass") is not True:
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED",
                "reason":"VERIFIED_POLICY_COVER_EXECUTION_REQUIRED",
                "actual_goal_satisfaction_verified":False,"terminal_authority":False}
    selection=executed.get("selection")
    if not isinstance(selection,Mapping):
        return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED",
                "reason":"SELECTION_RECEIPT_MISSING",
                "actual_goal_satisfaction_verified":False,"terminal_authority":False}
    pid=executed.get("selected_policy_id")
    goal=selection.get("goal")
    execution=executed.get("execution_result")
    realization={"kind":"VERIFIED_POLICY_COVER_EXECUTION","policy_id":pid,
                 "policy_cover_result_sha256":v1._digest(selection.get("decision_result")),
                 "execution_result":execution}
    out=v1._authenticate_goal_satisfaction_binding(
        request.get("goal_satisfaction_binding") if isinstance(request,Mapping) else None,
        goal=str(goal or ""),selected_policy_id=str(pid or ""),
        realization=realization,repo_root=root)
    return {"schema":SCHEMA,"pass":out.get("pass") is True,
            "status":out.get("status"),"acceptance":out,"realization":realization,
            "actual_goal_satisfaction_verified":out.get("pass") is True,
            "terminal_authority":False,"terminal_credit_delta":0}
