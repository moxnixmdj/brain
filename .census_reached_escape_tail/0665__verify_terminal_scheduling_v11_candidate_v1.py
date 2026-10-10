from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
CAND="canonical/governance/TERMINAL_SCHEDULING_V11_ACTIVE_AUTHORITY_CANDIDATE_V1.json"
OLD="canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json"
FRONT="canonical/governance/CURRENT_27_ZERO_REALITY_FRONTIER_V2.json"
VERIFY="canonical/verification/CURRENT_27_ZERO_REALITY_FRONTIER_V2_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json"
EXPECTED={OLD:"54be838a5a0a9698398893ad113641496d5051b8",FRONT:"bab3876a1c4bd6a065d20d42b320df4b4b3fa519",VERIFY:"ac56cdefc44aa9a9b649945d10e84c84ee9945be"}
def blob(p):
 d=(ROOT/p).read_bytes(); return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def evaluate():
 drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
 if drift:return {"pass":False,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","errors":["SOURCE_BLOB_DRIFT"],"drift":drift}
 c,o,f,v=load(CAND),load(OLD),load(FRONT),load(VERIFY); errors=[]
 if not str(o.get("status","")).startswith("ACTIVE_INDEPENDENT_PUBLIC_RUNNER_PASS__V10_CURRENT"):errors.append("V10_PRIOR_NOT_CURRENT")
 if not str(v.get("status","")).startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):errors.append("FRONTIER_V2_NOT_INDEPENDENT_PASS")
 fl=f.get("live_world") or {}; cl=c.get("live_world") or {}
 if (fl.get("proved_predicates"),fl.get("unresolved_predicates"),fl.get("active_zero_reality_requirements"),fl.get("active_nondominated_certificates"))!=(11,27,17,14):errors.append("FRONTIER_COUNTS_DRIFT")
 if (cl.get("proved_predicates"),cl.get("unresolved_predicates"),cl.get("active_zero_reality_requirements"),cl.get("active_nondominated_certificates"))!=(11,27,17,14):errors.append("CANDIDATE_COUNTS_DRIFT")
 if cl.get("opus55_acceptance")!="4/19_PASS__15/19_OPEN":errors.append("ACCEPTANCE_DRIFT")
 oldtd=o.get("mandatory_tool_discovery_retrieval") or {}; newtd=c.get("mandatory_tool_discovery_retrieval") or {}
 for k in ("gate_git_blob_sha","hypergraph_git_blob_sha","scheduler_runtime_git_blob_sha","v2_base_activation_git_blob_sha","v3_activation_git_blob_sha","v3_live_gate_verification_git_blob_sha","mandatory","direct_bypass_allowed","stale_authority_allowed","pre_v3_epoch_exhaustion_allowed","consumed_source_epoch_replay_allowed","no_result_means_nonexistence"):
  if newtd.get(k)!=oldtd.get(k):errors.append("TOOL_DISCOVERY_GATE_DRIFT:"+k)
 if any(c.get(k)!=0 for k in ("new_reality_units_consumed","incremental_spend_usd","acceptance_credit_delta","family_credit_delta","ownership_credit_delta")):errors.append("NONZERO_CREDIT_OR_REALITY")
 if c.get("fresh_reality_authority") is not False or c.get("execution_authority") is not False or c.get("promotion_authority") is not False:errors.append("AUTHORITY_LEAK")
 ok=not errors
 return {"pass":ok,"status":"PASS__V11_SCHEDULING_BINDS_17_REQUIREMENTS__27_PREDICATES_UNCHANGED__NO_FRESH_REALITY" if ok else "FAIL_CLOSED","errors":sorted(set(errors)),"active_zero_reality_requirements":17 if ok else None,"unresolved_predicates":27,"opus55_acceptance":"4/19_PASS__15/19_OPEN","fresh_reality_authority":False}
if __name__=="__main__":print(json.dumps(evaluate(),indent=2,sort_keys=True))
