"""V2 executable semantic verifier for V9 R12 policy-cover totality.

V2 repairs V1's schema mismatch by accepting the exact final-step local-totality
certificate schema already required by professional_step_binding_authority_v2.
One content-addressed certificate can therefore pass both the V8/V9 mediation
gate and this semantic totality gate.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping

from canonical.runtime import professional_r12_v9_policy_cover_totality_semantic_verify_v1 as v1
from canonical.runtime import professional_step_binding_authority_v2 as step_binding
from canonical.runtime import professional_v9_r12_reuse_closure_v1 as reuse

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_V9_POLICY_COVER_TOTALITY_SEMANTIC_VERIFIER_V2"
CERT_SCHEMA=step_binding.TOTALITY_CERT_SCHEMA
CLAIM_ID=v1.CLAIM_ID
CLAIM_PATH=v1.CLAIM_PATH
CLAIM_BLOB=v1.CLAIM_BLOB
AUTH_KEYS=v1.AUTH_KEYS
_ref=v1._ref


def _fail(reason:str,expected:Mapping[str,Any]|None=None)->dict[str,Any]:
 out={"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
      "semantic_totality_verified":False,**{k:False for k in AUTH_KEYS},
      "terminal_credit_delta":0,"incremental_spend_usd":0}
 if isinstance(expected,Mapping):
  for k in ("semantic_property_claim_id","semantic_scope_claim_id","semantic_obligation","target_scope_semantics"):
   if isinstance(expected.get(k),str):out[k]=expected[k]
 return out


def verify_certificate(*,root:Path,certificate_path:Path,expected_binding:Mapping[str,Any])->dict[str,Any]:
 root=root.resolve()
 try:cert=json.loads(certificate_path.read_text(encoding="utf-8"))
 except Exception:return _fail("CERTIFICATE_JSON_INVALID",expected_binding)
 if not isinstance(cert,Mapping) or cert.get("schema")!=CERT_SCHEMA:
  return _fail("CERTIFICATE_SCHEMA_INVALID",expected_binding)
 for k in ("semantic_property_claim_id","semantic_scope_claim_id","semantic_obligation","target_scope_semantics"):
  if cert.get(k)!=expected_binding.get(k):return _fail("BINDING_MISMATCH:"+k,expected_binding)
 if cert.get("claim_id")!=CLAIM_ID:return _fail("STABLE_CLAIM_ID_MISMATCH",expected_binding)
 if cert.get("v9_subject_id")!=reuse.V9_SUBJECT_ID or cert.get("v9_subject_sha256")!=reuse.V9_SUBJECT_SHA256:
  return _fail("V9_SUBJECT_MISMATCH",expected_binding)
 if cert.get("real_exact_run") is not True or cert.get("content_addressed") is not True:
  return _fail("REAL_CONTENT_ADDRESSED_CERTIFICATE_REQUIRED",expected_binding)
 if any(cert.get(k) is not False for k in AUTH_KEYS):return _fail("CERTIFICATE_AUTHORITY_OVERCLAIM",expected_binding)
 claim_ref=cert.get("active_claim") or {}
 if claim_ref.get("path")!=CLAIM_PATH or claim_ref.get("git_blob_sha")!=CLAIM_BLOB:
  return _fail("ACTIVE_CLAIM_REF_MISMATCH",expected_binding)
 claim_path=_ref(root,claim_ref,("canonical/governance/",))
 if claim_path is None:return _fail("ACTIVE_CLAIM_REF_INVALID",expected_binding)
 try:claim=json.loads(claim_path.read_text(encoding="utf-8"))
 except Exception:return _fail("ACTIVE_CLAIM_JSON_INVALID",expected_binding)
 if claim.get("claim_id")!=CLAIM_ID:return _fail("ACTIVE_CLAIM_BYTES_MISMATCH",expected_binding)
 ppath=_ref(root,cert.get("policy_cover_problem_ref"),("canonical/evidence/","canonical/verification/"))
 vpath=_ref(root,cert.get("independent_cover_verification_ref"),("canonical/verification/",))
 rpath=_ref(root,cert.get("r12_reconciliation_ref"),("canonical/governance/",))
 if ppath is None:return _fail("POLICY_COVER_PROBLEM_REF_INVALID",expected_binding)
 if vpath is None:return _fail("INDEPENDENT_COVER_VERIFICATION_REF_INVALID",expected_binding)
 if rpath is None:return _fail("R12_RECONCILIATION_REF_INVALID",expected_binding)
 try:
  problem=json.loads(ppath.read_text()); independent=json.loads(vpath.read_text()); recon=json.loads(rpath.read_text())
 except Exception:return _fail("REFERENCED_JSON_INVALID",expected_binding)
 out=reuse.evaluate_v9_totality_cover(problem,independent,r12_reconciliation=recon)
 if out.get("pass") is not True:return _fail("V9_POLICY_COVER_REJECTED:"+str(out.get("reason") or "UNKNOWN"),expected_binding)
 if out.get("v9_material_defeater_totality_proved") is not True or out.get("cc_r3_terminal_closure_proved") is not True:
  return _fail("V9_POLICY_COVER_TOTALITY_NOT_PROVED",expected_binding)
 if out.get("v9_c8_nonvacuity_proved") is not False:return _fail("C8_MUST_REMAIN_SEPARATE",expected_binding)
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__V2_LOCAL_TOTALITY_SCHEMA_PLUS_EXECUTABLE_V9_POLICY_COVER__C8_SEPARATE",
  "semantic_totality_verified":True,
  **{k:expected_binding[k] for k in ("semantic_property_claim_id","semantic_scope_claim_id","semantic_obligation","target_scope_semantics")},
  "claim_id":CLAIM_ID,"v9_subject_id":reuse.V9_SUBJECT_ID,"v9_subject_sha256":reuse.V9_SUBJECT_SHA256,
  "cc_r3_material_totality_proved":True,"c8_nonvacuity_proved":False,
  **{k:False for k in AUTH_KEYS},"terminal_credit_delta":0,"incremental_spend_usd":0}
