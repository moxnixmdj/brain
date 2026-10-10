"""CC_R2 mission-soundness verifier for the frozen professional R12 semantic claim.

This verifier proves one conditional semantic relation only:

    G_minus[C] subseteq G_real[C]

where C is the exact frozen R12 semantic property claim.  G_minus means that
the exact semantic-leaf acceptance has actually been satisfied.  G_real means
that the canonical mission permits positive property-progress credit for that
claim under its fail-closed correctness rule.

The verifier does NOT prove that G_minus holds for all admissible inputs.  That
is CC_R3/property-truth work.  It also does not prove global professional
quality, mission optimality, checkpoint completion, promotion, or terminality.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_whole_leaf_domain_equivalence_v1 as domain
from canonical.runtime import professional_semantic_identity_carrier_v1 as identity

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_COVERAGE_CC_R2_PROFESSIONAL_R12_SEMANTIC_MISSION_SOUNDNESS_VERIFY_V1"
ROOT_ID="CC_R2_MISSION_SOUNDNESS_V1"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::SEMANTIC"
CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
SCOPE_SHA="3958f259dba6bc6d4dfe1dad0b3ec26ecb1b8d92ea4763985f52ce96cfc55a1d"
SEMANTICS_SHA="bdb1e40284acf8f93f0552143ccfb2a3246428a1862c3f37907a00b20d18fc3e"
TARGET_SHA="4967b35be044567ae9fbcd01f2443996dc675f3154fd386790f79301ae9cff09"
MISSION_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
EPOCH="2026-10-10T18:05:00+02:00"
ACCEPTANCE="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"

CLAIM_PATH="canonical/governance/COVERAGE_COMPLETENESS_FROZEN_CLAIM_PROFESSIONAL_R12_SEMANTIC_20261010_V1.json"
CLAIM_BLOB="5e7c198da31b901bb4f53c4fc15cee7d6298c114"
CERT_PATH="canonical/governance/COVERAGE_CC_R2_PROFESSIONAL_R12_SEMANTIC_MISSION_SOUNDNESS_CERTIFICATE_20261010_V1.json"
MISSION_PATH="canonical/governance/REAL_MISSION_OBJECTIVE_20261008_V1.json"
CLOSURE_PATH="canonical/governance/PROFESSIONAL_QUALITY_CLOSURE_NORMAL_FORM_20261009_V1.json"
CLOSURE_BLOB="ebcfe5a48efce9df7fbc69a3817ac2f9adb1ff93"
MANIFEST_PATH=domain.MANIFEST_PATH
MANIFEST_BLOB=domain.MANIFEST_BLOB
IDENTITY_ACTIVATION_PATH="canonical/governance/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_ACTIVATION_20261010_V1.json"
IDENTITY_ACTIVATION_BLOB="3e99ddbf25cd8e392c5a22a5c14ae5fea5dc3138"
IDENTITY_VERIFY_PATH="canonical/verification/PROFESSIONAL_SEMANTIC_IDENTITY_CARRIER_VERIFY_20261010_V1.json"
IDENTITY_VERIFY_BLOB="35a3ccf9ad454aa0318a4ed10edc065830c3874d"

REQUIREMENTS=[
 "EXACT_CLAIM_SEMANTICS_AND_GROUNDING_ARE_BOUND_TO_TYPED_CURRENT_EVIDENCE",
 "EXACT_WHOLE_LEAF_SCOPE_AND_DECISION_RELEVANT_UNCERTAINTY_ARE_EXPLICITLY_BOUND",
 "ROOT_RELEVANT_DEFEATERS_ARE_RESOLVED_BY_TYPED_EVIDENCE_OR_ANY_RESIDUAL_IS_EXPLICITLY_DECISION_NULL",
 "ANY_UNRESOLVED_FATAL_OR_MATERIAL_FALSE_CERTIFICATION_CLASS_BLOCKS_POSITIVE_CERTIFICATION",
 "POSITIVE_CERTIFICATION_IS_NONVACUOUS_AND_REQUIRES_A_REAL_SUPPORTED_ROUTE",
]
EXPECTED_REDUCTION={
 REQUIREMENTS[0]:"A_POSITIVE_PROPERTY_CERTIFICATE_CANNOT_RECEIVE_PROGRESS_CREDIT_FROM_UNGROUNDED_OR_UNTYPED_SEMANTIC_EVIDENCE",
 REQUIREMENTS[1]:"A_POSITIVE_PROPERTY_CERTIFICATE_CANNOT_RECEIVE_PROGRESS_CREDIT_FROM_UNVERIFIED_SCOPE_WIDENING_OR_UNTYPED_DECISION_RELEVANT_UNCERTAINTY",
 REQUIREMENTS[2]:"A_POSITIVE_PROPERTY_CERTIFICATE_REQUIRES_EVERY_MATERIAL_ROOT_RELEVANT_DEFEATER_TO_BE_RESOLVED__ONLY_DECISION_NULL_RESIDUALS_MAY_REMAIN",
 REQUIREMENTS[3]:"MATERIAL_UNRESOLVED_SEMANTIC_OR_DEFEATER_PREMISES_HAVE_NO_SOUND_VERIFICATION_AND_THEREFORE_RECEIVE_ZERO_PROPERTY_PROGRESS_CREDIT",
 REQUIREMENTS[4]:"ABSTENTION_IS_NOT_RELABELED_AS_POSITIVE_VERIFIED_PROPERTY_PROGRESS__A_POSITIVE_CERTIFICATE_REQUIRES_AN_ACTUAL_SUPPORTED_ROUTE",
}
EXPECTED_TERMS={
 "G_minus":"IN_SCOPE_R12_SEMANTIC_CERTIFICATION_STATES_SATISFYING_THE_EXACT_LEAF_ACCEPTANCE_UNDER_THE_BOUND_CLOSURE_NORMAL_FORM",
 "G_real":"IN_SCOPE_STATES_AUTHORIZED_BY_THE_CANONICAL_MISSION_TO_RECEIVE_POSITIVE_PROGRESS_CREDIT_FOR_THIS_EXACT_R12_SEMANTIC_PROPERTY",
 "progress_credit_binding":"POSITIVE_R12_SEMANTIC_LEAF_PROPERTY_TRUTH_IS_PROGRESS_CREDIT_FOR_THIS_PROPERTY__ABSTENTION_IS_ZERO_PROPERTY_CREDIT",
 "sound_verification_binding":"THE_EXACT_R12_SEMANTIC_ACCEPTANCE_REQUIRES_GROUNDED_TYPED_EVIDENCE_FOR_SEMANTICS_SCOPE_UNCERTAINTY_AND_ROOT_RELEVANT_DEFEATER_RESOLUTION",
 "unresolved_binding":"ANY_UNRESOLVED_FATAL_OR_DECISION_RELEVANT_MATERIAL_SEMANTIC_SCOPE_UNCERTAINTY_OR_DEFEATER_PREMISE_BLOCKS_POSITIVE_CERTIFICATION_AND_MUST_RETURN_ABSTENTION_WITH_A_MINIMUM_BLOCKING_CUT",
 "decision_null_binding":"A_RESIDUAL_UNKNOWN_MAY_REMAIN_ONLY_WHEN_IT_DOES_NOT_CHANGE_THE_AUTHORIZED_DECISION",
}
REQUIRED_CLOSURE_RULES={
 "ALL_LOAD_BEARING_ROOT_CONTRACTS_CLOSED_OR_EXPLICITLY_DECISION_NULL",
 "NO_UNRESOLVED_FATAL_DEFEATER",
 "ADVERSARIAL_CHALLENGE_COVERAGE_HAS_NO_UNMAPPED_MATERIAL_FALSE_CERTIFICATION_CLASS",
 "RESIDUAL_UNKNOWN_DOES_NOT_CHANGE_THE_AUTHORIZED_DECISION",
}
EXPECTED_MISSION_AXIOM="FAIL_CLOSED_NO_PROGRESS_CREDIT_WITHOUT_SOUND_VERIFICATION"


def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()


def _load(path:Path)->dict[str,Any]:
 value=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(value,dict):
  raise ValueError("JSON_NOT_OBJECT")
 return value


def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED",
  "reason":reason,"root_id":ROOT_ID,"claim_id":CLAIM_ID,"leaf_id":LEAF_ID,
  "cc_r2_mission_soundness_proved":False,"g_minus_subseteq_g_real":False,
  "r12_semantic_property_truth_authority":False,"leaf_property_truth_authority":False,
  "semantic_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }


def evaluate_documents(
 *,
 manifest:Mapping[str,Any],
 frozen:Mapping[str,Any],
 certificate:Mapping[str,Any],
 mission:Mapping[str,Any],
 closure:Mapping[str,Any],
 identity_activation:Mapping[str,Any],
 identity_verification:Mapping[str,Any],
)->dict[str,Any]:
 errors:list[str]=[]

 # Recompute the exact professional claim from canonical domain machinery.
 expected_scope=domain.build_claim_scope(manifest,LEAF_ID,epoch=EPOCH)
 dv=domain.evaluate(manifest,expected_scope)
 if dv.get("pass") is not True or dv.get("whole_leaf_domain_equivalence_proved") is not True:
  return _fail("CANONICAL_R12_DOMAIN_EQUIVALENCE_RECOMPUTE_FAILED",domain_verdict=dv)
 exp=expected_scope["claim"]
 if (
  exp.get("claim_id")!=CLAIM_ID or exp.get("scope_sha256")!=SCOPE_SHA
  or exp.get("semantics_sha256")!=SEMANTICS_SHA
  or exp.get("target_predicate_sha256")!=TARGET_SHA
  or exp.get("mission_blob_sha")!=MISSION_BLOB
 ):
  return _fail("CANONICAL_R12_CLAIM_IDENTITY_DRIFT",observed_claim=exp)

 # The frozen governance object must be an exact wrapper around that claim.
 for field,value in (
  ("leaf_id",LEAF_ID),("root_id","R12_META_COMPOSITION_CLOSURE"),
  ("claim_id",CLAIM_ID),("claim_kind","PROPERTY_CERTIFICATE"),
  ("mission_blob_sha",MISSION_BLOB),("scope_sha256",SCOPE_SHA),
  ("target_predicate_sha256",TARGET_SHA),("semantics_sha256",SEMANTICS_SHA),
  ("epoch",EPOCH),("authority_id","PROJECT_BRAIN_PROFESSIONAL_QUALITY_WHOLE_LEAF"),
 ):
  if frozen.get(field)!=value:
   errors.append("FROZEN_CLAIM_FIELD_DRIFT:"+field)
 if frozen.get("claim_scope")!=expected_scope:
  errors.append("FROZEN_CLAIM_SCOPE_NOT_EXACT_CANONICAL_SCOPE")
 pred=frozen.get("target_predicate")
 if not isinstance(pred,Mapping):
  errors.append("FROZEN_TARGET_PREDICATE_INVALID")
 else:
  if pred.get("acceptance")!=ACCEPTANCE:
   errors.append("FROZEN_ACCEPTANCE_DRIFT")
  if pred.get("requires")!=REQUIREMENTS:
   errors.append("FROZEN_REQUIREMENT_SET_OR_ORDER_DRIFT")
  for field in ("true_when","false_when","unknown_when"):
   if not isinstance(pred.get(field),str) or not pred.get(field):
    errors.append("FROZEN_PREDICATE_SEMANTICS_MISSING:"+field)

 # Bind directly to immutable mission authority; this claim already uses its blob.
 if frozen.get("mission_blob_sha")!=MISSION_BLOB:
  errors.append("FROZEN_MISSION_BINDING_DRIFT")
 if mission.get("correctness_rule")!=EXPECTED_MISSION_AXIOM:
  errors.append("MISSION_CORRECTNESS_AXIOM_DRIFT")
 if mission.get("real_objective")!="BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE":
  errors.append("MISSION_OBJECTIVE_DRIFT")

 # Bind the project-authored meaning of "resolved": material unknowns block,
 # decision-null residuals may remain, and abstention is the explicit route.
 necessary=set((closure.get("closure_rule") or {}).get("necessary") or [])
 missing=sorted(REQUIRED_CLOSURE_RULES-necessary)
 if missing:
  errors.append("CLOSURE_NORMAL_FORM_REQUIRED_RULES_MISSING:"+",".join(missing))
 steps=(closure.get("p1_default_profile") or {}).get("steps") or []
 if "ISSUE_SCOPED_CERTIFICATE_OR_ABSTAIN_WITH_MINIMUM_BLOCKING_CUT" not in steps:
  errors.append("CLOSURE_NORMAL_FORM_ABSTENTION_ROUTE_MISSING")
 r12=[x for x in (closure.get("roots") or []) if isinstance(x,Mapping) and x.get("id")=="R12_META_COMPOSITION_CLOSURE"]
 if len(r12)!=1 or "explicit residual unknowns" not in str(r12[0].get("contract") or ""):
  errors.append("CLOSURE_NORMAL_FORM_R12_UNKNOWN_SEMANTICS_DRIFT")

 # Claim-scoped semantic carrier factorization must already be independently proved.
 if identity_activation.get("status")!="ACTIVE_CANDIDATE__INDEPENDENTLY_VERIFIED_12_OF_12_CLAIM_SCOPED_IDENTITY_CARRIER_FACTORIZATION__ZERO_PROPERTY_TRUTH_CREDIT":
  errors.append("IDENTITY_CARRIER_ACTIVATION_STATUS_DRIFT")
 if (identity_activation.get("current_state") or {}).get("r12_claim_id")!=CLAIM_ID:
  errors.append("IDENTITY_CARRIER_R12_CLAIM_DRIFT")
 if (identity_activation.get("current_state") or {}).get("claim_scoped_identity_factorization_proved_count")!=12:
  errors.append("IDENTITY_CARRIER_BATCH_COUNT_DRIFT")
 replay=identity_verification.get("independent_replay") or {}
 if replay.get("tests_passed")!=8 or replay.get("semantic_leaf_count")!=12 or replay.get("r12_claim_id")!=CLAIM_ID:
  errors.append("IDENTITY_CARRIER_INDEPENDENT_VERIFY_INVALID")
 if identity_verification.get("property_truth_count_delta")!=0:
  errors.append("IDENTITY_CARRIER_PROPERTY_OVERCLAIM")

 # Candidate certificate identity and authority boundary.
 if certificate.get("root_id")!=ROOT_ID:
  errors.append("CERTIFICATE_ROOT_MISMATCH")
 if certificate.get("claim_id")!=CLAIM_ID:
  errors.append("CERTIFICATE_CLAIM_MISMATCH")
 cref=certificate.get("active_claim") or {}
 if (cref.get("path"),cref.get("git_blob_sha"))!=(CLAIM_PATH,CLAIM_BLOB):
  errors.append("CERTIFICATE_FROZEN_CLAIM_REF_DRIFT")
 mref=certificate.get("mission_authority") or {}
 if (mref.get("path"),mref.get("git_blob_sha"))!=(MISSION_PATH,MISSION_BLOB):
  errors.append("CERTIFICATE_MISSION_AUTHORITY_REF_DRIFT")
 nref=certificate.get("closure_normal_form") or {}
 if (nref.get("path"),nref.get("git_blob_sha"))!=(CLOSURE_PATH,CLOSURE_BLOB):
  errors.append("CERTIFICATE_CLOSURE_NORMAL_FORM_REF_DRIFT")
 ia=(certificate.get("identity_carrier") or {}).get("activation") or {}
 iv=(certificate.get("identity_carrier") or {}).get("verification") or {}
 if (ia.get("path"),ia.get("git_blob_sha"))!=(IDENTITY_ACTIVATION_PATH,IDENTITY_ACTIVATION_BLOB):
  errors.append("CERTIFICATE_IDENTITY_ACTIVATION_REF_DRIFT")
 if (iv.get("path"),iv.get("git_blob_sha"))!=(IDENTITY_VERIFY_PATH,IDENTITY_VERIFY_BLOB):
  errors.append("CERTIFICATE_IDENTITY_VERIFY_REF_DRIFT")
 for field in (
  "semantic_claim_verified","r12_semantic_property_truth_authority",
  "promotion_authority","terminal_authority",
 ):
  if certificate.get(field) is not False:
   errors.append("CERTIFICATE_SELF_AUTHORITY_FORBIDDEN:"+field)
 acct=certificate.get("accounting") or {}
 if acct.get("property_truth_credit_delta")!=0 or acct.get("terminal_credit_delta")!=0:
  errors.append("CERTIFICATE_NONZERO_CREDIT_FORBIDDEN")

 # Only the canonical fail-closed correctness axiom may carry this reduction.
 axioms=certificate.get("authorized_mission_axioms")
 if not isinstance(axioms,Mapping) or set(axioms)!={"M_VERIFY"}:
  errors.append("CERTIFICATE_MISSION_AXIOM_SET_INVALID")
 else:
  row=axioms["M_VERIFY"]
  if not isinstance(row,Mapping) or row.get("field")!="correctness_rule" or row.get("exact_value")!=EXPECTED_MISSION_AXIOM:
   errors.append("CERTIFICATE_M_VERIFY_BINDING_INVALID")

 terms=certificate.get("claim_scoped_terms")
 if not isinstance(terms,Mapping):
  errors.append("CLAIM_SCOPED_TERMS_INVALID")
 else:
  for key,value in EXPECTED_TERMS.items():
   if terms.get(key)!=value:
    errors.append("CLAIM_SCOPED_TERM_DRIFT:"+key)

 rows=certificate.get("reduction")
 if not isinstance(rows,list) or len(rows)!=len(REQUIREMENTS):
  errors.append("REDUCTION_SHAPE_INVALID")
  rows=[]
 seen:set[str]=set()
 for row in rows:
  if not isinstance(row,Mapping):
   errors.append("REDUCTION_ROW_INVALID"); continue
  req=row.get("requirement")
  if req not in EXPECTED_REDUCTION:
   errors.append("REDUCTION_UNKNOWN_REQUIREMENT:"+str(req)); continue
  if req in seen:
   errors.append("REDUCTION_DUPLICATE_REQUIREMENT:"+str(req)); continue
  seen.add(str(req))
  if row.get("mission_axioms")!=["M_VERIFY"]:
   errors.append("REDUCTION_UNAUTHORIZED_AXIOM_SET:"+str(req))
  if row.get("consequence")!=EXPECTED_REDUCTION[req]:
   errors.append("REDUCTION_CONSEQUENCE_DRIFT:"+str(req))
 if seen!=set(REQUIREMENTS):
  errors.append("REDUCTION_REQUIREMENT_COVERAGE_INCOMPLETE")

 theorem=certificate.get("theorem") or {}
 if theorem.get("proof_mode")!="FORMAL_REDUCTION":
  errors.append("THEOREM_PROOF_MODE_DRIFT")
 if theorem.get("identity_carrier_factorization_required") is not True or theorem.get("identity_carrier_factorization_proved") is not True:
  errors.append("THEOREM_IDENTITY_CARRIER_PREMISE_MISSING")
 for field in (
  "full_mission_optimality_implied","global_mission_completion_implied",
  "professional_quality_closure_implied","r12_semantic_property_truth_implied",
 ):
  if theorem.get(field) is not False:
   errors.append("THEOREM_OVERCLAIM:"+field)

 if errors:
  return _fail("CC_R2_MISSION_SOUNDNESS_PREMISE_FAILED",errors=sorted(set(errors)))

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__CC_R2_R12_SEMANTIC_MISSION_SOUNDNESS_FORMAL_REDUCTION",
  "root_id":ROOT_ID,"claim_id":CLAIM_ID,"leaf_id":LEAF_ID,
  "cc_r2_mission_soundness_proved":True,
  "g_minus_subseteq_g_real":True,
  "authorized_mission_axiom_count":1,
  "claim_requirement_count":len(REQUIREMENTS),
  "reduction_rows_verified":len(REQUIREMENTS),
  "identity_carrier_factorization_proved":True,
  "material_unresolved_premise_positive_credit_forbidden":True,
  "decision_null_residual_allowed":True,
  "abstention_zero_property_credit":True,
  "claim_scoped_property_only":True,
  "full_mission_optimality_implied":False,
  "global_mission_completion_derivable":False,
  "professional_quality_closure_implied":False,
  "r12_semantic_property_truth_authority":False,
  "leaf_property_truth_authority":False,
  "semantic_truth_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
  "errors":[],
 }


def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 fixed={
  "manifest":(MANIFEST_PATH,MANIFEST_BLOB),
  "claim":(CLAIM_PATH,CLAIM_BLOB),
  "mission":(MISSION_PATH,MISSION_BLOB),
  "closure":(CLOSURE_PATH,CLOSURE_BLOB),
  "identity_activation":(IDENTITY_ACTIVATION_PATH,IDENTITY_ACTIVATION_BLOB),
  "identity_verification":(IDENTITY_VERIFY_PATH,IDENTITY_VERIFY_BLOB),
 }
 docs={}
 for key,(rel,expected) in fixed.items():
  p=root/rel
  if not p.is_file() or p.is_symlink():
   return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=expected:
   return _fail(key.upper()+"_BLOB_STALE",observed_blob=actual)
  try: docs[key]=_load(p)
  except Exception:return _fail(key.upper()+"_JSON_INVALID")
 cp=root/CERT_PATH
 if not cp.is_file() or cp.is_symlink():
  return _fail("CERTIFICATE_MISSING")
 try:cert=_load(cp)
 except Exception:return _fail("CERTIFICATE_JSON_INVALID")

 # Re-run the identity theorem itself rather than trusting receipt prose alone.
 ident=identity.verify(repo_root=root)
 if ident.get("pass") is not True or ident.get("r12_claim_id")!=CLAIM_ID:
  return _fail("IDENTITY_CARRIER_RECOMPUTE_FAILED",identity_verdict=ident)

 return evaluate_documents(
  manifest=docs["manifest"],frozen=docs["claim"],certificate=cert,
  mission=docs["mission"],closure=docs["closure"],
  identity_activation=docs["identity_activation"],
  identity_verification=docs["identity_verification"],
 )


if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
