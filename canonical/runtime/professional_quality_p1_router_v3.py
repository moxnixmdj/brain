from copy import deepcopy
from pathlib import Path
import json
from canonical.runtime import professional_artifact_hard_defect_preflight_v1 as hard
from canonical.runtime import professional_quality_p1_router_v2 as base

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_ROUTER_V3"
PROFILE_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_V3"
PROFILE_PATH="canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json"
BINDING_SHA="19c2d703366f64744c0d0f4bfcf4923516223a8e"
PREFLIGHT_STEP="RUN_FROZEN_SOURCE_OR_POLICY_BOUND_HARD_DEFECT_PREFLIGHT_WHEN_SUPPORTED"

def _fail(reason):
    out=base._base("FAIL_CLOSED")
    out.update({"schema":SCHEMA,"reason":reason})
    return out

def _profile_ok(repo_root=None):
    root=Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[2]
    p=json.loads((root/PROFILE_PATH).read_text())
    return (
        p.get("schema")==PROFILE_SCHEMA
        and PREFLIGHT_STEP in (p.get("steps") or [])
        and (p.get("hard_defect_preflight") or {}).get("binding_git_blob_sha")==BINDING_SHA
    )

def route(state,*,repo_root=None):
    if not isinstance(state,dict):
        return _fail("STATE_NOT_OBJECT")
    try:
        if not _profile_ok(repo_root):
            return _fail("PROFILE_ROUTER_CONTRACT_DRIFT")
    except Exception:
        return _fail("PROFILE_LOAD_FAILURE")
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
