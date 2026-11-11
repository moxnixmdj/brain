from __future__ import annotations
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
B={
"canonical/governance/CURRENT_TERMINAL_AUTHORITY_V3.json":"142cb46ac1bf0b5c570e6d2dc121dfca6f6e1544",
"canonical/governance/BRAIN_FIRST_DIFFERENTIAL_PREWAVE_V1.json":"43b5c74b5caf3b3065feaf98a87f798e7c14aead",
"canonical/verification/BRAIN_FIRST_DIFFERENTIAL_PREWAVE_PUBLIC_RUNNER_VERIFICATION_20261006_V1.json":"9a9437a07f7dad464800a6eddb9776e63916317a",
"canonical/verification/MATCHED_SUCCESS_FINITE_SCOPE_REDUCER_PUBLIC_RUNNER_VERIFICATION_20261006_V1.json":"d4937f70e21e49706324d46c292e131d9e96f4a0",
"canonical/verification/MATCHED_SUCCESS_SCOPE_COMPILER_PUBLIC_RUNNER_VERIFICATION_20261006_V1.json":"ea289a46559a6cb4373e9b38f62e49abad399fbc",
"canonical/verification/MATCHED_CASE_ISOLATION_RESET_PUBLIC_RUNNER_VERIFICATION_20261006_V1.json":"f7b4dd5bfb1967e1090ec51b270f7dc0a7a459d7",
"canonical/verification/MATCHED_SUCCESS_COMPONENT_BOUND_V4_SPRITE_REPLAY_20261006_V1.json":"8e7bb1690bd06e91d64c218fe5776db28dce1aa3"}
T={"AGENCY_MATCHED_SUCCESS_NONINFERIOR","IF_SCOPE_BOUNDARY_NONINFERIOR","COMPOSITION_TERMINAL_SUCCESS_NONINFERIOR"}
def h(p):
 b=p.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def j(p):return json.loads((R/p).read_text())
def verify():
 e=[]
 for p,x in B.items():
  if h(R/p)!=x:e.append("DRIFT:"+p)
 g=j("canonical/governance/MATCHED_BRAIN_FIRST_CURRENT_RECONCILIATION_20261006_V1.json")
 a=j("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V3.json")
 bf=j("canonical/governance/BRAIN_FIRST_DIFFERENTIAL_PREWAVE_V1.json")
 rv=j("canonical/verification/MATCHED_SUCCESS_FINITE_SCOPE_REDUCER_PUBLIC_RUNNER_VERIFICATION_20261006_V1.json")
 sv=j("canonical/verification/MATCHED_SUCCESS_SCOPE_COMPILER_PUBLIC_RUNNER_VERIFICATION_20261006_V1.json")
 iv=j("canonical/verification/MATCHED_CASE_ISOLATION_RESET_PUBLIC_RUNNER_VERIFICATION_20261006_V1.json")
 if a["current_truth"]["current_open_truth_obligations"]!=29:e.append("TRUTH_COUNT")
 if set(g["applies_exactly_to"])!=T:e.append("TARGETS")
 if set(bf["scope_boundary"]["directly_applicable_to"])!=T:e.append("BF_TARGETS")
 if "SUCCESS_SET_INCLUSION_IMPLIES_BRAIN_SUCCESS_COUNT_GTE_OPUS_SUCCESS_COUNT" not in rv["verified"]:e.append("MONOTONICITY")
 if sv["prewave_effect"]["conditional_compiler"]!="VERIFIED":e.append("SCOPE")
 if iv["prewave_effect"]["conditional_theorem"]!="VERIFIED":e.append("ISOLATION")
 if len(g["remaining_before_brain_execution"])!=4:e.append("CUT")
 return {"status":"PASS__CURRENT_BRAIN_FIRST_MATCHED_SCHEDULING_RECONCILED__ZERO_CREDIT" if not e else "FAIL_CLOSED","pass":not e,"errors":e,"target_count":3,"remaining_prebrain_cut_count":4,"comparator_before_brain_required":False if not e else None,"scheduling_authority":not e,"execution_authority":False,"fresh_reality_authority":False,"promotion_authority":False,"terminal_credit_delta":0}
if __name__=="__main__":print(json.dumps(verify(),sort_keys=True))
