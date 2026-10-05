from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT=Path("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
CURRENT=Path("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")

def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def git_blob_sha(path: Path) -> str:
    raw=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def check_ptr(ptr: dict) -> None:
    activation_path=Path(str(ptr["activation_path"]))
    assert activation_path.is_file()
    assert ptr["activation_git_blob_sha"]==git_blob_sha(activation_path)
    assert ptr["scheduling_authority"] is True
    assert ptr["execution_authority"] is False
    assert ptr["promotion_authority"] is False
    assert ptr["fresh_reality_authority"] is False

def verify_documents(root: dict,current: dict) -> dict:
    root_ptr=root["scheduler_policy"]["terminal_minimum_causal_depth"]
    current_ptr=current["terminal_minimum_causal_depth_authority"]
    assert root_ptr==current_ptr
    check_ptr(root_ptr)
    check_ptr(current_ptr)

    rc=root["current_acceptance"]
    cc=current["current_root_partition_override"]
    for key in ("accepted_families","open_families","proved_atomic","unresolved_atomic","terminal"):
        assert rc[key]==cc[key], f"CURRENT_ROOT_COUNT_MISMATCH:{key}:{rc[key]}:{cc[key]}"
    assert rc["accepted_families"]+rc["open_families"]==rc["total_families"]
    assert rc["proved_atomic"]+rc["unresolved_atomic"]==rc["total_atomic"]
    assert rc["total_families"]==19
    assert rc["total_atomic"]==38

    return {
      "schema":"PROJECT_BRAIN_TERMINAL_MINIMUM_CAUSAL_DEPTH_PROJECTION_GUARD_V2",
      "status":"PASS",
      "root_pointer_bound":True,
      "current_authority_pointer_bound":True,
      "activation_blob_current":True,
      "terminal_counts_preserved":True,
      "accepted_families":rc["accepted_families"],
      "open_families":rc["open_families"],
      "proved_atomic":rc["proved_atomic"],
      "unresolved_atomic":rc["unresolved_atomic"],
      "terminal":rc["terminal"],
      "fresh_reality_authority":False,
      "acceptance_credit_delta":0
    }

def verify() -> dict:
    return verify_documents(load(ROOT),load(CURRENT))

if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))
