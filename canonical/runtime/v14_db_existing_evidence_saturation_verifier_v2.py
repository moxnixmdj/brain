from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
M="canonical/governance/V14_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V2.json"
EXPECTED={
 "canonical/governance/CURRENT_TERMINAL_AUTHORITY_V14.json":"d9bd211b2557ac45331f6fe0c4347392f4cd7a95",
 "canonical/governance/V13_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V1.json":"7f116258890759d1730d688bdf713faa3e4440a8",
 "canonical/governance/V14_SYNTHESIS_UNSUPPORTED_CLAIM_SELECTED_PROPERTY_CELL_20261007_V1.json":"eece175e4aae05e34cdc7f44a25c12af94853228",
}
def blob(b:bytes)->str:
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((ROOT/p).read_text())
def verify():
 errors=[]
 for p,w in EXPECTED.items():
  q=ROOT/p
  if not q.is_file(): errors.append("SOURCE_MISSING:"+p); continue
  if blob(q.read_bytes())!=w: errors.append("SOURCE_DRIFT:"+p)
 d=load(M)
 regs=d.get("known_D_B_regions") or []
 if len(regs)!=8: errors.append("REGION_COUNT")
 ids={x.get("id") for x in regs}
 if "SYNTHESIS_T1_T3_FROZEN_60_ZERO_UNSUPPORTED_MATERIAL_CLAIMS" not in ids: errors.append("SYNTH_CELL_MISSING")
 if (d.get("saturation_result") or {}).get("known_D_B_region_count")!=8: errors.append("DECLARED_COUNT")
 if (d.get("saturation_result") or {}).get("regions_may_overlap") is not True: errors.append("OVERLAP_GUARD")
 if (d.get("saturation_result") or {}).get("coverage_measure_not_claimed") is not True: errors.append("COVERAGE_GUARD")
 if "THE_EIGHT_REGIONS_DO_NOT_CLOSE_ABC." not in (d.get("anti_overclaim") or []): errors.append("ABC_GUARD")
 return {"status":"PASS__EIGHT_KNOWN_DB_REGIONS__ZERO_REALITY__ZERO_CREDIT" if not errors else "FAIL_CLOSED","pass":not errors,"errors":errors,"known_region_count":8 if not errors else None,"abc_closed":False,"terminal_credit_delta":0}
if __name__=="__main__": print(json.dumps(verify(),indent=2,sort_keys=True))
