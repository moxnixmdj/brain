"""Professional-quality same-subject composition gate V4.

V4 preserves V3 receipt normalization and fail-closed composition semantics while
recognizing the one intentional current binding-schema strengthening:
R3_REALIZATION_OBSERVATION uses ROOT_SUBJECT_BINDING_V2 because it adds the
exact real-task render-step receipt to the already verified V1 structural scope.
All other current V7 root bindings remain V1. No schema wildcard is permitted.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import professional_quality_same_subject_composition_gate_v3 as v3

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_SAME_SUBJECT_COMPOSITION_GATE_V4"
EXPECTED_ROOTS=v3.EXPECTED_ROOTS
ALLOWED_BINDING_SCHEMA={
 "R1_TARGET_SPECIFICATION":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1",
 "R2_CANDIDATE_SEARCH":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1",
 "R3_REALIZATION_OBSERVATION":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V2",
 "R4_MEASUREMENT_CONSTRUCT":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1",
 "R5_EVALUATOR_REFERENCE":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1",
 "R6_EVIDENCE_GROUNDING_DEPENDENCE":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1",
 "R7_CAUSAL_PRESCRIPTIVE":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1",
 "R8_POPULATION_CONTEXT_OPERATOR":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1",
 "R9_TEMPORAL_DEPLOYMENT":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1",
 "R10_ANALYSIS_DECISION":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1",
 "R11_ADAPTIVE_INTEGRITY_SECURITY":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1",
 "R12_META_COMPOSITION_CLOSURE":"PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1",
}

def _base(status:str,*,passed:bool=False,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"status":status,"pass":passed,"composition_admissible":False,
 "professional_quality_closed":False,"semantic_truth_authority":False,
 "execution_authority":False,"quality_authority":False,"acceptance_authority":False,
 "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,**extra}
def _fail(reason:str,**extra:Any)->dict[str,Any]: return _base("FAIL_CLOSED",reason=reason,**extra)

def _r3_v2_binding_boundary(root:Path,binding:Mapping[str,Any])->str|None:
 sup=binding.get("supersedes")
 base_verify=binding.get("base_v1_verification")
 base,base_blob,error=v3._read_bound(root,sup,label="R3_BASE_V1_BINDING")
 if error:return error
 verify,_,error=v3._read_bound(root,base_verify,label="R3_BASE_V1_VERIFICATION")
 if error:return error
 assert base is not None and base_blob is not None and verify is not None
 if base.get("schema")!="PROJECT_BRAIN_PROFESSIONAL_QUALITY_ROOT_SUBJECT_BINDING_V1":return "R3_BASE_V1_SCHEMA_INVALID"
 if base.get("root_id")!="R3_REALIZATION_OBSERVATION":return "R3_BASE_V1_ROOT_INVALID"
 if (base.get("subject_kind"),base.get("subject_id"),base.get("subject_sha256"))!=(binding.get("subject_kind"),binding.get("subject_id"),binding.get("subject_sha256")):
  return "R3_BASE_V1_SUBJECT_DRIFT"
 if base.get("global_subject_identity_authority") is not False:return "R3_BASE_V1_GLOBAL_AUTHORITY_FORBIDDEN"
 if base.get("terminal_authority") is not False:return "R3_BASE_V1_TERMINAL_AUTHORITY_FORBIDDEN"
 if verify.get("root_subject_binding_authority") is not True:return "R3_BASE_V1_VERIFICATION_AUTHORITY_REQUIRED"
 if (verify.get("exact_blobs") or {}).get("binding")!=base_blob:return "R3_BASE_V1_VERIFICATION_BLOB_MISMATCH"
 if verify.get("terminal_authority") is not False:return "R3_BASE_V1_VERIFY_TERMINAL_AUTHORITY_FORBIDDEN"
 if binding.get("global_r3_root_closed") is not False:return "R3_V2_GLOBAL_ROOT_CLOSURE_FORBIDDEN"
 for field in ("root_subject_binding_authority","semantic_truth_authority","execution_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if binding.get(field) is not False:return "R3_V2_SELF_AUTHORITY_FORBIDDEN:"+field
 return None

def _verification_receipt_error(*,root_id:str,verification:Mapping[str,Any],binding_blob:str,subject_kind:str,subject_id:str,subject_sha:str)->str|None:
 if root_id=="R3_REALIZATION_OBSERVATION" and verification.get("schema")=="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R3_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V2":
  if verification.get("root_id")!=root_id:return "SUBJECT_BINDING_VERIFY_ROOT_MISMATCH"
  if (verification.get("exact_blobs") or {}).get("v2_binding")!=binding_blob:return "SUBJECT_BINDING_VERIFY_BLOB_MISMATCH"
  status=str(verification.get("status") or "")
  replay=verification.get("replay") or {}
  if not status.startswith("PASS__") or replay.get("package_execution")!="PASS" or not str(replay.get("verifier_status") or "").startswith("PASS__"):
   return "SUBJECT_BINDING_VERIFY_NOT_PASS"
  if verification.get("root_subject_binding_authority") is not True:return "ROOT_SUBJECT_BINDING_AUTHORITY_REQUIRED"
  if verification.get("global_r3_root_closed") is not False:return "R3_VERIFY_GLOBAL_ROOT_CLOSURE_FORBIDDEN"
  if verification.get("terminal_authority") is not False:return "SUBJECT_BINDING_VERIFY_TERMINAL_AUTHORITY_FORBIDDEN"
  if "NO_SAME_SUBJECT_COMPOSITION_PASS" not in set(verification.get("hard_nonclaims") or []):return "R3_VERIFY_COMPOSITION_NONCLAIM_REQUIRED"
  return None
 return v3._verification_receipt_error(root_id=root_id,verification=verification,binding_blob=binding_blob,subject_kind=subject_kind,subject_id=subject_id,subject_sha=subject_sha)

def evaluate(payload:Mapping[str,Any],*,repo_root:str|Path|None=None)->dict[str,Any]:
 if not isinstance(payload,Mapping):return _fail("PAYLOAD_NOT_OBJECT")
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 normal_ok,normal=v3._normal_form_ok(root)
 if not normal_ok:return _fail("NORMAL_FORM_SAME_SUBJECT_LAW_UNAVAILABLE",normal_form=normal)

 from canonical.runtime import professional_quality_scoped_evidence_overlay_v1 as scoped
 scoped_result=scoped.evaluate(repo_root=root)
 if scoped_result.get("pass") is not True:
  return _fail("SCOPED_EVIDENCE_REGISTRY_NOT_CURRENT",scoped_evidence_status=scoped_result.get("status"))
 admitted=scoped_result.get("admitted_scopes")
 if not isinstance(admitted,list):return _fail("SCOPED_EVIDENCE_ADMITTED_SCOPES_INVALID")
 admitted_roots={str(x.get("root_id") or "") for x in admitted if isinstance(x,Mapping)}
 if admitted_roots!=EXPECTED_ROOTS:
  return _fail("SCOPED_EVIDENCE_ROOT_COVER_INCOMPLETE",admitted_root_ids=sorted(admitted_roots),admitted_scope_count=len(admitted))

 rows=payload.get("root_subject_bindings")
 if not isinstance(rows,list):return _fail("ROOT_SUBJECT_BINDINGS_NOT_LIST")
 if not rows:
  return _base("OPEN__SAME_SUBJECT_BINDINGS_REQUIRED",normal_form=normal,scoped_root_count=len(admitted_roots),admitted_scope_count=len(admitted),missing_root_ids=sorted(EXPECTED_ROOTS))
 root_rows={}
 for i,row in enumerate(rows):
  if not isinstance(row,Mapping):return _fail("ROOT_SUBJECT_BINDING_ROW_INVALID",row_index=i)
  rid=row.get("root_id")
  if not isinstance(rid,str) or rid not in EXPECTED_ROOTS:return _fail("ROOT_SUBJECT_BINDING_ROOT_INVALID",row_index=i)
  if rid in root_rows:return _fail("ROOT_SUBJECT_BINDING_ROOT_DUPLICATE",root_id=rid)
  root_rows[rid]=row
 missing=sorted(EXPECTED_ROOTS-set(root_rows))
 if missing:return _base("OPEN__SAME_SUBJECT_BINDINGS_INCOMPLETE",normal_form=normal,missing_root_ids=missing,extra_root_ids=[])

 verified=[]; subjects=set()
 for rid in sorted(EXPECTED_ROOTS):
  row=root_rows[rid]
  binding,bblob,error=v3._read_bound(root,row.get("binding"),label="SUBJECT_BINDING")
  if error:return _fail(error,root_id=rid)
  assert binding is not None and bblob is not None
  if binding.get("schema")!=ALLOWED_BINDING_SCHEMA[rid]:
   return _fail("SUBJECT_BINDING_SCHEMA_INVALID",root_id=rid,expected_schema=ALLOWED_BINDING_SCHEMA[rid],actual_schema=binding.get("schema"))
  if binding.get("root_id")!=rid:return _fail("SUBJECT_BINDING_ROOT_MISMATCH",root_id=rid)
  kind,sid,sha=binding.get("subject_kind"),binding.get("subject_id"),binding.get("subject_sha256")
  if not isinstance(kind,str) or not isinstance(sid,str) or not isinstance(sha,str) or len(sha)!=64:
   return _fail("SUBJECT_IDENTITY_INVALID",root_id=rid)
  if rid=="R3_REALIZATION_OBSERVATION":
   boundary_error=_r3_v2_binding_boundary(root,binding)
   if boundary_error:return _fail(boundary_error,root_id=rid)
  else:
   if binding.get("global_subject_identity_authority") is not False:return _fail("GLOBAL_SUBJECT_AUTHORITY_FORBIDDEN",root_id=rid)
   if binding.get("terminal_authority") is not False:return _fail("SUBJECT_BINDING_TERMINAL_AUTHORITY_FORBIDDEN",root_id=rid)
  verification,_,error=v3._read_bound(root,row.get("verification"),label="SUBJECT_BINDING_VERIFICATION")
  if error:return _fail(error,root_id=rid)
  assert verification is not None
  receipt_error=_verification_receipt_error(root_id=rid,verification=verification,binding_blob=bblob,subject_kind=kind,subject_id=sid,subject_sha=sha)
  if receipt_error:return _fail(receipt_error,root_id=rid)
  subjects.add((kind,sid,sha))
  verified.append({"root_id":rid,"binding_schema":binding.get("schema"),"subject_kind":kind,"subject_id":sid,"subject_sha256":sha,"subject_binding_git_blob_sha":bblob})
 if len(subjects)!=1:
  return _base("OPEN__ROOT_SUBJECT_BINDINGS_NOT_IDENTICAL",normal_form=normal,distinct_subject_count=len(subjects),verified_bindings=verified)
 kind,sid,sha=next(iter(subjects))
 out=_base("PASS__SAME_SUBJECT_ROOT_COMPOSITION_ADMISSIBLE",passed=True,normal_form=normal,
  scoped_root_count=len(admitted_roots),admitted_scope_count=len(admitted),
  verified_root_subject_binding_count=len(verified),
  composed_subject={"subject_kind":kind,"subject_id":sid,"subject_sha256":sha},
  verified_bindings=verified)
 out["composition_admissible"]=True
 return out

if __name__=="__main__":
 print(json.dumps(evaluate({"root_subject_bindings":[]}),indent=2,sort_keys=True))
