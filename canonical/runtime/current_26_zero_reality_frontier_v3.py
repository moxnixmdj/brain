from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
FILES={
"canonical/governance/CURRENT_26_ZERO_REALITY_FRONTIER_V2.json":"352fe17467a8335a348949ce2f2b6fdb6235e9ac",
"canonical/governance/EXTERNAL_BENCHMARK_DOMINANCE_GATE_V1.json":"d5eba104f28f6ba0bb400967057dc02029e2353e",
"canonical/verification/EXTERNAL_BENCHMARK_DOMINANCE_V1_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"9fcad9359ad75d1dfa9b5fd672a2a081128d5001",
"canonical/governance/LIVEBENCH_IF_COMPARATOR_ROUTE_RECONCILIATION_V2.json":"7067a849585d9020f3d78aa374c0eeecb5078c8b",
}
def blob(p):
 b=(ROOT/p).read_bytes(); return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text())
def evaluate():
 drift={p:{"expected":h,"actual":blob(p)} for p,h in FILES.items() if blob(p)!=h}
 if drift:return {"pass":False,"status":"FAIL_CLOSED__SOURCE_BLOB_DRIFT","drift":drift,"fresh_reality_authority":False}
 old,gate,ver,live=map(load,FILES)
 e=old["exact_state"]; errors=[]
 if (e["proved_predicates"],e["unresolved_predicates"],e["primitive_zero_reality_work_units"])!=(12,26,30):errors.append("PRIOR_COUNTS_DRIFT")
 if gate["current_result"]["verified_external_full_substitutions"]!=0:errors.append("EXTERNAL_SUBSTITUTION_DELTA_NONZERO")
 if gate["current_result"]["public_fixed_bars_reuse_only"]!=15:errors.append("PUBLIC_FIXED_BAR_REUSE_COUNT_DRIFT")
 if ver["verified"]["immediate_external_full_substitutions"]!=0:errors.append("VERIFIER_SUBSTITUTION_DELTA_NONZERO")
 rs=live["current_route_state"]
 if not (rs["comparator_abi"]=="CLOSED" and rs["comparator_population_identity"]=="CLOSED" and rs["brain_score"]=="OPEN"):errors.append("LIVEBENCH_ROUTE_STATE_DRIFT")
 ok=not errors
 return {
  "pass":ok,
  "status":"PASS__BENCHMARK_DOMINANCE_BOUND__COUNTS_UNCHANGED__30_PRIMITIVE_ZERO_REALITY_UNITS__ZERO_CREDIT" if ok else "FAIL_CLOSED",
  "errors":errors,
  "exact_state":e,
  "delta":{"zero_reality_requirement_delta":0,"primitive_work_unit_delta":0,"acceptance_predicate_delta":0,"family_delta":0},
  "reason":"NO_VERIFIED_EXTERNAL_FULL_SUBSTITUTION__LIVEBENCH_ONLY_DOES_NOT_DISCHARGE_SHARED_PUBLIC_BENCHMARK_CERTIFICATE",
  "scheduling_precedence":["EXACT_EXISTING_OPUS55_BENCHMARK_REUSE","VERIFIED_EXTERNAL_EXACT_OR_SUPERSET_SUBSTITUTION","EXISTING_BRAIN_RECEIPT_SATURATION","FORMAL_OR_DEDUCTIVE_DISCHARGE","IRREDUCIBLE_FRESH_EVALUATION_ONLY_AFTER_VERIFIED_FIXED_POINT"],
  "new_reality_units_consumed":0,"incremental_spend_usd":0,"acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,"fresh_reality_authority":False
 }
if __name__=="__main__":print(json.dumps(evaluate(),indent=2,sort_keys=True))
