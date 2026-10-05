from __future__ import annotations
import json
from pathlib import Path

REPAIR=Path("canonical/governance/ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_V1.json")
ROOT=Path("canonical/governance/TERMINAL_ROOT_CAUSE_STATE_V1.json")
CURRENT=Path("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V1.json")

def load(p: Path)->dict:
    return json.loads(p.read_text(encoding="utf-8"))

def verify()->dict:
    r=load(REPAIR); root=load(ROOT); cur=load(CURRENT)
    assert r["observed_now"]["authenticated_api_portal_existence_publicly_reproducible"] is True
    assert r["observed_now"]["endpoint_and_routing_semantics_unauthenticated_publicly_reproducible"] is False
    gated=set(r["corrected_classification"]["login_gated_or_account_specific"])
    assert "GET_V1_MODELS_ENDPOINT_SEMANTICS" in gated
    assert "DIRECT_MODEL_PARAMETER_ROUTING_SEMANTICS" in gated
    assert "FALLBACK_CONTROL_SEMANTICS" in gated
    assert "RESOLVED_MODEL_RESPONSE_HEADER_SEMANTICS" in gated
    assert r["execution_authority"] is False
    assert r["fresh_reality_authority"] is False
    for ptr in (
        root["scheduler_policy"]["arena_public_semantics_truth_repair"],
        cur["arena_public_semantics_truth_repair"],
    ):
        assert ptr["path"]=="canonical/governance/ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_V1.json"
        assert ptr["scheduling_authority"] is True
        assert ptr["execution_authority"] is False
        assert ptr["fresh_reality_authority"] is False
    a=root["current_acceptance"]
    c=current["current_root_partition_override"] if "current" in locals() else cur["current_root_partition_override"]
    atomic=(current if "current" in locals() else cur)["atomic_acceptance_frontier"]
    assert a["accepted_families"]==c["accepted_families"]
    assert a["open_families"]==c["open_families"]
    assert a["proved_atomic"]==c["proved_atomic"]==atomic["proved"]
    assert a["unresolved_atomic"]==c["unresolved_atomic"]==atomic["unresolved"]
    assert a["total_atomic"]==atomic["total"]
    assert a["proved_atomic"]+a["unresolved_atomic"]==a["total_atomic"]
    assert a["accepted_families"]+a["open_families"]==a["total_families"]
    assert a["terminal"] is False and c["terminal"] is False
    return {
      "schema":"PROJECT_BRAIN_ARENA_PUBLIC_SEMANTICS_TRUTH_REPAIR_GUARD_V1",
      "status":"PASS",
      "unauthenticated_public_overclaim_repaired":True,
      "terminal_counts_preserved":True,
      "fresh_reality_authority":False,
      "acceptance_credit_delta":0
    }

if __name__=="__main__":
    print(json.dumps(verify(),sort_keys=True))
