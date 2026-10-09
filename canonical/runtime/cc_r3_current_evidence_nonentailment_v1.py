import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES={
"canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json":"87d154877fd195d4726db46db8a607a02e4dcc31",
"canonical/governance/CURRENT_PRIMITIVE_U_FRONTIER_20261007_V1.json":"8340829830dc81095abd4d643a8be6894a39f2f3",
"canonical/governance/SELECTED_COVER_COMPLEMENT_UNSAT_NORMAL_FORM_20261007_V1.json":"fbcf760f4bbcfcd5b14af529f1fb2f16f0787f4a",
"canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json":"6a97c7f13717b5b31a75b6938f1cf55b9398d6d9",
}
def blob(p):
 d=p.read_bytes();return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def evaluate(root=ROOT):
 e=[];docs={}
 for rel,want in SOURCES.items():
  p=root/rel
  if not p.is_file(): e.append("MISSING:"+rel);continue
  got=blob(p)
  if got!=want:e.append("DRIFT:"+rel);continue
  docs[rel]=json.loads(p.read_text())
 if e:return {"pass":False,"status":"FAIL_CLOSED_SOURCE_DRIFT","errors":e,"terminal_credit_delta":0}
 reg=docs["canonical/governance/COVERAGE_COMPLETENESS_ROOT_CERTIFICATE_REGISTRY_V1.json"]
 u=docs["canonical/governance/CURRENT_PRIMITIVE_U_FRONTIER_20261007_V1.json"]
 c=docs["canonical/governance/SELECTED_COVER_COMPLEMENT_UNSAT_NORMAL_FORM_20261007_V1.json"]
 r2=docs["canonical/governance/CURRENT_R2_DECISION_INTELLIGENCE.json"]
 slot=next((x for x in reg.get("certificate_slots",[]) if x.get("root_id")=="CC_R3_TERMINAL_CLOSURE_V1"),{})
 if slot.get("status")!="OPEN_NO_GLOBAL_CERTIFICATE_BOUND":e.append("CC_R3_SLOT_NOT_OPEN")
 if (u.get("current_truth") or {}).get("U_empty") is not False:e.append("U_EMPTY_STATE_DRIFT")
 if (c.get("current_truth") or {}).get("residual_complement_unsat_proved") is not False:e.append("RESIDUAL_UNSAT_STATE_DRIFT")
 if "NO_CLAIM_U_IS_EMPTY." not in (u.get("hard_nonclaims") or []):e.append("U_NONCLAIM_MISSING")
 if "NO_CLAIM_R_IS_UNSAT." not in (c.get("hard_nonclaims") or []):e.append("R_NONCLAIM_MISSING")
 if r2.get("global_open_world_closure_claimed") is not False:e.append("R2_CLOSURE_DRIFT")
 return {"pass":not e,"status":"PASS_CC_R3_CURRENT_EVIDENCE_OPEN" if not e else "FAIL_CLOSED_STATE_DRIFT","errors":e,"cc_r3_closed":False,"cc_r3_falsified":False,"terminal_credit_delta":0}
if __name__=="__main__":print(json.dumps(evaluate(),indent=2,sort_keys=True))
