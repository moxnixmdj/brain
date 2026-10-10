"""R8 execution-leaf property-truth verifier V1.

Binds current whole-leaf scope completion, exact V7 R8 root binding, the
independently verified frozen 512-case population preflight, and observed
fail-closed responses for every declared R8 attack class and near miss.

Leaf authority only. No constituency, operator, invariance, semantic, root,
quality, acceptance, promotion, or terminal closure.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import professional_quality_r8_execution_guard_v1 as guard

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R8_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
ROOT_ID="R8_POPULATION_CONTEXT_OPERATOR"
LEAF_ID="PQ::R8_POPULATION_CONTEXT_OPERATOR::EXECUTION"
ACCEPTANCE="RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "scope_batch":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "r8_root_verify":("canonical/verification/PROFESSIONAL_QUALITY_R8_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1.json","e3e6a3e1cc09779ec59903a721d03a94b6ab441d"),
 "population_verify":("canonical/verification/DELEGATION_TERMINAL_POPULATION_BINDING_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json","3965db684d7104c5829ce1fcfa8ee08d2cd42cfc"),
 "population_runtime":("canonical/runtime/delegation_terminal_population_binding_v1.py","fae6d0bf2efbcb9b8fe2a2a627900889c5ec6cab"),
 "guard":("canonical/runtime/professional_quality_r8_execution_guard_v1.py","d113595017f242debaf2ea8de8aaa8d420cdd0cb"),
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
  "detection_completeness_proved":False,"constituency_support_proved":False,
  "operator_generalization_proved":False,"measurement_invariance_proved":False,
  "social_reactivity_closure_proved":False,"semantic_leaf_closed":False,
  "root_closed":False,"domain_execution_closure":False,"domain_semantic_closure":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

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
                       r8_root_verify:Mapping[str,Any],population_verify:Mapping[str,Any])->dict[str,Any]:
 if _execution_acceptance(manifest)!=ACCEPTANCE:
  return _fail("R8_EXECUTION_ACCEPTANCE_DRIFT",observed_acceptance=_execution_acceptance(manifest))
 ids=_catalog_ids(catalog)
 if ids!=set(guard.KNOWN_R8_DEFEATERS):
  return _fail("R8_CATALOG_NOT_EXACT",expected=sorted(guard.KNOWN_R8_DEFEATERS),observed=sorted(ids))

 replay=scope_batch.get("independent_replay") or {}
 if (not str(scope_batch.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE")
     or replay.get("leaf_count")!=24 or replay.get("domain_equivalence_pass_count")!=24
     or replay.get("scope_complete_count")!=24):
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_CURRENT_24_OF_24")

 if (not str(r8_root_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE_5_OF_5")
     or r8_root_verify.get("root_subject_binding_authority") is not True
     or r8_root_verify.get("conditional_population_transport_support") is not True):
  return _fail("R8_ROOT_BINDING_NOT_ADMISSIBLE")
 eb=r8_root_verify.get("exact_blobs") or {}
 if eb.get("population_preflight_verification")!=PINS["population_verify"][1]:
  return _fail("R8_ROOT_POPULATION_RECEIPT_DRIFT")

 verified=set(population_verify.get("verified") or [])
 required={
  "EXACT_CURRENT_BRAIN_BLOBS_BOUND",
  "FROZEN_BINDING_MANIFEST_INVARIANTS_PASS",
  "CURRENT_SCOPE_GATE_RECEIPT_ADMISSIBLE_WITH_ZERO_ERRORS",
  "CANONICAL_BINDING_REGRESSIONS_PASS",
  "FRESH_512_CASE_PRE_BEACON_POPULATION_PASSES",
  "ALL_SIX_FROZEN_DELEGATION_CASE_CLASSES_PRESENT",
  "ZERO_CASE_REPLACEMENT",
  "ZERO_ADAPTIVE_CASE_SELECTION",
  "ZERO_TUNING_REPLAY",
 }
 runtime_blob=(population_verify.get("exact_bound_blobs") or {}).get(
  "canonical/runtime/delegation_terminal_population_binding_v1.py")
 if (not str(population_verify.get("status") or "").startswith("INDEPENDENT_PASS__EXACT_CURRENT_512_CASE_BINDING_PREFLIGHT")
     or runtime_blob!=PINS["population_runtime"][1]
     or not required <= verified
     or population_verify.get("terminal_results_observed")!=0):
  return _fail("R8_POPULATION_PREFLIGHT_NOT_ADMISSIBLE")

 positive=guard.evaluate(population_preflight_pass=True)
 if positive.get("pass") is not True or positive.get("ordinary_acceptance_path_allowed") is not True:
  return _fail("R8_POSITIVE_PATH_FAILED",verdict=positive)

 adversarial={}
 for did in sorted(guard.KNOWN_R8_DEFEATERS):
  out=guard.evaluate(population_preflight_pass=True,detected_defeater_ids=(did,))
  adversarial[did]=(out.get("pass") is False
                    and out.get("status")=="ABSTAIN_OR_ESCALATE__KNOWN_R8_DEFEATER_ACTIVE"
                    and out.get("ordinary_acceptance_path_allowed") is False)
 if len(adversarial)!=12 or not all(adversarial.values()):
  return _fail("R8_ADVERSARIAL_CHALLENGE_MATRIX_INCOMPLETE",adversarial=adversarial)

 near={}
 for signal,trigger in sorted(guard.NEAR_MISS_TO_TRIGGER.items()):
  out=guard.evaluate(population_preflight_pass=True,near_miss_signals=(signal,))
  near[signal]=(out.get("pass") is False
                and out.get("status")=="ESCALATE__R8_NEAR_MISS_TRIGGER"
                and trigger in set(out.get("active_escalation_triggers") or [])
                and out.get("ordinary_acceptance_path_allowed") is False)
 if len(near)!=12 or not all(near.values()):
  return _fail("R8_NEAR_MISS_MATRIX_INCOMPLETE",near_miss=near)

 unknown=guard.evaluate(population_preflight_pass=True,detected_defeater_ids=("C999_FRESH_R8_ATTACK",))
 unmapped=guard.evaluate(population_preflight_pass=True,unmapped_material_defeater=True)
 failed=guard.evaluate(population_preflight_pass=False)
 if not all(x.get("pass") is False and x.get("ordinary_acceptance_path_allowed") is False
            for x in (unknown,unmapped,failed)):
  return _fail("R8_FAIL_CLOSED_CATCHALL_INCOMPLETE")

 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__R8_FROZEN_512_POPULATION_PREFLIGHT_PLUS_ALL_DECLARED_ROOT_ATTACK_CLASSES_NEAR_MISSES_AND_CATCHALLS_OBSERVED_FAIL_CLOSED__ONE_EXECUTION_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"manifest_acceptance":ACCEPTANCE,
  "whole_leaf_scope_complete":True,"population_preflight_pass":True,
  "positive_case_pass":True,"adversarial_case_count":12,"adversarial_cases":adversarial,
  "near_miss_case_count":12,"near_miss_cases":near,
  "unknown_defeater_catchall":True,"unmapped_material_defeater_catchall":True,
  "failed_population_preflight_catchall":True,"leaf_property_truth_authority":True,
  "property_truth_basis":"EXACT_FROZEN_512_POPULATION_PREFLIGHT__INDEPENDENT_ROOT_AND_POPULATION_RECEIPTS__ALL_DECLARED_R8_ROOT_ATTACKS_AND_NEAR_MISSES_OBSERVED_FAIL_CLOSED",
  "detection_completeness_proved":False,"constituency_support_proved":False,
  "operator_generalization_proved":False,"measurement_invariance_proved":False,
  "social_reactivity_closure_proved":False,"post_freeze_terminal_result_proved":False,
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
  if key in {"manifest","catalog","scope_batch","r8_root_verify","population_verify"}: docs[key]=_load(p)
 return evaluate_documents(docs["manifest"],docs["catalog"],docs["scope_batch"],
                           docs["r8_root_verify"],docs["population_verify"])
