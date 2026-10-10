"""Stable R12 CC_R3 verifier V4: forbid run-scoped-to-whole-leaf scope inflation.

V3 correctly composes stable C8 with executable material-totality evidence, but
its upstream policy-cover adapter can originate from one exact run. The frozen
R12 property quantifies over the entire admissible whole-leaf domain. V4
therefore requires an explicit independently verified whole-leaf lift before
V3 success can receive CC_R3 root authority.

This is a soundness guard, not a proof of the missing lift.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import coverage_cc_r3_professional_r12_semantic_verify_v3 as v3

ROOT_ID=v3.ROOT_ID
CLAIM_ID=v3.CLAIM_ID
CLAIM_PATH=v3.CLAIM_PATH
CLAIM_BLOB=v3.CLAIM_BLOB
CERT_SCHEMA=v3.CERT_SCHEMA
SCOPE_CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
LIFT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_WHOLE_LEAF_TOTALITY_LIFT_V1"
LIFT_VERIFY_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_WHOLE_LEAF_TOTALITY_LIFT_INDEPENDENT_VERIFY_V1"
ALLOWED_PROOF_MODES=frozenset({"FORMAL_UNIVERSAL_REDUCTION","INDEPENDENT_CERTIFIED_COMPLETE_UNION"})
_fail=v3._fail

def _canon_sha(value:Any)->str:
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def _lift_ok(lift:Any,verification:Any)->tuple[bool,list[str]]:
 errors=[]
 if not isinstance(lift,Mapping):return False,["WHOLE_LEAF_TOTALITY_LIFT_REQUIRED"]
 if lift.get("schema")!=LIFT_SCHEMA:errors.append("WHOLE_LEAF_LIFT_SCHEMA_INVALID")
 if lift.get("property_claim_id")!=CLAIM_ID:errors.append("WHOLE_LEAF_LIFT_CLAIM_ID_MISMATCH")
 if lift.get("scope_claim_id")!=SCOPE_CLAIM_ID:errors.append("WHOLE_LEAF_LIFT_SCOPE_ID_MISMATCH")
 if lift.get("proof_mode") not in ALLOWED_PROOF_MODES:errors.append("WHOLE_LEAF_LIFT_PROOF_MODE_INVALID")
 for field in ("whole_leaf_domain_equivalence_proved","all_admissible_inputs_covered","unknown_remainder_empty","independent_verified","content_addressed"):
  if lift.get(field) is not True:errors.append("WHOLE_LEAF_LIFT_PREMISE_UNPROVED:"+field)
 if lift.get("finite_single_run_extrapolation") is not False:errors.append("SINGLE_RUN_EXTRAPOLATION_FORBIDDEN")
 if lift.get("source_scope_kind") not in ("UNIVERSAL_WHOLE_LEAF","INDEPENDENT_CERTIFIED_COMPLETE_UNION"):
  errors.append("WHOLE_LEAF_LIFT_SOURCE_SCOPE_NOT_GLOBAL")
 if lift.get("terminal_credit_delta",0)!=0:errors.append("WHOLE_LEAF_LIFT_NONZERO_TERMINAL_CREDIT")
 if not isinstance(verification,Mapping):errors.append("WHOLE_LEAF_LIFT_INDEPENDENT_VERIFY_REQUIRED")
 else:
  if verification.get("schema")!=LIFT_VERIFY_SCHEMA:errors.append("WHOLE_LEAF_LIFT_VERIFY_SCHEMA_INVALID")
  if verification.get("pass") is not True or verification.get("independent_verified") is not True:
   errors.append("WHOLE_LEAF_LIFT_VERIFY_NOT_PASS")
  if verification.get("property_claim_id")!=CLAIM_ID or verification.get("scope_claim_id")!=SCOPE_CLAIM_ID:
   errors.append("WHOLE_LEAF_LIFT_VERIFY_BINDING_MISMATCH")
  if verification.get("lift_sha256")!=_canon_sha(lift):errors.append("WHOLE_LEAF_LIFT_VERIFY_DIGEST_MISMATCH")
  if verification.get("finite_single_run_extrapolation_rejected") is not True:
   errors.append("WHOLE_LEAF_LIFT_VERIFY_SINGLE_RUN_GUARD_MISSING")
 return not errors,errors

def verify_certificate(*,root:Path,certificate_path:Path,active_claim:Mapping[str,Any],root_id:str)->dict[str,Any]:
 root=root.resolve();cid=str(active_claim.get("claim_id") or "")
 if root_id!=ROOT_ID:return _fail(root_id,cid,"ROOT_ID_MISMATCH")
 if cid!=CLAIM_ID:return _fail(root_id,cid,"ACTIVE_CLAIM_ID_MISMATCH")
 try:cert=json.loads(certificate_path.read_text(encoding="utf-8"))
 except Exception:return _fail(root_id,cid,"CERTIFICATE_JSON_INVALID")
 if not isinstance(cert,Mapping) or cert.get("schema")!=CERT_SCHEMA:return _fail(root_id,cid,"CERTIFICATE_SCHEMA_INVALID")
 ok,errors=_lift_ok(cert.get("whole_leaf_totality_lift"),cert.get("whole_leaf_totality_lift_verification"))
 if not ok:return _fail(root_id,cid,*errors)
 base=v3.verify_certificate(root=root,certificate_path=certificate_path,active_claim=active_claim,root_id=root_id)
 if base.get("pass") is not True:return base
 result=dict(base)
 result["status"]="PASS__CC_R3_STABLE_R12_V4__WHOLE_LEAF_LIFT_PLUS_V3_TOTALITY_AND_STABLE_C8"
 result["whole_leaf_totality_lift_verified"]=True
 result["finite_single_run_extrapolation_rejected"]=True
 result["cc_r3_terminal_closure_proved"]=True
 result["terminal_credit_delta"]=0
 return result
