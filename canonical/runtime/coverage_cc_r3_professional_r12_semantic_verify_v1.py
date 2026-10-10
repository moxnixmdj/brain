"""Stable R12 CC_R3 semantic verifier.

Fine-tunes the previously successful bounded CC_R3 proof pattern to the stable
R12 semantic claim. A root certificate passes only when:
- it binds the exact stable claim;
- its V9 route state uses the exact declared policy-cover totality certificate,
  verifier, and independent receipt;
- rerunning V9 on those exact bytes returns a real positive certificate; and
- V9's executable semantic firewall accepts that same totality proof.

No stored PASS boolean, policy-cover metadata, or synthetic nonvacuity flag is
root authority.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any,Mapping

from canonical.runtime import professional_quality_p1_router_v9 as v9
from canonical.runtime import professional_r12_v9_policy_cover_totality_semantic_verify_v1 as totality_verify

ROOT_ID="CC_R3_TERMINAL_CLOSURE_V1"
CLAIM_ID=totality_verify.CLAIM_ID
CLAIM_PATH=totality_verify.CLAIM_PATH
CLAIM_BLOB=totality_verify.CLAIM_BLOB
CERT_SCHEMA="PROJECT_BRAIN_CC_R3_PROFESSIONAL_R12_SEMANTIC_CERTIFICATE_V1"
TOTALITY_VERIFIER_PATH="canonical/runtime/professional_r12_v9_policy_cover_totality_semantic_verify_v1.py"
TOTALITY_VERIFIER_BLOB="b8f09cdb191388683ac04dba829f83adeb1b00ad"
AUTH_KEYS=("semantic_truth_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority")


def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _safe(root:Path,ref:Any,prefixes:tuple[str,...])->Path|None:
 if not isinstance(ref,Mapping):return None
 rel=ref.get("path"); expected=ref.get("git_blob_sha")
 if not isinstance(rel,str) or not rel or rel.startswith("/") or ".." in Path(rel).parts:return None
 if not any(rel.startswith(p) for p in prefixes):return None
 full=(root/rel).resolve()
 try:full.relative_to(root.resolve())
 except ValueError:return None
 if not full.is_file() or full.is_symlink():return None
 if not isinstance(expected,str) or _blob(full)!=expected:return None
 return full


def _fail(root_id:str,claim_id:str,*errors:str)->dict[str,Any]:
 return {"pass":False,"status":"FAIL_CLOSED__CC_R3_STABLE_R12_UNPROVED",
  "root_id":root_id,"claim_id":claim_id,"errors":sorted(set(errors)),
  "semantic_claim_verified":False,"cc_r3_terminal_closure_proved":False,
  "c8_real_positive_execution_verified":False,"terminal_credit_delta":0}


def verify_certificate(*,root:Path,certificate_path:Path,active_claim:Mapping[str,Any],root_id:str)->dict[str,Any]:
 root=root.resolve();claim_id=str(active_claim.get("claim_id") or "")
 if root_id!=ROOT_ID:return _fail(root_id,claim_id,"ROOT_ID_MISMATCH")
 if claim_id!=CLAIM_ID:return _fail(root_id,claim_id,"ACTIVE_CLAIM_ID_MISMATCH")
 try:cert=json.loads(certificate_path.read_text(encoding="utf-8"))
 except Exception:return _fail(root_id,claim_id,"CERTIFICATE_JSON_INVALID")
 if not isinstance(cert,Mapping) or cert.get("schema")!=CERT_SCHEMA:
  return _fail(root_id,claim_id,"CERTIFICATE_SCHEMA_INVALID")
 errors=[]
 if cert.get("root_id")!=ROOT_ID:errors.append("CERTIFICATE_ROOT_ID_MISMATCH")
 if cert.get("claim_id")!=CLAIM_ID:errors.append("CERTIFICATE_CLAIM_ID_MISMATCH")
 if any(cert.get(k) is not False for k in AUTH_KEYS):errors.append("CERTIFICATE_AUTHORITY_OVERCLAIM")
 if (cert.get("accounting") or {}).get("terminal_credit_delta",0)!=0:errors.append("CERTIFICATE_NONZERO_TERMINAL_CREDIT")

 claim_ref=cert.get("active_claim") or {}
 if claim_ref.get("path")!=CLAIM_PATH or claim_ref.get("git_blob_sha")!=CLAIM_BLOB:
  errors.append("ACTIVE_CLAIM_REF_MISMATCH")
 claim_path=_safe(root,claim_ref,("canonical/governance/",))
 if claim_path is None:errors.append("ACTIVE_CLAIM_REF_INVALID")
 else:
  try:frozen=json.loads(claim_path.read_text(encoding="utf-8"))
  except Exception:frozen={};errors.append("ACTIVE_CLAIM_JSON_INVALID")
  for k in ("claim_id","claim_kind","mission_blob_sha","scope_sha256","target_predicate_sha256","semantics_sha256","epoch","authority_id"):
   if frozen.get(k)!=active_claim.get(k):errors.append("ACTIVE_CLAIM_BINDING_MISMATCH:"+k)

 totality_cert=cert.get("material_totality_certificate")
 totality_verifier=cert.get("material_totality_semantic_verifier")
 totality_receipt=cert.get("material_totality_semantic_verification")
 route_ref=cert.get("v9_route_state")
 if not isinstance(totality_verifier,Mapping) or totality_verifier.get("path")!=TOTALITY_VERIFIER_PATH or totality_verifier.get("git_blob_sha")!=TOTALITY_VERIFIER_BLOB:
  errors.append("TOTALITY_VERIFIER_NOT_EXACT_STABLE_ADAPTER")
 if _safe(root,totality_cert,("canonical/governance/","canonical/evidence/","canonical/verification/")) is None:
  errors.append("TOTALITY_CERT_REF_INVALID")
 if _safe(root,totality_verifier,("canonical/runtime/",)) is None:
  errors.append("TOTALITY_VERIFIER_REF_INVALID")
 if _safe(root,totality_receipt,("canonical/verification/",)) is None:
  errors.append("TOTALITY_RECEIPT_REF_INVALID")
 route_path=_safe(root,route_ref,("canonical/evidence/","canonical/verification/"))
 if route_path is None:errors.append("V9_ROUTE_STATE_REF_INVALID")
 if errors:return _fail(root_id,claim_id,*errors)

 try:state=json.loads(route_path.read_text(encoding="utf-8"))
 except Exception:return _fail(root_id,claim_id,"V9_ROUTE_STATE_JSON_INVALID")
 if not isinstance(state,Mapping):return _fail(root_id,claim_id,"V9_ROUTE_STATE_NOT_OBJECT")
 bindings=state.get(v9.base.STEP_BINDINGS_KEY)
 final=bindings.get(v9.base.FINAL_STEP) if isinstance(bindings,Mapping) else None
 if not isinstance(final,Mapping):return _fail(root_id,claim_id,"V9_FINAL_STEP_BINDING_MISSING")
 for field,expected in (
  ("material_totality_certificate",totality_cert),
  ("material_totality_semantic_verifier",totality_verifier),
  ("material_totality_semantic_verification",totality_receipt),
 ):
  if final.get(field)!=expected:return _fail(root_id,claim_id,"V9_ROUTE_TOTALITY_BINDING_MISMATCH:"+field)

 out=v9.route(state,repo_root=root)
 if not isinstance(out,Mapping):return _fail(root_id,claim_id,"V9_ROUTE_RESULT_NOT_OBJECT")
 if out.get("final_step_outcome")!="POSITIVE_CERTIFICATE":
  return _fail(root_id,claim_id,"V9_REAL_POSITIVE_EXECUTION_NOT_OBSERVED")
 if out.get("positive_certification_authorized") is not True:
  return _fail(root_id,claim_id,"V9_POSITIVE_CERTIFICATION_NOT_AUTHORIZED")
 if out.get("v9_executable_r12_totality_semantics_verified") is not True:
  return _fail(root_id,claim_id,"V9_EXECUTABLE_TOTALITY_SEMANTICS_NOT_VERIFIED")
 sem=out.get("r12_totality_semantic_verification") or {}
 if sem.get("pass") is not True or sem.get("semantic_totality_verified") is not True:
  return _fail(root_id,claim_id,"V9_TOTALITY_SEMANTIC_RECEIPT_NOT_PASS")
 if sem.get("semantic_property_claim_id")!=totality_verify.reuse.PROPERTY_CLAIM_ID:
  return _fail(root_id,claim_id,"V9_TOTALITY_PROPERTY_BINDING_MISMATCH")

 return {"pass":True,"status":"PASS__CC_R3_STABLE_R12__UNIVERSAL_MATERIAL_TOTALITY_PLUS_REAL_V9_POSITIVE_EXECUTION",
  "root_id":ROOT_ID,"claim_id":CLAIM_ID,"semantic_claim_verified":True,
  "cc_r3_terminal_closure_proved":True,"material_defeater_totality_verified":True,
  "c8_real_positive_execution_verified":True,"v9_executable_semantic_authority_verified":True,
  "semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,"errors":[]}
