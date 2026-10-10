"""Executable verifier for the subordinate R12 safe-certification property.

This verifier closes only claim 4d94... over the exact safe-wrapper invocation
domain. It explicitly does not close or transport authority to the stronger
whole-leaf R12 semantic-sufficiency claim 11870....
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any,Mapping
from unittest.mock import patch

from canonical.runtime.coverage_claim_scope_guard_v1 import compute_claim_id
from canonical.runtime import professional_r12_safe_meta_composition_v1 as safe

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SAFE_CERTIFICATION_DISPOSITION_PROPERTY_VERIFY_V1"
CLAIM_ID="4d94bc346ec20e2778c1fe8655274dd0e9ff4cd67e94681164f77be9fb4e1962"
STRONGER_CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
CERT_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SAFE_CERTIFICATION_DISPOSITION_PROPERTY_CERTIFICATE_V1"
PINS={
 "claim":("canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SAFE_CERTIFICATION_DISPOSITION_20261011_V1.json","89f42a45b6b26232473e891da5e8708805c65d98"),
 "runtime":("canonical/runtime/professional_r12_safe_meta_composition_v1.py","7c1b6631fc237e7ff7160ba1080f326555e05c52"),
 "tests":("canonical/tests/test_professional_r12_safe_meta_composition_v1.py","73d48eb3de1f72c6f8083a5a44fb59f140c58167"),
 "runtime_verify":("canonical/verification/PROFESSIONAL_R12_SAFE_CERTIFICATION_DISPOSITION_INDEPENDENT_VERIFY_20261011_V1.json","028a5f8200b033914cb5202b2f6f512a9abab9d5"),
 "v8_verify":("canonical/verification/PROFESSIONAL_QUALITY_P1_ROUTER_V8_TOTALITY_MEDIATION_INDEPENDENT_VERIFY_20261010_V1.json","ee8a51e8db8e5f58f8b09cc658001c9f19b664c4"),
 "v9_verify":("canonical/verification/PROFESSIONAL_R12_V9_EXECUTABLE_TOTALITY_SEMANTIC_INDEPENDENT_VERIFY_20261010_V2.json","450b28d112be708bb65698581f64410e4991e86d"),
 "refine_verify":("canonical/verification/PROFESSIONAL_V8_TO_V9_R12_POSITIVE_REFINEMENT_INDEPENDENT_VERIFY_20261010_V1.json","555f8b37ff9b02d4a313121b531f12c60914cf44"),
 "real_replay":("canonical/verification/V9_REAL_R12_SECOND_CARRIER_REPLAY_VERIFY_20261011_V1.json","93fd0bcb6ec271df53fd9694cc3dc242a185aab0"),
 "stronger_claim":("canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V2.json","7b26ddba501358d42d6fa342efd27d389bb30654"),
 "mission":("canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json","13c470645b037bbb46245c687dd35197b420d51a"),
}

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "claim_id":CLAIM_ID,"safe_property_truth_proved":False,
  "stronger_r12_semantic_sufficiency_proved":False,"stronger_r12_authority_transported":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,**extra}

def _pin(root:Path,key:str)->Path:
 rel,expected=PINS[key];p=root/rel
 if not p.is_file() or p.is_symlink():raise ValueError("PIN_MISSING:"+key)
 got=_blob(p)
 if got!=expected:raise ValueError("PIN_BLOB_DRIFT:"+key+":"+got)
 return p

def _load(root:Path,key:str)->dict[str,Any]:
 p=_pin(root,key)
 if p.suffix!=".json":raise ValueError("JSON_PIN_REQUIRED:"+key)
 o=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(o,dict):raise ValueError("PIN_NOT_OBJECT:"+key)
 return o

def verify_certificate(*,repo_root:str|Path|None=None,certificate_path:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  for key in ("runtime","tests"):_pin(root,key)
  docs={k:_load(root,k) for k in PINS if k not in ("runtime","tests")}
 except Exception as exc:return _fail(type(exc).__name__+":"+str(exc))
 cp=Path(certificate_path) if certificate_path is not None else root/"canonical/governance/PROFESSIONAL_R12_SAFE_CERTIFICATION_DISPOSITION_PROPERTY_CERTIFICATE_20261011_V1.json"
 if not cp.is_absolute():cp=root/cp
 try:cert=json.loads(cp.read_text(encoding="utf-8"))
 except Exception:return _fail("CERTIFICATE_JSON_INVALID")
 if not isinstance(cert,Mapping) or cert.get("schema")!=CERT_SCHEMA:return _fail("CERTIFICATE_SCHEMA_INVALID")
 if cert.get("claim_id")!=CLAIM_ID:return _fail("CERTIFICATE_CLAIM_ID_MISMATCH")
 if (cert.get("stronger_r12_claim") or {}).get("authority_transported") is not False:return _fail("STRONGER_AUTHORITY_TRANSPORT_FORBIDDEN")
 if cert.get("stronger_r12_semantic_truth_authority") is not False:return _fail("STRONGER_TRUTH_OVERCLAIM")
 if cert.get("terminal_authority") is not False or cert.get("terminal_credit_delta")!=0:return _fail("TERMINAL_OVERCLAIM")

 claim=docs["claim"]
 material={k:claim[k] for k in ("claim_kind","mission_blob_sha","scope_sha256","target_predicate_sha256","semantics_sha256","epoch","authority_id","terminal_credit_delta")}
 if compute_claim_id(material)!=CLAIM_ID or claim.get("claim_id")!=CLAIM_ID:return _fail("CLAIM_ID_RECOMPUTE_MISMATCH")
 if ((claim.get("scope") or {}).get("relation_to_stronger_whole_leaf_scope")!="NO_EQUIVALENCE_OR_AUTHORITY_TRANSPORT_CLAIMED"):
  return _fail("SAFE_SCOPE_RELATION_OVERCLAIM")
 if ((claim.get("semantics") or {}).get("stronger_claim_authority_transported") is not False):
  return _fail("SAFE_SEMANTICS_TRANSPORT_OVERCLAIM")
 if ((claim.get("stronger_r12_claim") or {}).get("claim_id")!=STRONGER_CLAIM_ID or (claim.get("stronger_r12_claim") or {}).get("discharged_by_this_claim") is not False):
  return _fail("STRONGER_CLAIM_BOUNDARY_INVALID")
 if docs["stronger_claim"].get("claim_id")!=STRONGER_CLAIM_ID:return _fail("STRONGER_CLAIM_ID_DRIFT")
 mission=docs["mission"]
 if mission.get("schema")!="PROJECT_BRAIN_REAL_MISSION_OBJECTIVE_V1" or mission.get("status")!="ACTIVE_CANONICAL_MISSION_OBJECTIVE_OVERRIDE":
  return _fail("MISSION_AUTHORITY_NOT_ACTIVE")
 if claim.get("mission_blob_sha")!=PINS["mission"][1]:return _fail("SAFE_CLAIM_MISSION_BINDING_DRIFT")

 wr=docs["runtime_verify"]
 if not str(wr.get("status") or "").startswith("PASS__SECOND_INDEPENDENT_SPRITE"):return _fail("WRAPPER_INDEPENDENT_VERIFY_NOT_PASS")
 replay=wr.get("replay") or {}
 if replay.get("tests_run")!=9 or replay.get("tests_passed")!=9 or replay.get("positive_control_valuations_checked")!=16 or replay.get("exception_fail_closed_checked") is not True:
  return _fail("WRAPPER_REPLAY_INCOMPLETE")
 proved=wr.get("proved") or {}
 for field in ("positive_requires_all_four_control_predicates","nonpositive_never_receives_positive_authority","nonpositive_always_has_explicit_blocking_diagnostic","v9_exception_is_normalized_fail_closed"):
  if proved.get(field) is not True:return _fail("WRAPPER_PROOF_MISSING:"+field)
 if proved.get("stronger_semantic_sufficiency_claim_proved") is not False or proved.get("whole_leaf_scope_equivalence_proved") is not False:
  return _fail("WRAPPER_RECEIPT_OVERCLAIM")

 # Rerun the finite control abstraction directly, rather than trusting stored booleans.
 vals=(False,True);count=0
 for f in vals:
  for a in vals:
   for t in vals:
    for s in vals:
     count+=1
     out=safe.classify_v9_result({"final_step_outcome":"POSITIVE_CERTIFICATE" if f else "ABSTAIN",
      "positive_certification_authorized":a,"material_totality_proved":t,
      "v9_executable_r12_totality_semantics_verified":s,"status":"ABSTRACTION_CASE"})
     expected=f and a and t and s
     if (out.get("status")=="SAFE_POSITIVE_VERIFIED") is not expected:return _fail("CONTROL_ABSTRACTION_CLASSIFICATION_ERROR",valuation=[f,a,t,s])
     if not expected and (out.get("positive_certification_authorized") is not False or not isinstance(out.get("blocking_diagnostic"),Mapping)):
      return _fail("CONTROL_ABSTRACTION_FAIL_CLOSED_ERROR",valuation=[f,a,t,s])
 if count!=16:return _fail("CONTROL_ABSTRACTION_COUNT_DRIFT")
 nm=safe.classify_v9_result(None)
 if nm.get("status")!="SAFE_NONPOSITIVE_FAIL_CLOSED" or nm.get("positive_certification_authorized") is not False or not isinstance(nm.get("blocking_diagnostic"),Mapping):
  return _fail("NONMAPPING_FAIL_CLOSED_ERROR")
 with patch.object(safe.v9,"route",side_effect=RuntimeError("proof")):
  ex=safe.route({})
 if ex.get("status")!="SAFE_NONPOSITIVE_FAIL_CLOSED" or ex.get("positive_certification_authorized") is not False or (ex.get("blocking_diagnostic") or {}).get("value")!="V9_EXCEPTION:RuntimeError":
  return _fail("EXCEPTION_FAIL_CLOSED_ERROR")

 v8=docs["v8_verify"].get("proved") or {}
 for field in ("positive_without_material_totality_rejected","positive_delegation_requires_v2_totality_authority","exact_r12_property_claim_binding_required","exact_r12_material_obligation_binding_required"):
  if v8.get(field) is not True:return _fail("V8_SAFETY_PREMISE_MISSING:"+field)
 v9p=docs["v9_verify"].get("proves") or []
 if "V9_POSITIVE_PATH_REQUIRES_EXECUTABLE_R12_TOTALITY_SEMANTIC_VERIFICATION" not in v9p:return _fail("V9_EXECUTABLE_SEMANTIC_PREMISE_MISSING")
 rt=docs["refine_verify"].get("truth") or {}
 if rt.get("v9_positive_requires_v8_positive") is not True or rt.get("v9_positive_adds_executable_semantic_totality_verification") is not True:
  return _fail("V8_TO_V9_REFINEMENT_PREMISE_MISSING")
 real=docs["real_replay"].get("truth") or {}
 if real.get("real_v9_positive_execution_observed") is not True or real.get("v9_c8_nonvacuity_proved") is not True:
  return _fail("REAL_POSITIVE_NONVACUITY_MISSING")
 if real.get("whole_leaf_universal_cc_r3_proved") is not False or real.get("r12_semantic_property_truth_authority") is not False:
  return _fail("REAL_REPLAY_OVERCLAIM")

 theorem=cert.get("theorem") or {}
 if theorem.get("positive_control_valuation_count")!=16 or theorem.get("safe_property_truth_proved") is not True or theorem.get("stronger_whole_leaf_semantic_sufficiency_proved") is not False:
  return _fail("CERTIFICATE_THEOREM_DRIFT")
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__SAFE_CERTIFICATION_DISPOSITION_PROPERTY_TRUTH_ON_EXACT_WRAPPER_DOMAIN__STRONGER_R12_REMAINS_OPEN",
  "claim_id":CLAIM_ID,"safe_property_truth_proved":True,"positive_control_valuations_verified":16,
  "real_positive_nonvacuity_verified":True,"stronger_r12_claim_id":STRONGER_CLAIM_ID,
  "stronger_r12_semantic_sufficiency_proved":False,"stronger_r12_authority_transported":False,
  "whole_leaf_scope_equivalence_proved":False,
  "semantic_truth_authority":True,"scope_authority":"EXACT_SAFE_WRAPPER_INVOCATION_DOMAIN_ONLY",
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 return verify_certificate(repo_root=repo_root)
