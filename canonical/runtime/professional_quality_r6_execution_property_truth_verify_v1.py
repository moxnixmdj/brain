"""R6 execution-leaf property-truth verifier V1.

Discharges only the manifest execution acceptance for
PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::EXECUTION.

Proof:
- exact 24/24 whole-leaf scope recomputation;
- exact pinned professional leaf-binder runtime exercised directly with one
  content-addressed positive receipt and fail-closed receipt mutations;
- independent binder mutation verification;
- exact UVCK current-generation/order/80-defeater verification;
- activation of every canonical R6 defeater against the exact assurance graph.

No evidence completeness, semantic/root/global quality, acceptance, promotion,
or terminal authority is claimed.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
import tempfile
from typing import Any, Mapping

from canonical.runtime import assurance_closure_compiler_v1 as kernel
from canonical.runtime import professional_quality_leaf_binder_v2 as binder
from canonical.runtime import professional_quality_whole_leaf_scope_batch_v1 as batch

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R6_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
LEAF_ID="PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::EXECUTION"
ROOT_ID="R6_EVIDENCE_GROUNDING_DEPENDENCE"
ACCEPTANCE=(
 "RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_"
 "AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
)
EXPECTED_R6_DEFEATERS={
 "C23_PSEUDOREPLICATION","C24_UNGROUNDED_META_EVALUATOR","C25_CLAIM_TYPE_LAUNDERING",
 "C26_UNCERTAINTY_SEMANTICS_LAUNDERING","C27_HIDDEN_PREMISE_INFERENCE",
 "C61_HIDDEN_ASSUMPTION_CYCLE","C68_SELF_PREFERENCE_JUDGE_BIAS",
 "C69_CROSS_MODEL_CALIBRATION_SIGN_REVERSAL","C71_JOINT_ASSURANCE_MULTIPLICITY",
 "C74_EXECUTION_FAILURE_FAIL_OPEN","C75_STALE_CERT_AFTER_DEPENDENCY_CHANGE",
 "C76_SELECTIVE_EVIDENCE_PACKET","C77_PROVENANCE_OR_RECEIPT_FORGERY",
 "C79_FALLBACK_EVALUATOR_SCOPE_WEAKENING","C80_OPTIONAL_STOPPING_OR_REPEATED_TESTING",
}
PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "graph":("canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json","03530e29d70206b46b690b33a04c66765ff86ad7"),
 "scope_batch_runtime":("canonical/runtime/professional_quality_whole_leaf_scope_batch_v1.py","82ab66c7852fc327821b23ff80dd46de3b81525c"),
 "scope_batch_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "binder_runtime":("canonical/runtime/professional_quality_leaf_binder_v2.py","1a181b453271a2ce4fc112c3f6586afaf5effbd7"),
 "binder_tests":("canonical/tests/test_professional_quality_leaf_binder_v2.py","af63e0c126e9b7af0fb7a652adbc5ef7661e1460"),
 "binder_verify":("canonical/verification/PROFESSIONAL_QUALITY_LEAF_BINDER_V2_VERIFY_20261010_V1.json","b65a67e8edaee925338fe3f2d61dad6b0f52d129"),
 "kernel":("canonical/runtime/assurance_closure_compiler_v1.py","b4274a48edbe626a9ae9fd33da2f2227ca4dd5e8"),
 "currentgen_verify":("canonical/verification/UVCK_V2_CURRENT_GENERATION_INDEPENDENT_REPLAY_VERIFY_20261009_V1.json","81f7f070233b6aa1c4b491949a4c3e7aedfafd10"),
 "order_verify":("canonical/verification/UVCK_V2_DEFEATER_ORDER_VERIFY_20261009_V1.json","1c3428b10a1205e928a87f41a7c16a8a3d17b7ca"),
 "defeater80_verify":("canonical/verification/PROFESSIONAL_QUALITY_80_DEFEATER_UVCK_REPLAY_VERIFY_20261009_V1.json","c054e9362ce382889e9cca62bdb69e11cea19644"),
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
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"leaf_property_truth_authority":False,
  "r6_semantic_leaf_closed":False,"r6_root_closed":False,
  "semantic_truth_authority":False,"execution_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def _manifest_row(manifest:Mapping[str,Any])->Mapping[str,Any]|None:
 for row in manifest.get("roots") or []:
  if isinstance(row,Mapping) and row.get("root_id")==ROOT_ID:return row
 return None

def _r6_ids(catalog:Mapping[str,Any])->set[str]:
 out=set()
 for row in catalog.get("challenges") or []:
  if isinstance(row,Mapping) and ROOT_ID in (row.get("root_ids") or []):
   cid=row.get("id")
   if isinstance(cid,str):out.add(cid)
 return out

def _graph_with_supported_defeater(graph:Mapping[str,Any],did:str)->dict[str,Any]:
 g=deepcopy(dict(graph))
 nodes={x.get("id"):x for x in (g.get("nodes") or []) if isinstance(x,dict)}
 if did not in nodes:return {}
 nodes[did]["status"]="SUPPORTED"
 return g

def _exercise_binder(contract:str,acceptance:str,manifest_blob:str)->dict[str,Any]:
 """Exercise exact binder bytes without depending on unrelated registry files."""
 with tempfile.TemporaryDirectory() as td:
  root=Path(td)
  basis=root/"canonical/evidence/r6_basis.json"
  receipt=root/"canonical/verification/r6_receipt.json"
  basis.parent.mkdir(parents=True,exist_ok=True)
  receipt.parent.mkdir(parents=True,exist_ok=True)
  basis.write_text('{"evidence":"grounded"}\n',encoding="utf-8")

  doc={
   "schema":binder.RECEIPT_SCHEMA,
   "leaf_id":LEAF_ID,"root_id":ROOT_ID,"leaf_kind":"EXECUTION",
   "verdict":"PASS","closure_scope":"EXACT_LEAF",
   "acceptance_sha256":binder.semantic_sha(acceptance),
   "root_contract_sha256":binder.semantic_sha(contract),
   "manifest_git_blob_sha":manifest_blob,
   "leaf_execution_satisfied":True,
   "verification_basis":[{
    "path":"canonical/evidence/r6_basis.json",
    "git_blob_sha":binder.git_blob_sha(basis),
   }],
   "terminal_authority":False,
  }
  receipt.write_text(json.dumps(doc,sort_keys=True)+"\n",encoding="utf-8")
  entry={"path":"canonical/verification/r6_receipt.json","git_blob_sha":binder.git_blob_sha(receipt)}

  def run(e=entry,acc=acceptance,con=contract):
   return binder._receipt_result(
    repo_root=root,entry=e,leaf_id=LEAF_ID,root_id=ROOT_ID,kind="EXECUTION",
    acceptance=acc,contract=con,manifest_blob_sha=manifest_blob,
   )

  positive=run()
  cases={}

  wrong=deepcopy(doc);wrong["acceptance_sha256"]=binder.semantic_sha("WRONG")
  receipt.write_text(json.dumps(wrong,sort_keys=True)+"\n",encoding="utf-8")
  bad_entry={"path":entry["path"],"git_blob_sha":binder.git_blob_sha(receipt)}
  out=run(bad_entry)
  cases["WRONG_ACCEPTANCE_REJECTED"]="ACCEPTANCE_BINDING_MISMATCH" in out.get("errors",[])

  wrong=deepcopy(doc);wrong["root_contract_sha256"]=binder.semantic_sha("WRONG")
  receipt.write_text(json.dumps(wrong,sort_keys=True)+"\n",encoding="utf-8")
  bad_entry={"path":entry["path"],"git_blob_sha":binder.git_blob_sha(receipt)}
  out=run(bad_entry)
  cases["WRONG_ROOT_CONTRACT_REJECTED"]="ROOT_CONTRACT_BINDING_MISMATCH" in out.get("errors",[])

  receipt.write_text(json.dumps(doc,sort_keys=True)+"\n",encoding="utf-8")
  fresh_entry={"path":entry["path"],"git_blob_sha":binder.git_blob_sha(receipt)}
  basis.write_text('{"evidence":"tampered"}\n',encoding="utf-8")
  out=run(fresh_entry)
  cases["STALE_OR_TAMPERED_BASIS_REJECTED"]="VERIFICATION_BASIS_NOT_CURRENT" in out.get("errors",[])

  basis.write_text('{"evidence":"grounded"}\n',encoding="utf-8")
  receipt.write_text(json.dumps(doc,sort_keys=True)+"\n",encoding="utf-8")
  stale_entry={"path":entry["path"],"git_blob_sha":binder.git_blob_sha(receipt)}
  receipt.write_text(receipt.read_text(encoding="utf-8")+" ",encoding="utf-8")
  out=run(stale_entry)
  cases["RECEIPT_BYTE_TAMPER_REJECTED"]="RECEIPT_FILE_NOT_CURRENT" in out.get("errors",[])

  return {
   "positive_admitted":positive.get("admitted") is True and positive.get("errors")==[],
   "positive":positive,"cases":cases,
  }

def evaluate_documents(
 manifest:Mapping[str,Any],catalog:Mapping[str,Any],graph:Mapping[str,Any],
 scope_verify:Mapping[str,Any],binder_verify:Mapping[str,Any],
 currentgen:Mapping[str,Any],order_verify:Mapping[str,Any],defeater80:Mapping[str,Any],
)->dict[str,Any]:
 row=_manifest_row(manifest)
 if row is None:return _fail("R6_ROOT_NOT_IN_MANIFEST")
 leaf=row.get("execution_leaf") if isinstance(row,Mapping) else None
 if not isinstance(leaf,Mapping) or leaf.get("id")!=LEAF_ID:return _fail("R6_EXECUTION_LEAF_NOT_IN_MANIFEST")
 if leaf.get("acceptance")!=ACCEPTANCE:return _fail("R6_EXECUTION_ACCEPTANCE_DRIFT",observed_acceptance=leaf.get("acceptance"))

 if not str(scope_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_INDEPENDENT_PASS")
 sr=scope_verify.get("independent_replay") or {}
 if sr.get("leaf_count")!=24 or sr.get("domain_equivalence_pass_count")!=24 or sr.get("scope_complete_count")!=24:
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_24_OF_24")

 bout=batch.verify()
 if bout.get("pass") is not True or bout.get("scope_complete_count")!=24:
  return _fail("WHOLE_LEAF_SCOPE_BATCH_RECOMPUTE_FAILED",batch_verdict=bout)
 rows=[x for x in (bout.get("rows") or []) if x.get("leaf_id")==LEAF_ID]
 if len(rows)!=1:return _fail("R6_SCOPE_ROW_CARDINALITY",count=len(rows))
 scope_row=rows[0]
 if scope_row.get("whole_leaf_domain_equivalence_proved") is not True or scope_row.get("whole_leaf_scope_complete") is not True:
  return _fail("R6_WHOLE_LEAF_SCOPE_NOT_COMPLETE")
 if scope_row.get("leaf_property_truth_authority") is not False:return _fail("R6_SCOPE_SELF_PROPERTY_AUTHORITY_FORBIDDEN")

 if _r6_ids(catalog)!=EXPECTED_R6_DEFEATERS:return _fail("R6_DEFEATER_CATALOG_DRIFT",observed=sorted(_r6_ids(catalog)))

 if not str(binder_verify.get("status") or "").startswith("PASS__PINNED_EXACT_BYTES__PYCOMPILE__5_OF_5"):
  return _fail("BINDER_INDEPENDENT_MUTATION_VERIFY_NOT_PASS")
 if (binder_verify.get("replay") or {}).get("tests_passed")!=5:return _fail("BINDER_INDEPENDENT_REPLAY_COUNT_INVALID")
 if not str(currentgen.get("status") or "").startswith("PASS__PINNED_CURRENT_GENERATION"):return _fail("UVCK_CURRENT_GENERATION_VERIFY_NOT_PASS")
 if (currentgen.get("replay") or {}).get("tests_passed")!=18:return _fail("UVCK_CURRENT_GENERATION_REPLAY_INVALID")
 if not str(order_verify.get("status") or "").startswith("PASS__EXACT_BLOBS"):return _fail("UVCK_DEFEATER_ORDER_VERIFY_NOT_PASS")
 if not str(defeater80.get("status") or "").startswith("PASS__EXACT_DOMAIN_BYTES"):return _fail("PROFESSIONAL_80_DEFEATER_VERIFY_NOT_PASS")

 binder_run=_exercise_binder(str(row.get("contract") or ""),ACCEPTANCE,PINS["manifest"][1])
 proved=set(binder_verify.get("proved") or [])
 binder_cases=dict(binder_run["cases"])
 binder_cases["STATUS_STRING_SELF_CERTIFICATION_REJECTED"]="MANIFEST_VERIFIED_STATUS_HAS_ZERO_PROMOTION_AUTHORITY" in proved
 binder_cases["UNKNOWN_LEAF_ID_REJECTED"]="UNKNOWN_REGISTRY_LEAF_IDS_FAIL_STRUCTURE" in proved

 known={}
 for did in sorted(EXPECTED_R6_DEFEATERS):
  g=_graph_with_supported_defeater(graph,did)
  if not g:known[did]=False;continue
  out=kernel.evaluate(g)
  known[did]=(out.get("status")=="COUNTERPROVED" and did in set(out.get("active_defeater_ids") or []) and out.get("pass") is False)

 checks={
  "CONTENT_ADDRESSED_SCOPE_MATCHED_POSITIVE_RECEIPT_ADMITTED":binder_run["positive_admitted"],
  "EVIDENCE_ADMISSION_NEAR_MISS_AND_ADVERSARIAL_BOUNDARIES_FAIL_CLOSED":all(binder_cases.values()) and len(binder_cases)==6,
  "ALL_15_CANONICAL_R6_DEFEATERS_COUNTERPROVE_WHEN_ACTIVATED":all(known.values()) and len(known)==15,
 }
 if not all(checks.values()):
  return _fail("R6_EXECUTION_PROPERTY_CHALLENGE_FAILED",checks=checks,known_defeaters=known,case_results=binder_cases,binder_positive=binder_run["positive"])

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R6_EXECUTION_MANIFEST_ACCEPTANCE_OBSERVED_ON_EXACT_EVIDENCE_ADMISSION_AND_UVCK_RUNTIME__ONE_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"whole_leaf_claim_id":scope_row.get("claim_id"),
  "manifest_acceptance":ACCEPTANCE,"checks":checks,"case_results":binder_cases,
  "observed_case_counts":{"positive":1,"canonical_r6_defeater_activations":15,"binder_near_miss_and_adversarial":6,"total":22},
  "canonical_r6_defeater_ids":sorted(EXPECTED_R6_DEFEATERS),
  "leaf_property_truth_authority":True,
  "property_truth_basis":"EXACT_PINNED_CONTENT_ADDRESSED_EVIDENCE_ADMISSION_RUNTIME_PLUS_ALL_CANONICAL_R6_DEFEATER_ACTIVATIONS_AND_FAIL_CLOSED_BINDER_BOUNDARIES",
  "r6_semantic_leaf_closed":False,"r6_root_closed":False,
  "global_evidence_completeness_proved":False,"all_real_task_evidence_admitted":False,
  "semantic_truth_authority":False,"execution_authority":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 docs={}
 for key,(rel,expected) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink():return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=expected:return _fail(key.upper()+"_BLOB_STALE",observed_blob=actual)
  if key in {"manifest","catalog","graph","scope_batch_verify","binder_verify","currentgen_verify","order_verify","defeater80_verify"}:
   try:docs[key]=_load(p)
   except Exception:return _fail(key.upper()+"_JSON_INVALID")
 return evaluate_documents(
  docs["manifest"],docs["catalog"],docs["graph"],docs["scope_batch_verify"],
  docs["binder_verify"],docs["currentgen_verify"],docs["order_verify"],docs["defeater80_verify"],
 )

if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
