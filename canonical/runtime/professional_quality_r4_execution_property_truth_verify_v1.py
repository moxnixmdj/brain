"""R4 execution-leaf property-truth verifier V1.

Verifies observed runtime response over all declared R4 challenge classes while
binding exact content-addressed measurement machinery. It does not prove that
all real attacks are detected, holistic construct validity, or R4 semantics.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_r4_execution_guard_v1 as guard

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R4_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
ROOT_ID="R4_MEASUREMENT_CONSTRUCT"
LEAF_ID="PQ::R4_MEASUREMENT_CONSTRUCT::EXECUTION"
ACCEPTANCE="RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"

PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "measurement":("canonical/runtime/content_addressed_artifact_measurement_v1.py","4da88dc71e85874b6445988b792951fb3c36d62f"),
 "measured_acceptance":("canonical/runtime/measured_typed_acceptance_program_v1.py","7cb47bbefa807e93007e13e84607b41e27245f62"),
 "measurement_tests":("canonical/tests/test_content_addressed_artifact_measurement_v1.py","765e27ee66351b4f1289e4b1fb1c778f4c111da6"),
 "measurement_verify":("canonical/verification/ARTIFACT_MEASUREMENT_VERIFY_20261007_V1.json","34c64ed759d2e70df48a76d7a254047ac5fe9e2b"),
 "guard":("canonical/runtime/professional_quality_r4_execution_guard_v1.py","e7fa69957f6b3e3655612261e4f358900bd7cc19"),
}

def _blob(p:Path)->str:
 raw=p.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(p:Path)->dict[str,Any]:
 v=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(v,dict): raise ValueError("NOT_OBJECT")
 return v

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,
  "leaf_property_truth_authority":False,
  "detection_completeness_proved":False,
  "construct_validity_completeness_proved":False,
  "semantic_leaf_closed":False,"root_closed":False,
  "domain_execution_closure":False,"domain_semantic_closure":False,
  "quality_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
  **extra,
 }

def _execution_acceptance(manifest:Mapping[str,Any])->str|None:
 for row in manifest.get("roots") or []:
  if not isinstance(row,Mapping) or row.get("root_id")!=ROOT_ID: continue
  leaf=row.get("execution_leaf")
  if isinstance(leaf,Mapping) and leaf.get("id")==LEAF_ID:
   x=leaf.get("acceptance")
   return x if isinstance(x,str) else None
 return None

def _catalog_ids(catalog:Mapping[str,Any])->set[str]:
 rows=catalog.get("defeaters") or catalog.get("attack_classes") or catalog.get("nodes") or catalog.get("challenges") or []
 out=set()
 for row in rows:
  if isinstance(row,Mapping) and ROOT_ID in set(row.get("root_ids") or []):
   rid=row.get("id")
   if isinstance(rid,str) and rid: out.add(rid)
 return out

def evaluate_documents(manifest:Mapping[str,Any],catalog:Mapping[str,Any],measurement_verify:Mapping[str,Any])->dict[str,Any]:
 if _execution_acceptance(manifest)!=ACCEPTANCE:
  return _fail("R4_EXECUTION_ACCEPTANCE_DRIFT",observed_acceptance=_execution_acceptance(manifest))
 ids=_catalog_ids(catalog)
 if ids!=set(guard.KNOWN_R4_DEFEATERS):
  return _fail("R4_CATALOG_NOT_EXACT",expected=sorted(guard.KNOWN_R4_DEFEATERS),observed=sorted(ids))

 result=measurement_verify.get("result") or {}
 verified=set(measurement_verify.get("verified") or [])
 if (
  not str(measurement_verify.get("status") or "").startswith("INDEPENDENT_SPRITE_PASS")
  or result.get("passed")!=8 or result.get("total")!=8
  or "ARTIFACT_SHA_AND_MEASUREMENTS_DERIVED_FROM_REAL_BYTES" not in verified
  or "PATH_ESCAPE_FAILS_CLOSED" not in verified
  or "FIELD_TYPE_MISMATCH_FAILS_CLOSED" not in verified
 ):
  return _fail("MEASUREMENT_EXECUTION_RECEIPT_NOT_ADMISSIBLE")

 positive=guard.evaluate(measurement_pass=True)
 if positive.get("pass") is not True or positive.get("ordinary_acceptance_path_allowed") is not True:
  return _fail("R4_POSITIVE_PATH_FAILED",verdict=positive)

 adversarial={}
 for did in sorted(guard.KNOWN_R4_DEFEATERS):
  out=guard.evaluate(measurement_pass=True,detected_defeater_ids=(did,))
  adversarial[did]=(
   out.get("pass") is False
   and out.get("status")=="ABSTAIN_OR_ESCALATE__KNOWN_R4_DEFEATER_ACTIVE"
   and out.get("ordinary_acceptance_path_allowed") is False
  )
 if len(adversarial)!=7 or not all(adversarial.values()):
  return _fail("R4_ADVERSARIAL_CHALLENGE_MATRIX_INCOMPLETE",adversarial=adversarial)

 near={}
 for signal,trigger in sorted(guard.NEAR_MISS_TO_TRIGGER.items()):
  out=guard.evaluate(measurement_pass=True,near_miss_signals=(signal,))
  near[signal]=(
   out.get("pass") is False
   and out.get("status")=="ESCALATE__R4_NEAR_MISS_TRIGGER"
   and trigger in set(out.get("active_escalation_triggers") or [])
   and out.get("ordinary_acceptance_path_allowed") is False
  )
 if len(near)!=7 or not all(near.values()):
  return _fail("R4_NEAR_MISS_MATRIX_INCOMPLETE",near_miss=near)

 unknown=guard.evaluate(measurement_pass=True,detected_defeater_ids=("C999_FRESH_R4_ATTACK",))
 unmapped=guard.evaluate(measurement_pass=True,unmapped_material_defeater=True)
 failed=guard.evaluate(measurement_pass=False)
 if not (
  unknown.get("pass") is False and unknown.get("ordinary_acceptance_path_allowed") is False
  and unmapped.get("pass") is False and unmapped.get("ordinary_acceptance_path_allowed") is False
  and failed.get("pass") is False and failed.get("ordinary_acceptance_path_allowed") is False
 ):
  return _fail("R4_FAIL_CLOSED_CATCHALL_INCOMPLETE")

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R4_EXECUTION_CONTENT_ADDRESSED_MEASUREMENT_PLUS_ALL_DECLARED_ROOT_ATTACK_CLASSES_NEAR_MISSES_AND_CATCHALLS_OBSERVED_FAIL_CLOSED__ONE_EXECUTION_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,
  "manifest_acceptance":ACCEPTANCE,
  "measurement_execution_receipt_pass":True,
  "positive_case_pass":True,
  "adversarial_case_count":7,"adversarial_cases":adversarial,
  "near_miss_case_count":7,"near_miss_cases":near,
  "unknown_defeater_catchall":True,
  "unmapped_material_defeater_catchall":True,
  "failed_measurement_catchall":True,
  "leaf_property_truth_authority":True,
  "property_truth_basis":"EXACT_MEASUREMENT_BYTES__INDEPENDENT_MEASUREMENT_EXECUTION_RECEIPT__ALL_DECLARED_R4_ROOT_ATTACKS_AND_NEAR_MISSES_OBSERVED_FAIL_CLOSED",
  "detection_completeness_proved":False,
  "construct_validity_completeness_proved":False,
  "holistic_visual_quality_measured":False,
  "absolute_professional_floor_proved":False,
  "semantic_leaf_closed":False,"root_closed":False,
  "domain_execution_closure":False,"domain_semantic_closure":False,
  "quality_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 docs={}
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink(): return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=expected: return _fail(key.upper()+"_BLOB_STALE",expected_blob=expected,observed_blob=actual)
  if key in {"manifest","catalog","measurement_verify"}: docs[key]=_load(p)
 return evaluate_documents(docs["manifest"],docs["catalog"],docs["measurement_verify"])
