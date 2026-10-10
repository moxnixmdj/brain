"""V2 stable R12 CC_R3 semantic verifier.

V2 is identical in proof intent to V1, but requires the schema-compatible V2
material-totality semantic verifier. The exact same local-totality certificate
must pass V8/V9 mediation, V9 executable semantic verification, and this root
gate.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping

from canonical.runtime import coverage_cc_r3_professional_r12_semantic_verify_v1 as old
from canonical.runtime import professional_r12_v9_policy_cover_totality_semantic_verify_v2 as totality_verify
from canonical.runtime import professional_quality_p1_router_v9 as v9

ROOT_ID=old.ROOT_ID
CLAIM_ID=old.CLAIM_ID
CLAIM_PATH=old.CLAIM_PATH
CLAIM_BLOB=old.CLAIM_BLOB
CERT_SCHEMA=old.CERT_SCHEMA
AUTH_KEYS=old.AUTH_KEYS
TOTALITY_VERIFIER_PATH="canonical/runtime/professional_r12_v9_policy_cover_totality_semantic_verify_v2.py"
TOTALITY_VERIFIER_BLOB="08ee0e1a82162032daadf002f6364b2b10a86ed3"
_safe=old._safe
_fail=old._fail


def verify_certificate(*,root:Path,certificate_path:Path,active_claim:Mapping[str,Any],root_id:str)->dict[str,Any]:
 root=root.resolve();claim_id=str(active_claim.get("claim_id") or "")
 if root_id!=ROOT_ID:return _fail(root_id,claim_id,"ROOT_ID_MISMATCH")
 if claim_id!=CLAIM_ID:return _fail(root_id,claim_id,"ACTIVE_CLAIM_ID_MISMATCH")
 try:cert=json.loads(certificate_path.read_text(encoding="utf-8"))
 except Exception:return _fail(root_id,claim_id,"CERTIFICATE_JSON_INVALID")
 if not isinstance(cert,Mapping) or cert.get("schema")!=CERT_SCHEMA:return _fail(root_id,claim_id,"CERTIFICATE_SCHEMA_INVALID")
 errors=[]
 if cert.get("root_id")!=ROOT_ID:errors.append("CERTIFICATE_ROOT_ID_MISMATCH")
 if cert.get("claim_id")!=CLAIM_ID:errors.append("CERTIFICATE_CLAIM_ID_MISMATCH")
 if any(cert.get(k) is not False for k in AUTH_KEYS):errors.append("CERTIFICATE_AUTHORITY_OVERCLAIM")
 if (cert.get("accounting") or {}).get("terminal_credit_delta",0)!=0:errors.append("CERTIFICATE_NONZERO_TERMINAL_CREDIT")
 cref=cert.get("active_claim") or {}
 if cref.get("path")!=CLAIM_PATH or cref.get("git_blob_sha")!=CLAIM_BLOB:errors.append("ACTIVE_CLAIM_REF_MISMATCH")
 cp=_safe(root,cref,("canonical/governance/",))
 if cp is None:errors.append("ACTIVE_CLAIM_REF_INVALID")
 else:
  try:frozen=json.loads(cp.read_text())
  except Exception:frozen={};errors.append("ACTIVE_CLAIM_JSON_INVALID")
  for k in ("claim_id","claim_kind","mission_blob_sha","scope_sha256","target_predicate_sha256","semantics_sha256","epoch","authority_id"):
   if frozen.get(k)!=active_claim.get(k):errors.append("ACTIVE_CLAIM_BINDING_MISMATCH:"+k)
 tc=cert.get("material_totality_certificate");tv=cert.get("material_totality_semantic_verifier")
 tr=cert.get("material_totality_semantic_verification");rr=cert.get("v9_route_state")
 if not isinstance(tv,Mapping) or tv.get("path")!=TOTALITY_VERIFIER_PATH or tv.get("git_blob_sha")!=TOTALITY_VERIFIER_BLOB:
  errors.append("TOTALITY_VERIFIER_NOT_EXACT_V2_ADAPTER")
 if _safe(root,tc,("canonical/governance/","canonical/evidence/","canonical/verification/")) is None:errors.append("TOTALITY_CERT_REF_INVALID")
 if _safe(root,tv,("canonical/runtime/",)) is None:errors.append("TOTALITY_VERIFIER_REF_INVALID")
 if _safe(root,tr,("canonical/verification/",)) is None:errors.append("TOTALITY_RECEIPT_REF_INVALID")
 rp=_safe(root,rr,("canonical/evidence/","canonical/verification/"))
 if rp is None:errors.append("V9_ROUTE_STATE_REF_INVALID")
 if errors:return _fail(root_id,claim_id,*errors)
 try:state=json.loads(rp.read_text())
 except Exception:return _fail(root_id,claim_id,"V9_ROUTE_STATE_JSON_INVALID")
 if not isinstance(state,Mapping):return _fail(root_id,claim_id,"V9_ROUTE_STATE_NOT_OBJECT")
 bindings=state.get(v9.base.STEP_BINDINGS_KEY);final=bindings.get(v9.base.FINAL_STEP) if isinstance(bindings,Mapping) else None
 if not isinstance(final,Mapping):return _fail(root_id,claim_id,"V9_FINAL_STEP_BINDING_MISSING")
 for field,expected in (
  ("material_totality_certificate",tc),
  ("material_totality_semantic_verifier",tv),
  ("material_totality_semantic_verification",tr),
 ):
  if final.get(field)!=expected:return _fail(root_id,claim_id,"V9_ROUTE_TOTALITY_BINDING_MISMATCH:"+field)
 out=v9.route(state,repo_root=root)
 if not isinstance(out,Mapping):return _fail(root_id,claim_id,"V9_ROUTE_RESULT_NOT_OBJECT")
 if out.get("final_step_outcome")!="POSITIVE_CERTIFICATE":return _fail(root_id,claim_id,"V9_REAL_POSITIVE_EXECUTION_NOT_OBSERVED")
 if out.get("positive_certification_authorized") is not True:return _fail(root_id,claim_id,"V9_POSITIVE_CERTIFICATION_NOT_AUTHORIZED")
 if out.get("v9_executable_r12_totality_semantics_verified") is not True:return _fail(root_id,claim_id,"V9_EXECUTABLE_TOTALITY_SEMANTICS_NOT_VERIFIED")
 sem=out.get("r12_totality_semantic_verification") or {}
 if sem.get("pass") is not True or sem.get("semantic_totality_verified") is not True:return _fail(root_id,claim_id,"V9_TOTALITY_SEMANTIC_RECEIPT_NOT_PASS")
 if sem.get("semantic_property_claim_id")!=totality_verify.reuse.PROPERTY_CLAIM_ID:return _fail(root_id,claim_id,"V9_TOTALITY_PROPERTY_BINDING_MISMATCH")
 return {"pass":True,"status":"PASS__CC_R3_STABLE_R12_V2__SHARED_LOCAL_TOTALITY_CERT_PLUS_REAL_V9_POSITIVE_EXECUTION",
  "root_id":ROOT_ID,"claim_id":CLAIM_ID,"semantic_claim_verified":True,
  "cc_r3_terminal_closure_proved":True,"material_defeater_totality_verified":True,
  "c8_real_positive_execution_verified":True,"v9_executable_semantic_authority_verified":True,
  "semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,"errors":[]}
