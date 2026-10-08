from copy import deepcopy
from typing import Mapping
from canonical.runtime import unified_cognitive_fabric_v1 as f1
from canonical.runtime import general_adequate_decision_controller_v1 as d1
from canonical.runtime.r2_policy_cover_live_v1 import run as cover_run
SCHEMA="PROJECT_BRAIN_UNIFIED_COGNITIVE_FABRIC_V2"

class _DecisionV2:
    @staticmethod
    def run(payload,**kw):
        d=payload.get("decision_payload") if isinstance(payload,Mapping) else None
        if isinstance(d,Mapping) and "observable_policy_cover" in d:
            allowed={"repo_root","proposal_provider","capability_expander"}
            return cover_run(payload,**{k:v for k,v in kw.items() if k in allowed})
        return d1.run(payload,**kw)
decision_v2=_DecisionV2()

def run(request,**kw):
    if not isinstance(request,Mapping) or str(request.get("mode") or "").upper()!="ADEQUATE_DECISION":
        return f1.run(request,**kw)
    payload=request.get("payload") or {}
    out=decision_v2.run(payload,**kw)
    return {"schema":SCHEMA,"status":"FABRIC_DISPATCH_COMPLETE","mode":"ADEQUATE_DECISION",
            "requested_mode":"ADEQUATE_DECISION","auto_routed":False,
            "engine":"R2_POLICY_COVER_LIVE_V1_OR_V1_DECISION",
            "inner_pass":out.get("pass") is True,"inner_status":out.get("status"),
            "result":deepcopy(dict(out)),"single_front_door":True,
            "terminal_authority":False,"terminal_credit_delta":0}
