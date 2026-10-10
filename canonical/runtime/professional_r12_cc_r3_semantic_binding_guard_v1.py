"""R12 CC_R3 semantic-binding truth guard V1.

Prevents a subordinate positive-certification safety theorem from being
transported as the stronger root inclusion B_plus ⊆ G_minus when G_minus is
defined by the exact whole-leaf acceptance predicate.

This guard preserves the safety theorem and revokes only the invalid authority
transport. It grants zero property or terminal credit.
"""
from __future__ import annotations
import json
from hashlib import sha1
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_CC_R3_SEMANTIC_BINDING_GUARD_V1"
CLAIM_PATH="canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V2.json"
CLAIM_BLOB="7b26ddba501358d42d6fa342efd27d389bb30654"
R2_PATH="canonical/governance/COVERAGE_CC_R2_PROFESSIONAL_R12_SEMANTIC_CERTIFICATE_20261010_V2.json"
R2_BLOB="8fc8057152ba26cd91643ec75d8853d421b59cba"
UNIVERSAL_PATH="canonical/runtime/professional_r12_universal_positive_gate_totality_v1.py"
UNIVERSAL_BLOB="d1030eaf687110f5ca34de24c37e595973a596ac"
SAFE_PATH="canonical/runtime/professional_r12_safe_meta_composition_v1.py"
SAFE_BLOB="7c1b6631fc237e7ff7160ba1080f326555e05c52"
CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
FULL_ACCEPTANCE="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"
FULL_QUANTIFICATION="FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE"
SAFETY_OBLIGATION="ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_RESOLVED_OR_PROVED_DECISION_NULL_BEFORE_POSITIVE_CERTIFICATION"

def _blob(p:Path)->str:
 raw=p.read_bytes(); return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _load(root:Path,rel:str,blob:str)->Mapping[str,Any]:
 p=root/rel
 if not p.is_file() or p.is_symlink() or _blob(p)!=blob: raise ValueError("PIN_FAIL:"+rel)
 o=json.loads(p.read_text())
 if not isinstance(o,Mapping): raise ValueError("NOT_OBJECT:"+rel)
 return o

def _fail(reason:str)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
 "universal_positive_gate_safety_retained":False,"cc_r3_set_inclusion_proved":False,
 "authority_transport_allowed":False,"r4_proof_closure_authorized":False,
 "semantic_property_truth_authority":False,"terminal_authority":False,"terminal_credit_delta":0}

def verify(*,repo_root:Path|str|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 try:
  claim=_load(root,CLAIM_PATH,CLAIM_BLOB); r2=_load(root,R2_PATH,R2_BLOB)
  up=root/UNIVERSAL_PATH; sp=root/SAFE_PATH
  if not up.is_file() or _blob(up)!=UNIVERSAL_BLOB: return _fail("UNIVERSAL_PIN_FAIL")
  if not sp.is_file() or _blob(sp)!=SAFE_BLOB: return _fail("SAFE_PIN_FAIL")
 except Exception as e: return _fail(type(e).__name__+":"+str(e))
 if claim.get("claim_id")!=CLAIM_ID: return _fail("CLAIM_ID_DRIFT")
 tp=claim.get("target_predicate") or {}
 if tp.get("acceptance")!=FULL_ACCEPTANCE or tp.get("quantification")!=FULL_QUANTIFICATION:
  return _fail("FROZEN_TARGET_PREDICATE_DRIFT")
 terms=r2.get("claim_scoped_terms") or {}
 if terms.get("G_minus")!="IN_SCOPE_R12_SEMANTIC_CERTIFICATION_STATES_SATISFYING_THE_EXACT_LEAF_ACCEPTANCE_UNDER_THE_BOUND_CLOSURE_NORMAL_FORM":
  return _fail("G_MINUS_SEMANTICS_DRIFT")
 universal_text=up.read_text()
 safe_text=sp.read_text()
 if ('OBLIGATION = "'+SAFETY_OBLIGATION+'"') not in universal_text:
  return _fail("UNIVERSAL_SAFETY_OBLIGATION_DRIFT")
 if "This proves a subordinate safety capability only. It does NOT close the stronger" not in safe_text:
  return _fail("SAFE_STRONGER_NONCLAIM_MISSING")
 # Countermodel to implication S => A:
 # admissible state has unresolved material premise; runtime returns nonpositive fail-closed.
 # S holds because no positive certificate occurred. A is false because the exact
 # acceptance requires all root-relevant defeaters resolved with typed evidence.
 countermodel={
  "admissible_state":"W_C_STATE_WITH_UNRESOLVED_MATERIAL_PREMISE",
  "runtime_disposition":"SAFE_NONPOSITIVE_FAIL_CLOSED",
  "positive_certificate":False,
  "safety_obligation_satisfied":True,
  "full_acceptance_satisfied":False,
 }
 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__SEMANTIC_BINDING_GAP_PROVED__UNIVERSAL_SAFETY_RETAINED__CC_R3_SET_INCLUSION_NOT_DERIVED",
  "claim_id":CLAIM_ID,
  "full_leaf_acceptance":FULL_ACCEPTANCE,
  "full_leaf_quantification":FULL_QUANTIFICATION,
  "universal_positive_gate_obligation":SAFETY_OBLIGATION,
  "countermodel_to_safety_implies_full_acceptance":countermodel,
  "universal_positive_gate_safety_retained":True,
  "safety_implies_full_acceptance":False,
  "cc_r3_set_inclusion_proved":False,
  "authority_transport_allowed":False,
  "r4_proof_closure_authorized":False,
  "semantic_property_truth_authority":False,
  "exact_remaining_obligation":"PROVE_B_PLUS_SUBSETEQ_G_MINUS_FOR_THE_EXACT_FROZEN_WHOLE_LEAF_ACCEPTANCE__OR_CREATE_A_SUCCESSOR_CLAIM_WITH_THE_INTENDED_SAFE_CERTIFICATION_PREDICATE_AND_REPROVE_ROOTS_WITHOUT_TRANSPORT",
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0
 }
