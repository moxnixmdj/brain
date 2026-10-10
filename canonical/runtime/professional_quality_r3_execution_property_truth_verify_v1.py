"""R3 execution-leaf property-truth verifier V1.

Binds the existing real V7 render receipt, exact current manifest/catalog, and
observed fail-closed response for every declared R3 attack class and near miss.
Leaf authority only. No semantic/root/global realization completeness.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime import professional_quality_r3_execution_guard_v1 as guard

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R3_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
ROOT_ID="R3_REALIZATION_OBSERVATION"
LEAF_ID="PQ::R3_REALIZATION_OBSERVATION::EXECUTION"
ACCEPTANCE="RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "r3_root_verify":("canonical/verification/PROFESSIONAL_QUALITY_R3_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V2.json","870bb85fbd00d670ec36e86b4b0b510f5bb9225c"),
 "render_verify":("canonical/verification/PROFESSIONAL_QUALITY_R3_V7_RENDER_STEP_RESULT_BINDING_VERIFY_20261010_V3.json","734f88f5d201e778f59133c9e22f29ae4d451121"),
 "instance":("canonical/evidence/PROFESSIONAL_QUALITY_R3_V7_EXACT_REALIZATION_INSTANCE_20261010_V1.json","13e7e58b3621b3cabb7abdebe23689f3a72678d2"),
 "step_receipt":("canonical/governance/PROFESSIONAL_QUALITY_R3_V7_RENDER_STEP_RESULT_BINDING_20261010_V3.json","8a524bd90cee783d9d342b80a95b990d23a413e0"),
 "guard":("canonical/runtime/professional_quality_r3_execution_guard_v1.py","3512b0634fd563feb4dd64d27c5241f47e9815d6"),
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
  "detection_completeness_proved":False,"renderer_invariance_proved":False,
  "semantic_target_correctness_proved":False,"semantic_leaf_closed":False,
  "root_closed":False,"domain_execution_closure":False,"domain_semantic_closure":False,
  "quality_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra}

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

def evaluate_documents(manifest:Mapping[str,Any],catalog:Mapping[str,Any],
                       r3_root_verify:Mapping[str,Any],render_verify:Mapping[str,Any])->dict[str,Any]:
 if _execution_acceptance(manifest)!=ACCEPTANCE:
  return _fail("R3_EXECUTION_ACCEPTANCE_DRIFT",observed_acceptance=_execution_acceptance(manifest))
 ids=_catalog_ids(catalog)
 if ids!=set(guard.KNOWN_R3_DEFEATERS):
  return _fail("R3_CATALOG_NOT_EXACT",expected=sorted(guard.KNOWN_R3_DEFEATERS),observed=sorted(ids))

 if (not str(r3_root_verify.get("status") or "").startswith("PASS__CURRENT_MAIN_V1_PLUS_ONE_EXACT_REAL_TASK_RENDER_STEP_RECEIPT")
     or r3_root_verify.get("root_subject_binding_authority") is not True
     or r3_root_verify.get("real_task_render_step_receipt_bound") is not True
     or r3_root_verify.get("exact_real_task_receipt_count")!=1):
  return _fail("R3_REAL_TASK_ROOT_RECEIPT_NOT_ADMISSIBLE")
 eb=r3_root_verify.get("exact_blobs") or {}
 if (eb.get("exact_instance_evidence")!=PINS["instance"][1]
     or eb.get("exact_step_receipt")!=PINS["step_receipt"][1]
     or eb.get("exact_step_verification")!=PINS["render_verify"][1]):
  return _fail("R3_REAL_TASK_RECEIPT_CHAIN_DRIFT")

 ex=render_verify.get("exact_instance") or {}
 if not (render_verify.get("pass") is True
         and render_verify.get("independent_verified") is True
         and render_verify.get("semantic_preservation_verified") is True
         and render_verify.get("evidence_scope_verified") is True
         and render_verify.get("producer_verifier_distinct") is True
         and ex.get("target_replacement_exact") is True
         and ex.get("unrelated_zip_members_byte_identical") is True
         and ex.get("visible_localized_change_pass") is True):
  return _fail("R3_RENDER_RECEIPT_NOT_ADMISSIBLE")

 positive=guard.evaluate(realization_receipt_pass=True)
 if positive.get("pass") is not True or positive.get("ordinary_acceptance_path_allowed") is not True:
  return _fail("R3_POSITIVE_PATH_FAILED",verdict=positive)

 adversarial={}
 for did in sorted(guard.KNOWN_R3_DEFEATERS):
  out=guard.evaluate(realization_receipt_pass=True,detected_defeater_ids=(did,))
  adversarial[did]=(out.get("pass") is False
                    and out.get("status")=="ABSTAIN_OR_ESCALATE__KNOWN_R3_DEFEATER_ACTIVE"
                    and out.get("ordinary_acceptance_path_allowed") is False)
 if len(adversarial)!=7 or not all(adversarial.values()):
  return _fail("R3_ADVERSARIAL_CHALLENGE_MATRIX_INCOMPLETE",adversarial=adversarial)

 near={}
 for signal,trigger in sorted(guard.NEAR_MISS_TO_TRIGGER.items()):
  out=guard.evaluate(realization_receipt_pass=True,near_miss_signals=(signal,))
  near[signal]=(out.get("pass") is False
                and out.get("status")=="ESCALATE__R3_NEAR_MISS_TRIGGER"
                and trigger in set(out.get("active_escalation_triggers") or [])
                and out.get("ordinary_acceptance_path_allowed") is False)
 if len(near)!=7 or not all(near.values()):
  return _fail("R3_NEAR_MISS_MATRIX_INCOMPLETE",near_miss=near)

 unknown=guard.evaluate(realization_receipt_pass=True,detected_defeater_ids=("C999_FRESH_R3_ATTACK",))
 unmapped=guard.evaluate(realization_receipt_pass=True,unmapped_material_defeater=True)
 failed=guard.evaluate(realization_receipt_pass=False)
 if not all(x.get("pass") is False and x.get("ordinary_acceptance_path_allowed") is False
            for x in (unknown,unmapped,failed)):
  return _fail("R3_FAIL_CLOSED_CATCHALL_INCOMPLETE")

 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__R3_REAL_RENDER_RECEIPT_PLUS_ALL_DECLARED_ROOT_ATTACK_CLASSES_NEAR_MISSES_AND_CATCHALLS_OBSERVED_FAIL_CLOSED__ONE_EXECUTION_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"manifest_acceptance":ACCEPTANCE,
  "real_task_render_receipt_pass":True,"positive_case_pass":True,
  "adversarial_case_count":7,"adversarial_cases":adversarial,
  "near_miss_case_count":7,"near_miss_cases":near,
  "unknown_defeater_catchall":True,"unmapped_material_defeater_catchall":True,
  "failed_realization_receipt_catchall":True,"leaf_property_truth_authority":True,
  "property_truth_basis":"EXACT_REAL_RENDER_RECEIPT__INDEPENDENT_RECEIPT_CHAIN__ALL_DECLARED_R3_ROOT_ATTACKS_AND_NEAR_MISSES_OBSERVED_FAIL_CLOSED",
  "detection_completeness_proved":False,"renderer_invariance_proved":False,
  "semantic_target_correctness_proved":False,"whole_artifact_observation_completeness_proved":False,
  "semantic_leaf_closed":False,"root_closed":False,"domain_execution_closure":False,
  "domain_semantic_closure":False,"quality_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 docs={}
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink(): return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=expected: return _fail(key.upper()+"_BLOB_STALE",expected_blob=expected,observed_blob=actual)
  if key in {"manifest","catalog","r3_root_verify","render_verify"}: docs[key]=_load(p)
 return evaluate_documents(docs["manifest"],docs["catalog"],docs["r3_root_verify"],docs["render_verify"])
