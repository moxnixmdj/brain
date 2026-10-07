from __future__ import annotations
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
C="canonical/governance/CURRENT_TERMINAL_AUTHORITY_POINTER_V15_CANDIDATE.json"
E={
"canonical/governance/CURRENT_TERMINAL_AUTHORITY.json":"f66928a97218fa5d327a9faaf53e90bcb1c89aec",
"canonical/governance/DB_EXISTING_EVIDENCE_SATURATION_UNION_20261007_V12.json":"0c98bea583d35392cbde49e2830b283bdbb09d06",
"canonical/verification/DB_EXISTING_EVIDENCE_SATURATION_UNION_V12_CONNECTOR_VERIFICATION_20261007_V2.json":"006023b2d89a5e6f869a92a013b426409793e420",
"canonical/governance/P2_STRONG_VISIBLE_QUALITY_COMPARISON_ORDER_ADMISSION_V2_20261007_V1.json":"bf5fbe5957901ea998db89594f1bbc94796d007b",
"canonical/verification/P2_STRONG_VISIBLE_QUALITY_COMPARISON_ORDER_V2_INDEPENDENT_REPLAY_20261007_V1.json":"8f9ea47493931af8b9e80809e783d8e85f002860"
}
def blob(p):
 b=(R/p).read_bytes()
 return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def load(p): return json.loads((R/p).read_text())
def verify():
 e=[]
 for p,h in E.items():
  if blob(p)!=h:e.append("DRIFT:"+p)
 c=load(C)
 db=load("canonical/verification/DB_EXISTING_EVIDENCE_SATURATION_UNION_V12_CONNECTOR_VERIFICATION_20261007_V2.json")
 p2=load("canonical/verification/P2_STRONG_VISIBLE_QUALITY_COMPARISON_ORDER_V2_INDEPENDENT_REPLAY_20261007_V1.json")
 if (db.get("verified") or {}).get("known_sound_D_B_certificate_record_count")!=17:e.append("DB_COUNT")
 if (db.get("verified") or {}).get("semantic_union_widened") is not True:e.append("DB_NOT_WIDENED")
 if (db.get("verified") or {}).get("U_empty_proved") is not False:e.append("DB_OVERCLAIM")
 if (p2.get("replay") or {}).get("pass_count")!=11:e.append("P2_REPLAY")
 if "BOUND_COMPARISON_ORDER_MODE_PASSES_WITHOUT_FULL_RUBRIC_EQUIVALENCE." not in (p2.get("verified") or []):e.append("P2_ORDER_MODE")
 t=c.get("preserved_live_truth") or {}
 if t.get("known_sound_D_B_certificate_record_count")!=17:e.append("C_COUNT")
 if t.get("open_ABC_refinement_family_count")!=13:e.append("C_OPEN")
 if t.get("terminal") is not False:e.append("C_TERMINAL")
 if (c.get("scheduler_delta") or {}).get("professional_quality",{}).get("real_AA_or_GDP_context_admission_count")!=0:e.append("REAL_CONTEXT_OVERCLAIM")
 return {"pass":not e,"errors":e,"db_records":17 if not e else None,"open_abc":13 if not e else None,"terminal":False,"terminal_credit_delta":0}
if __name__=="__main__":
 o=verify();print(json.dumps(o,sort_keys=True));raise SystemExit(0 if o["pass"] else 1)
