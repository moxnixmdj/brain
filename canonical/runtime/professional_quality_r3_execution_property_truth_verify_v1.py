"""R3 execution-leaf property-truth adjudicator V1.

This verifier grants authority only for the execution leaf
PQ::R3_REALIZATION_OBSERVATION::EXECUTION. It does not claim semantic/root/global
professional-quality closure.

The proof reuses two already-independent evidence channels:
1. the exact-byte public native-artifact render-preservation capsule, and
2. one exact current V7 real-task render-step receipt with distinct verifier.

A current whole-leaf scope batch is recomputed before any property-truth result.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_quality_whole_leaf_scope_batch_v1 as batch

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R3_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
LEAF_ID="PQ::R3_REALIZATION_OBSERVATION::EXECUTION"
ROOT_ID="R3_REALIZATION_OBSERVATION"
ACCEPTANCE=(
 "RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_"
 "AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
)
PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "public_render_verify":("canonical/verification/NATIVE_ARTIFACT_RENDER_PRESERVATION_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json","1a0b4ca6627aaf28eb25f6990682e87319d14d6d"),
 "root_binding_verify":("canonical/verification/PROFESSIONAL_QUALITY_R3_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V2.json","870bb85fbd00d670ec36e86b4b0b510f5bb9225c"),
 "step_verify":("canonical/verification/PROFESSIONAL_QUALITY_R3_V7_RENDER_STEP_RESULT_BINDING_VERIFY_20261010_V3.json","734f88f5d201e778f59133c9e22f29ae4d451121"),
 "step_binding":("canonical/governance/PROFESSIONAL_QUALITY_R3_V7_RENDER_STEP_RESULT_BINDING_20261010_V3.json","8a524bd90cee783d9d342b80a95b990d23a413e0"),
 "subject":("canonical/governance/PROFESSIONAL_QUALITY_P1_V7_DECLARED_SYSTEM_SUBJECT_20261010_V6.json","1d598bc8757017ceb34928d0df9f5fce859ef868"),
 "preflight":("canonical/governance/NATIVE_ARTIFACT_RENDER_PRESERVATION_PREFLIGHT_V1.json","b5ddc896811875b59840959e27dbb515265fc9f8"),
}
REQUIRED_PUBLIC_VERIFIED={
 "DOCX_XLSX_PPTX_RENDER_THROUGH_LIBREOFFICE_AND_ALL_FORMATS_RASTERIZE_THROUGH_POPPLER",
 "SOURCE_AND_OUTPUT_PAGE_COUNTS_EQUAL",
 "SOURCE_AND_OUTPUT_PAGE_PIXEL_DIMENSIONS_EQUAL",
 "UNCHANGED_PAGES_ARE_ACCEPTED_AS_PRESERVED",
 "AT_LEAST_ONE_PAGE_MUST_VISIBLY_CHANGE",
 "CHANGED_PIXELS_AND_BOUNDING_BOX_MUST_REMAIN_WITHIN_FROZEN_LOCALIZATION_BOUNDS",
 "UNCHANGED_WHOLE_OUTPUT_IS_REJECTED",
 "LARGE_DOCX_PAGE_GEOMETRY_MUTATION_IS_REJECTED",
 "STRUCTURAL_HIDDEN_ORACLE_MUST_PASS_BEFORE_RENDER_ACCEPTANCE",
 "EXACT_BRAIN_BLOBS_VERIFIED_BY_PUBLIC_CAPSULE",
}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _load(path:Path)->dict[str,Any]:
 value=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(value,dict): raise ValueError("NOT_OBJECT")
 return value

def _leaf_acceptance(manifest:Mapping[str,Any])->str|None:
 for row in manifest.get("roots") or []:
  if isinstance(row,Mapping) and row.get("root_id")==ROOT_ID:
   leaf=row.get("execution_leaf")
   if isinstance(leaf,Mapping) and leaf.get("id")==LEAF_ID:
    v=leaf.get("acceptance")
    return v if isinstance(v,str) else None
 return None

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"leaf_property_truth_authority":False,
  "r3_semantic_leaf_closed":False,"r3_root_closed":False,
  "unknown_defeater_completeness_proved":False,"full_main_regression_proved":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def evaluate_documents(
 manifest:Mapping[str,Any],
 public_verify:Mapping[str,Any],
 root_binding_verify:Mapping[str,Any],
 step_verify:Mapping[str,Any],
 step_binding:Mapping[str,Any],
 subject:Mapping[str,Any],
 preflight:Mapping[str,Any],
 scope_row:Mapping[str,Any],
 observed_native_blobs:Mapping[str,str],
)->dict[str,Any]:
 if _leaf_acceptance(manifest)!=ACCEPTANCE:
  return _fail("R3_EXECUTION_ACCEPTANCE_DRIFT",observed_acceptance=_leaf_acceptance(manifest))
 if (
  scope_row.get("leaf_id")!=LEAF_ID
  or scope_row.get("whole_leaf_domain_equivalence_proved") is not True
  or scope_row.get("whole_leaf_scope_complete") is not True
  or scope_row.get("leaf_property_truth_authority") is not False
 ):
  return _fail("R3_WHOLE_LEAF_SCOPE_NOT_CURRENT_AND_COMPLETE",scope_row=dict(scope_row))

 if not str(public_verify.get("status") or "").startswith("INDEPENDENT_BOUNDED_RENDER_PRESERVATION_PREFLIGHT_PASS"):
  return _fail("R3_PUBLIC_RENDER_VERIFICATION_NOT_PASS")
 runner=public_verify.get("independent_public_runner") or {}
 if runner.get("conclusion")!="success":
  return _fail("R3_PUBLIC_RUNNER_CONCLUSION_NOT_SUCCESS")
 expected_native=public_verify.get("exact_brain_blobs")
 if not isinstance(expected_native,Mapping) or dict(expected_native)!=dict(observed_native_blobs):
  return _fail("R3_NATIVE_BLOB_SET_NOT_EXACT_CURRENT",expected=expected_native,observed=dict(observed_native_blobs))
 verified=set(public_verify.get("verified") or [])
 missing=sorted(REQUIRED_PUBLIC_VERIFIED-verified)
 if missing:
  return _fail("R3_PUBLIC_CHALLENGE_COVERAGE_INCOMPLETE",missing=missing)

 if not str(preflight.get("status") or "").startswith("INDEPENDENT_PUBLIC_RUNNER_PASS"):
  return _fail("R3_PREFLIGHT_NOT_INDEPENDENT_PASS")

 subject_id=subject.get("subject_id")
 subject_sha=subject.get("subject_sha256")
 if not isinstance(subject_id,str) or not isinstance(subject_sha,str):
  return _fail("R3_SUBJECT_IDENTITY_INVALID")

 if (
  root_binding_verify.get("root_id")!=ROOT_ID
  or root_binding_verify.get("root_subject_binding_authority") is not True
  or root_binding_verify.get("real_task_render_step_receipt_bound") is not True
  or root_binding_verify.get("exact_real_task_receipt_count")!=1
 ):
  return _fail("R3_ROOT_BINDING_REAL_TASK_RECEIPT_NOT_BOUND")
 exact_blobs=root_binding_verify.get("exact_blobs") or {}
 if exact_blobs.get("exact_step_receipt")!=PINS["step_binding"][1] or exact_blobs.get("exact_step_verification")!=PINS["step_verify"][1]:
  return _fail("R3_ROOT_BINDING_STEP_IDENTITY_DRIFT")

 exact=step_verify.get("exact_instance") or {}
 if (
  step_verify.get("pass") is not True
  or step_verify.get("independent_verified") is not True
  or step_verify.get("semantic_preservation_verified") is not True
  or step_verify.get("evidence_scope_verified") is not True
  or step_verify.get("producer_verifier_distinct") is not True
  or step_verify.get("subject_id")!=subject_id
  or step_verify.get("subject_sha256")!=subject_sha
  or step_verify.get("subject_git_blob_sha")!=PINS["step_binding"][1]
  or exact.get("target_replacement_exact") is not True
  or exact.get("unrelated_zip_members_byte_identical") is not True
  or exact.get("visible_localized_change_pass") is not True
 ):
  return _fail("R3_REAL_TASK_STEP_RECEIPT_INVALID")

 checks={
  "CURRENT_WHOLE_LEAF_SCOPE_COMPLETE":True,
  "EXACT_CURRENT_NATIVE_BYTES_MATCH_INDEPENDENT_PUBLIC_CAPSULE":True,
  "POSITIVE_FOUR_FORMAT_RENDER_ENVELOPE_VERIFIED":True,
  "NEAR_MISS_LARGE_LAYOUT_MUTATION_REJECTED":True,
  "ADVERSARIAL_UNCHANGED_OUTPUT_REJECTED":True,
  "STRUCTURAL_HIDDEN_ORACLE_REQUIRED":True,
  "EXACT_CURRENT_V7_REAL_TASK_RENDER_RECEIPT_BOUND":True,
 }
 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R3_EXECUTION_MANIFEST_ACCEPTANCE_BOUND_TO_EXACT_CURRENT_NATIVE_RENDER_BYTES_AND_CURRENT_V7_REAL_TASK_RECEIPT__ONE_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"claim_id":scope_row.get("claim_id"),
  "manifest_acceptance":ACCEPTANCE,"checks":checks,
  "observed_case_basis":{
   "public_positive_formats":["docx","xlsx","pptx","pdf"],
   "public_near_miss":["LARGE_DOCX_PAGE_GEOMETRY_MUTATION_IS_REJECTED"],
   "public_adversarial":["UNCHANGED_WHOLE_OUTPUT_IS_REJECTED","STRUCTURAL_HIDDEN_ORACLE_MUST_PASS_BEFORE_RENDER_ACCEPTANCE"],
   "current_real_task_receipt_count":1,
  },
  "leaf_property_truth_authority":True,
  "property_truth_basis":"EXACT_BLOB_EQUIVALENCE_TO_INDEPENDENT_PUBLIC_RENDER_CHALLENGE_PLUS_CURRENT_V7_REAL_TASK_RENDER_RECEIPT",
  "unknown_defeater_completeness_proved":False,"full_main_regression_proved":False,
  "r3_semantic_leaf_closed":False,"r3_root_closed":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 docs={}
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink(): return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=expected:return _fail(key.upper()+"_BLOB_STALE",observed_blob=actual)
  try:docs[key]=_load(p)
  except Exception:return _fail(key.upper()+"_JSON_INVALID")
 batch_out=batch.verify(repo_root=root)
 if batch_out.get("pass") is not True or batch_out.get("scope_complete_count")!=24:
  return _fail("R3_SCOPE_BATCH_RECOMPUTE_FAILED",batch_verdict=batch_out)
 rows=[r for r in batch_out.get("rows") or [] if r.get("leaf_id")==LEAF_ID]
 if len(rows)!=1:return _fail("R3_SCOPE_ROW_CARDINALITY",count=len(rows))
 public=docs["public_render_verify"]
 native=public.get("exact_brain_blobs") or {}
 observed={}
 for rel in native:
  p=root/rel
  if not p.is_file() or p.is_symlink():return _fail("R3_NATIVE_FILE_MISSING",path=rel)
  observed[rel]=_blob(p)
 return evaluate_documents(
  docs["manifest"],docs["public_render_verify"],docs["root_binding_verify"],
  docs["step_verify"],docs["step_binding"],docs["subject"],docs["preflight"],
  rows[0],observed,
 )

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
