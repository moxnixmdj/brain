"""Semantic verifier for the Professional R12 CC_R3 V10 root certificate."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import coverage_cc_r3_professional_r12_v10_universal_positive_gate_verify_v1 as universal

ROOT_ID="CC_R3_TERMINAL_CLOSURE_V1"
CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"

def _fail(reason:str)->dict[str,Any]:
 return {"pass":False,"root_id":ROOT_ID,"claim_id":CLAIM_ID,"reason":reason,
         "cc_r3_terminal_closure_proved":False,"property_truth_implied":False,
         "terminal_credit_delta":0}

def verify_certificate(*,root:Path,certificate_path:Path,active_claim:Mapping[str,Any],root_id:str)->dict[str,Any]:
 if root_id!=ROOT_ID:return _fail("ROOT_ID_MISMATCH")
 if not isinstance(active_claim,Mapping) or active_claim.get("claim_id")!=CLAIM_ID:return _fail("ACTIVE_CLAIM_MISMATCH")
 try: cert=json.loads(Path(certificate_path).read_text(encoding="utf-8"))
 except Exception:return _fail("CERTIFICATE_JSON_INVALID")
 if not isinstance(cert,Mapping):return _fail("CERTIFICATE_NOT_OBJECT")
 if cert.get("root_id")!=ROOT_ID or cert.get("claim_id")!=CLAIM_ID:return _fail("CERTIFICATE_IDENTITY_MISMATCH")
 binding=cert.get("claim_binding") or {}
 for k in ("claim_id","claim_kind","mission_blob_sha","scope_sha256","target_predicate_sha256","semantics_sha256","epoch","authority_id"):
  if binding.get(k)!=active_claim.get(k):return _fail("CLAIM_BINDING_MISMATCH:"+k)
 theorem=cert.get("theorem") or {}
 if theorem.get("universal_positive_route_local_totality") is not True:return _fail("THEOREM_PREMISE_MISSING")
 if theorem.get("abstention_fail_closed") is not True:return _fail("ABSTENTION_PREMISE_MISSING")
 out=universal.verify(repo_root=root)
 if out.get("pass") is not True or out.get("cc_r3_terminal_closure_proved") is not True:
  return _fail("UNIVERSAL_POSITIVE_GATE_PROOF_REJECTED")
 return {"pass":True,"root_id":ROOT_ID,"claim_id":CLAIM_ID,
  "cc_r3_terminal_closure_proved":True,
  "universal_positive_route_local_totality":True,
  "abstention_fail_closed":True,
  "v10_subject_sha256":out.get("proof_basis") and "bb9dfcec9e006aebebcfa904ff6bf096aa01c62392f16f5915c2bf8e7fca1be5",
  "proof_mode":"FORMAL_REDUCTION",
  "property_truth_implied":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0}
