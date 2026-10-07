from __future__ import annotations
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
PTR="canonical/governance/CURRENT_TERMINAL_AUTHORITY.json"
V16="canonical/governance/CURRENT_TERMINAL_AUTHORITY_V16.json"
FR="canonical/governance/COMPLETE_SELECTED_ROUTE_COVER_SINGLE_ABC_FRONTIER_20261007_V3.json"
DB="canonical/governance/V16_DB_EXISTING_EVIDENCE_SATURATION_MANIFEST_20261007_V7.json"
DBV="canonical/verification/V16_DB_EXISTING_EVIDENCE_SATURATION_VERIFY_20261007_V7.json"
P3="canonical/governance/P3_FROZEN_DIRECT_CONJUNCTION_TOPLAW_20261007_V1.json"
FALS="canonical/governance/P3_FROZEN_DIRECT_CONJUNCTION_TOPLAW_EXECUTED_SCORER_FALSIFIER_20261007_V1.json"
EXPECTED={
 PTR:"1a40d6de0b0203323b12a432676de28266c46f43",
 V16:"24aba9397af4bdd9c2d7f9abc47d6f2b9966bcff",
 FR:"1cfad0bc541ee6516bd6963da195c5e6e13344af",
 DB:"862649b49fe0b94ff2d6e3cea05119ade614cfb3",
 DBV:"60e46a05dac7b37853da42c21c6168b9d0239fa6",
 P3:"768953c6f754a911a1483733e84164087e77dd31",
 FALS:"d4339cca92dabd058ae4675bcb3fa9e6d25bf391",
}
def blob(rel):
 b=(R/rel).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(rel): return json.loads((R/rel).read_text(encoding="utf-8"))
def verify():
 e=[]
 for p,h in EXPECTED.items():
  if not (R/p).is_file(): e.append("MISSING:"+p)
  elif blob(p)!=h: e.append("DRIFT:"+p)
 if e:return {"pass":False,"errors":e,"terminal":False}
 ptr=load(PTR); v16=load(V16); fr=load(FR); db=load(DB); dbv=load(DBV); p3=load(P3); fals=load(FALS)
 if ptr.get("live_truth",{}).get("known_sound_D_B_certificate_record_count")!=14:e.append("POINTER_COUNT")
 if v16.get("truth_repair",{}).get("known_sound_D_B_certificate_record_count")!=14:e.append("V16_COUNT")
 if fr.get("current_reconciliation",{}).get("known_cached_certificate_record_count")!=14:e.append("FRONTIER_COUNT")
 if db.get("reconciliation",{}).get("known_sound_region_certificate_count")!=14:e.append("DB_COUNT")
 if dbv.get("reconciliation_check",{}).get("reconciled_certificate_count")!=14:e.append("DB_VERIFY_COUNT")
 if p3.get("active") is not False:e.append("P3_NOT_REVOKED")
 if p3.get("abc_effect",{}).get("add_to_D_B") is not None:e.append("P3_STILL_ADDED")
 if fals.get("falsified_claim",{}).get("invalidated_derived_claims") is None:e.append("FALSIFIER_MISSING")
 if fr.get("truth_repair",{}).get("removed_record")!="P3_T1_T3_FROZEN_60_WHOLE_DIRECT_SYNTHESIS_CONJUNCTION":e.append("FRONTIER_REVOCATION_BINDING")
 if ptr.get("truth_repair",{}).get("revoked_record")!="P3_T1_T3_FROZEN_60_WHOLE_DIRECT_SYNTHESIS_CONJUNCTION":e.append("POINTER_REVOCATION_BINDING")
 if ptr.get("live_truth",{}).get("terminal") is not False:e.append("TERMINAL_DRIFT")
 if v16.get("truth_repair",{}).get("current_U_empty_proved") is not False:e.append("U_FALSELY_CLOSED")
 return {"schema":"PROJECT_BRAIN_CURRENT_TERMINAL_POINTER_V3_TRUTH_REPAIR_VERIFY_V1","pass":not e,"errors":e,"sound_D_B_record_count":14 if not e else None,"revoked_p3_whole_cell_excluded":not e,"U_empty_proved":False,"terminal":False,"terminal_credit_delta":0}
if __name__=="__main__":
 o=verify();print(json.dumps(o,sort_keys=True));raise SystemExit(0 if o["pass"] else 1)
