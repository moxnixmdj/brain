"""Executable R12 semantic specification split guard V1.

Makes one critical distinction explicit:
* universal safe certification disposition may be proved over its exact runtime domain;
* stronger whole-leaf semantic adequacy remains a distinct property and receives
  no authority by scope, name, or implementation reuse alone.

This is a truth-preserving normal-form guard. It does not weaken or close the
stronger R12 claim.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import professional_r12_safe_certification_disposition_claim_verify_v1 as safev
from canonical.runtime import coverage_cc_r3_professional_r12_semantic_verify_v4 as v4

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R12_SEMANTIC_SPEC_SPLIT_GUARD_V1"
SAFE_CLAIM_ID=safev.CLAIM_ID
STRONGER_CLAIM_ID=safev.STRONGER_CLAIM_ID
WHOLE_DOMAIN_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_DOMAIN_EQUIVALENCE_V1_INDEPENDENT_VERIFY_20261010_V1.json"
WHOLE_SCOPE_VERIFY_PATH="canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json"

def _fail(reason:str)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "safe_universal_property_proved":False,"stronger_r12_semantic_sufficiency_proved":False,
  "authority_transport_allowed":False,"quality_authority":False,"acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0}

def verify(*,root:Path|None=None)->dict[str,Any]:
 root=(root or Path(__file__).resolve().parents[2]).resolve()
 safe=safev.verify(repo_root=root)
 if safe.get("pass") is not True or safe.get("safe_property_truth_proved") is not True:
  return _fail("SAFE_PROPERTY_NOT_VERIFIED")
 if safe.get("claim_id")!=SAFE_CLAIM_ID or safe.get("stronger_r12_claim_id")!=STRONGER_CLAIM_ID:
  return _fail("SAFE_STRONGER_CLAIM_BINDING_MISMATCH")
 if safe.get("stronger_r12_semantic_sufficiency_proved") is not False or safe.get("stronger_r12_authority_transported") is not False:
  return _fail("SAFE_PROPERTY_OVERCLAIMS_STRONGER_AUTHORITY")
 try:
  whole=json.loads((root/WHOLE_DOMAIN_VERIFY_PATH).read_text())
  scope=json.loads((root/WHOLE_SCOPE_VERIFY_PATH).read_text())
 except Exception:
  return _fail("WHOLE_LEAF_SCOPE_EVIDENCE_MISSING_OR_INVALID")
 if not str(whole.get("status") or "").startswith("PASS__"):
  return _fail("WHOLE_LEAF_DOMAIN_EQUIVALENCE_NOT_PASS")
 if ((whole.get("independent_replay") or {}).get("real_manifest_passed")!=24 or
     (whole.get("independent_replay") or {}).get("unique_claim_id_count")!=24):
  return _fail("WHOLE_LEAF_DOMAIN_REPLAY_INCOMPLETE")
 if not str(scope.get("status") or "").startswith("PASS__") or (scope.get("independent_replay") or {}).get("scope_complete_count")!=24:
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_COMPLETE")
 if "NO_LEAF_PROPERTY_TRUTH" not in (whole.get("hard_nonclaims") or []):
  return _fail("DOMAIN_EQUIVALENCE_PROPERTY_TRUTH_BOUNDARY_MISSING")
 if "NO_LEAF_PROPERTY_TRUTH" not in (scope.get("hard_nonclaims") or []):
  return _fail("SCOPE_BATCH_PROPERTY_TRUTH_BOUNDARY_MISSING")
 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R12_SPECIFICATION_SPLIT_ENFORCED__SAFE_UNIVERSAL_PROPERTY_PROVED__STRONGER_ADEQUACY_REMAINS_OPEN",
  "safe_claim_id":SAFE_CLAIM_ID,"stronger_r12_claim_id":STRONGER_CLAIM_ID,
  "safe_universal_property_proved":True,
  "whole_leaf_domain_equivalence_proved":True,
  "whole_leaf_scope_complete":True,
  "whole_leaf_scope_or_domain_implies_property_truth":False,
  "stronger_r12_semantic_sufficiency_proved":False,
  "authority_transport_allowed":False,
  "required_stronger_route":"INDEPENDENT_WHOLE_LEAF_PREDICATE_TRUTH_OR_COMPLETE_UNION__NOT_SCOPE_EQUIVALENCE_ALONE",
  "repaired_normal_form":{
   "universal_safety":"FOR_ALL_ADMISSIBLE_RUNTIME_INPUTS__POSITIVE_ONLY_IF_MATERIAL_TOTALITY_AND_EXECUTABLE_SEMANTIC_VERIFICATION_HOLD__OTHERWISE_EXPLICIT_FAIL_CLOSED_NONPOSITIVE",
   "nonvacuity":"AT_LEAST_ONE_REAL_SUPPORTED_POSITIVE_ROUTE",
   "separate_adequacy":"MEASURE_OR_PROVE_WHICH_ADMISSIBLE_INPUTS_HAVE_SUFFICIENT_TYPED_EVIDENCE_FOR_POSITIVE_SEMANTIC_SUFFICIENCY__DO_NOT_REQUIRE_SUCCESS_ON_UNRESOLVED_INPUTS"
  },
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0
 }
