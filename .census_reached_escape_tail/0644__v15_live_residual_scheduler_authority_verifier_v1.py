from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V15.json":"09f11461c7aa1ee7719409723726712f68d03da8",
 "canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V2.json":"0618f2b4ee0638f8ea8adf93a3c0cfbaa6761cc7",
 "canonical/governance/M0_GLOBAL_SEMANTIC_DECOMPOSITION_NECESSITY_FALSIFIER_20261007_V1.json":"0c02f1c3a2b4eacf9d84b1cb81c09643305c6f8a",
 "canonical/verification/M0_GLOBAL_SEMANTIC_DECOMPOSITION_NECESSITY_WOLFRAM_VERIFICATION_20261007_V1.json":"5fc202513e8eb7389fd4c93fd9248b3bb3fe81bc",
 "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V2.json":"483a75adf710efd66fb5075e35c0e2599ed26ffc",
 "canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json":"3896e98565bf2a9c593beaf05615563dcb61d282",
}
PTR="canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V3.json"
AUTH="canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V2.json"
PTR_SHA="b4527223ba723039abe15856c4ffac163b4f02c6"
AUTH_SHA="c590c6c86777bf7f8085ef55cb97527671a74b13"
ACTIONS={"ACTION::SATURATE_EXISTING_EVIDENCE_INTO_D_B","ACTION::COMPUTE_RESIDUAL_CONTEXT_K_c_MINUS_FROM_EXISTING_EVIDENCE","ACTION::CERTIFY_SELECTED_ROUTE_LOCAL_SEMANTICS_FROM_EXISTING_EVIDENCE","ACTION::CHECK_NEW_D_ROUTE_DELTA_FROM_EXISTING_EVIDENCE"}
PROGRAMS={"ABC_DB_SATURATION_FIXED_POINT","ABC_LIVE_RESIDUAL_TOP_LAW_RACE","ABC_NAMED_RESIDUAL_REDUCTIONS","D_DELTA_ONLY"}
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text())
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("MISSING:"+p)
  elif blob(q.read_bytes())!=w: errors.append("DRIFT:"+p)
 for p,w in ((PTR,PTR_SHA),(AUTH,AUTH_SHA)):
  q=ROOT/p
  if not q.is_file(): errors.append("MISSING:"+p)
  elif blob(q.read_bytes())!=w: errors.append("DRIFT:"+p)
 ptr=load(PTR); auth=load(AUTH); v15=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V15.json")
 if set(x.get("id") for x in ptr.get("active_zero_reality_programs",[]))!=PROGRAMS: errors.append("PROGRAMS")
 if set(auth.get("authorized_actions",[]))!=ACTIONS: errors.append("ACTIONS")
 if auth.get("pointer",{}).get("git_blob_sha")!=PTR_SHA: errors.append("PTR_BINDING")
 if auth.get("execution_authority") is not True: errors.append("EXEC_AUTH")
 if auth.get("fresh_reality_authority") is not False or auth.get("promotion_authority") is not False: errors.append("AUTH_BOUNDARY")
 if auth.get("execution_authority_scope")!="ZERO_REALITY_EXISTING_EVIDENCE_SATURATION_AND_FORMAL_REDUCTION_ONLY": errors.append("EXEC_SCOPE")
 truth=v15.get("current_truth",{})
 if truth.get("independent_top_level_terminal_predicate_count")!=2 or truth.get("known_sound_D_B_region_count")!=9: errors.append("V15_STATE")
 exact=ptr.get("exact_state",{})
 if exact.get("known_cached_D_B_regions")!=9 or exact.get("global_M0_semantic_decomposition_independently_required") is not False: errors.append("PTR_STATE")
 if auth.get("live_world",{}).get("global_M0_semantic_decomposition_independently_required") is not False: errors.append("AUTH_M0")
 if auth.get("live_world",{}).get("terminal") is not False: errors.append("TERMINAL_GUARD")
 if auth.get("accounting",{}).get("terminal_credit_delta")!=0 or ptr.get("accounting",{}).get("terminal_credit_delta")!=0: errors.append("CREDIT")
 return {"pass":not errors,"errors":errors,"top_level_predicates":2 if not errors else None,"cached_D_B_regions":9 if not errors else None,"active_program_count":4 if not errors else None,"authorized_action_count":4 if not errors else None,"global_M0_required":False,"fresh_reality_authority":False,"promotion_authority":False,"abc_closed":False,"d_finality_closed":False,"terminal":False,"terminal_credit_delta":0}
if __name__=="__main__":
 x=verify(); print(json.dumps(x,indent=2,sort_keys=True)); raise SystemExit(0 if x["pass"] else 1)
