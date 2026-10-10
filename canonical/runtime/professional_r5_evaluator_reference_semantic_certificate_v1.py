"""Bounded R5 evaluator/reference semantic certificate.

This certifies the meaning of the already independently replayed hybrid evaluator
uncertainty theorem. It does not certify that any hidden/current evaluator is a
member of the declared reference class.
"""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_R5_EVALUATOR_REFERENCE_SEMANTIC_CERTIFICATE_V1"
ROOT_ID="R5_EVALUATOR_REFERENCE"
SOURCE_SCHEMA="PROJECT_BRAIN_GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_V1"
VERIFY_SCHEMA="PROJECT_BRAIN_GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_SPRITE_VERIFICATION_V1"
CLAIM_KIND="CONDITIONAL_HYBRID_EVALUATOR_REFERENCE_CLASS_SEMANTICS"

ALLOWED={
 "AUTHENTIC_CURRENT_OWNER_SEMANTICS",
 "EXTENSIONALLY_EQUIVALENT_CURRENT_PREFERENCE_RELATION",
 "INDEPENDENTLY_VERIFIED_RESTRICTED_OWNER_CLASS",
 "EVALUATOR_INDEPENDENT_SCOPE_COMPLETE_BOUND",
}
FORBIDDEN={
 "PUBLIC_METHODOLOGY_ONLY",
 "PUBLIC_RUBRIC_ONLY",
 "HISTORICAL_V1_PROMPT_CARRYFORWARD",
 "UNVERIFIED_RECONSTRUCTED_GRADER",
}
DEFINITIONS={
 "d":"BRAIN_MINUS_OPUS55_PROBABILITY_LAW_ON_A_SOUND_COMPLETE_EVALUATOR_FACING_QUOTIENT_OR_SOUND_COMPLETE_GENERATOR_PROJECTION",
 "u0":"AUTHENTICATED_NOMINAL_OWNER_EVALUATOR_DIRECTION",
 "K":"CONE_OF_AUTHENTICATED_ONE_SIDED_OWNER_PREFERENCE_DIRECTIONS",
 "B":"BOUNDED_CONVEX_OWNER_PREFERENCE_UNCERTAINTY_SET",
 "L":"LINEALITY_SUBSPACE_OF_TRULY_ARBITRARY_SYMMETRIC_OWNER_PREFERENCE_DIRECTIONS",
 "Uhat":"u0_PLUS_CONE_K_PLUS_CONV_B_PLUS_SPAN_L",
}
ROLES={
 "comparison_object":"d_IS_BRAIN_MINUS_REFERENCE_SYSTEM_PROBABILITY_LAW_ON_A_SOUND_COMPLETE_EVALUATOR_FACING_REPRESENTATION",
 "nominal_reference":"u0_IS_AN_AUTHENTICATED_NOMINAL_OWNER_EVALUATOR_DIRECTION",
 "one_sided_reference":"K_IS_A_CONE_OF_AUTHENTICATED_ONE_SIDED_OWNER_PREFERENCE_DIRECTIONS",
 "bounded_reference_uncertainty":"B_IS_A_BOUNDED_CONVEX_OWNER_PREFERENCE_UNCERTAINTY_SET",
 "arbitrary_reference_uncertainty":"L_IS_THE_LINEALITY_SUBSPACE_OF_TRULY_ARBITRARY_SYMMETRIC_OWNER_PREFERENCE_DIRECTIONS",
 "reference_class":"Uhat_EQUALS_u0_PLUS_CONE_K_PLUS_CONV_B_PLUS_SPAN_L",
 "certificate_meaning":"NONNEGATIVE_ROBUST_MARGIN_PROVES_NONINFERIORITY_FOR_EVERY_EVALUATOR_DIRECTION_INSIDE_THE_AUTHENTICATED_OUTER_CLASS_ONLY",
 "membership_boundary":"THE_CERTIFICATE_DOES_NOT_PROVE_THE_TRUE_CURRENT_OWNER_EVALUATOR_BELONGS_TO_Uhat",
}
REQUIRED_MECHANICS={
 "POSITIVE_ROBUST_MARGIN_CERTIFICATE_PASSES",
 "UNPROVED_DECOMPOSITION_FAILS_CLOSED",
 "PUBLIC_RUBRIC_ONLY_SEMANTIC_CLASS_IS_FIREWALLED",
 "NONINDEPENDENT_DECOMPOSITION_RECEIPT_FAILS_CLOSED",
 "NONZERO_MASS_DIFFERENCE_VECTOR_FAILS_CLOSED",
 "NEGATIVE_K_CONE_DIRECTION_FAILS_DUAL_MEMBERSHIP",
 "NONORTHOGONAL_LINEALITY_FAILS_EVEN_WITH_LARGE_NOMINAL_MARGIN",
 "BOUNDED_UNCERTAINTY_CAN_BE_ABSORBED_BY_SUFFICIENT_CERTIFIED_MARGIN",
 "EXCESS_BOUNDED_UNCERTAINTY_FAILS",
 "EMPTY_BOUNDED_SET_REDUCES_TO_ZERO_ADJUSTMENT",
 "DIMENSION_MISMATCH_FAILS_CLOSED",
}

def _canon(v:Any)->str:
 return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)

def digest(v:Any)->str:
 return sha256(_canon(v).encode()).hexdigest()

def _fail(errors:list[str])->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":sorted(set(errors)),
         "semantic_leaf_credit":False,"global_leaf_closure":False,"global_root_closure":False,
         "domain_semantic_closure":False,"quality_authority":False,"terminal_authority":False,
         "terminal_credit_delta":0}

def certify(source:Mapping[str,Any],verification:Mapping[str,Any],binding:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(source,Mapping): return _fail(["SOURCE_NOT_OBJECT"])
 if not isinstance(verification,Mapping): return _fail(["VERIFICATION_NOT_OBJECT"])
 if not isinstance(binding,Mapping): return _fail(["BINDING_NOT_OBJECT"])
 e=[]
 if source.get("schema")!=SOURCE_SCHEMA: e.append("SOURCE_SCHEMA_INVALID")
 if source.get("scope")!="GDPVAL_AA_V2_1_HIDDEN_QUALITATIVE_OWNER_RELATION": e.append("SOURCE_SCOPE_INVALID")
 defs=source.get("definitions")
 if not isinstance(defs,Mapping): e.append("DEFINITIONS_INVALID")
 else:
  for k,v in DEFINITIONS.items():
   if defs.get(k)!=v: e.append("DEFINITION_INVALID:"+k)
 fw=source.get("soundness_firewall")
 if not isinstance(fw,Mapping): e.append("SOUNDNESS_FIREWALL_INVALID")
 else:
  if set(fw.get("admissible_decomposition_proof_classes") or [])!=ALLOWED: e.append("ALLOWED_PROOF_CLASSES_DRIFT")
  if set(fw.get("forbidden_as_semantic_containment_proof") or [])!=FORBIDDEN: e.append("FORBIDDEN_PROOF_CLASSES_DRIFT")
 reality=source.get("current_reality")
 if not isinstance(reality,Mapping): e.append("CURRENT_REALITY_INVALID")
 else:
  for k in ("sound_complete_gdpval_owner_decomposition_bound","current_owner_pairwise_relation_bound","complete_opus55_220_evaluator_facing_laws_bound","gdpval_closed"):
   if reality.get(k) is not False: e.append("CURRENT_REALITY_OVERCLAIM:"+k)
 theorem=source.get("theorem")
 if not isinstance(theorem,Mapping): e.append("THEOREM_INVALID")
 else:
  if "TRUE_CURRENT_OWNER_EVALUATOR_DIRECTION_IS_CONTAINED_IN_Uhat" not in str(theorem.get("premise")): e.append("CONTAINMENT_PREMISE_MISSING")
  if "FOR_EVERY_OWNER_EVALUATOR_DIRECTION_IN_Uhat" not in str(theorem.get("statement")): e.append("REFERENCE_CLASS_CONCLUSION_MISSING")
 if verification.get("schema")!=VERIFY_SCHEMA: e.append("VERIFY_SCHEMA_INVALID")
 if not str(verification.get("status") or "").startswith("INDEPENDENT_SPRITE_EXACT_BLOB_REPLAY_PASS"): e.append("VERIFY_NOT_INDEPENDENT_PASS")
 replay=verification.get("replay")
 if not isinstance(replay,Mapping) or replay.get("tests_passed")!=11 or replay.get("tests_total")!=11: e.append("VERIFY_REPLAY_INVALID")
 if not REQUIRED_MECHANICS<=set(verification.get("verified_mechanics") or []): e.append("VERIFY_MECHANICS_INCOMPLETE")
 if binding.get("root_id")!=ROOT_ID: e.append("BINDING_ROOT_INVALID")
 if binding.get("claim_kind")!=CLAIM_KIND: e.append("BINDING_CLAIM_KIND_INVALID")
 if binding.get("source_sha256")!=digest(dict(source)): e.append("SOURCE_DIGEST_MISMATCH")
 if binding.get("verification_sha256")!=digest(dict(verification)): e.append("VERIFY_DIGEST_MISMATCH")
 roles=binding.get("semantic_roles")
 if not isinstance(roles,Mapping): e.append("SEMANTIC_ROLES_INVALID")
 else:
  for k,v in ROLES.items():
   if roles.get(k)!=v: e.append("SEMANTIC_ROLE_INVALID:"+k)
 b=binding.get("boundaries")
 if not isinstance(b,Mapping): e.append("BOUNDARIES_INVALID")
 else:
  for k in ("true_current_evaluator_membership_proved","public_rubric_is_owner_semantics","historical_prompt_is_current_owner_semantics","global_r5_semantic_leaf_closed","domain_semantic_closure"):
   if b.get(k) is not False: e.append("BOUNDARY_OVERCLAIM:"+k)
  if b.get("outside_declared_reference_class_stays_unclaimed") is not True: e.append("OUTSIDE_CLASS_BOUNDARY_MISSING")
 return {"schema":SCHEMA,"pass":not e,
         "status":"PASS__BOUNDED_HYBRID_EVALUATOR_REFERENCE_SEMANTICS" if not e else "FAIL_CLOSED",
         "errors":sorted(set(e)),"root_id":ROOT_ID,"claim_kind":CLAIM_KIND,
         "semantic_roles":dict(ROLES),"source_sha256":digest(dict(source)),
         "verification_sha256":digest(dict(verification)),
         "semantic_leaf_credit":False,"global_leaf_closure":False,"global_root_closure":False,
         "domain_semantic_closure":False,"quality_authority":False,"terminal_authority":False,
         "terminal_credit_delta":0}
