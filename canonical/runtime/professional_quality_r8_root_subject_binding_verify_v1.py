from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path

BIND="canonical/governance/PROFESSIONAL_QUALITY_R8_ROOT_SUBJECT_BINDING_20261010_V1.json"
BLOB="e5b0b434fb040b77443e541e80c6f5e0890ff7aa"
SUB="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUB_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SSH="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
TRIGGER="POPULATION_CONTEXT_OPERATOR_OR_TIME_TRANSPORT_GAP"
REFS={
"execution_profile":("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
"r8_context_scope":("canonical/governance/PROFESSIONAL_QUALITY_R8_POPULATION_CONTEXT_SCOPE_20261010_V1.json","b174a62c94d36474f0b102d37362ea9fc3adaa91"),
"r8_semantic_scope":("canonical/governance/PROFESSIONAL_QUALITY_R8_POPULATION_SEMANTIC_SCOPE_20261010_V1.json","5bdcf0f7f46daf9abc2cca90524e702c9b601007"),
"r8_semantic_verification":("canonical/verification/PROFESSIONAL_QUALITY_R8_POPULATION_SEMANTIC_VERIFY_20261010_V1.json","e47503a3b1f61bbb9effa04edccbf158b8b28e96"),
"population_preflight_verification":("canonical/verification/DELEGATION_TERMINAL_POPULATION_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json","3965db684d7104c5829ce1fcfa8ee08d2cd42cfc")}
def blob(p):
 d=p.read_bytes(); return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def read(root,path,sha):
 p=root/path
 if not p.is_file() or blob(p)!=sha:return None
 try:o=json.loads(p.read_text())
 except Exception:return None
 return o if isinstance(o,dict) else None
def fail(r):return {"pass":False,"status":"FAIL_CLOSED","reason":r,"root_subject_binding_authority":False,"terminal_authority":False}
def verify(repo_root=None):
 root=Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
 b=read(root,BIND,BLOB); s=read(root,SUB,SUB_BLOB)
 if not b or not s:return fail("IDENTITY_BYTES_INVALID")
 if (b.get("subject_id"),b.get("subject_sha256"))!=(SID,SSH) or (s.get("subject_id"),s.get("subject_sha256"))!=(SID,SSH):return fail("SUBJECT_TUPLE_MISMATCH")
 for f in ("root_subject_binding_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if b.get(f) is not False:return fail("SELF_AUTHORITY_FORBIDDEN")
 if b.get("target_constituency_generalization_proved") is not False or b.get("operator_generalization_proved") is not False or b.get("post_freeze_terminal_result_proved") is not False:return fail("SCOPE_OVERCLAIM")
 docs={}
 for k,(p,h) in REFS.items():
  r=(b.get("bridge_evidence") or {}).get(k)
  if not isinstance(r,dict) or (r.get("path"),r.get("git_blob_sha"))!=(p,h):return fail("REFERENCE_MISMATCH:"+k)
  docs[k]=read(root,p,h)
  if docs[k] is None:return fail("REFERENCE_BYTES_INVALID:"+k)
 if TRIGGER not in set(docs["execution_profile"].get("escalation_triggers") or []):return fail("TRIGGER_MISSING")
 sem=docs["r8_semantic_scope"]
 if sem.get("root_id")!="R8_POPULATION_CONTEXT_OPERATOR" or sem.get("global_root_closure") is not False:return fail("SEMANTIC_SCOPE_INVALID")
 limits=set(sem.get("limitations") or [])
 if "NO_CONSTITUENCY_SUPPORT_CLAIM" not in limits or "NO_PRESENTER_OR_OPERATOR_GENERALIZATION" not in limits:return fail("SEMANTIC_BOUNDARY_MISSING")
 sv=docs["r8_semantic_verification"]
 if (sv.get("replay") or {}).get("tests_passed")!=6:return fail("SEMANTIC_REPLAY_INVALID")
 pre=docs["population_preflight_verification"]
 req={"FRESH_512_CASE_PRE_BEACON_POPULATION_PASSES","ALL_SIX_FROZEN_DELEGATION_CASE_CLASSES_PRESENT","ZERO_CASE_REPLACEMENT","ZERO_ADAPTIVE_CASE_SELECTION","ZERO_TUNING_REPLAY"}
 if pre.get("workflow_conclusion")!="success" or not req<=set(pre.get("verified") or []) or pre.get("terminal_results_observed")!=0:return fail("POPULATION_PREFLIGHT_INVALID")
 bl=set((b.get("binding_scope") or {}).get("limitations") or [])
 if not {"NO_CONSTITUENCY_SUPPORT_CLAIM","NO_PRESENTER_OR_OPERATOR_GENERALIZATION","NO_POST_FREEZE_TERMINAL_RESULT","NO_GLOBAL_R8_ROOT_CLOSURE"}<=bl:return fail("BINDING_LIMITS_INVALID")
 return {"pass":True,"status":"PASS__R8_BOUND_TO_V7_FROZEN_512_POPULATION_SCOPE","root_id":"R8_POPULATION_CONTEXT_OPERATOR","subject_id":SID,"subject_sha256":SSH,"root_subject_binding_authority":True,"target_constituency_generalization_proved":False,"operator_generalization_proved":False,"post_freeze_terminal_result_proved":False,"global_r8_root_closed":False,"quality_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
