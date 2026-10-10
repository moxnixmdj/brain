from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BUNDLE="canonical/governance/V13_NATIVE_ARTIFACT_MECHANICAL_SELECTED_CELL_20261007_V1.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V13.json":"0d18488b51a222e5da414329ccd9d33cbc1fc31c",
 "canonical/governance/DIRECT_END_TO_END_SELECTED_CELL_CERTIFICATE_THEOREM_20261007_V1.json":"ecb52ca25fa14a60b7c34206fea25d8d3cfdcf0d",
 "canonical/governance/NATIVE_ARTIFACT_T1_MULTIPLEX_TERMINAL_BINDING_V1.json":"977e18ce2c19f7bb8a429a8f1c99407ff3000e92",
 "canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json":"bd86b4c53992b47a4a60b64a60ba03db9a442cfc",
 "canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json":"a3fd20e58fdbd9b86278b7de0c245de3063dce27",
 "canonical/verification/NATIVE_ARTIFACT_CROSS_FORMAT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"34d8a3b7a99363902d6212759125ac71fa54a986",
 "canonical/verification/NATIVE_ARTIFACT_RENDER_PRESERVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json":"1a0b4ca6627aaf28eb25f6990682e87319d14d6d",
 "canonical/runtime/native_artifact_cross_format_candidate_v1.py":"f3e5090647dd9029ab9f46efd06dc0c0d0addbc3",
 "canonical/runtime/ooxml_package_transaction.py":"970be62854c918b306ae3f62989009bfbd0e8fc7",
 "canonical/runtime/pdf_native_edit_transaction.py":"b9f673ffe0474d00a598089077ad93db40c00dd8",
}
def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("SOURCE_MISSING:"+p); continue
  if blob(q.read_bytes())!=w: errors.append("SOURCE_DRIFT:"+p)
 b=json.loads((ROOT/BUNDLE).read_text())
 c=b.get("selected_cell") or {}
 if c.get("id")!="NATIVE_ARTIFACT_T1_FROZEN_8_MECHANICAL": errors.append("CELL_ID")
 if c.get("population_complete") is not True: errors.append("POPULATION_NOT_COMPLETE")
 if c.get("semantic_target_selection") is not False: errors.append("SEMANTIC_SCOPE_EXPANDED")
 if c.get("professional_quality_judgment") is not False: errors.append("QUALITY_SCOPE_EXPANDED")
 w=json.loads((ROOT/"canonical/verification/TERMINAL_V3_ONE_SHOT_WAVE_RESULT_20261002_V1.json").read_text())
 rows=[]
 for arr in ((w.get("reduction_input") or {}).get("wave") or {}).get("parent_portfolio_receipts",{}).values():
  rows.extend(arr or [])
 hit=[x for x in rows if x.get("case_id")=="T1::NATIVE_ARTIFACT_STRUCTURED_EDIT_PRESERVATION_001::aggregate::8"]
 if len(hit)!=1 or hit[0].get("direct_instrumentation_pass") is not True or hit[0].get("parent_terminal_acceptance_pass") is not True:
  errors.append("TERMINAL_WAVE_CELL_NOT_BOUND")
 e=json.loads((ROOT/"canonical/governance/OPUS55_ACCEPTANCE_PREDICATE_EVIDENCE_BINDINGS_V2.json").read_text())
 claims=[x for x in e.get("claims",[]) if x.get("predicate_id")=="ARTIFACT_MECHANICAL_GATES_CEILING"]
 if len(claims)!=1: errors.append("CEILING_BINDING_CARDINALITY")
 else:
  x=claims[0]
  if not (x.get("state")=="PROVED" and x.get("scope_complete") is True and x.get("objective_ceiling") is True and x.get("brain_value")==1 and x.get("objective_ceiling_value")==1):
   errors.append("CEILING_BINDING_INVALID")
 if "NO_WHOLE_ARTIFACT_FAMILY_CLOSURE" not in (b.get("hard_nonclaims") or []): errors.append("FAMILY_OVERCLAIM_GUARD")
 if (b.get("D_boundary") or {}).get("global_D_finality")!="OPEN": errors.append("D_FALSELY_CLOSED")
 return {"status":"PASS__BOUNDED_NATIVE_ARTIFACT_ABC_CELL__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"cell_closed":not errors,"family_closed":False,"abc_closed":False,"terminal_credit_delta":0}
if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
