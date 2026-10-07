from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
AUTH="canonical/governance/CURRENT_TERMINAL_AUTHORITY_V13.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V12.json":"3ab55ad2e9df6a7f94acb2e1950569bdc18c8136",
 "canonical/governance/V12_TARGET_LAW_UNCERTAINTY_RESIDUAL_THEOREM_20261007_V1.json":"014d7d5102093251789673dff0a191203663a90d",
 "canonical/verification/V12_TARGET_LAW_RESIDUAL_VERIFY_20261007_V1.json":"87448a55aee6fb3f2b89a5cd4c55dcd7a71b99d9",
 "canonical/governance/CURRENT_ACCEPTED_FIVE_D_REDUCTION_20261007_V1.json":"a1d2dac1ab98462c3505543f8047442a60017d19",
}
def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("SOURCE_MISSING:"+p); continue
  if blob(q.read_bytes())!=w: errors.append("SOURCE_DRIFT:"+p)
 a=json.loads((ROOT/AUTH).read_text())
 ct=a.get("current_truth") or {}
 if ct.get("independent_top_level_terminal_predicate_count")!=2: errors.append("TOP_COUNT")
 if ct.get("target_universe_scope_superset_closed") is not True: errors.append("SCOPE_REOPENED")
 if ct.get("target_information_residualized_to_undominated_laws") is not True: errors.append("LAW_RESIDUALIZATION_MISSING")
 if ct.get("terminal") is not False: errors.append("TERMINAL_FALSE_REQUIRED")
 abc=a.get("abc_normal_form") or {}
 ti=abc.get("target_law_information") or {}
 if ti.get("comparator_free_condition")!="K_c_minus_IS_EMPTY": errors.append("RESIDUAL_RULE_DRIFT")
 if "EXACT_TARGET_IDENTITY_AS_A_DEFAULT_REQUIREMENT." not in (a.get("deleted_scheduler_work") or []): errors.append("EXACT_IDENTITY_RESURRECTED")
 if (a.get("D_normal_form") or {}).get("state")!="OPEN_FINALITY": errors.append("D_FALSELY_CLOSED")
 return {"status":"PASS__V13_TARGET_LAW_RESIDUALIZED_AUTHORITY__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"terminal":False,"terminal_credit_delta":0}
if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
