"""R5 evaluator/reference execution-leaf property-truth verifier V1.

Binds exact current professional leaf scope, R5 subject binding, independently
verified evaluator-uncertainty mechanics, and fail-closed challenge responses.
Leaf authority only. The true owner-evaluator class remains unproved.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import professional_quality_r5_execution_guard_v1 as guard

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R5_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
ROOT_ID="R5_EVALUATOR_REFERENCE"
LEAF_ID="PQ::R5_EVALUATOR_REFERENCE::EXECUTION"
ACCEPTANCE="RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "scope_batch":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "r5_root_verify":("canonical/verification/PROFESSIONAL_QUALITY_R5_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1.json","d4dc698d89738470cf3b41fe860b8c3f666a56a9"),
 "evaluator_verify":("canonical/verification/GDPVAL_HYBRID_EVALUATOR_UNCERTAINTY_SPRITE_VERIFICATION_20261008_V1.json","e852c4fbc14147c17469f1a4ede4e274d768bbf7"),
 "evaluator_runtime":("canonical/runtime/gdpval_hybrid_evaluator_uncertainty_v1.py","7adf19997ec90913fb70e618eb4e3adda055deac"),
 "guard":("canonical/runtime/professional_quality_r5_execution_guard_v1.py","f10fd198562d60105da123db3ee6c4d85402108c"),
}

def _blob(p:Path)->str:
 raw=p.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(v,dict): raise ValueError("NOT_OBJECT")
 return v

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"leaf_property_truth_authority":False,
  "detection_completeness_proved":False,"true_owner_evaluator_containment_proved":False,
  "reference_correctness_proved":False,"cross_model_calibration_proved":False,
  "semantic_leaf_closed":False,"root_closed":False,"domain_execution_closure":False,
  "domain_semantic_closure":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
  "incremental_spend_usd":0,**extra}

def _execution_acceptance(manifest:Mapping[str,Any])->str|None:
 for row in manifest.get("roots") or []:
  if isinstance(row,Mapping) and row.get("root_id")==ROOT_ID:
   leaf=row.get("execution_leaf")
   if isinstance(leaf,Mapping) and leaf.get("id")==LEAF_ID:
    return leaf.get("acceptance") if isinstance(leaf.get("acceptance"),str) else None
 return None

def _catalog_ids(catalog:Mapping[str,Any])->set[str]:
 rows=catalog.get("defeaters") or catalog.get("attack_classes") or catalog.get("nodes") or catalog.get("challenges") or []
 return {str(row["id"]) for row in rows if isinstance(row,Mapping)
         and ROOT_ID in set(row.get("root_ids") or []) and isinstance(row.get("id"),str)}

def evaluate_documents(manifest:Mapping[str,Any],catalog:Mapping[str,Any],scope_batch:Mapping[str,Any],
                       r5_root_verify:Mapping[str,Any],evaluator_verify:Mapping[str,Any])->dict[str,Any]:
 if _execution_acceptance(manifest)!=ACCEPTANCE:
  return _fail("R5_EXECUTION_ACCEPTANCE_DRIFT",observed_acceptance=_execution_acceptance(manifest))
 ids=_catalog_ids(catalog)
 if ids!=set(guard.KNOWN_R5_DEFEATERS):
  return _fail("R5_CATALOG_NOT_EXACT",expected=sorted(guard.KNOWN_R5_DEFEATERS),observed=sorted(ids))
 replay=scope_batch.get("independent_replay") or {}
 if (not str(scope_batch.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE")
     or replay.get("leaf_count")!=24 or replay.get("domain_equivalence_pass_count")!=24
     or replay.get("scope_complete_count")!=24):
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_CURRENT_24_OF_24")
 if (not str(r5_root_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE_6_OF_6")
     or r5_root_verify.get("root_subject_binding_authority") is not True
     or r5_root_verify.get("true_owner_evaluator_containment_proved") is not False):
  return _fail("R5_ROOT_BINDING_NOT_ADMISSIBLE")
 replay2=evaluator_verify.get("replay") or {}
 mechanics=set(evaluator_verify.get("verified_mechanics") or [])
 required={
  "POSITIVE_ROBUST_MARGIN_CERTIFICATE_PASSES",
  "UNPROVED_DECOMPOSITION_FAILS_CLOSED",
  "PUBLIC_RUBRIC_ONLY_SEMANTIC_CLASS_IS_FIREWALLED",
  "NONINDEPENDENT_DECOMPOSITION_RECEIPT_FAILS_CLOSED",
  "NONZERO_MASS_DIFFERENCE_VECTOR_FAILS_CLOSED",
  "NONORTHOGONAL_LINEALITY_FAILS_EVEN_WITH_LARGE_NOMINAL_MARGIN",
  "EXCESS_BOUNDED_UNCERTAINTY_FAILS",
 }
 if (not str(evaluator_verify.get("status") or "").startswith("INDEPENDENT_SPRITE_EXACT_BLOB_REPLAY_PASS__11_OF_11")
     or replay2.get("tests_passed")!=11 or replay2.get("tests_total")!=11
     or not required <= mechanics):
  return _fail("R5_EVALUATOR_MECHANICS_NOT_ADMISSIBLE")
 boundary=" ".join(evaluator_verify.get("verification_boundary") or [])
 if ("IT_DOES_NOT_PROVE_THE_TRUE_CURRENT_GDPVAL_OWNER_EVALUATOR" not in boundary
     or "NO_GDPVAL_ACCEPTANCE_FAMILY_CAPABILITY_OWNERSHIP_OR_TERMINAL_CREDIT" not in boundary):
  return _fail("R5_EVALUATOR_VERIFICATION_BOUNDARY_MISSING")

 positive=guard.evaluate(evaluator_preflight_pass=True,root_binding_pass=True)
 if positive.get("pass") is not True or positive.get("ordinary_acceptance_path_allowed") is not True:
  return _fail("R5_POSITIVE_PATH_FAILED",verdict=positive)
 adversarial={}
 for did in sorted(guard.KNOWN_R5_DEFEATERS):
  out=guard.evaluate(evaluator_preflight_pass=True,root_binding_pass=True,detected_defeater_ids=(did,))
  adversarial[did]=(out.get("pass") is False and
                    out.get("status")=="ABSTAIN_OR_ESCALATE__KNOWN_R5_DEFEATER_ACTIVE" and
                    out.get("ordinary_acceptance_path_allowed") is False)
 if len(adversarial)!=16 or not all(adversarial.values()):
  return _fail("R5_ADVERSARIAL_CHALLENGE_MATRIX_INCOMPLETE",adversarial=adversarial)
 near={}
 for signal,trigger in sorted(guard.NEAR_MISS_TO_TRIGGER.items()):
  out=guard.evaluate(evaluator_preflight_pass=True,root_binding_pass=True,near_miss_signals=(signal,))
  near[signal]=(out.get("pass") is False and out.get("status")=="ESCALATE__R5_NEAR_MISS_TRIGGER"
                and trigger in set(out.get("active_escalation_triggers") or [])
                and out.get("ordinary_acceptance_path_allowed") is False)
 if len(near)!=16 or not all(near.values()):
  return _fail("R5_NEAR_MISS_MATRIX_INCOMPLETE",near_miss=near)
 catchalls=(
  guard.evaluate(evaluator_preflight_pass=True,root_binding_pass=True,detected_defeater_ids=("C999_FRESH_R5_ATTACK",)),
  guard.evaluate(evaluator_preflight_pass=True,root_binding_pass=True,unmapped_material_defeater=True),
  guard.evaluate(evaluator_preflight_pass=False,root_binding_pass=True),
  guard.evaluate(evaluator_preflight_pass=True,root_binding_pass=False),
 )
 if not all(x.get("pass") is False and x.get("ordinary_acceptance_path_allowed") is False for x in catchalls):
  return _fail("R5_FAIL_CLOSED_CATCHALL_INCOMPLETE")

 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__R5_VERIFIED_EVALUATOR_MECHANICS_PLUS_ALL_DECLARED_ROOT_ATTACK_CLASSES_NEAR_MISSES_AND_CATCHALLS_OBSERVED_FAIL_CLOSED__ONE_EXECUTION_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"manifest_acceptance":ACCEPTANCE,
  "whole_leaf_scope_complete":True,"bounded_evaluator_mechanics_pass":True,
  "positive_case_pass":True,"adversarial_case_count":16,"adversarial_cases":adversarial,
  "near_miss_case_count":16,"near_miss_cases":near,
  "unknown_defeater_catchall":True,"unmapped_material_defeater_catchall":True,
  "failed_evaluator_preflight_catchall":True,"failed_root_binding_catchall":True,
  "leaf_property_truth_authority":True,
  "property_truth_basis":"EXACT_R5_ROOT_BINDING__INDEPENDENT_11_OF_11_EVALUATOR_MECHANICS__ALL_DECLARED_R5_ATTACKS_AND_NEAR_MISSES_OBSERVED_FAIL_CLOSED",
  "detection_completeness_proved":False,"true_owner_evaluator_containment_proved":False,
  "reference_correctness_proved":False,"cross_model_calibration_proved":False,
  "real_task_comparative_evaluation_step_receipt_proved":False,
  "semantic_leaf_closed":False,"root_closed":False,"domain_execution_closure":False,
  "domain_semantic_closure":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
  "incremental_spend_usd":0}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 docs={}
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink(): return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=expected: return _fail(key.upper()+"_BLOB_STALE",expected_blob=expected,observed_blob=actual)
  if key in {"manifest","catalog","scope_batch","r5_root_verify","evaluator_verify"}:
   docs[key]=_load(p)
 return evaluate_documents(docs["manifest"],docs["catalog"],docs["scope_batch"],
                           docs["r5_root_verify"],docs["evaluator_verify"])
