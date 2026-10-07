from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MANIFEST="canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V3.json"
EXPECTED={
 "canonical/governance/V13_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V1.json":"7f116258890759d1730d688bdf713faa3e4440a8",
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json":"d9bd211b2557ac45331f6fe0c4347392f4cd7a95",
 "canonical/governance/UNKNOWN_DOMAIN_TRANSFER_SELECTED_CONTEXT_ABC_E2E_BUNDLE_20261007_V1.json":"a5f1895a23bbd0208751fd7437083c137f1102a1",
 "canonical/governance/V14_P2_PROFESSIONAL_TOP_LAW_SELECTED_CELL_20261007_V1.json":"481b8efd7925c19d7f4e77faf70dfb2ec649cca5",
 "canonical/governance/V14_SYNTHESIS_UNSUPPORTED_CLAIM_SELECTED_PROPERTY_CELL_20261007_V1.json":"eece175e4aae05e34cdc7f44a25c12af94853228",
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
 old=load("canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V2.json")
 new=load(MANIFEST)
 old_ids=[x["id"] for x in old.get("known_D_B_regions",[])]
 new_ids=[x["id"] for x in new.get("known_D_B_regions",[])]
 if len(old_ids)!=9 or len(set(old_ids))!=9: errors.append("BASE_NINE_INVALID")
 if len(new_ids)!=10 or len(set(new_ids))!=10: errors.append("NEW_TEN_INVALID")
 if not set(old_ids).issubset(new_ids): errors.append("BASE_REGION_LOST")
 expected_new={"P2_PROFESSIONAL_T1_FROZEN_30_HIDDEN_OPTIMUM"}
 if set(new_ids)-set(old_ids)!=expected_new: errors.append("DELTA_NOT_EXACTLY_ONE")

 p2=load("canonical/governance/V14_P2_PROFESSIONAL_TOP_LAW_SELECTED_CELL_20261007_V1.json")
 if not ((p2.get("theorem") or {}).get("D_B_effect")=="ADD_ONLY_P2_PROFESSIONAL_T1_FROZEN_30_HIDDEN_OPTIMUM_TO_D_B" and (p2.get("selected_cell") or {}).get("global_professional_scope_complete") is False): errors.append("P2_CELL_INVALID")
 u=load("canonical/governance/UNKNOWN_DOMAIN_TRANSFER_SELECTED_CONTEXT_ABC_E2E_BUNDLE_20261007_V1.json")
 if not ((u.get("consequence") or {}).get("selected_cell_ABC_candidate") is True and
         (u.get("E2E") or {}).get("scope_complete") is True and
         (u.get("E2E") or {}).get("independent_or_objective") is True and
         (u.get("consequence") or {}).get("family_closed") is False):
  errors.append("UNKNOWN_DOMAIN_CELL_INVALID")

 s=load("canonical/governance/V14_SYNTHESIS_UNSUPPORTED_CLAIM_SELECTED_PROPERTY_CELL_20261007_V1.json")
 if not ((s.get("selected_property_cell") or {}).get("brain_value")==1 and
         (s.get("selected_property_cell") or {}).get("top_value")==1 and
         (s.get("v14_effect") or {}).get("K_c_minus")=="EMPTY_BECAUSE_BRAIN_VALUE_IS_THE_TOP_ELEMENT_ONE" and
         "NO_SYNTHESIS_FAMILY_CLOSURE" in (s.get("hard_nonclaims") or [])):
  errors.append("SYNTHESIS_CELL_INVALID")

 if (new.get("saturation_result") or {}).get("known_D_B_region_count")!=10:
  errors.append("COUNT_DRIFT")
 if (new.get("saturation_result") or {}).get("coverage_measure_not_claimed") is not True:
  errors.append("COVERAGE_OVERCLAIM")
 if any("CLOSE_ABC" in str(x) for x in new.get("scheduler_effect",[])):
  errors.append("ABC_FALSELY_CLOSED")
 return {
  "schema":"PROJECT_BRAIN_V14_DB_EXISTING_EVIDENCE_SATURATION_VERIFY_V2",
  "status":"PASS__TEN_SOUND_CACHED_D_B_REGIONS__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
  "pass":not errors,
  "errors":errors,
  "base_region_count":9,
  "new_region_count":10 if not errors else 0,
  "delta_region_count":1 if not errors else 0,
  "abc_closed":False,
  "d_finality_closed":False,
  "terminal":False,
  "terminal_credit_delta":0,
 }
if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
