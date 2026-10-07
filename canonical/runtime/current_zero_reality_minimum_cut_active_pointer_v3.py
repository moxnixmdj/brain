from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
POINTER="canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V3.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json":"d9bd211b2557ac45331f6fe0c4347392f4cd7a95",
 "canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V2.json":"0618f2b4ee0638f8ea8adf93a3c0cfbaa6761cc7",
 "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V2.json":"483a75adf710efd66fb5075e35c0e2599ed26ffc",
}
def blob(b:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text())
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("MISSING:"+p)
  elif blob(q.read_bytes())!=w: errors.append("DRIFT:"+p)
 p=load(POINTER)
 a=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json")
 d=load("canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V2.json")
 truth=a.get("current_truth",{})
 exact=p.get("exact_state",{})
 sat=d.get("saturation_result",{})
 if truth.get("independent_top_level_terminal_predicate_count")!=2: errors.append("AUTH_TOP_LEVEL")
 if truth.get("target_universe_scope_superset_closed") is not True: errors.append("AUTH_SCOPE")
 if truth.get("default_context_law_overapproximation")!="K_c_EQUALS_L_c": errors.append("AUTH_KC")
 if sat.get("known_D_B_region_count")!=9: errors.append("DB_COUNT")
 if exact.get("known_cached_D_B_regions")!=9: errors.append("PTR_DB_COUNT")
 if exact.get("independent_top_level_terminal_predicate_count")!=2: errors.append("PTR_TOP_LEVEL")
 if exact.get("terminal") is not False: errors.append("TERMINAL_GUARD")
 programs=[x.get("id") for x in p.get("active_zero_reality_programs",[])]
 expected_programs={"ABC_DB_SATURATION_FIXED_POINT","ABC_RESIDUAL_CONTEXT_TOP_LAW_RACE","ABC_LOCAL_C_ONLY_ON_SELECTED_ROUTES","D_DELTA_ONLY"}
 if set(programs)!=expected_programs: errors.append("PROGRAM_SET")
 invalid=set(p.get("invalidated_as_top_level_scheduler_work",[]))
 for x in ("29_TRUTH_J_G_T_D_U_ROUTING","32_OPEN_TRUTH_OBLIGATION_QUEUE","19_FAMILY_INDEPENDENT_TARGET_ACQUISITION_QUEUE","FIXED_BENCHMARK_SCORE_QUEUE_AS_DEFAULT_TERMINAL_PROGRAM"):
  if x not in invalid: errors.append("OBSOLETE_NOT_INVALIDATED:"+x)
 if p.get("accounting",{}).get("terminal_credit_delta")!=0: errors.append("CREDIT")
 return {
  "pass":not errors,"errors":errors,
  "top_level_predicates":2 if not errors else None,
  "cached_D_B_regions":9 if not errors else None,
  "active_program_count":4 if not errors else None,
  "target_scope_closed":True if not errors else None,
  "abc_closed":False,"d_finality_closed":False,"terminal":False,
  "terminal_credit_delta":0
 }
if __name__=="__main__":
 out=verify(); print(json.dumps(out,indent=2,sort_keys=True)); raise SystemExit(0 if out["pass"] else 1)
