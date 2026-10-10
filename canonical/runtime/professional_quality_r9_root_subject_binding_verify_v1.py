from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
BIND="canonical/governance/PROFESSIONAL_QUALITY_R9_ROOT_SUBJECT_BINDING_20261010_V1.json"; BLOB="7c9f22e80110389768d4c16876571d54304b4536"
SUB="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"; SUB_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"; SSH="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
TRIGGER="POPULATION_CONTEXT_OPERATOR_OR_TIME_TRANSPORT_GAP"
REFS={
"execution_profile":("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
"censor_scope":("canonical/governance/PROFESSIONAL_QUALITY_R9_CONSERVATIVE_CENSORING_SCOPE_20261010_V1.json","7755bc709169abe0db35a6418fd8568ed14131b7"),
"temporal_scope":("canonical/governance/PROFESSIONAL_QUALITY_R9_TEMPORAL_SEMANTIC_SCOPE_20261010_V1.json","0f2a434454802d5f76157ce51f19f16bb9cbfd8f"),
"censor_verification":("canonical/verification/PROFESSIONAL_QUALITY_R9_CONSERVATIVE_CENSORING_VERIFY_20261010_V1.json","7081a52621a1bb8f1ad07d1da23b40c8e57e16c2"),
"temporal_verification":("canonical/verification/PROFESSIONAL_QUALITY_R9_TEMPORAL_SEMANTIC_VERIFY_20261010_V1.json","e4527631fbf6e95cb20381d60eb4fe4b978c176f")}
def blob(p):
 d=p.read_bytes(); return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def read(root,p,h):
 q=root/p
 if not q.is_file() or blob(q)!=h:return None
 try:o=json.loads(q.read_text())
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
 for f in ("multihorizon_deployment_validity_proved","rare_event_coverage_proved","distribution_shift_transport_proved","performative_equilibrium_stability_proved"):
  if b.get(f) is not False:return fail("TEMPORAL_OVERCLAIM")
 docs={}
 for k,(p,h) in REFS.items():
  rr=(b.get("bridge_evidence") or {}).get(k)
  if not isinstance(rr,dict) or (rr.get("path"),rr.get("git_blob_sha"))!=(p,h):return fail("REFERENCE_MISMATCH:"+k)
  docs[k]=read(root,p,h)
  if docs[k] is None:return fail("REFERENCE_BYTES_INVALID:"+k)
 if TRIGGER not in set(docs["execution_profile"].get("escalation_triggers") or []):return fail("TRIGGER_MISSING")
 sc=docs["censor_scope"]; sem=docs["temporal_scope"]
 if sc.get("root_id")!="R9_TEMPORAL_DEPLOYMENT" or sc.get("global_root_closure") is True:return fail("CENSOR_SCOPE_INVALID")
 if sem.get("root_id")!="R9_TEMPORAL_DEPLOYMENT" or sem.get("global_root_closure") is not False:return fail("TEMPORAL_SCOPE_INVALID")
 lim=set(sem.get("limitations") or [])
 if not {"NO_MULTIHORIZON_DEPLOYMENT_VALIDITY","NO_RARE_EVENT_COVERAGE_CLAIM","NO_DISTRIBUTION_SHIFT_TRANSPORT_CLAIM","NO_PERFORMATIVE_OR_EQUILIBRIUM_STABILITY"}<=lim:return fail("TEMPORAL_BOUNDARY_MISSING")
 cv=docs["censor_verification"]; tv=docs["temporal_verification"]
 if (cv.get("replay") or {}).get("exhaustive_final_success_counts_checked")!=211:return fail("CENSOR_REPLAY_INSUFFICIENT")
 if (tv.get("replay") or {}).get("tests_passed")!=8:return fail("TEMPORAL_REPLAY_INSUFFICIENT")
 bl=set((b.get("binding_scope") or {}).get("limitations") or [])
 if not {"NO_MULTIHORIZON_DEPLOYMENT_VALIDITY","NO_RARE_EVENT_COVERAGE_CLAIM","NO_DISTRIBUTION_SHIFT_TRANSPORT_CLAIM","NO_GLOBAL_R9_ROOT_CLOSURE"}<=bl:return fail("BINDING_LIMITS_INVALID")
 return {"pass":True,"status":"PASS__R9_BOUND_TO_V7_FROZEN_210_SLOT_TEMPORAL_ACCOUNTING_SCOPE","root_id":"R9_TEMPORAL_DEPLOYMENT","subject_id":SID,"subject_sha256":SSH,"root_subject_binding_authority":True,"bounded_temporal_accounting_support":True,"multihorizon_deployment_validity_proved":False,"rare_event_coverage_proved":False,"distribution_shift_transport_proved":False,"performative_equilibrium_stability_proved":False,"global_r9_root_closed":False,"quality_authority":False,"terminal_authority":False,"terminal_credit_delta":0}
if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
