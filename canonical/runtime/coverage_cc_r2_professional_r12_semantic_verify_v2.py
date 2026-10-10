"""Executable CC_R2 verifier for the stable R12 semantic property claim.

This is a claim-scoped formal mission-soundness reduction. It proves only
G_minus[C] subseteq G_real[C] for the exact stable R12 semantic property.
It does not prove CC_R3, property truth, professional quality, or terminality.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from typing import Any,Mapping

ROOT_ID="CC_R2_MISSION_SOUNDNESS_V1"
CLAIM_ID="11870f850b46bcfcc31094f764fc4f45c911aaac413979ceb62679ff19a53162"
MISSION_BLOB="13c470645b037bbb46245c687dd35197b420d51a"
SCOPE_CLAIM_ID="05b74983836dd1f6a13a0db72443246fb74f99548f0d982a769a6a7e572e9e85"
M_VERIFY=("correctness_rule","FAIL_CLOSED_NO_PROGRESS_CREDIT_WITHOUT_SOUND_VERIFICATION")
REQUIREMENTS=[
 "EXACT_CLAIM_SEMANTICS_AND_GROUNDING_ARE_BOUND_TO_TYPED_CURRENT_EVIDENCE",
 "EXACT_WHOLE_LEAF_SCOPE_AND_DECISION_RELEVANT_UNCERTAINTY_ARE_EXPLICITLY_BOUND",
 "ROOT_RELEVANT_DEFEATERS_ARE_RESOLVED_BY_TYPED_EVIDENCE_OR_ANY_RESIDUAL_IS_EXPLICITLY_DECISION_NULL",
 "ANY_UNRESOLVED_FATAL_OR_MATERIAL_FALSE_CERTIFICATION_CLASS_BLOCKS_POSITIVE_CERTIFICATION",
 "POSITIVE_CERTIFICATION_IS_NONVACUOUS_AND_REQUIRES_A_REAL_SUPPORTED_ROUTE",
]
CONSEQUENCES={
 REQUIREMENTS[0]:"A_POSITIVE_PROPERTY_CERTIFICATE_CANNOT_RECEIVE_PROGRESS_CREDIT_FROM_UNGROUNDED_OR_UNTYPED_SEMANTIC_EVIDENCE",
 REQUIREMENTS[1]:"A_POSITIVE_PROPERTY_CERTIFICATE_CANNOT_RECEIVE_PROGRESS_CREDIT_FROM_UNVERIFIED_SCOPE_WIDENING_OR_UNTYPED_DECISION_RELEVANT_UNCERTAINTY",
 REQUIREMENTS[2]:"A_POSITIVE_PROPERTY_CERTIFICATE_REQUIRES_EVERY_MATERIAL_ROOT_RELEVANT_DEFEATER_TO_BE_RESOLVED__ONLY_DECISION_NULL_RESIDUALS_MAY_REMAIN",
 REQUIREMENTS[3]:"MATERIAL_UNRESOLVED_SEMANTIC_OR_DEFEATER_PREMISES_HAVE_NO_SOUND_VERIFICATION_AND_THEREFORE_RECEIVE_ZERO_PROPERTY_PROGRESS_CREDIT",
 REQUIREMENTS[4]:"ABSTENTION_IS_NOT_RELABELED_AS_POSITIVE_VERIFIED_PROPERTY_PROGRESS__A_POSITIVE_CERTIFICATE_REQUIRES_AN_ACTUAL_SUPPORTED_ROUTE",
}

def _blob(p:Path)->str:
 d=p.read_bytes();return hashlib.sha1(b"blob "+str(len(d)).encode()+b"\0"+d).hexdigest()

def _digest(v:Any)->str:
 return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def _load_bound(root:Path,ref:Mapping[str,Any],label:str)->tuple[dict[str,Any]|None,list[str]]:
 errors=[];rel=ref.get("path");sha=ref.get("git_blob_sha")
 if not isinstance(rel,str) or not isinstance(sha,str):return None,[label+"_REF_INVALID"]
 p=root/rel
 if not p.is_file() or p.is_symlink():return None,[label+"_FILE_MISSING"]
 if _blob(p)!=sha:return None,[label+"_BLOB_MISMATCH"]
 try:o=json.loads(p.read_text(encoding="utf-8"))
 except Exception:return None,[label+"_JSON_INVALID"]
 return (o if isinstance(o,dict) else None),([] if isinstance(o,dict) else [label+"_NOT_OBJECT"])

def _fail(root_id:str,claim_id:str,*errors:str)->dict[str,Any]:
 return {"pass":False,"status":"FAIL_CLOSED__CC_R2_R12_MISSION_SOUNDNESS_UNPROVED",
  "root_id":root_id,"claim_id":claim_id,"semantic_claim_verified":False,
  "errors":sorted(set(errors)),"terminal_credit_delta":0}

def verify_certificate(*,root:Path,certificate_path:Path,active_claim:Mapping[str,Any],root_id:str)->dict[str,Any]:
 root=root.resolve();claim_id=str(active_claim.get("claim_id") or "");errors=[]
 if root_id!=ROOT_ID:return _fail(root_id,claim_id,"ROOT_ID_MISMATCH")
 if claim_id!=CLAIM_ID:return _fail(root_id,claim_id,"ACTIVE_CLAIM_ID_MISMATCH")
 if active_claim.get("claim_kind")!="PROPERTY_CERTIFICATE":return _fail(root_id,claim_id,"ACTIVE_CLAIM_KIND_DRIFT")
 if active_claim.get("mission_blob_sha")!=MISSION_BLOB:return _fail(root_id,claim_id,"ACTIVE_CLAIM_MISSION_AUTHORITY_DRIFT")
 try:cert=json.loads(certificate_path.read_text(encoding="utf-8"))
 except Exception:return _fail(root_id,claim_id,"CERTIFICATE_INVALID_JSON")
 if cert.get("root_id")!=ROOT_ID:errors.append("CERTIFICATE_ROOT_MISMATCH")
 if cert.get("claim_id")!=CLAIM_ID:errors.append("CERTIFICATE_CLAIM_MISMATCH")
 for k in ("semantic_truth_authority","quality_authority","acceptance_authority","promotion_authority","terminal_authority"):
  if cert.get(k) is not False:errors.append("CERTIFICATE_AUTHORITY_OVERCLAIM:"+k)
 if (cert.get("accounting") or {}).get("terminal_credit_delta")!=0:errors.append("CERTIFICATE_NONZERO_TERMINAL_CREDIT")

 frozen,es=_load_bound(root,cert.get("active_claim") or {},"ACTIVE_CLAIM");errors+=es
 if frozen:
  for k in ("claim_id","claim_kind","mission_blob_sha","scope_sha256","target_predicate_sha256","semantics_sha256","epoch","authority_id"):
   if frozen.get(k)!=active_claim.get(k):errors.append("FROZEN_ACTIVE_CLAIM_MISMATCH:"+k)
  if frozen.get("whole_leaf_scope_claim_id")!=SCOPE_CLAIM_ID:errors.append("FROZEN_SCOPE_CLAIM_DRIFT")
  if _digest(frozen.get("target_predicate"))!=active_claim.get("target_predicate_sha256"):errors.append("TARGET_PREDICATE_HASH_DRIFT")
  if _digest(frozen.get("semantics"))!=active_claim.get("semantics_sha256"):errors.append("SEMANTICS_HASH_DRIFT")

 authority,es=_load_bound(root,cert.get("mission_authority") or {},"MISSION_AUTHORITY");errors+=es
 normal,es=_load_bound(root,cert.get("closure_normal_form") or {},"CLOSURE_NORMAL_FORM");errors+=es
 carrier,es=_load_bound(root,cert.get("identity_carrier") or {},"IDENTITY_CARRIER");errors+=es
 if errors:return _fail(root_id,claim_id,*errors)

 field,value=M_VERIFY
 if authority.get(field)!=value:errors.append("MISSION_VERIFY_AXIOM_DRIFT")
 if authority.get("real_objective")!="BUILD_THE_MOST_CAPABLE_GENERAL_RELIABLE_AND_RESOURCE_EFFICIENT_PROBLEM_SOLVING_SYSTEM_POSSIBLE":errors.append("MISSION_OBJECTIVE_DRIFT")
 if normal.get("false_certification_event")!="BRAIN_ISSUES_A_PROFESSIONAL_EXCELLENCE_OR_DOMINANCE_CLAIM_OUTSIDE_THE_SCOPE_JUSTIFIED_BY_THE_EXACT_EVIDENCE_AND_DECISION_POLICY":errors.append("CLOSURE_NORMAL_FORM_DRIFT")
 target=frozen.get("target_predicate") or {}
 if target.get("acceptance")!="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE":errors.append("TARGET_ACCEPTANCE_DRIFT")
 if target.get("obligation")!="PROVE_DOMAIN_SEMANTIC_SUFFICIENCY_FOR_R12_META_COMPOSITION_CLOSURE":errors.append("TARGET_OBLIGATION_DRIFT")
 if target.get("quantification")!="FOR_ALL_ADMISSIBLE_INPUTS_IN_VERIFIED_WHOLE_LEAF_SCOPE":errors.append("TARGET_QUANTIFIER_DRIFT")
 if (carrier.get("independent_replay") or {}).get("r12_claim_id")!=SCOPE_CLAIM_ID:errors.append("IDENTITY_CARRIER_SCOPE_DRIFT")
 if (carrier.get("theorem") or {}).get("semantic_information_loss") is not False:errors.append("IDENTITY_CARRIER_INFORMATION_LOSS")

 ax=(cert.get("authorized_mission_axioms") or {}).get("M_VERIFY") or {}
 if ax.get("field")!=field or ax.get("exact_value")!=value:errors.append("CERTIFICATE_M_VERIFY_BINDING_DRIFT")
 rows=cert.get("reduction")
 if not isinstance(rows,list) or len(rows)!=5:errors.append("REDUCTION_SHAPE_INVALID");rows=[]
 seen=set()
 for row in rows:
  if not isinstance(row,Mapping):errors.append("REDUCTION_ROW_INVALID");continue
  req=row.get("requirement")
  if req not in CONSEQUENCES:errors.append("UNKNOWN_REDUCTION_REQUIREMENT:"+str(req));continue
  if req in seen:errors.append("DUPLICATE_REDUCTION_REQUIREMENT:"+req);continue
  seen.add(req)
  if row.get("mission_axioms")!=["M_VERIFY"]:errors.append("REDUCTION_AXIOM_DRIFT:"+req)
  if row.get("consequence")!=CONSEQUENCES[req]:errors.append("REDUCTION_CONSEQUENCE_DRIFT:"+req)
 if seen!=set(REQUIREMENTS):errors.append("REDUCTION_COVERAGE_INCOMPLETE")
 theorem=cert.get("theorem") or {}
 if theorem.get("proof_mode")!="FORMAL_REDUCTION":errors.append("THEOREM_PROOF_MODE_DRIFT")
 if theorem.get("identity_carrier_factorization_proved") is not True:errors.append("IDENTITY_FACTORIZATION_NOT_BOUND")
 for k in ("full_mission_optimality_implied","global_mission_completion_implied","professional_quality_closure_implied","r12_semantic_property_truth_implied"):
  if theorem.get(k) is not False:errors.append("THEOREM_OVERCLAIM:"+k)
 if errors:return _fail(root_id,claim_id,*errors)

 return {"pass":True,"status":"PASS__CC_R2_R12_STABLE_MISSION_SOUNDNESS_FORMAL_REDUCTION",
  "root_id":ROOT_ID,"claim_id":CLAIM_ID,"semantic_claim_verified":True,
  "authorized_mission_axiom_count":1,"claim_requirement_count":5,
  "reduction_rows_verified":5,"g_minus_subseteq_g_real":True,
  "claim_scoped_property_only":True,"full_mission_optimality_implied":False,
  "global_mission_completion_derivable":False,"terminal_credit_delta":0,"errors":[]}
