from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MAN="canonical/governance/V13_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V1.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V13.json":"0d18488b51a222e5da414329ccd9d33cbc1fc31c",
 "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json":"cf736088c1ff460283f9b62d873b8e0710374e79",
 "canonical/governance/CURRENT_ACCEPTED_FIVE_D_REDUCTION_20261007_V1.json":"a1d2dac1ab98462c3505543f8047442a60017d19",
 "canonical/governance/LIVEBENCH_IF_V9_SELECTED_CONTEXT_ABC_BUNDLE_20261007_V1.json":"7119d8e5e3c262048107a6ab8295b2e3f93326b2",
 "canonical/governance/V13_NATIVE_ARTIFACT_MECHANICAL_SELECTED_CELL_20261007_V1.json":"10b766b2983357081f592dc64e576a8cfdd5ad7b",
}
ACCEPTED={
 "LONG_HORIZON_MEMORY_AND_CONTINUITY",
 "SUBAGENT_DELEGATION_AND_COORDINATION",
 "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
 "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
 "EXACT_SYMBOLIC_COMPUTATION",
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
 m=load(MAN)
 matrix=load("canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json")
 current={r.get("family") for r in matrix.get("rows",[]) if r.get("status")=="VERIFIED_OWNED_EQUAL_OR_BETTER" or r.get("postwave_ownership_credit")=="VERIFIED_OWNED_EQUAL_OR_BETTER"}
 if current!=ACCEPTED: errors.append("ACCEPTED_FIVE_DRIFT")
 regions=m.get("known_D_B_regions") or []
 if len(regions)!=7: errors.append("REGION_COUNT")
 ids={x.get("id") for x in regions}
 expected_ids={
  "ACCEPTED_LONG_HORIZON_MEMORY_AND_CONTINUITY",
  "ACCEPTED_SUBAGENT_DELEGATION_AND_COORDINATION",
  "ACCEPTED_SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
  "ACCEPTED_TOOL_DISCOVERY_SELECTION_AND_LEARNING",
  "ACCEPTED_EXACT_SYMBOLIC_COMPUTATION",
  "LIVEBENCH_IF_ACTIVE15_FROZEN_200",
  "NATIVE_ARTIFACT_T1_FROZEN_8_MECHANICAL",
 }
 if ids!=expected_ids: errors.append("REGION_SET_DRIFT")
 lb=load("canonical/governance/LIVEBENCH_IF_V9_SELECTED_CONTEXT_ABC_BUNDLE_20261007_V1.json")
 if (lb.get("selected_cell") or {}).get("id")!="LIVEBENCH_IF_ACTIVE15_FROZEN_200": errors.append("LIVEBENCH_CELL_DRIFT")
 art=load("canonical/governance/V13_NATIVE_ARTIFACT_MECHANICAL_SELECTED_CELL_20261007_V1.json")
 if (art.get("selected_cell") or {}).get("id")!="NATIVE_ARTIFACT_T1_FROZEN_8_MECHANICAL": errors.append("ARTIFACT_CELL_DRIFT")
 sat=m.get("saturation_result") or {}
 if sat.get("regions_may_overlap") is not True or sat.get("coverage_measure_not_claimed") is not True: errors.append("OVERCLAIM_GUARD")
 if "THE_SEVEN_REGIONS_DO_NOT_CLOSE_ABC." not in (m.get("anti_overclaim") or []): errors.append("ABC_OVERCLAIM_GUARD")
 d=load("canonical/governance/CURRENT_ACCEPTED_FIVE_D_REDUCTION_20261007_V1.json")
 if (d.get("current_D_effect_frontier") or {}).get("current_accepted_family_effect_mediator_residual_count")!=0: errors.append("ACCEPTED_D_NOT_SATURATED")
 return {"status":"PASS__SEVEN_KNOWN_DB_REGIONS__ZERO_REALITY__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"known_region_count":7 if not errors else None,"abc_closed":False,"terminal_credit_delta":0}
if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
