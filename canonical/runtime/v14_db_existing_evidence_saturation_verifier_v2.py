from __future__ import annotations
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MAN="canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V2.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json":"d9bd211b2557ac45331f6fe0c4347392f4cd7a95",
 "canonical/capabilities/opus55/OPUS_5_5_CAPABILITY_OWNERSHIP_MATRIX_V1.json":"cf736088c1ff460283f9b62d873b8e0710374e79",
 "canonical/governance/CURRENT_ACCEPTED_FIVE_D_REDUCTION_20261007_V1.json":"a1d2dac1ab98462c3505543f8047442a60017d19",
 "canonical/governance/LIVEBENCH_IF_V9_SELECTED_CONTEXT_ABC_BUNDLE_20261007_V1.json":"7119d8e5e3c262048107a6ab8295b2e3f93326b2",
 "canonical/governance/V13_NATIVE_ARTIFACT_MECHANICAL_SELECTED_CELL_20261007_V1.json":"10b766b2983357081f592dc64e576a8cfdd5ad7b",
 "canonical/governance/UNKNOWN_DOMAIN_TRANSFER_SELECTED_CONTEXT_ABC_E2E_BUNDLE_20261007_V1.json":"a5f1895a23bbd0208751fd7437083c137f1102a1",
}
ACCEPTED={
 "LONG_HORIZON_MEMORY_AND_CONTINUITY",
 "SUBAGENT_DELEGATION_AND_COORDINATION",
 "SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
 "TOOL_DISCOVERY_SELECTION_AND_LEARNING",
 "EXACT_SYMBOLIC_COMPUTATION",
}
EXPECTED_IDS={
 "ACCEPTED_LONG_HORIZON_MEMORY_AND_CONTINUITY",
 "ACCEPTED_SUBAGENT_DELEGATION_AND_COORDINATION",
 "ACCEPTED_SELF_VERIFICATION_DEBUGGING_AND_RECOVERY",
 "ACCEPTED_TOOL_DISCOVERY_SELECTION_AND_LEARNING",
 "ACCEPTED_EXACT_SYMBOLIC_COMPUTATION",
 "LIVEBENCH_IF_ACTIVE15_FROZEN_200",
 "NATIVE_ARTIFACT_T1_FROZEN_8_MECHANICAL",
 "UNKNOWN_DOMAIN_V7_EXACT_REACHABLE_FROZEN_PRODUCTION_DOMAIN",
}

def blob(data:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

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
 ids={x.get("id") for x in regions}
 if len(regions)!=8: errors.append("REGION_COUNT")
 if ids!=EXPECTED_IDS: errors.append("REGION_SET_DRIFT")

 lb=load("canonical/governance/LIVEBENCH_IF_V9_SELECTED_CONTEXT_ABC_BUNDLE_20261007_V1.json")
 if (lb.get("selected_cell") or {}).get("id")!="LIVEBENCH_IF_ACTIVE15_FROZEN_200": errors.append("LIVEBENCH_CELL_DRIFT")
 art=load("canonical/governance/V13_NATIVE_ARTIFACT_MECHANICAL_SELECTED_CELL_20261007_V1.json")
 if (art.get("selected_cell") or {}).get("id")!="NATIVE_ARTIFACT_T1_FROZEN_8_MECHANICAL": errors.append("ARTIFACT_CELL_DRIFT")
 unk=load("canonical/governance/UNKNOWN_DOMAIN_TRANSFER_SELECTED_CONTEXT_ABC_E2E_BUNDLE_20261007_V1.json")
 if (unk.get("selected_cell") or {}).get("id")!="UNKNOWN_DOMAIN_V7_EXACT_REACHABLE_FROZEN_PRODUCTION_DOMAIN": errors.append("UNKNOWN_CELL_DRIFT")
 if (unk.get("E2E") or {}).get("scope_complete") is not True: errors.append("UNKNOWN_E2E_SCOPE_NOT_COMPLETE")
 if (unk.get("selected_brain_route") or {}).get("external_model_calls")!=0: errors.append("UNKNOWN_EXTERNAL_MODEL_CALLS")
 if (unk.get("route_local_D") or {}).get("material_effect_footprint")!=[]: errors.append("UNKNOWN_ROUTE_EFFECT_DRIFT")

 sat=m.get("saturation_result") or {}
 if sat.get("known_D_B_region_count")!=8: errors.append("SATURATION_COUNT")
 if sat.get("fresh_target_reality_consumed")!=0: errors.append("FRESH_REALITY_NONZERO")
 if sat.get("regions_may_overlap") is not True or sat.get("coverage_measure_not_claimed") is not True: errors.append("OVERCLAIM_GUARD")
 if "THE_EIGHT_REGIONS_DO_NOT_CLOSE_ABC." not in (m.get("anti_overclaim") or []): errors.append("ABC_OVERCLAIM_GUARD")

 v14=load("canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json")
 if (v14.get("current_truth") or {}).get("terminal") is not False: errors.append("TERMINAL_DRIFT")
 if (v14.get("current_truth") or {}).get("default_context_law_overapproximation")!="K_c_EQUALS_L_c": errors.append("V14_KC_DRIFT")

 return {
  "schema":"PROJECT_BRAIN_V14_DB_SATURATION_V2_VERIFIER",
  "status":"PASS__EIGHT_KNOWN_DB_REGIONS__ZERO_REALITY__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
  "pass":not errors,
  "errors":errors,
  "known_region_count":8 if not errors else None,
  "abc_closed":False,
  "terminal_credit_delta":0,
 }

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
