from __future__ import annotations
import json
from pathlib import Path

ROOT=Path("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
CURRENT=Path("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")
ACTIVATION_SHA="c184c1aed33c06f6b4307ace79a959c21de96958"
RUN_ID=37190119446
PR=1777

def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def check_ptr(ptr: dict) -> None:
    assert ptr["activation_path"]=="canonical/governance/TERMINAL_MINIMUM_CAUSAL_DEPTH_ACTIVATION_V1.json"
    assert ptr["activation_git_blob_sha"]==ACTIVATION_SHA
    assert ptr["verification_runner_pr"]==PR
    assert ptr["verification_workflow_run_id"]==RUN_ID
    assert ptr["scheduling_authority"] is True
    assert ptr["execution_authority"] is False
    assert ptr["promotion_authority"] is False
    assert ptr["fresh_reality_authority"] is False

def verify() -> dict:
    root=load(ROOT)
    current=load(CURRENT)
    check_ptr(root["scheduler_policy"]["terminal_minimum_causal_depth"])
    check_ptr(current["terminal_minimum_causal_depth_authority"])
    assert root["current_acceptance"]["accepted_families"]==5
    assert root["current_acceptance"]["proved_atomic"]==12
    assert root["current_acceptance"]["unresolved_atomic"]==26
    assert root["current_acceptance"]["terminal"] is False
    return {
      "schema":"PROJECT_BRAIN_TERMINAL_MINIMUM_CAUSAL_DEPTH_PROJECTION_GUARD_V1",
      "status":"PASS",
      "root_pointer_bound":True,
      "current_authority_pointer_bound":True,
      "terminal_counts_preserved":True,
      "fresh_reality_authority":False,
      "acceptance_credit_delta":0
    }

if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))
