"""CC_R3 verifier for the exact Professional R12 V10 subject.

The frozen R12 obligation is universal over admissible inputs but conditional on
positive certification: all root-relevant material defeaters must be resolved or
proved decision-null before a positive certificate is emitted.

V10 closes this by construction. Exact V9 executes first; V10 can only preserve
or reject V9-positive routes, and every preserved positive route must pass one
fixed content-addressed trusted local-totality verifier. Abstention remains
fail-closed and receives no positive certificate.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any

from canonical.runtime import professional_v9_to_v10_r12_positive_refinement_v1 as refinement

SCHEMA="PROJECT_BRAIN_CC_R3_PROFESSIONAL_R12_V10_UNIVERSAL_POSITIVE_GATE_VERIFY_V1"
ROOT_ID="CC_R3_TERMINAL_CLOSURE_V1"
CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
CLAIM_PATH="canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V2.json"
CLAIM_BLOB="7b26ddba501358d42d6fa342efd27d389bb30654"
REFINEMENT_PATH="canonical/runtime/professional_v9_to_v10_r12_positive_refinement_v1.py"
REFINEMENT_BLOB="95915ab44b5ede08241bb8c706b9bb9b7a64b805"
OBLIGATION="ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_RESOLVED_OR_PROVED_DECISION_NULL_BEFORE_POSITIVE_CERTIFICATION"
QUANTIFICATION="FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE"

def _blob(p:Path)->str:
 d=p.read_bytes();return sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _fail(reason:str)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "root_id":ROOT_ID,"claim_id":CLAIM_ID,"semantic_claim_verified":False,
  "cc_r3_terminal_closure_proved":False,"r4_proof_realization_authority":False,
  "semantic_property_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else Path(__file__).resolve().parents[2]
 cp=root/CLAIM_PATH; rp=root/REFINEMENT_PATH
 if not cp.is_file() or cp.is_symlink() or _blob(cp)!=CLAIM_BLOB:return _fail("FROZEN_CLAIM_PIN_INVALID")
 if not rp.is_file() or rp.is_symlink() or _blob(rp)!=REFINEMENT_BLOB:return _fail("REFINEMENT_VERIFIER_PIN_INVALID")
 try: claim=json.loads(cp.read_text(encoding="utf-8"))
 except Exception:return _fail("FROZEN_CLAIM_JSON_INVALID")
 if claim.get("claim_id")!=CLAIM_ID:return _fail("CLAIM_ID_MISMATCH")
 target=claim.get("target_predicate") or {}
 if target.get("quantification")!=QUANTIFICATION:return _fail("CLAIM_QUANTIFICATION_MISMATCH")
 semantics=claim.get("semantics") or {}
 if semantics.get("true_when")!="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE":
  return _fail("CLAIM_TRUE_WHEN_MISMATCH")
 r=refinement.verify(repo_root=root)
 if r.get("pass") is not True:return _fail("V9_TO_V10_REFINEMENT_NOT_PROVED")
 for key in ("positive_route_refinement_proved","preexisting_v9_execution_preserved_before_new_gate",
             "universal_fixed_verifier_gate_proved"):
  if r.get(key) is not True:return _fail("REFINEMENT_PREMISE_FALSE:"+key)
 if r.get("v10_can_add_positive_route") is not False:return _fail("V10_POSITIVE_EXPANSION_NOT_EXCLUDED")
 if r.get("v10_can_only_preserve_or_reject_v9_positive_route") is not True:
  return _fail("V10_REFINEMENT_DIRECTION_NOT_PROVED")
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__CC_R3_R12_V10_UNIVERSAL_POSITIVE_GATE_DIRECT_SUBSET_CLOSURE",
  "root_id":ROOT_ID,"claim_id":CLAIM_ID,"semantic_claim_verified":True,
  "proof_mode":"KERNEL_CHECKED_FORMAL_REDUCTION",
  "quantification":QUANTIFICATION,"semantic_obligation":OBLIGATION,
  "universal_implication":"FOR_EVERY_ADMISSIBLE_INPUT__POSITIVE_CERTIFICATE_IMPLIES_TRUSTED_EXACT_RUN_MATERIAL_TOTALITY",
  "abstention_semantics":"UNRESOLVED_OR_UNTRUSTED_INPUTS_FAIL_CLOSED_WITHOUT_POSITIVE_CERTIFICATION",
  "cc_r3_terminal_closure_proved":True,
  "proof_basis":"EXACT_V10_CONTROL_FLOW_PLUS_PINNED_TRUSTED_LOCAL_TOTALITY_VERIFIER",
  "fresh_reality_units_consumed":0,
  "r4_proof_realization_authority":False,"semantic_property_truth_authority":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}
