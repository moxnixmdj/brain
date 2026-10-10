"""R7 execution-leaf property-truth verifier V1.

Discharges only the manifest execution acceptance for
PQ::R7_CAUSAL_PRESCRIPTIVE::EXECUTION by recomputing:
- the exact current whole-leaf scope row from the independently verified 24-leaf batch,
- one real exact-byte single-edit fail->pass intervention,
- fail-closed near-miss/adversarial variants that would overclaim causality.

No R7 semantic/root/global quality authority is granted.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import professional_edit_causal_certificate_v1 as causal
from canonical.runtime import professional_quality_whole_leaf_scope_batch_v1 as batch

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R7_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
LEAF_ID="PQ::R7_CAUSAL_PRESCRIPTIVE::EXECUTION"
ROOT_ID="R7_CAUSAL_PRESCRIPTIVE"
ACCEPTANCE=(
 "RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_"
 "AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
)

PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "scope_batch_runtime":("canonical/runtime/professional_quality_whole_leaf_scope_batch_v1.py","82ab66c7852fc327821b23ff80dd46de3b81525c"),
 "scope_batch_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "causal_runtime":("canonical/runtime/professional_edit_causal_certificate_v1.py","c3f2da4c97f26126cd304c9d630b4e13655958ea"),
 "causal_verify":("canonical/verification/PROFESSIONAL_EDIT_CAUSAL_CERTIFICATE_VERIFY_20261010_V1.json","380d26afd8210096e397dacde3f2a339abc75c1c"),
 "source_receipt":("canonical/verification/PROFESSIONAL_QUALITY_R7_SINGLE_EDIT_CAUSAL_INSTANCE_VERIFY_20261009_V1.json","0c692f55dedb6a8523bcd78541d4cb77ef06d610"),
}

EXPECTED_R7_DEFEATERS={
 "C28_PREDICTIVE_PRESCRIPTIVE_GAP",
 "C29_COMPOUND_EDIT_ATTRIBUTION",
 "C30_TREATMENT_VERSION_NONINVARIANCE",
 "C31_EDIT_SEQUENCE_INTERACTION",
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
  "r7_semantic_leaf_closed":False,"r7_root_closed":False,
  "semantic_truth_authority":False,"execution_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def _manifest_leaf(manifest:Mapping[str,Any])->Mapping[str,Any]|None:
 for row in manifest.get("roots") or []:
  if not isinstance(row,Mapping) or row.get("root_id")!=ROOT_ID: continue
  leaf=row.get("execution_leaf")
  if isinstance(leaf,Mapping) and leaf.get("id")==LEAF_ID:
   return leaf
 return None

def _r7_catalog_ids(catalog:Mapping[str,Any])->set[str]:
 rows=catalog.get("challenges")
 if not isinstance(rows,list): return set()
 out=set()
 for row in rows:
  if isinstance(row,Mapping) and ROOT_ID in (row.get("root_ids") or []):
   did=row.get("id")
   if isinstance(did,str): out.add(did)
 return out

def evaluate_documents(
 manifest:Mapping[str,Any],catalog:Mapping[str,Any],
 scope_batch_verify:Mapping[str,Any],source:Mapping[str,Any],
 causal_verify:Mapping[str,Any],
)->dict[str,Any]:
 leaf=_manifest_leaf(manifest)
 if leaf is None:return _fail("R7_EXECUTION_LEAF_NOT_IN_MANIFEST")
 if leaf.get("acceptance")!=ACCEPTANCE:
  return _fail("R7_EXECUTION_ACCEPTANCE_DRIFT",observed_acceptance=leaf.get("acceptance"))

 if not str(scope_batch_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_INDEPENDENT_PASS")
 replay=scope_batch_verify.get("independent_replay") or {}
 if replay.get("leaf_count")!=24 or replay.get("domain_equivalence_pass_count")!=24 or replay.get("scope_complete_count")!=24:
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_24_OF_24")
 if replay.get("property_truth_count")!=0:
  return _fail("WHOLE_LEAF_SCOPE_BATCH_PROPERTY_TRUTH_OVERCLAIM")

 batch_out=batch.verify()
 if batch_out.get("pass") is not True or batch_out.get("scope_complete_count")!=24:
  return _fail("WHOLE_LEAF_SCOPE_BATCH_RECOMPUTE_FAILED",batch_verdict=batch_out)
 rows=[x for x in (batch_out.get("rows") or []) if x.get("leaf_id")==LEAF_ID]
 if len(rows)!=1:return _fail("R7_SCOPE_BATCH_ROW_CARDINALITY",count=len(rows))
 scope_row=rows[0]
 if scope_row.get("whole_leaf_domain_equivalence_proved") is not True or scope_row.get("whole_leaf_scope_complete") is not True:
  return _fail("R7_WHOLE_LEAF_SCOPE_NOT_COMPLETE")
 if scope_row.get("leaf_property_truth_authority") is not False:
  return _fail("R7_SCOPE_BATCH_SELF_PROPERTY_AUTHORITY_FORBIDDEN")

 if _r7_catalog_ids(catalog)!=EXPECTED_R7_DEFEATERS:
  return _fail("R7_DEFEATER_CATALOG_DRIFT",observed=sorted(_r7_catalog_ids(catalog)))

 if causal_verify.get("status")!="PASS__EXACT_BLOBS__PYCOMPILE__8_OF_8__REUSABLE_CLAIM_SCOPED_CAUSAL_MECHANISM__ZERO_TERMINAL_CREDIT":
  return _fail("CAUSAL_COMPILER_INDEPENDENT_VERIFICATION_NOT_PASS")
 if (causal_verify.get("replay") or {}).get("tests_passed")!=8:
  return _fail("CAUSAL_COMPILER_REPLAY_COUNT_INVALID")

 positive=causal.compile_certificate(source)
 positive_ok=(
  positive.get("pass") is True
  and positive.get("causal_claim_authority") is True
  and positive.get("execution_signature")=="PREDECESSOR_FAIL__REPAIRED_PASS__IDENTICAL_TEST_BYTES"
  and positive.get("global_r7_authority") is False
 )

 cases={}

 row=deepcopy(source);row["real_execution"]["same_test_bytes"]=False
 out=causal.compile_certificate(row)
 cases["CHANGED_TEST_BYTES_REJECTED"]=out.get("reason")=="SAME_TEST_BYTES_REQUIRED"

 row=deepcopy(source)
 row["exact_subject"]["repaired_runtime_git_blob_sha"]=row["exact_subject"]["predecessor_runtime_git_blob_sha"]
 row["byte_identity"]["repaired_runtime_materialized_git_hash_object"]=row["exact_subject"]["predecessor_runtime_git_blob_sha"]
 out=causal.compile_certificate(row)
 cases["NO_INTERVENTION_BYTE_CHANGE_REJECTED"]=out.get("reason")=="NO_INTERVENTION_BYTE_CHANGE"

 row=deepcopy(source);row["real_execution"]["predecessor_result"]["outcome"]="PASS";row["real_execution"]["predecessor_result"]["return_code"]=0
 out=causal.compile_certificate(row)
 cases["PASS_TO_PASS_NOT_CAUSAL_RESCUE"]=out.get("reason")=="REQUIRED_FAIL_TO_PASS_SIGNATURE_MISSING"

 row=deepcopy(source);row["r7_defeater_disposition"]["C29_COMPOUND_EDIT_ATTRIBUTION"]["claim_scoped_state"]="DISCHARGED_FOR_THIS_EXACT_INSTANCE"
 out=causal.compile_certificate(row)
 cases["COMPOUND_ATTRIBUTION_OVERCLAIM_REJECTED"]=out.get("reason")=="R7_DEFEATER_STATE_INVALID:C29_COMPOUND_EDIT_ATTRIBUTION"

 row=deepcopy(source);row["conclusions"]["sequence_invariance_proved"]=True
 out=causal.compile_certificate(row)
 cases["SEQUENCE_INVARIANCE_OVERCLAIM_REJECTED"]=out.get("reason")=="SOURCE_OVERCLAIM_FORBIDDEN:sequence_invariance_proved"

 row=deepcopy(source);row["conclusions"]["treatment_generalization_proved"]=True
 out=causal.compile_certificate(row)
 cases["TREATMENT_GENERALIZATION_OVERCLAIM_REJECTED"]=out.get("reason")=="SOURCE_OVERCLAIM_FORBIDDEN:treatment_generalization_proved"

 row=deepcopy(source);row["conclusions"]["r7_global_root_closed"]=True
 out=causal.compile_certificate(row)
 cases["GLOBAL_R7_OVERCLAIM_REJECTED"]=out.get("reason")=="SOURCE_OVERCLAIM_FORBIDDEN:r7_global_root_closed"

 row=deepcopy(source);row["byte_identity"]["repaired_runtime_materialized_git_hash_object"]="0"*40
 out=causal.compile_certificate(row)
 cases["MATERIALIZED_BYTE_REBINDING_REJECTED"]=out.get("reason")=="REPAIRED_BYTE_IDENTITY_MISMATCH"

 checks={
  "POSITIVE_REAL_FAIL_TO_PASS_INTERVENTION_BOUND":positive_ok,
  "ALL_4_CANONICAL_R7_DEFEATER_CLASSES_BOUND_TO_EXACT_CLAIM_SCOPE":set((positive.get("r7_disposition") or {}).keys())==EXPECTED_R7_DEFEATERS,
  "NEAR_MISS_AND_ADVERSARIAL_OVERREACH_FAILS_CLOSED":all(cases.values()) and len(cases)==8,
 }
 if not all(checks.values()):
  return _fail("R7_EXECUTION_PROPERTY_CHALLENGE_FAILED",checks=checks,case_results=cases,positive=positive)

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R7_EXECUTION_MANIFEST_ACCEPTANCE_OBSERVED_ON_EXACT_CAUSAL_INTERVENTION_AND_FAIL_CLOSED_BOUNDARIES__ONE_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,
  "whole_leaf_claim_id":scope_row.get("claim_id"),
  "manifest_acceptance":ACCEPTANCE,
  "checks":checks,
  "case_results":cases,
  "observed_case_counts":{"positive":1,"near_miss_and_adversarial":8,"total":9},
  "canonical_r7_defeater_ids":sorted(EXPECTED_R7_DEFEATERS),
  "leaf_property_truth_authority":True,
  "property_truth_basis":"REAL_SINGLE_EDIT_FAIL_TO_PASS_PLUS_FAIL_CLOSED_CLAIM_SCOPE_BOUNDARY_CHALLENGES",
  "r7_semantic_leaf_closed":False,"r7_root_closed":False,
  "multi_edit_attribution_proved":False,"sequence_invariance_proved":False,
  "treatment_generalization_proved":False,
  "semantic_truth_authority":False,"execution_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 docs={}
 for key,(rel,expected) in PINS.items():
  path=root/rel
  if not path.is_file() or path.is_symlink():return _fail(key.upper()+"_MISSING")
  actual=_blob(path)
  if actual!=expected:return _fail(key.upper()+"_BLOB_STALE",observed_blob=actual)
  if key in {"manifest","catalog","scope_batch_verify","causal_verify","source_receipt"}:
   try:docs[key]=_load(path)
   except Exception:return _fail(key.upper()+"_JSON_INVALID")
 return evaluate_documents(
  docs["manifest"],docs["catalog"],docs["scope_batch_verify"],
  docs["source_receipt"],docs["causal_verify"]
 )

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
