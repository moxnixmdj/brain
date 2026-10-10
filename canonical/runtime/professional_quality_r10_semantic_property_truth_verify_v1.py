"""R10 semantic-leaf property-truth verifier V1.

Closes only PQ::R10_ANALYSIS_DECISION::SEMANTIC when the exact whole-leaf
claim scope is admitted and the already-verified R10 decision semantics,
constitution, catalog, and root-shared fail-closed policy jointly establish
typed resolution for every declared R10-relevant defeater.

Detection completeness remains explicitly separate and unproved.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_whole_leaf_domain_equivalence_v1 as domain
from canonical.runtime import professional_r10_decision_semantic_certificate_v1 as semcert
from canonical.runtime import professional_quality_r10_execution_guard_v1 as guard
from canonical.runtime import professional_quality_r10_execution_property_truth_verify_v1 as execprop

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R10_SEMANTIC_PROPERTY_TRUTH_VERIFY_V1"
LEAF_ID="PQ::R10_ANALYSIS_DECISION::SEMANTIC"
ROOT_ID="R10_ANALYSIS_DECISION"
EPOCH="2026-10-10T17:50:00+02:00"
ACCEPTANCE="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"

PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "scope_batch_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "semantic_source":("canonical/verification/PROFESSIONAL_QUALITY_R10_DECISION_SUFFICIENCY_SCOPED_VERIFY_20261010_V1.json","18574110321eb1bacc18db46cbd0673bf6a0a0ac"),
 "semantic_history":("canonical/verification/ONE_SHOT_DECISION_SUFFICIENT_GATE_VERIFY_20261009_V2.json","188881365c8bb182ebd10cd4bc37aedff8547acd"),
 "constitution":("canonical/governance/PROFESSIONAL_QUALITY_R10_DECISION_CONSTITUTION_20261010_V1.json","a087db2645b03e589965d50eb51d32a3049dc2fe"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "profile":("canonical/governance/PROFESSIONAL_QUALITY_P1_EXECUTION_PROFILE_20261010_V3.json","f7e89eafbb691c16d1bdf5b8d295a468d5e3bec5"),
 "domain_runtime":("canonical/runtime/professional_quality_whole_leaf_domain_equivalence_v1.py","76bf7e1a6f26ff3664ed8c355dff8a688b074159"),
 "semantic_runtime":("canonical/runtime/professional_r10_decision_semantic_certificate_v1.py","79b4d0eb3aff7daa11f7ba511ee0f8f026b49f08"),
 "guard_runtime":("canonical/runtime/professional_quality_r10_execution_guard_v1.py","83ae7bc81660bd4be7f66b9454de5d007c0db959"),
 "execution_property_runtime":("canonical/runtime/professional_quality_r10_execution_property_truth_verify_v1.py","21fc794513f38c72b7a335d6fab6bb2500add40b"),
}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(path:Path)->dict[str,Any]:
 value=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(value,dict): raise ValueError("NOT_OBJECT")
 return value

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,
  "leaf_property_truth_authority":False,
  "detection_completeness_proved":False,
  "r10_semantic_leaf_closed":False,"r10_root_closed":False,
  "domain_semantic_closure":False,"domain_execution_closure":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def _leaf_acceptance(manifest:Mapping[str,Any])->str|None:
 for row in manifest.get("roots") or []:
  if not isinstance(row,Mapping) or row.get("root_id")!=ROOT_ID: continue
  leaf=row.get("semantic_leaf")
  if isinstance(leaf,Mapping) and leaf.get("id")==LEAF_ID:
   v=leaf.get("acceptance")
   return v if isinstance(v,str) else None
 return None

def _semantic_binding(source:Mapping[str,Any],history:Mapping[str,Any])->dict[str,Any]:
 return {
  "source_sha256":semcert.digest(dict(source)),
  "history_sha256":semcert.digest(dict(history)),
  "semantic_claim":{
   "baseline_representation":"LOSSLESS_IDENTITY_CONTENT_ADDRESSED",
   "omission_rule":"INDEPENDENT_OMISSION_CERTIFICATE_REQUIRED",
   "information_rule":"MINIMUM_POLICY_CHANGING_INFORMATION_FIRST",
   "broad_acquisition_rule":"FORBIDDEN_WITHOUT_MINIMALITY_PROOF",
   "empirical_evaluation_position":"LAST",
   "provider_verification_authority_mutation":False,
   "unchanged_frontier_progress":"FAIL_CLOSED",
  },
  "hard_nonclaims":[
   "NO_GENERAL_PROFESSIONAL_RISK_POLICY_CLOSURE",
   "NO_NORMATIVE_AGGREGATION_CLOSURE",
   "NO_MODEL_MULTIPLICITY_DECISION_CLOSURE",
   "NO_GENERAL_SEMANTIC_COMPRESSION_CLAIM",
   "NO_GLOBAL_R10_LEAF_OR_ROOT_CLOSURE",
  ],
 }

def _constitution_checks(c:Mapping[str,Any])->dict[str,bool]:
 safe=c.get("safe_default_modes") or {}
 auth=c.get("authority_boundary") or {}
 laws=c.get("governing_laws") or {}
 uncertainty=set(c.get("uncertainty_types") or [])
 return {
  "AGGREGATION_SAFE_MODES_EXACT":set(safe.get("aggregation_modes_without_extra_normative_authority") or [])=={"PARETO_ONLY","NECESSARY_DOMINANCE","MINIMAX_REGRET"},
  "UNBOUND_NORMATIVE_POLICY_ABSTAINS":safe.get("unbound_normative_policy")=="ABSTAIN_WITH_MINIMUM_BLOCKING_CUT",
  "UNBOUND_RISK_POLICY_ABSTAINS":safe.get("unbound_risk_policy")=="ABSTAIN_WITH_MINIMUM_BLOCKING_CUT",
  "UNRESOLVED_MULTIPLICITY_ESCALATES":safe.get("unresolved_model_multiplicity")=="ESCALATE_OR_ABSTAIN",
  "ABSOLUTE_FLOOR_REQUIRED":safe.get("absent_absolute_floor")=="FORBID_ABSOLUTE_EXCELLENCE_CLAIM",
  "NO_USER_UTILITY_INVENTION":auth.get("policy_file_can_invent_user_utility") is False,
  "NO_RISK_TOLERANCE_INVENTION":auth.get("policy_file_can_invent_risk_tolerance") is False,
  "NO_NORMATIVE_WEIGHT_INVENTION":auth.get("policy_file_can_invent_normative_weights") is False,
  "NO_HARD_CONSTRAINT_WAIVER":auth.get("policy_file_can_waive_hard_constraint") is False,
  "UNCERTAINTY_TYPES_TYPED":{"CONFIDENCE_INTERVAL","POSTERIOR_PROBABILITY","PREDICTIVE_RISK","DEPLOYMENT_RISK","MEASUREMENT_UNCERTAINTY","MODEL_UNCERTAINTY"}<=uncertainty,
  "VETO_NONCOMPENSATORY":"NONCOMPENSATORY" in str(laws.get("veto") or ""),
  "UNCERTAINTY_NONINTERCHANGEABLE":"NOT_INTERCHANGEABLE" in str(laws.get("uncertainty") or ""),
 }

def evaluate_documents(
 manifest:Mapping[str,Any],scope_batch_verify:Mapping[str,Any],
 semantic_source:Mapping[str,Any],semantic_history:Mapping[str,Any],
 constitution:Mapping[str,Any],catalog:Mapping[str,Any],profile:Mapping[str,Any],
)->dict[str,Any]:
 if _leaf_acceptance(manifest)!=ACCEPTANCE:
  return _fail("R10_SEMANTIC_ACCEPTANCE_DRIFT",observed_acceptance=_leaf_acceptance(manifest))

 batch=scope_batch_verify.get("independent_replay") or {}
 if (
  not str(scope_batch_verify.get("status") or "").startswith("PASS__")
  or batch.get("leaf_count")!=24
  or batch.get("domain_equivalence_pass_count")!=24
  or batch.get("scope_complete_count")!=24
  or batch.get("property_truth_count")!=0
 ):
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_ADMISSIBLE")

 claim_scope=domain.build_claim_scope(manifest,LEAF_ID,epoch=EPOCH)
 dv=domain.evaluate(manifest,claim_scope)
 if dv.get("pass") is not True or dv.get("whole_leaf_domain_equivalence_proved") is not True:
  return _fail("R10_SEMANTIC_DOMAIN_EQUIVALENCE_FAILED",verdict=dv)
 claim_id=dv.get("claim_id")

 sc=semcert.certify(semantic_source,semantic_history,_semantic_binding(semantic_source,semantic_history))
 if sc.get("pass") is not True:
  return _fail("BOUNDED_R10_SEMANTIC_CERTIFICATE_FAILED",verdict=sc)

 constitution_checks=_constitution_checks(constitution)
 if not all(constitution_checks.values()):
  return _fail("R10_CONSTITUTION_SEMANTICS_INCOMPLETE",constitution_checks=constitution_checks)

 catalog_ids=guard._r10_catalog_ids(catalog)
 if catalog_ids!=set(guard.KNOWN_R10_DEFEATERS):
  return _fail("R10_DEFEATER_CATALOG_NOT_EXACT",expected=sorted(guard.KNOWN_R10_DEFEATERS),observed=sorted(catalog_ids))

 typed_resolution={}
 for did in sorted(guard.KNOWN_R10_DEFEATERS):
  out=execprop._guard(profile,catalog,constitution,detected=(did,))
  typed_resolution[did]=(
   out.get("pass") is False
   and out.get("status")=="ABSTAIN_OR_ESCALATE__KNOWN_R10_DEFEATER_ACTIVE"
   and did in set(out.get("detected_defeater_ids") or [])
   and out.get("ordinary_certificate_path_allowed") is False
  )
 if len(typed_resolution)!=17 or not all(typed_resolution.values()):
  return _fail("R10_TYPED_DEFEATER_RESOLUTION_INCOMPLETE",typed_resolution=typed_resolution)

 near={}
 for signal,trigger in sorted(guard.NEAR_MISS_TO_TRIGGER.items()):
  out=execprop._guard(profile,catalog,constitution,near={signal:True})
  near[signal]=(
   out.get("pass") is False
   and out.get("status")=="ESCALATE__R10_NEAR_MISS_TRIGGER"
   and trigger in set(out.get("active_escalation_triggers") or [])
   and out.get("ordinary_certificate_path_allowed") is False
  )
 if not all(near.values()):
  return _fail("R10_NEAR_MISS_SEMANTIC_RESOLUTION_INCOMPLETE",near_miss_resolution=near)

 unknown=execprop._guard(profile,catalog,constitution,detected=("C999_FRESH_DECISION_ATTACK",))
 unmapped=execprop._guard(profile,catalog,constitution,unmapped=True)
 catchall_ok=(
  unknown.get("status")=="ESCALATE__UNMAPPED_DETECTED_DEFEATER"
  and unknown.get("ordinary_certificate_path_allowed") is False
  and unmapped.get("status")=="ESCALATE__UNMAPPED_MATERIAL_FALSE_CERTIFICATION_DEFEATER"
  and unmapped.get("ordinary_certificate_path_allowed") is False
 )
 if not catchall_ok:
  return _fail("R10_UNMAPPED_DEFEATER_CATCHALL_INCOMPLETE")

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R10_SEMANTIC_MANIFEST_ACCEPTANCE_BOUND_TO_EXACT_WHOLE_DOMAIN_AND_TYPED_FAIL_CLOSED_DEFEATER_RESOLUTION__ONE_SEMANTIC_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"claim_id":claim_id,
  "manifest_acceptance":ACCEPTANCE,
  "whole_leaf_domain_equivalence_proved":True,
  "whole_leaf_scope_complete":True,
  "bounded_semantic_certificate_pass":True,
  "constitution_checks":constitution_checks,
  "typed_defeater_resolution_count":len(typed_resolution),
  "typed_defeater_resolution":typed_resolution,
  "near_miss_resolution_count":len(near),
  "unmapped_defeater_catchall":True,
  "leaf_property_truth_authority":True,
  "property_truth_basis":"EXACT_MANIFEST_SEMANTIC_ACCEPTANCE__WHOLE_DOMAIN_SCOPE__BOUND_DECISION_SEMANTICS__TYPED_FAIL_CLOSED_RESOLUTION_FOR_ALL_DECLARED_R10_DEFEATERS",
  "detection_completeness_proved":False,
  "underlying_fact_truth_completeness_proved":False,
  "r10_semantic_leaf_closed":True,
  "r10_execution_leaf_closed":True,
  "r10_root_closed":False,
  "domain_semantic_closure":False,"domain_execution_closure":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 docs={}
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink():
   return _fail(key.upper()+"_MISSING")
  observed=_blob(p)
  if observed!=expected:
   return _fail(key.upper()+"_BLOB_STALE",expected_blob=expected,observed_blob=observed)
  if key not in {"domain_runtime","semantic_runtime","guard_runtime","execution_property_runtime"}:
   docs[key]=_load(p)
 return evaluate_documents(
  docs["manifest"],docs["scope_batch_verify"],docs["semantic_source"],docs["semantic_history"],
  docs["constitution"],docs["catalog"],docs["profile"],
 )
