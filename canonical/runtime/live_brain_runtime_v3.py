from typing import Mapping
from canonical.runtime import live_brain_runtime_v1 as v1
from canonical.runtime.r2_policy_cover_live_v1 import run as cover
SCHEMA="PROJECT_BRAIN_UNIFIED_LIVE_COGNITIVE_ARCHITECTURE_V3"

def run(request,**kw):
    if not isinstance(request,Mapping): return v1.run(request,**kw)
    nested=request.get("request")
    p=nested if isinstance(nested,Mapping) else request
    d=p.get("decision_payload") if isinstance(p,Mapping) else None
    if not isinstance(d,Mapping) or "observable_policy_cover" not in d:
        return v1.run(request,**kw)
    allowed={"repo_root","proposal_provider","capability_expander"}
    args={k:v for k,v in kw.items() if k in allowed}
    out=cover(p,**args)
    return {"schema":SCHEMA,"status":"UNIFIED_DECISION_EXECUTION_COMPLETE",
            "pass":out.get("pass") is True,"decision_controller":"R2_POLICY_COVER_LIVE_V1",
            "decision_output":out,"semantic_acceptance_complete":out.get("semantic_acceptance_complete") is True,
            "actual_goal_satisfaction_verified":out.get("actual_goal_satisfaction_verified") is True,
            "terminal_authority":False,"capability_promotion_authority":False,"terminal_credit_delta":0}
