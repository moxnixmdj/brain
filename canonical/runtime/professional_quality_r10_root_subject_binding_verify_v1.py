from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
BIND="canonical/governance/PROFESSIONAL_QUALITY_R10_ROOT_SUBJECT_BINDING_20261010_V1.json";BLOB="6d8cc56e9273f15f199a624c4a11f1482c76e039"
SUB="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json";SUB_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6";SSH="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
TRIG="MODEL_OR_ANALYSIS_MULTIPLICITY_DECISION_SENSITIVE";STEP="ISSUE_SCOPED_CERTIFICATE_OR_ABSTAIN_WITH_MINIMUM_BLOCKING_CUT"
REFS={
"execution_profile":("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
"decision_scope":("canonical/governance/PROFESSIONAL_QUALITY_R10_DECISION_SEMANTIC_SCOPE_20261010_V1.json","40149db88374c054fd974cc121ee464a3d3996fd"),
"decision_semantic_verification":("canonical/verification/PROFESSIONAL_QUALITY_R10_DECISION_SEMANTIC_VERIFY_20261010_V1.json","c298b2510e352d876c1abacc069e915447e97823"),
"decision_sufficiency_verification":("canonical/verification/PROFESSIONAL_QUALITY_R10_DECISION_SUFFICIENCY_SCOPED_VERIFY_20261010_V1.json","18574110321eb1bacc18db46cbd0673bf6a0a0ac")}
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
 for f in ("normative_aggregation_closure_proved","model_multiplicity_decision_closure_proved","general_risk_policy_closure_proved"):
  if b.get(f) is not False:return fail("R10_SCOPE_OVERCLAIM")
 docs={}
 for k,(p,h) in REFS.items():
  rr=(b.get("bridge_evidence") or {}).get(k)
  if not isinstance(rr,dict) or (rr.get("path"),rr.get("git_blob_sha"))!=(p,h):return fail("REFERENCE_MISMATCH:"+k)
  docs[k]=read(root,p,h)
  if docs[k] is None:return fail("REFERENCE_BYTES_INVALID:"+k)
 profile=docs["execution_profile"]
 if TRIG not in set(profile.get("escalation_triggers") or []):return fail("DECISION_ESCALATION_MISSING")
 if STEP not in set(profile.get("steps") or []):return fail("MINIMUM_BLOCKING_CUT_STEP_MISSING")
 scope=docs["decision_scope"]
 if scope.get("root_id")!="R10_ANALYSIS_DECISION" or scope.get("global_root_closure") is not False:return fail("DECISION_SCOPE_INVALID")
 lim=set(scope.get("limitations") or [])
 if not {"NO_GENERAL_PROFESSIONAL_RISK_POLICY_CLOSURE","NO_NORMATIVE_AGGREGATION_CLOSURE","NO_MODEL_MULTIPLICITY_DECISION_CLOSURE"}<=lim:return fail("DECISION_BOUNDARY_MISSING")
 if (docs["decision_semantic_verification"].get("replay") or {}).get("tests_passed")!=6:return fail("SEMANTIC_REPLAY_INVALID")
 if (docs["decision_sufficiency_verification"].get("replay") or {}).get("tests_passed")!=23:return fail("SUFFICIENCY_REPLAY_INVALID")
 return {"pass":True,"status":"PASS__R10_BOUND_TO_V7_LOSSLESS_MINIMUM_INFORMATION_DECISION_SCOPE","root_id":"R10_ANALYSIS_DECISION","subject_id":SID,"subject_sha256":SSH,"root_subject_binding_authority":True,"minimum_information_decision_support":True,"normative_aggregation_closure_proved":False,"model_multiplicity_decision_closure_proved":False,"general_risk_policy_closure_proved":False,"global_r10_root_closed":False,"quality_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
