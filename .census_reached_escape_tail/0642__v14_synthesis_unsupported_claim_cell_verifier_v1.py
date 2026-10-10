from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BUNDLE="canonical/governance/V14_SYNTHESIS_UNSUPPORTED_CLAIM_SELECTED_PROPERTY_CELL_20261007_V1.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json":"d9bd211b2557ac45331f6fe0c4347392f4cd7a95",
 "canonical/governance/DIRECT_END_TO_END_SELECTED_CELL_CERTIFICATE_THEOREM_20261007_V1.json":"ecb52ca25fa14a60b7c34206fea25d8d3cfdcf0d",
 "canonical/runtime/p3_information_safe_candidate_v3.py":"54bfc7e5ee205aa328863a5ea1ca6f47f864d85a",
 "canonical/governance/P3_SYNTHESIS_T1_T3_MULTIPLEX_TERMINAL_BINDING_V1.json":"ad790afa864bd8f770c3d8a6e3ac901ed2843d26",
 "canonical/governance/SYNTHESIS_SCOPE_CERTIFICATE_V1.json":"dea9028f92f111ee3c8be71615fa4b02e8a8bfb6",
 "canonical/runtime/p3_information_safe_proof_suite_v3.py":"7b4fef2a2ba2c84b3499ded1ed4bbaac6714fa42",
 "canonical/verification/P3_INFORMATION_SAFE_V3_PREFLIGHT_VERIFICATION_20261002_V1.json":"c0812ad6e7ee1e1c93d7419ed72f4fc7c9980381",
 "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json":"bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
 "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"a3fd20e58fdbd9b86278b7de0c245de3063dce27",
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
 c=b.get("selected_property_cell") or {}
 if c.get("id")!="SYNTHESIS_T1_T3_FROZEN_60_ZERO_UNSUPPORTED_MATERIAL_CLAIMS": errors.append("CELL_ID")
 if c.get("population_complete") is not True: errors.append("POPULATION_NOT_COMPLETE")
 if c.get("property")!="ZERO_UNSUPPORTED_MATERIAL_CLAIMS": errors.append("PROPERTY_DRIFT")
 if c.get("brain_value")!=1 or c.get("top_value")!=1: errors.append("TOP_VALUE")
 wave=load("canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json")
 rows=[]
 for arr in ((wave.get("reduction_input") or {}).get("wave") or {}).get("parent_portfolio_receipts",{}).values():
  rows.extend(arr or [])
 ids=set((b.get("direct_end_to_end_witness") or {}).get("case_ids") or [])
 hits=[x for x in rows if x.get("case_id") in ids]
 if len(hits)!=2: errors.append("WAVE_CASE_CARDINALITY")
 elif any(x.get("direct_instrumentation_pass") is not True or x.get("load_bearing") is not True or x.get("parent_terminal_acceptance_pass") is not True for x in hits):
  errors.append("WAVE_CASE_NOT_PASS")
 reg=load("canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json")
 claims=[x for x in reg.get("claims",[]) if x.get("predicate_id")=="SYNTHESIS_ZERO_UNSUPPORTED_MATERIAL_CLAIMS"]
 if len(claims)!=1 or claims[0].get("state")!="PROVED" or claims[0].get("scope_complete") is not True:
  errors.append("PREDICATE_BINDING")
 if (b.get("v14_effect") or {}).get("K_c_minus")!="EMPTY_BECAUSE_BRAIN_VALUE_IS_THE_TOP_ELEMENT_ONE": errors.append("RESIDUAL_RULE")
 if "NO_SYNTHESIS_FAMILY_CLOSURE" not in (b.get("hard_nonclaims") or []): errors.append("FAMILY_GUARD")
 if "NO_MATCHED_QUALITY_CLOSURE" not in (b.get("hard_nonclaims") or []): errors.append("QUALITY_GUARD")
 if (b.get("D_boundary") or {}).get("global_D_finality")!="OPEN": errors.append("D_FALSELY_CLOSED")
 return {"status":"PASS__BOUNDED_SYNTHESIS_UNSUPPORTED_CLAIM_TOP_LAW_CELL__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"cell_closed":not errors,"synthesis_family_closed":False,"abc_closed":False,"terminal_credit_delta":0}
if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
