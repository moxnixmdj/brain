"""R12 execution-leaf property-truth verifier V1.

Discharges only the manifest execution acceptance for
PQ::R12_META_COMPOSITION_CLOSURE::EXECUTION by exercising the exact current
UVCK/meta-assurance kernel over positive, near-miss, and adversarial cases.
No R12 semantic/root/global quality authority is granted.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import assurance_closure_compiler_v1 as kernel
from canonical.runtime import professional_quality_whole_leaf_scope_batch_v1 as batch

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R12_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
LEAF_ID="PQ::R12_META_COMPOSITION_CLOSURE::EXECUTION"
ROOT_ID="R12_META_COMPOSITION_CLOSURE"
ACCEPTANCE=(
 "RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_"
 "AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
)
EXPECTED_R12_DEFEATERS={
 "C16_INVALID_CHALLENGE_GENERATOR","C27_HIDDEN_PREMISE_INFERENCE",
 "C60_ROOT_CONJUNCTION_FAILURE","C61_HIDDEN_ASSUMPTION_CYCLE",
 "C62_UNSOUND_ABSTRACTION","C63_PROOF_SEARCH_FALSE_NEGATIVE",
 "C64_META_CONTROLLER_FALSE_IRRELEVANCE","C65_UNMAPPED_DEFEATER",
 "C66_ALWAYS_ABSTAIN_VACUITY","C71_JOINT_ASSURANCE_MULTIPLICITY",
 "C74_EXECUTION_FAILURE_FAIL_OPEN","C75_STALE_CERT_AFTER_DEPENDENCY_CHANGE",
 "C78_CONTEXT_TRUNCATION_OBLIGATION_DROP","C79_FALLBACK_EVALUATOR_SCOPE_WEAKENING",
}
PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "graph":("canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json","03530e29d70206b46b690b33a04c66765ff86ad7"),
 "kernel":("canonical/runtime/assurance_closure_compiler_v1.py","b4274a48edbe626a9ae9fd33da2f2227ca4dd5e8"),
 "scope_batch_runtime":("canonical/runtime/professional_quality_whole_leaf_scope_batch_v1.py","82ab66c7852fc327821b23ff80dd46de3b81525c"),
 "scope_batch_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "currentgen_verify":("canonical/verification/UVCK_V2_CURRENT_GENERATION_INDEPENDENT_REPLAY_VERIFY_20261009_V1.json","81f7f070233b6aa1c4b491949a4c3e7aedfafd10"),
 "order_verify":("canonical/verification/UVCK_V2_DEFEATER_ORDER_VERIFY_20261009_V1.json","1c3428b10a1205e928a87f41a7c16a8a3d17b7ca"),
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
  "r12_semantic_leaf_closed":False,"r12_root_closed":False,
  "semantic_truth_authority":False,"execution_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
  "terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def _manifest_leaf(manifest:Mapping[str,Any])->Mapping[str,Any]|None:
 for row in manifest.get("roots") or []:
  if isinstance(row,Mapping) and row.get("root_id")==ROOT_ID:
   leaf=row.get("execution_leaf")
   if isinstance(leaf,Mapping) and leaf.get("id")==LEAF_ID:return leaf
 return None

def _r12_ids(catalog:Mapping[str,Any])->set[str]:
 out=set()
 for row in catalog.get("challenges") or []:
  if isinstance(row,Mapping) and ROOT_ID in (row.get("root_ids") or []):
   cid=row.get("id")
   if isinstance(cid,str):out.add(cid)
 return out

def _positive_graph()->dict[str,Any]:
 return {
  "schema":kernel.GRAPH_SCHEMA,"root_ids":["r12:claim"],
  "nodes":[
   {"id":"r12:evidence","type":"EVIDENCE","status":"SUPPORTED","authoritative_leaf":True},
   {"id":"r12:claim","type":"CLAIM","status":"SUPPORTED","depends_on":["r12:evidence"],"defeated_by":[]},
  ],
 }

def _open_defeater_graph()->dict[str,Any]:
 return {
  "schema":kernel.GRAPH_SCHEMA,"root_ids":["r12:claim"],
  "nodes":[
   {"id":"r12:evidence","type":"EVIDENCE","status":"SUPPORTED","authoritative_leaf":True},
   {"id":"r12:defeater","type":"DEFEATER","status":"OPEN","depends_on":[],"defeated_by":[]},
   {"id":"r12:claim","type":"CLAIM","status":"SUPPORTED","depends_on":["r12:evidence"],"defeated_by":["r12:defeater"]},
  ],
 }

def evaluate_documents(
 manifest:Mapping[str,Any],catalog:Mapping[str,Any],graph:Mapping[str,Any],
 scope_verify:Mapping[str,Any],currentgen:Mapping[str,Any],order_verify:Mapping[str,Any],
)->dict[str,Any]:
 leaf=_manifest_leaf(manifest)
 if leaf is None:return _fail("R12_EXECUTION_LEAF_NOT_IN_MANIFEST")
 if leaf.get("acceptance")!=ACCEPTANCE:
  return _fail("R12_EXECUTION_ACCEPTANCE_DRIFT",observed_acceptance=leaf.get("acceptance"))

 if not str(scope_verify.get("status") or "").startswith("PASS__INDEPENDENT_SPRITE"):
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_INDEPENDENT_PASS")
 sr=scope_verify.get("independent_replay") or {}
 if sr.get("leaf_count")!=24 or sr.get("domain_equivalence_pass_count")!=24 or sr.get("scope_complete_count")!=24:
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_24_OF_24")
 if sr.get("property_truth_count")!=0:return _fail("WHOLE_LEAF_SCOPE_BATCH_PROPERTY_OVERCLAIM")

 bout=batch.verify()
 if bout.get("pass") is not True or bout.get("scope_complete_count")!=24:
  return _fail("WHOLE_LEAF_SCOPE_BATCH_RECOMPUTE_FAILED",batch_verdict=bout)
 rows=[x for x in (bout.get("rows") or []) if x.get("leaf_id")==LEAF_ID]
 if len(rows)!=1:return _fail("R12_SCOPE_ROW_CARDINALITY",count=len(rows))
 scope_row=rows[0]
 if scope_row.get("whole_leaf_domain_equivalence_proved") is not True or scope_row.get("whole_leaf_scope_complete") is not True:
  return _fail("R12_WHOLE_LEAF_SCOPE_NOT_COMPLETE")
 if scope_row.get("leaf_property_truth_authority") is not False:
  return _fail("R12_SCOPE_SELF_PROPERTY_AUTHORITY_FORBIDDEN")

 ids=_r12_ids(catalog)
 if ids!=EXPECTED_R12_DEFEATERS:return _fail("R12_DEFEATER_CATALOG_DRIFT",observed=sorted(ids))

 if not str(currentgen.get("status") or "").startswith("PASS__PINNED_CURRENT_GENERATION"):
  return _fail("UVCK_CURRENT_GENERATION_VERIFY_NOT_PASS")
 if (currentgen.get("replay") or {}).get("tests_passed")!=18:
  return _fail("UVCK_CURRENT_GENERATION_REPLAY_INVALID")
 if not str(order_verify.get("status") or "").startswith("PASS__EXACT_BLOBS"):
  return _fail("UVCK_DEFEATER_ORDER_VERIFY_NOT_PASS")

 structural=kernel.evaluate(_positive_graph())
 structural_ok=(
  structural.get("closure_gates",{}).get("representation_closure") is True
  and structural.get("closure_gates",{}).get("proof_closure") is True
  and structural.get("closure_gates",{}).get("execution_closure") is False
  and structural.get("closure_gates",{}).get("adversarial_closure") is False
  and structural.get("status")=="OPEN__EXECUTION_CLOSURE_REQUIRED"
 )
 controller=kernel.evaluate_controller_result({
  "schema":"R12_PROPERTY_POSITIVE_CONTROLLER_CASE","status":"PASS","pass":True,
  "semantic_acceptance_complete":True,"actual_goal_satisfaction_verified":True,
 })
 controller_ok=(
  controller.get("closure_gates",{}).get("execution_closure") is True
  and controller.get("closure_gates",{}).get("adversarial_closure") is False
  and controller.get("status")=="OPEN__ADVERSARIAL_CLOSURE_REQUIRED"
 )

 known={}
 for did in sorted(EXPECTED_R12_DEFEATERS):
  g=deepcopy(graph)
  nodes={n.get("id"):n for n in g.get("nodes") or [] if isinstance(n,Mapping)}
  if did not in nodes:
   known[did]=False;continue
  nodes[did]["status"]="SUPPORTED"
  out=kernel.evaluate(g)
  known[did]=(
   out.get("status")=="COUNTERPROVED"
   and did in set(out.get("active_defeater_ids") or [])
   and out.get("pass") is False
  )

 cases={}
 out=kernel.evaluate(_open_defeater_graph())
 cases["OPEN_DEFEATER_BLOCKS_CLOSURE"]=(
  out.get("status")=="OPEN__ASSURANCE_RESIDUAL"
  and "r12:defeater" in set(out.get("unresolved_defeater_ids") or [])
 )
 g=_positive_graph();g["nodes"][0]["status"]="STALE";out=kernel.evaluate(g)
 cases["STALE_EVIDENCE_BLOCKS_CLOSURE"]=(
  out.get("pass") is False and "r12:evidence" in set(out.get("stale_ids") or [])
 )
 g=_positive_graph();g["nodes"][1]["depends_on"]=["missing"];out=kernel.evaluate(g)
 cases["DANGLING_REFERENCE_FAILS_CLOSED"]=out.get("reason")=="DANGLING_NODE_REFERENCE"
 g=_positive_graph();g["nodes"][0]["depends_on"]=["r12:claim"];out=kernel.evaluate(g)
 cases["DEPENDENCY_CYCLE_FAILS_CLOSED"]=out.get("reason")=="UNSUPPORTED_DEPENDENCY_CYCLE"
 g=_positive_graph();g["nodes"].append({"id":"alien","type":"UNMODELED_META_MAGIC","status":"OPEN","depends_on":[],"defeated_by":[]});g["nodes"][1]["depends_on"]=["alien"];out=kernel.evaluate(g)
 cases["UNMODELED_PRIMITIVE_FAILS_TO_ARCHITECTURE_GAP"]=(
  out.get("status")=="OPEN__NEW_PRIMITIVE_REPRESENTATION_REQUIRED"
  and out.get("new_primitive_required") is True
 )
 g=_positive_graph();g["nodes"][0].pop("authoritative_leaf");out=kernel.evaluate(g)
 cases["NONAUTHORITATIVE_EVIDENCE_CANNOT_CLOSE"]=(
  out.get("pass") is False and "r12:evidence" in set(out.get("unsupported_leaf_ids") or [])
 )
 g=_positive_graph();g["execution_closure"]=True;g["adversarial_closure"]=True;out=kernel.evaluate(g)
 cases["CALLER_GATE_BOOLEANS_HAVE_ZERO_AUTHORITY"]=(
  out.get("closure_gates",{}).get("execution_closure") is False
  and out.get("closure_gates",{}).get("adversarial_closure") is False
 )
 g=_open_defeater_graph();g["nodes"].insert(2,{"id":"r12:supported","type":"DEFEATER","status":"SUPPORTED","depends_on":[],"defeated_by":[]});g["nodes"][-1]["defeated_by"]=["r12:defeater","r12:supported"];out=kernel.evaluate(g)
 cases["SUPPORTED_DEFEATER_DOMINATES_OPEN_IN_ANY_ORDER"]=(
  out.get("status")=="COUNTERPROVED" and "r12:supported" in set(out.get("active_defeater_ids") or [])
 )

 checks={
  "STRUCTURAL_POSITIVE_REACHES_PROOF_CLOSURE_BUT_NOT_SELF_CERTIFIED_EXECUTION":structural_ok,
  "VERIFIED_CONTROLLER_POSITIVE_REACHES_EXECUTION_BUT_NOT_SELF_CERTIFIED_ADVERSARIAL_CLOSURE":controller_ok,
  "ALL_14_CANONICAL_R12_DEFEATERS_COUNTERPROVE_WHEN_ACTIVATED":all(known.values()) and len(known)==14,
  "META_COMPOSITION_NEAR_MISS_AND_ADVERSARIAL_CASES_FAIL_CLOSED":all(cases.values()) and len(cases)==8,
 }
 if not all(checks.values()):
  return _fail("R12_EXECUTION_PROPERTY_CHALLENGE_FAILED",checks=checks,known_defeaters=known,case_results=cases)

 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R12_EXECUTION_MANIFEST_ACCEPTANCE_OBSERVED_ON_EXACT_UVCK_META_ASSURANCE_RUNTIME__ONE_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"whole_leaf_claim_id":scope_row.get("claim_id"),
  "manifest_acceptance":ACCEPTANCE,"checks":checks,"case_results":cases,
  "observed_case_counts":{"positive":2,"known_adversarial":14,"near_miss_and_structural_adversarial":8,"total":24},
  "canonical_r12_defeater_ids":sorted(EXPECTED_R12_DEFEATERS),
  "leaf_property_truth_authority":True,
  "property_truth_basis":"EXACT_UVCK_RUNTIME_META_COMPOSITION_POSITIVE_PATHS_PLUS_ALL_CANONICAL_R12_DEFEATERS_AND_FAIL_CLOSED_STRUCTURAL_BOUNDARIES",
  "r12_semantic_leaf_closed":False,"r12_root_closed":False,
  "unknown_defeater_completeness_proved":False,"full_main_regression_proved":False,
  "semantic_truth_authority":False,"execution_authority":False,
  "quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,
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
  if key in {"manifest","catalog","graph","scope_batch_verify","currentgen_verify","order_verify"}:
   try:docs[key]=_load(p)
   except Exception:return _fail(key.upper()+"_JSON_INVALID")
 return evaluate_documents(
  docs["manifest"],docs["catalog"],docs["graph"],docs["scope_batch_verify"],
  docs["currentgen_verify"],docs["order_verify"],
 )

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
