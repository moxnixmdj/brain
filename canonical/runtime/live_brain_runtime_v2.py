"""Live Brain V2: R2 V2 for decisions, V1 unchanged otherwise."""
from copy import deepcopy
from typing import Mapping
from canonical.runtime import live_brain_runtime_v1 as v1
from canonical.runtime import general_adequate_decision_controller_v2 as d2
SCHEMA="PROJECT_BRAIN_UNIFIED_LIVE_COGNITIVE_ARCHITECTURE_V2"

def run(request,*,repo_root=v1.ROOT,information_provider=None,proposal_provider=None,capability_expander=None):
    if not isinstance(request,Mapping):
        return v1.run(request,repo_root=repo_root)
    mode=str(request.get("mode") or "").strip()
    decision=(mode=="decision" or (not mode and isinstance(request.get("goal"),str) and bool(request.get("goal"))))
    if not decision:
        return v1.run(request,repo_root=repo_root,information_provider=information_provider,
                      proposal_provider=proposal_provider,capability_expander=capability_expander)
    nested=request.get("request")
    if isinstance(nested,Mapping):
        payload=nested
    else:
        keys={"task_id","goal","decision_payload","goal_to_decision_binding","execution_problem",
              "policy_execution_binding","goal_satisfaction_binding","max_information_rounds",
              "policy_cover_observation_bindings","max_policy_cover_observations","episode_id","scope_id"}
        payload={k:deepcopy(v) for k,v in request.items() if k in keys}
    out=d2.run(payload,repo_root=repo_root,information_provider=information_provider,
               proposal_provider=proposal_provider,capability_expander=capability_expander)
    if isinstance(out,Mapping) and out.get("r2_v2_route")=="OBSERVABLE_POLICY_COVER":
        out=deepcopy(dict(out)); out["schema"]="PROJECT_BRAIN_GENERAL_ADEQUATE_DECISION_CONTROLLER_V2"
    execution=out.get("execution_result") if isinstance(out,Mapping) else None
    learning=None
    if request.get("learn",True) is not False and isinstance(execution,Mapping):
        learning=v1._integrate_learning(execution,state_path=request.get("state_path"))
    return {"schema":SCHEMA,"status":"UNIFIED_DECISION_EXECUTION_COMPLETE",
            "pass":out.get("pass") is True,"decision_controller":"GENERAL_ADEQUATE_DECISION_CONTROLLER_V2",
            "decision_output":out,"learning":learning,
            "semantic_acceptance_complete":out.get("semantic_acceptance_complete") is True,
            "actual_goal_satisfaction_verified":out.get("actual_goal_satisfaction_verified") is True,
            "terminal_authority":False,"capability_promotion_authority":False,"terminal_credit_delta":0}
