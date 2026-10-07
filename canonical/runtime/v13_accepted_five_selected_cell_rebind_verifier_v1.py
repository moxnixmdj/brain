from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BUNDLE="canonical/governance/V13_ACCEPTED_FIVE_SELECTED_CELL_REBIND_20261007_V1.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V13.json":"0d18488b51a222e5da414329ccd9d33cbc1fc31c",
 "canonical/governance/DIRECT_END_TO_END_SELECTED_CELL_CERTIFICATE_THEOREM_20261007_V1.json":"ecb52ca25fa14a60b7c34206fea25d8d3cfdcf0d",
 "canonical/verification/ACCEPTED_THREE_OWNERSHIP_PROMOTION_PROOF_20261003_V1.json":"4711fb5eed330990edea369725de6eaedfd3bc70",
 "canonical/verification/DELEGATION_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"d04f2a8c5594d261158835db1cae3822411b6b23",
 "canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json":"981c8ac9b66ee7fccf5b531525849e29df9be483",
 "canonical/verification/TOOL_DISCOVERY_ACCEPTANCE_REDUCTION_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json":"913d171b3c855000d322e183b142b3200eeaf0a9",
 "canonical/capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json":"2d912cf8df64bd806fffb6a1070d95644d005470",
 "canonical/governance/CONTINUITY_CREDITED_REBIND_20261007_V1.json":"839af46fd8ef214251b44bd1398fa2d1543f00c5",
 "canonical/capabilities/obsolescence/EXACT_SYMBOLIC_COMPUTATION_V1_ADJUDICATION.json":"a691d49ef377fa216bbbeff70183112d65445463",
 "canonical/runtime/delegation_whole_scope_candidate_v2.py":"f1a93ee66d90093de61dc17c6ebf2e24073df522",
 "canonical/runtime/trajectory_failure_typed_ir_candidate_v7.py":"28940387bd6c11671035ad9201e37bba13fd9bc9",
 "canonical/runtime/tool_discovery_information_safe_candidate.py":"64c02edd568d95ec5ed54b7b8122183ce5b82e17",
 "canonical/runtime/same_identity_supervisor_credited_v1.py":"47c461f502e840def0c38728e1bfd7c6401cb804",
 "canonical/obsolescence/run_exact_symbolic_v1.py":"8f6f04fee00664b26ddf1a45a65698399c7ca6c3",
}
def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def load(p): return json.loads((ROOT/p).read_text())
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("SOURCE_MISSING:"+p); continue
  if blob(q.read_bytes())!=w: errors.append("SOURCE_DRIFT:"+p)
 b=load(BUNDLE)
 cells=b.get("cells") or []
 if len(cells)!=5: errors.append("CELL_COUNT")
 if len({c.get("family") for c in cells})!=5: errors.append("FAMILY_DUPLICATE")
 if any(c.get("add_to_D_B") is not True for c in cells): errors.append("DB_FLAG")
 if (b.get("v13_effect") or {}).get("global_ABC_closed") is not False: errors.append("ABC_FALSELY_CLOSED")
 if (b.get("v13_effect") or {}).get("global_D_finality")!="OPEN": errors.append("D_FALSELY_CLOSED")

 promo=load("canonical/verification/ACCEPTED_THREE_OWNERSHIP_PROMOTION_PROOF_20261003_V1.json")
 got={x.get("family"):(x.get("promotion"),(x.get("operative_artifact") or {}).get("git_blob_sha")) for x in promo.get("families",[])}
 expected_three={
  "SUBAGENT_DELEGATION_AND_COORDINATION":("VERIFIED_OWNED_EQUAL_OR_BETTER","f1a93ee66d90093de61dc17c6ebf2e24073df522"),
  "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY":("VERIFIED_OWNED_EQUAL_OR_BETTER","28940387bd6c11671035ad9201e37bba13fd9bc9"),
  "TOOL_DISCOVERY_SELECTION_AND_LEARNING":("VERIFIED_OWNED_EQUAL_OR_BETTER","64c02edd568d95ec5ed54b7b8122183ce5b82e17"),
 }
 for fam,want in expected_three.items():
  if got.get(fam)!=want: errors.append("PROMOTION_BINDING:"+fam)

 cont=load("canonical/capabilities/opus55/OPUS55_LONG_HORIZON_MEMORY_AND_CONTINUITY_V1.json")
 if cont.get("status")!="VERIFIED_OWNED_EQUAL_OR_BETTER": errors.append("CONTINUITY_STATUS")
 if (cont.get("brain_owned_route") or {}).get("supervisor_git_blob")!="47c461f502e840def0c38728e1bfd7c6401cb804": errors.append("CONTINUITY_ROUTE")
 if (cont.get("decision") or {}).get("parent_family_closed_for_claim_scope") is not True: errors.append("CONTINUITY_SCOPE")

 reb=load("canonical/governance/CONTINUITY_CREDITED_REBIND_20261007_V1.json")
 if reb.get("credited_path_blob")!="47c461f502e840def0c38728e1bfd7c6401cb804": errors.append("CONTINUITY_REBIND")

 sym=load("canonical/capabilities/obsolescence/EXACT_SYMBOLIC_COMPUTATION_V1_ADJUDICATION.json")
 if (sym.get("decision") or {}).get("obsolescence_status")!="OBSOLETE_VERIFIED": errors.append("SYMBOLIC_STATUS")
 if (sym.get("producer_execution") or {}).get("pass_count")!=12 or (sym.get("producer_execution") or {}).get("fail_count")!=0: errors.append("SYMBOLIC_PASS")
 if (sym.get("independent_adjudication") or {}).get("all_pass") is not True: errors.append("SYMBOLIC_ADJUDICATION")

 return {
   "status":"PASS__ACCEPTED_FIVE_SELECTED_CELLS_REBOUND_INTO_DB__ZERO_NEW_CREDIT" if not errors else "FAIL_CLOSED",
   "pass":not errors,
   "errors":errors,
   "cell_count":5 if not errors else 0,
   "new_family_credit":0,
   "abc_closed":False,
   "global_d_closed":False,
   "terminal_credit_delta":0,
 }
if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
