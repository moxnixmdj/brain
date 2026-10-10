from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
BIND="canonical/governance/PROFESSIONAL_QUALITY_R11_ROOT_SUBJECT_BINDING_20261010_V1.json";BLOB="43007547e14da89b0aef9fad7d0f89cad2bbf77f"
SUB="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json";SUB_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6";SSH="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
TRIG="ADAPTIVE_CONTAMINATION_OR_HOLDOUT_EXPOSURE"
REFS={"execution_profile":("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),"firewall_scope":("canonical/governance/PROFESSIONAL_QUALITY_R11_FIREWALL_SEMANTIC_SCOPE_20261010_V1.json","76494c75e3f2c5af87b77c99ce9984eafec60e32"),"firewall_execution_verification":("canonical/verification/PROFESSIONAL_QUALITY_R11_EVALUATION_FIREWALL_SCOPED_VERIFY_20261010_V1.json","346d369a811aa77af02be901a5b04458fb528667"),"firewall_semantic_verification":("canonical/verification/PROFESSIONAL_QUALITY_R11_FIREWALL_SEMANTIC_VERIFY_20261010_V1.json","7f0468c4abae22504d71ef627efeaf57e85f02a6")}
def blob(p):
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def read(root,p,h):
 q=root/p
 if not q.is_file() or blob(q)!=h:return None
 try:o=json.loads(q.read_text())
 except Exception:return None
 return o if isinstance(o,dict) else None
def fail(r):return {"pass":False,"status":"FAIL_CLOSED","reason":r,"root_subject_binding_authority":False,"terminal_authority":False}
def verify(repo_root=None):
 root=Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
 b=read(root,BIND,BLOB);s=read(root,SUB,SUB_BLOB)
 if not b or not s:return fail("IDENTITY_BYTES_INVALID")
 if (b.get("subject_id"),b.get("subject_sha256"))!=(SID,SSH) or (s.get("subject_id"),s.get("subject_sha256"))!=(SID,SSH):return fail("SUBJECT_TUPLE_MISMATCH")
 for f in ("root_subject_binding_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if b.get(f) is not False:return fail("SELF_AUTHORITY_FORBIDDEN")
 for f in ("prompt_injection_closure_proved","goodhart_closure_proved","holdout_lifecycle_closure_proved","cross_lane_security_proved"):
  if b.get(f) is not False:return fail("R11_SCOPE_OVERCLAIM")
 docs={}
 for k,(p,h) in REFS.items():
  rr=(b.get("bridge_evidence") or {}).get(k)
  if not isinstance(rr,dict) or (rr.get("path"),rr.get("git_blob_sha"))!=(p,h):return fail("REFERENCE_MISMATCH:"+k)
  docs[k]=read(root,p,h)
  if docs[k] is None:return fail("REFERENCE_BYTES_INVALID:"+k)
 if TRIG not in set(docs["execution_profile"].get("escalation_triggers") or []):return fail("HOLDOUT_ESCALATION_MISSING")
 scope=docs["firewall_scope"]
 if scope.get("root_id")!="R11_ADAPTIVE_INTEGRITY_SECURITY" or scope.get("global_root_closure") is not False:return fail("FIREWALL_SCOPE_INVALID")
 lim=set(scope.get("limitations") or [])
 if not {"NO_GENERAL_PROMPT_INJECTION_CLOSURE","NO_GENERAL_GOODHART_CLOSURE","NO_HOLDOUT_LIFECYCLE_CLOSURE"}<=lim:return fail("FIREWALL_BOUNDARY_MISSING")
 if (docs["firewall_execution_verification"].get("replay") or {}).get("tests_passed")!=4:return fail("EXECUTION_REPLAY_INVALID")
 if (docs["firewall_semantic_verification"].get("replay") or {}).get("tests_passed")!=6:return fail("SEMANTIC_REPLAY_INVALID")
 return {"pass":True,"status":"PASS__R11_BOUND_TO_V7_CLEAN_LANE_POST_IDENTITY_REVOCATION_SCOPE","root_id":"R11_ADAPTIVE_INTEGRITY_SECURITY","subject_id":SID,"subject_sha256":SSH,"root_subject_binding_authority":True,"clean_lane_revocation_support":True,"prompt_injection_closure_proved":False,"goodhart_closure_proved":False,"holdout_lifecycle_closure_proved":False,"cross_lane_security_proved":False,"global_r11_root_closed":False,"quality_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
