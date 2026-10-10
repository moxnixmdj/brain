"""Stable R12 CC_R3 verifier V3: reuse already-proved stable C8.

Current R12 C8 nonvacuity is already proved for this exact stable claim by a
real independently replayed supported route. V3 therefore requires no new V9
positive execution. CC_R3 closes only when that current C8 proof is combined
with executable independently verified claim-wide material-defeater totality.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import coverage_cc_r3_professional_r12_semantic_verify_v2 as v2
from canonical.runtime import professional_r12_totality_semantic_receipt_v1 as sem
from canonical.runtime import professional_r12_v9_policy_cover_totality_semantic_verify_v2 as totality

ROOT_ID=v2.ROOT_ID
CLAIM_ID=v2.CLAIM_ID
CLAIM_PATH=v2.CLAIM_PATH
CLAIM_BLOB=v2.CLAIM_BLOB
CERT_SCHEMA=v2.CERT_SCHEMA
RECON_PATH="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V3.json"
RECON_BLOB="56a5f85e6133661dd7afbc8fc5041ad799f0736f"
C8_PATH="canonical/verification/PROFESSIONAL_R12_STABLE_C8_NONVACUITY_VERIFY_20261010_V1.json"
C8_BLOB="6ed0f5d253d0fc734af2998e86ad72f73fe8c073"
TOTALITY_VERIFIER_PATH="canonical/runtime/professional_r12_v9_policy_cover_totality_semantic_verify_v2.py"
TOTALITY_VERIFIER_BLOB="08ee0e1a82162032daadf002f6364b2b10a86ed3"
AUTH=v2.AUTH_KEYS
_safe=v2._safe
_fail=v2._fail

def expected_binding():
 return {"semantic_property_claim_id":totality.reuse.PROPERTY_CLAIM_ID,
  "semantic_scope_claim_id":totality.reuse.SCOPE_CLAIM_ID,
  "semantic_obligation":totality.reuse.OBLIGATION,
  "target_scope_semantics":totality.reuse.TARGET_SCOPE_SEMANTICS}

def verify_certificate(*,root:Path,certificate_path:Path,active_claim:Mapping[str,Any],root_id:str)->dict[str,Any]:
 root=root.resolve();cid=str(active_claim.get("claim_id") or "")
 if root_id!=ROOT_ID:return _fail(root_id,cid,"ROOT_ID_MISMATCH")
 if cid!=CLAIM_ID:return _fail(root_id,cid,"ACTIVE_CLAIM_ID_MISMATCH")
 try:cert=json.loads(certificate_path.read_text())
 except Exception:return _fail(root_id,cid,"CERTIFICATE_JSON_INVALID")
 if not isinstance(cert,Mapping) or cert.get("schema")!=CERT_SCHEMA:return _fail(root_id,cid,"CERTIFICATE_SCHEMA_INVALID")
 errors=[]
 if cert.get("root_id")!=ROOT_ID:errors.append("CERTIFICATE_ROOT_ID_MISMATCH")
 if cert.get("claim_id")!=CLAIM_ID:errors.append("CERTIFICATE_CLAIM_ID_MISMATCH")
 if any(cert.get(k) is not False for k in AUTH):errors.append("CERTIFICATE_AUTHORITY_OVERCLAIM")
 if (cert.get("accounting") or {}).get("terminal_credit_delta",0)!=0:errors.append("CERTIFICATE_NONZERO_TERMINAL_CREDIT")
 refs=(("active_claim",CLAIM_PATH,CLAIM_BLOB,"canonical/governance/"),
       ("r12_reconciliation",RECON_PATH,RECON_BLOB,"canonical/governance/"),
       ("stable_c8_verification",C8_PATH,C8_BLOB,"canonical/verification/"))
 bound={}
 for key,path,blob,prefix in refs:
  ref=cert.get(key)
  if not isinstance(ref,Mapping) or ref.get("path")!=path or ref.get("git_blob_sha")!=blob:
   errors.append(key.upper()+"_REF_MISMATCH");continue
  p=_safe(root,ref,(prefix,))
  if p is None:errors.append(key.upper()+"_REF_INVALID")
  else:bound[key]=p
 verifier=cert.get("material_totality_semantic_verifier")
 if not isinstance(verifier,Mapping) or verifier.get("path")!=TOTALITY_VERIFIER_PATH or verifier.get("git_blob_sha")!=TOTALITY_VERIFIER_BLOB:
  errors.append("TOTALITY_VERIFIER_NOT_V2")
 if errors:return _fail(root_id,cid,*errors)
 try:
  frozen=json.loads(bound["active_claim"].read_text())
  recon=json.loads(bound["r12_reconciliation"].read_text())
  c8=json.loads(bound["stable_c8_verification"].read_text())
 except Exception:return _fail(root_id,cid,"BOUND_SUPPORT_JSON_INVALID")
 for k in ("claim_id","claim_kind","mission_blob_sha","scope_sha256","target_predicate_sha256","semantics_sha256","epoch","authority_id"):
  if frozen.get(k)!=active_claim.get(k):errors.append("ACTIVE_CLAIM_BINDING_MISMATCH:"+k)
 d=recon.get("derived") or {}
 if d.get("all_eight_root_contract_clauses_verified") is not True or d.get("verified_clause_count")!=8:
  errors.append("C1_C8_NOT_CURRENT")
 reasoning=c8.get("reasoning") or {}; consequence=c8.get("consequence") or {}
 if c8.get("claim_id")!=CLAIM_ID or c8.get("scope_sha256")!=active_claim.get("scope_sha256"):
  errors.append("STABLE_C8_CLAIM_SCOPE_DRIFT")
 if reasoning.get("witness_is_real_executed_route") is not True or reasoning.get("witness_is_independently_replayed") is not True:
  errors.append("STABLE_C8_REAL_WITNESS_NOT_PROVED")
 if consequence.get("r12_c8_nonvacuity_proved") is not True:errors.append("STABLE_C8_NOT_PROVED")
 if errors:return _fail(root_id,cid,*errors)
 s=sem.validate(root=root,certificate_ref=cert.get("material_totality_certificate"),
  semantic_verifier_ref=verifier,
  independent_verification_ref=cert.get("material_totality_semantic_verification"),
  expected_binding=expected_binding())
 if s.get("pass") is not True or s.get("semantic_totality_verified") is not True:
  return _fail(root_id,cid,"EXECUTABLE_MATERIAL_TOTALITY_NOT_PROVED")
 return {"pass":True,"status":"PASS__CC_R3_STABLE_R12_V3__STABLE_C8_REUSED_PLUS_EXECUTABLE_MATERIAL_TOTALITY",
  "root_id":ROOT_ID,"claim_id":CLAIM_ID,"semantic_claim_verified":True,
  "c1_c8_verified":True,"stable_c8_reused":True,"new_v9_positive_route_required":False,
  "material_defeater_totality_verified":True,"cc_r3_terminal_closure_proved":True,
  "semantic_truth_authority":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,"errors":[]}
