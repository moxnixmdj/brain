from __future__ import annotations
import hashlib, json
from pathlib import Path
from canonical.runtime import tool_discovery_retrieval_authority_gate_v1 as td_gate

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_VERIFY_TERMINAL_SCHEDULING_V12_CANDIDATE_V1"
CAND="canonical/governance/TERMINAL_SCHEDULING_V12_ACTIVE_AUTHORITY_CANDIDATE_V1.json"
PATHS={
 "frontier":"canonical/governance/CURRENT_27_ZERO_REALITY_FRONTIER_V2.json",
 "frontier_verification":"canonical/verification/CURRENT_27_ZERO_REALITY_FRONTIER_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
 "gate":"canonical/runtime/tool_discovery_retrieval_authority_gate_v1.py",
 "v4_activation":"canonical/governance/TOOL_DISCOVERY_RESIDUAL_WITNESS_RETRIEVAL_FRONTIER_V4_ACTIVATION_V1.json",
 "v4_activation_verification":"canonical/verification/RETRIEVAL_V4_ACTIVATION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
 "v4_live_gate_verification":"canonical/verification/RETRIEVAL_V4_LIVE_GATE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
 "hypergraph":"canonical/governance/OPUS55_ACCEPTANCE_ACTION_HYPERGRAPH_V2.json",
 "scheduling_runtime":"canonical/runtime/current_terminal_scheduling_world_v1.py",
}
EXPECTED={
 PATHS["frontier"]:"bab3876a1c4bd6a065d20d42b320df4b4b3fa519",
 PATHS["frontier_verification"]:"ac56cdefc44aa9a9b649945d10e84c84ee9945be",
 PATHS["gate"]:"b01292c1f198f251b8a9606b4de173541204c2dc",
 PATHS["v4_activation"]:"643890c1d09844ea49de434df8ffec02962806e4",
 PATHS["v4_activation_verification"]:"e35dc954e0cf892d5522e62b5948bb64edeed4f7",
 PATHS["v4_live_gate_verification"]:"ebb4ab1a05e47e20ecfacba41eb99d1f5c71694d",
 PATHS["hypergraph"]:"38b53147597b5457859e3b0d031168842560e3e2",
 PATHS["scheduling_runtime"]:"9ae2b990578b042dd24074fd5013378b72e64b6b",
}

def blob(p:str)->str:
    raw=(ROOT/p).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def load(p:str):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

def evaluate():
    errors=[]
    drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
    if drift:
        return {"schema":SCHEMA,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","pass":False,"errors":["SOURCE_BLOB_DRIFT"],"drift":drift}

    c=load(CAND)
    f=load(PATHS["frontier"])
    fv=load(PATHS["frontier_verification"])
    v4=load(PATHS["v4_activation"])
    v4v=load(PATHS["v4_activation_verification"])
    livev=load(PATHS["v4_live_gate_verification"])

    fl=f.get("live_world") or {}
    cl=c.get("live_world") or {}
    expected_counts=(11,27,17,14)
    actual_front=(fl.get("proved_predicates"),fl.get("unresolved_predicates"),fl.get("active_zero_reality_requirements"),fl.get("active_nondominated_certificates"))
    actual_cand=(cl.get("proved_predicates"),cl.get("unresolved_predicates"),cl.get("active_zero_reality_requirements"),cl.get("active_nondominated_certificates"))
    if actual_front!=expected_counts: errors.append("FRONTIER_COUNTS_DRIFT")
    if actual_cand!=expected_counts: errors.append("CANDIDATE_COUNTS_DRIFT")
    if cl.get("registry_predicates")!=38: errors.append("REGISTRY_COUNT_DRIFT")
    if cl.get("opus55_acceptance")!="4/19_PASS__15/19_OPEN": errors.append("ACCEPTANCE_DRIFT")
    if cl.get("tool_learning_success_route_noninferior")!="OPEN": errors.append("TOOL_DISCOVERY_TARGET_STATE_DRIFT")

    if not str(fv.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("FRONTIER_NOT_INDEPENDENT_PASS")
    fvv=fv.get("verified") or {}
    if (fvv.get("proved_predicates"),fvv.get("unresolved_predicates"),fvv.get("active_zero_reality_requirements"),fvv.get("active_nondominated_certificates"))!=expected_counts:
        errors.append("FRONTIER_VERIFICATION_COUNTS_DRIFT")
    if fvv.get("fresh_reality_authority") is not False:
        errors.append("FRONTIER_FRESH_REALITY_AUTHORITY_LEAK")

    if not str(v4v.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("V4_ACTIVATION_NOT_INDEPENDENT_PASS")
    if not str(livev.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
        errors.append("V4_LIVE_GATE_NOT_INDEPENDENT_PASS")
    if (livev.get("verified") or {}).get("v4_activation_mandatory_in_live_gate") is not True:
        errors.append("V4_NOT_MANDATORY")
    if (livev.get("verified") or {}).get("v2_and_v3_base_authority_preserved") is not True:
        errors.append("V2_V3_BASE_NOT_PRESERVED")
    if (livev.get("verified") or {}).get("epoch_consumption_nonexistence_inference_forbidden") is not True:
        errors.append("NONEXISTENCE_FIREWALL_MISSING")

    gate=td_gate.evaluate_repository(ROOT)
    if gate.get("pass") is not True:
        errors.append("LIVE_TOOL_DISCOVERY_GATE_FAIL")
    if "V2_V3_V4" not in str(gate.get("status","")):
        errors.append("LIVE_TOOL_DISCOVERY_GATE_NOT_V4")

    td=c.get("mandatory_tool_discovery_retrieval") or {}
    if td.get("gate_git_blob_sha")!=EXPECTED[PATHS["gate"]]: errors.append("CANDIDATE_GATE_HASH_DRIFT")
    if td.get("v4_activation_git_blob_sha")!=EXPECTED[PATHS["v4_activation"]]: errors.append("CANDIDATE_V4_ACTIVATION_HASH_DRIFT")
    if td.get("v4_activation_verification_git_blob_sha")!=EXPECTED[PATHS["v4_activation_verification"]]: errors.append("CANDIDATE_V4_ACTIVATION_VERIFICATION_HASH_DRIFT")
    if td.get("v4_live_gate_verification_git_blob_sha")!=EXPECTED[PATHS["v4_live_gate_verification"]]: errors.append("CANDIDATE_V4_LIVE_GATE_VERIFICATION_HASH_DRIFT")
    for k,v in (
        ("mandatory",True),
        ("direct_bypass_allowed",False),
        ("stale_authority_allowed",False),
        ("consumed_source_epoch_replay_allowed",False),
        ("backend_unbound_counts_as_attempt",False),
        ("failed_or_empty_attempt_means_nonexistence",False),
        ("source_epoch_consumption_means_open_world_complete",False),
    ):
        if td.get(k) is not v: errors.append("CANDIDATE_TOOL_GATE_POLICY_DRIFT:"+k)

    for k in ("new_reality_units_consumed","incremental_spend_usd","acceptance_credit_delta","family_credit_delta","ownership_credit_delta"):
        if c.get(k)!=0: errors.append("NONZERO_CREDIT_OR_REALITY:"+k)
    for k in ("execution_authority","promotion_authority","fresh_reality_authority"):
        if c.get(k) is not False: errors.append("AUTHORITY_LEAK:"+k)

    ok=not errors
    return {
      "schema":SCHEMA,
      "status":"PASS__V12_BINDS_17_REQUIREMENT_FRONTIER_TO_MANDATORY_V4_TOOL_DISCOVERY_GATE__NO_FRESH_REALITY" if ok else "FAIL_CLOSED",
      "pass":ok,
      "errors":sorted(set(errors)),
      "active_zero_reality_requirements":17 if ok else None,
      "active_nondominated_certificates":14 if ok else None,
      "proved_predicates":11,
      "unresolved_predicates":27,
      "opus55_acceptance":"4/19_PASS__15/19_OPEN",
      "tool_discovery_gate_status":gate.get("status"),
      "fresh_reality_authority":False,
      "acceptance_credit_delta":0,
      "family_credit_delta":0,
      "ownership_credit_delta":0,
    }

if __name__=="__main__":
    print(json.dumps(evaluate(),indent=2,sort_keys=True))
