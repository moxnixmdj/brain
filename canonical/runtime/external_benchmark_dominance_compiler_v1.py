from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
REG="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_REGISTRY_V2.json"
EVID="canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json"
MATCHED="canonical/governance/OPUS55_MATCHED_TARGET_NORMALIZATION_CANDIDATE_V3.json"
FRONTIER="canonical/governance/CURRENT_26_ZERO_REALITY_FRONTIER_V2.json"
CAND="canonical/governance/EXTERNAL_BENCHMARK_DOMINANCE_CANDIDATE_V1.json"
EXPECTED={
 REG:"562536d9ba3f245a6bd24490a1eb3b30f27e0c3a",
 EVID:"bc420c6d1a6caaab7a6d5c257640d3f5797170f5",
 MATCHED:"9b400e6eb1a95bacbd9c0cdb93b155ced0f72558",
 FRONTIER:"352fe17467a8335a348949ce2f2b6fdb6235e9ac",
}
def blob(p):
 b=(ROOT/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text())
def evaluate():
 drift={p:{"expected":h,"actual":blob(p)} for p,h in EXPECTED.items() if blob(p)!=h}
 if drift:
  return {"pass":False,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","drift":drift,"fresh_reality_authority":False}
 reg,evid,matched,frontier,cand=map(load,[REG,EVID,MATCHED,FRONTIER,CAND])
 proved={x.get("predicate_id") for x in evid.get("claims",[]) if x.get("state")=="PROVED"}
 unresolved=[x for x in reg.get("predicates",[]) if x.get("id") not in proved]
 fixed=[x for x in unresolved if x.get("kind")=="PUBLIC_FIXED_BAR"]
 mt={x.get("predicate_id") for x in matched.get("targets",[])}
 adj={x.get("predicate_id"):x for x in cand.get("matched_target_adjudication",[])}
 errors=[]
 if len(fixed)!=15: errors.append("PUBLIC_FIXED_BAR_COUNT_DRIFT")
 if set(adj)!=mt: errors.append("MATCHED_TARGET_ADJUDICATION_NOT_TOTAL")
 if len(mt)!=8: errors.append("MATCHED_TARGET_COUNT_DRIFT")
 if cand.get("public_fixed_bar_policy",{}).get("custom_benchmark_creation_authorized") is not False:
  errors.append("CUSTOM_BENCHMARK_AUTHORITY_MUST_BE_FALSE")
 unauthorized=[]
 for pid,row in adj.items():
  if row.get("replacement_authorized"):
   if row.get("coverage_state")!="VERIFIED_EXACT_OR_SUPERSET":
    unauthorized.append(pid)
 if unauthorized: errors.append("UNVERIFIED_SUBSTITUTION_AUTHORIZED")
 official={x.get("id") for x in cand.get("official_opus55_reference_surfaces",[])}
 required_official={"TERMINAL_BENCH_4_0","FRONTIERCODE_V1_1_MAIN","CURSORBENCH_4_0","GDPVAL_AA_V2_1","AUTOMATIONBENCH","HLE_WITH_TOOLS","TERMINAL_BENCH_SCIENCE_0_1","OSWORLD_2_1_PARTIAL","CHARTOGRAPHY_WITH_TOOLS","AA_BRIEFCASE_V1_1"}
 if not required_official.issubset(official): errors.append("OFFICIAL_OPUS55_REFERENCE_VECTOR_INCOMPLETE")
 ok=not errors
 return {
  "pass":ok,
  "status":"PASS__BENCHMARK_REUSE_FIRST_GATE__15_PUBLIC_FIXED_BARS_REUSE__8_MATCHED_TARGETS_ADJUDICATED__ZERO_UNVERIFIED_SUBSTITUTIONS__ZERO_CREDIT" if ok else "FAIL_CLOSED",
  "errors":errors,
  "current":{"proved":len(proved),"unresolved":len(unresolved),"public_fixed_bars":len(fixed),"matched_targets":len(mt),"current_frontier_primitive_units":frontier.get("exact_state",{}).get("primitive_zero_reality_work_units")},
  "policy":{"custom_benchmark_creation_authorized":False,"fresh_reality_authority":False,"immediate_full_substitutions":sum(1 for x in adj.values() if x.get("replacement_authorized") is True)},
  "next":"INDEPENDENT_SOURCE_VERIFICATION__THEN_TARGET_LEVEL_EXACT_OR_SUPERSET_ADJUDICATION__THEN_RECOMPUTE_FRONTIER",
  "new_reality_units_consumed":0,"incremental_spend_usd":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False
 }
if __name__=="__main__":
 print(json.dumps(evaluate(),indent=2,sort_keys=True))
