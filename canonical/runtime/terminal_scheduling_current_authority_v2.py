from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUTH="canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V2.json"
EXPECTED={
 "canonical/governance/TERMINAL_SCHEDULING_CURRENT_AUTHORITY_V1.json":"3896e98565bf2a9c593beaf05615563dcb61d282",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json":"d9bd211b2557ac45331f6fe0c4347392f4cd7a95",
 "canonical/governance/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V3.json":"a1db7d6a2553a0660b1dbcbbb9b920bbf7453f03",
 "canonical/verification/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V3_SPRITE_VERIFICATION_20261007_V1.json":"646c1b455e2a0cf1583647c99ea68599aa67fbd0",
}
ACTIONS={
 "ACTION::SATURATE_EXISTING_EVIDENCE_INTO_D_B",
 "ACTION::COMPUTE_RESIDUAL_CONTEXT_K_c_MINUS_FROM_EXISTING_EVIDENCE",
 "ACTION::CERTIFY_SELECTED_ROUTE_LOCAL_C_FROM_EXISTING_EVIDENCE",
 "ACTION::CHECK_NEW_D_ROUTE_DELTA_FROM_EXISTING_EVIDENCE",
}
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text())
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("MISSING:"+p)
  elif blob(q.read_bytes())!=w: errors.append("DRIFT:"+p)
 a=load(AUTH)
 v14=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json")
 vr=load("canonical/verification/CURRENT_ZERO_REALITY_MINIMUM_CUT_ACTIVE_POINTER_V3_SPRITE_VERIFICATION_20261007_V1.json")
 if set(a.get("authorized_actions",[]))!=ACTIONS: errors.append("ACTIONS")
 if a.get("execution_authority") is not True: errors.append("EXEC_AUTH")
 if a.get("execution_authority_scope")!="ZERO_REALITY_EXISTING_EVIDENCE_SATURATION_AND_FORMAL_REDUCTION_ONLY": errors.append("SCOPE")
 if a.get("fresh_reality_authority") is not False: errors.append("FRESH")
 if a.get("promotion_authority") is not False: errors.append("PROMOTION")
 if (v14.get("current_truth") or {}).get("independent_top_level_terminal_predicate_count")!=2: errors.append("V14_TOP")
 if (vr.get("verified") or {}).get("top_level_predicates")!=2 or (vr.get("verified") or {}).get("cached_D_B_regions")!=9: errors.append("PTR_VERIFY")
 rules=set(a.get("execution_rules",[]))
 for req in ("NO_FRESH_REALITY","NO_FIXED_BENCHMARK_SCORE_QUEUE_AS_DEFAULT_SCHEDULER","NO_29_OR_32_TRUTH_QUEUE_AS_TOP_LEVEL_SCHEDULER","NO_19_FAMILY_INDEPENDENT_ACQUISITION_QUEUE"):
  if req not in rules: errors.append("RULE:"+req)
 if a.get("live_world",{}).get("terminal") is not False: errors.append("TERMINAL_GUARD")
 if a.get("accounting",{}).get("terminal_credit_delta")!=0: errors.append("CREDIT")
 return {"pass":not errors,"errors":errors,"authorized_action_count":4 if not errors else None,"top_level_predicates":2 if not errors else None,"cached_D_B_regions":9 if not errors else None,"fresh_reality_authority":False,"promotion_authority":False,"abc_closed":False,"d_finality_closed":False,"terminal":False,"terminal_credit_delta":0}
if __name__=="__main__":
 x=verify(); print(json.dumps(x,indent=2,sort_keys=True)); raise SystemExit(0 if x["pass"] else 1)
