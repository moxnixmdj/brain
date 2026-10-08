from canonical.runtime.r2_policy_cover_execution_v2 import run as execute
from canonical.runtime.r2_policy_cover_acceptance_gate_v2 import evaluate as accept
SCHEMA="PROJECT_BRAIN_R2_POLICY_COVER_LIVE_V1"

def run(request,**kw):
    e=execute(request,repo_root=kw.get("repo_root"),proposal_provider=kw.get("proposal_provider"),capability_expander=kw.get("capability_expander"))
    if e.get("pass") is not True: return e
    a=accept(request,e,repo_root=kw.get("repo_root"))
    if a.get("pass") is not True: return a
    s=e["selection"]; raw=s.get("raw_contract") or {}
    return {"schema":SCHEMA,"status":"PASS__GOAL_BOUND_POLICY_COVER_EXECUTED_AND_ACCEPTANCE_VERIFIED","pass":True,
            "task_id":s.get("task_id"),"goal_sha256":s.get("goal_sha256"),
            "raw_task_contract_sha256":raw.get("task_contract_sha256"),
            "decision_result":s.get("decision_result"),"selected_policy_id":e.get("selected_policy_id"),
            "execution_result":e.get("execution_result"),"realization":a.get("realization"),
            "goal_satisfaction_binding":a.get("acceptance"),
            "semantic_acceptance_complete":True,"actual_goal_satisfaction_verified":True,
            "terminal_authority":False,"terminal_credit_delta":0}
