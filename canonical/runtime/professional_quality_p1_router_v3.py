from copy import deepcopy
from canonical.runtime import professional_artifact_hard_defect_preflight_v1 as hard
from canonical.runtime import professional_quality_p1_router_v2 as base

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V3"
PREFLIGHT_STEP="RUN_FROZEN_SOURCE_OR_POLICY_BOUND_HARD_DEFECT_PREFLIGHT_WHEN_SUPPORTED"

def _fail(reason):
    out=base._base("FAIL_CLOSED")
    out.update({"schema":SCHEMA,"reason":reason})
    return out

def route(state,*,repo_root=None):
    if not isinstance(state,dict):
        return _fail("STATE_NOT_OBJECT")
    supplied=state.get("step_results",{})
    if not isinstance(supplied,dict):
        return _fail("STEP_RESULTS_NOT_OBJECT")
    if PREFLIGHT_STEP in supplied:
        return _fail("PREFLIGHT_SELF_ATTESTATION_FORBIDDEN")
    if ("artifact_paths" in state)!=("hard_defect_profile_id" in state):
        return _fail("PREFLIGHT_INPUT_PAIR_REQUIRED")
    if "artifact_paths" not in state:
        out=base._base("ABSTAIN__P1_INCOMPLETE")
        out.update({"schema":SCHEMA,"route":"ABSTAIN","blocking_steps":[PREFLIGHT_STEP]})
        return out
    pre=hard.verify({"artifact_paths":state["artifact_paths"],"profile_id":state["hard_defect_profile_id"]})
    if pre.get("pass") is not True:
        out=base._base("ABSTAIN__P1_HARD_FAILURE")
        out.update({"schema":SCHEMA,"route":"ABSTAIN","blocking_steps":[PREFLIGHT_STEP],"hard_defect_preflight_result":pre})
        return out
    delegated=deepcopy(state)
    delegated.pop("artifact_paths",None)
    delegated.pop("hard_defect_profile_id",None)
    out=base.route(delegated,repo_root=repo_root)
    out["schema"]=SCHEMA
    out["hard_defect_preflight_result"]=pre
    out["preflight_self_attestation_allowed"]=False
    return out
