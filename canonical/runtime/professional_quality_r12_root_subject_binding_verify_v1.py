from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R12_ROOT_SUBJECT_BINDING_VERIFY_V1"
BIND="canonical/governance/PROFESSIONAL_QUALITY_R12_ROOT_SUBJECT_BINDING_20261010_V1.json"
BLOB="6eb32264e98bf0b36d48ad3519f9c7c88757d0d7"
SUB="canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json"
SUB_BLOB="1d598bc8757017ceb34928d0df9f5fce859ef868"
SID="PROFESSIONAL_QUALITY_P1_V7_PROOF_BOUND_EXECUTION_SYSTEM_20261010_V6"
SSH="d6671b578b3afbf8f6629462f88ae93a1de62b10eef4df7d5bd90ced6118990e"
REFS={
"subject_verification":("canonical/verification/PROFESSIONAL_QUALITY_DECLARED_SYSTEM_SUBJECT_V7_VERIFY_20261010_V1.json","9bca985bfcef8f5cc6d62b42a51ccc72a6abfd2c"),
"r12_scope":("canonical/governance/PROFESSIONAL_QUALITY_R12_META_COMPOSITION_SCOPE_20261010_V1.json","4c69313ae31905f6aa379361d515dffdfb41efae"),
"uvck_current_generation":("canonical/verification/UVCK_V2_CURRENT_GENERATION_INDEPENDENT_REPLAY_VERIFY_20261009_V1.json","81f7f070233b6aa1c4b491949a4c3e7aedfafd10"),
"defeater_order_soundness":("canonical/verification/UVCK_V2_DEFEATER_ORDER_VERIFY_20261009_V1.json","1c3428b10a1205e928a87f41a7c16a8a3d17b7ca"),
"known_defeater_binding":("canonical/verification/PROFESSIONAL_QUALITY_80_DEFEATER_UVCK_REPLAY_VERIFY_20261009_V1.json","c054e9362ce382889e9cca62bdb69e11cea19644"),
"prior_root_binding_worklist":("canonical/governance/PROFESSIONAL_QUALITY_P1_V7_SAME_SUBJECT_ROOT_BINDING_WORKLIST_20261010_V17.json","ac7750ee9d7cc8e839bf454a2835ad14c9472c0e"),
"composition_gate":("canonical/governance/PROFESSIONAL_QUALITY_SAME_SUBJECT_COMPOSITION_GATE_20261010_V1.json","f7a4496a6579041c6e2606243732c23b22bcf89c"),
"closure_normal_form":("canonical/governance/PROFESSIONAL_QUALITY_CLOSURE_NORMAL_FORM_20261009_V1.json","ebcfe5a48efce9df7fbc69a3817ac2f9adb1ff93")
}
PRIOR_ROOTS=[f"R{i}_" for i in range(1,12)]

def blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()
def read(root:Path,p:str,h:str):
 q=(root/p).resolve()
 try:q.relative_to(root.resolve())
 except ValueError:return None
 if not q.is_file() or q.is_symlink() or blob(q)!=h:return None
 try:o=json.loads(q.read_text())
 except Exception:return None
 return o if isinstance(o,dict) else None
def fail(r:str,**x):
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":r,
 "root_subject_binding_authority":False,"quality_authority":False,"terminal_authority":False,
 "terminal_credit_delta":0,**x}
def auth(doc):
 if doc.get("root_subject_binding_authority") is True:return True
 a=doc.get("authority")
 return isinstance(a,dict) and a.get("root_subject_binding_authority") is True

def verify(repo_root=None):
 root=Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parents[2]
 b=read(root,BIND,BLOB);s=read(root,SUB,SUB_BLOB)
 if not b or not s:return fail("IDENTITY_BYTES_INVALID")
 if b.get("root_id")!="R12_META_COMPOSITION_CLOSURE":return fail("ROOT_ID_INVALID")
 if (b.get("subject_id"),b.get("subject_sha256"))!=(SID,SSH) or (s.get("subject_id"),s.get("subject_sha256"))!=(SID,SSH):return fail("SUBJECT_TUPLE_MISMATCH")
 for f in ("root_subject_binding_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if b.get(f) is not False:return fail("SELF_AUTHORITY_FORBIDDEN:"+f)
 if b.get("unknown_defeater_completeness_proved") is not False:return fail("UNKNOWN_DEFEATER_OVERCLAIM")
 docs={}
 for k,(p,h) in REFS.items():
  rr=(b.get("bridge_evidence") or {}).get(k)
  if not isinstance(rr,dict) or (rr.get("path"),rr.get("git_blob_sha"))!=(p,h):return fail("REFERENCE_MISMATCH:"+k)
  docs[k]=read(root,p,h)
  if docs[k] is None:return fail("REFERENCE_BYTES_INVALID:"+k)
 sv=docs["subject_verification"].get("real_subject_replay") or {}
 if not(sv.get("pass") is True and sv.get("component_count")==22 and sv.get("subject_identity_verified") is True and sv.get("component_currentness_verified") is True):return fail("SUBJECT_VERIFICATION_INSUFFICIENT")
 scope=docs["r12_scope"]
 if scope.get("root_id")!="R12_META_COMPOSITION_CLOSURE" or scope.get("global_root_closure") is not False:return fail("R12_SCOPE_INVALID")
 needg={"SUPPORTED_DEFEATER_DOMINANCE_IS_ORDER_INDEPENDENT","GENERIC_GRAPH_CANNOT_SELF_CERTIFY_EXECUTION_OR_ADVERSARIAL_CLOSURE","UNKNOWN_PRIMITIVE_REMAINS_A_REPRESENTATION_GAP_NOT_AUTOMATIC_CLOSURE","DANGLING_REFERENCES_AND_UNSUPPORTED_DEPENDENCY_CYCLES_FAIL_CLOSED","OPEN_OR_STALE_SUPPORT_REMAINS_AN_EXPLICIT_RESIDUAL"}
 if not needg<=set(scope.get("guarantees") or []):return fail("R12_SCOPE_GUARANTEE_MISSING")
 uv=docs["uvck_current_generation"]
 if (uv.get("replay") or {}).get("tests_passed")!=18:return fail("UVCK_REPLAY_INVALID")
 if "UNKNOWN_DEFEATER_COMPLETENESS" not in set(uv.get("not_proved") or []):return fail("UVCK_UNKNOWN_BOUNDARY_MISSING")
 od=docs["defeater_order_soundness"]
 if (od.get("replay") or {}).get("tests_run")!=11 or (od.get("replay") or {}).get("failures")!=0:return fail("DEFEATER_ORDER_REPLAY_INVALID")
 kd=docs["known_defeater_binding"]
 if (kd.get("replay") or {}).get("tests_run")!=7:return fail("KNOWN_DEFEATER_REPLAY_INVALID")
 if "ALL_80_DECLARED_KNOWN_ATTACK_CLASSES_BIND_TO_EXISTING_12_ROOT_ASSURANCE_ONTOLOGY" not in set(kd.get("proved") or []):return fail("KNOWN_DEFEATER_MAPPING_UNPROVED")
 if "NO_ADVERSARIAL_COMPLETENESS_OF_UNKNOWN_ATTACKS" not in set(kd.get("hard_nonclaims") or []):return fail("KNOWN_DEFEATER_SCOPE_OVERCLAIM")
 nf=docs["closure_normal_form"]
 roots=nf.get("roots") or []
 root_ids={x.get("id") for x in roots if isinstance(x,dict)}
 if len(root_ids)!=12 or "R12_META_COMPOSITION_CLOSURE" not in root_ids:return fail("NORMAL_FORM_ROOT_SET_INVALID")
 necessary=set((nf.get("closure_rule") or {}).get("necessary") or [])
 if "SAME_EXACT_ARTIFACT_OR_DECLARED_SYSTEM_SATISFIES_ALL_ROOT_CLAIMS" not in necessary:return fail("NORMAL_FORM_SAME_SUBJECT_RULE_MISSING")
 gate=docs["composition_gate"]
 if ((gate.get("composition_contract") or {}).get("required_root_count")!=12 or
     (gate.get("authority_boundary") or {}).get("composition_admissibility_only") is not True or
     (gate.get("authority_boundary") or {}).get("quality_authority") is not False):
  return fail("COMPOSITION_GATE_BOUNDARY_INVALID")
 wl=docs["prior_root_binding_worklist"]
 if wl.get("verified_root_subject_binding_count")!=11:return fail("PRIOR_BINDING_COUNT_INVALID")
 rows=wl.get("roots")
 if not isinstance(rows,list) or len(rows)!=12:return fail("WORKLIST_ROOT_SET_INVALID")
 verified=0
 for row in rows:
  rid=row.get("root_id")
  if rid=="R12_META_COMPOSITION_CLOSURE":
   if not str(row.get("same_subject_binding_status","")).startswith("OPEN"):return fail("R12_PREMATURE_AUTHORITY")
   continue
  if not any(str(rid).startswith(p) for p in PRIOR_ROOTS):return fail("UNEXPECTED_PRIOR_ROOT:"+str(rid))
  if not str(row.get("same_subject_binding_status","")).startswith("PASS"):return fail("PRIOR_ROOT_NOT_VERIFIED:"+str(rid))
  br=row.get("binding") or {};vr=row.get("verification") or {}
  bd=read(root,br.get("path",""),br.get("git_blob_sha",""));vd=read(root,vr.get("path",""),vr.get("git_blob_sha",""))
  if bd is None or vd is None:return fail("PRIOR_ROOT_BYTES_INVALID:"+str(rid))
  if (bd.get("subject_id"),bd.get("subject_sha256"))!=(SID,SSH):return fail("PRIOR_ROOT_SUBJECT_DRIFT:"+str(rid))
  if not auth(vd):return fail("PRIOR_ROOT_AUTHORITY_MISSING:"+str(rid))
  verified+=1
 if verified!=11:return fail("PRIOR_VERIFIED_ROOT_TOTAL_INVALID")
 limits=set((b.get("binding_scope") or {}).get("limitations") or [])
 need={"NO_UNKNOWN_DEFEATER_COMPLETENESS","NO_GLOBAL_R12_ROOT_CLOSURE","NO_DOMAIN_SEMANTIC_CLOSURE","NO_DOMAIN_EXECUTION_CLOSURE","NO_FULL_PRIVATE_CURRENT_MAIN_FULL_SYSTEM_REGRESSION","NO_SAME_SUBJECT_COMPOSITION_PASS_FROM_THIS_BINDING_ALONE","NO_LIVE_DEFAULT_PROMOTION"}
 if not need<=limits:return fail("BINDING_LIMITATIONS_INSUFFICIENT")
 return {"schema":SCHEMA,"pass":True,"status":"PASS__R12_BOUND_TO_V7_FAIL_CLOSED_META_COMPOSITION_SCOPE",
 "root_id":"R12_META_COMPOSITION_CLOSURE","subject_id":SID,"subject_sha256":SSH,
 "prior_verified_root_count":11,"known_defeater_count":80,"root_subject_binding_authority":True,
 "unknown_defeater_completeness_proved":False,"global_r12_root_closed":False,
 "same_subject_composition_pass":False,"quality_authority":False,"terminal_authority":False,
 "terminal_credit_delta":0,"incremental_spend_usd":0}
if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
