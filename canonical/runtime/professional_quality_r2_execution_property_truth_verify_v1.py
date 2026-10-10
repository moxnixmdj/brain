"""R2 candidate-search execution leaf property-truth verifier V1.

Proves only the execution acceptance of PQ::R2_CANDIDATE_SEARCH::EXECUTION on
current retrieval bytes. It does not prove open-world search completeness,
semantic closure, root closure, or professional-quality sufficiency.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import residual_witness_retrieval_compiler_v1 as core
from canonical.runtime import retrieval_verified_route_portfolio_v1 as portfolio

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R2_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
LEAF_ID="PQ::R2_CANDIDATE_SEARCH::EXECUTION"
ROOT_ID="R2_CANDIDATE_SEARCH"
ACCEPTANCE="RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
EXPECTED={"C04_BEST_OF_MEDIOCRE","C05_SEARCH_LINEAGE_FIXATION","C06_NOVELTY_PENALTY"}
PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "scope_batch_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "retrieval_authority":("canonical/governance/GLOBAL_RETRIEVAL_CURRENT_AUTHORITY_V1.json","55b1d411561f720fcd9d66c127cecd63ef0b5f5e"),
 "v19_verify":("canonical/verification/RETRIEVAL_V19_ROUTE_PORTFOLIO_PUBLIC_RUNNER_VERIFICATION_20261004_V1.json","4604a93bf220edcf9691ad9cb059df38f8674c48"),
 "retrieval_core":("canonical/runtime/residual_witness_retrieval_compiler_v1.py","9daa8d590f3356b3fc51eccf75c56cbf515239e4"),
 "route_portfolio":("canonical/runtime/retrieval_verified_route_portfolio_v1.py","855a6cba59fff8c079f61212acadc254c4e9e736"),
}

def _blob(path:Path)->str:
 raw=path.read_bytes()
 return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"leaf_property_truth_authority":False,
  "search_completeness_proved":False,"r2_semantic_leaf_closed":False,
  "r2_root_closed":False,"quality_authority":False,"acceptance_authority":False,
  "promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,
  **extra,
 }

def _manifest_leaf(manifest:Mapping[str,Any])->Mapping[str,Any]|None:
 for row in manifest.get("roots") or []:
  if isinstance(row,Mapping) and row.get("root_id")==ROOT_ID:
   leaf=row.get("execution_leaf")
   if isinstance(leaf,Mapping) and leaf.get("id")==LEAF_ID:return leaf
 return None

def _catalog_ids(catalog:Mapping[str,Any])->set[str]:
 return {
  row["id"] for row in catalog.get("challenges") or []
  if isinstance(row,Mapping) and ROOT_ID in (row.get("root_ids") or [])
  and isinstance(row.get("id"),str)
 }

def _residual()->dict[str,Any]:
 return {
  "residual_id":"R2_PROPERTY_SEARCH_FIXTURE",
  "effect":"decode legacy binary telemetry envelope with checksum and framing",
  "required_capabilities":["telemetry.decode","checksum.verify"],
  "aliases":["frame decoder","packet envelope reader"],
  "language_variants":{"ar":["فك ترميز حزمة القياس عن بعد"],"ja":["テレメトリ フレーム デコーダ"]},
  "observables":{
   "api_symbols":["decode_frame","verify_checksum"],
   "file_formats":[".tlm"],
   "error_strings":["checksum mismatch"],
  },
 }

def _exercise_current_runtime()->tuple[dict[str,bool],dict[str,Any]]:
 program=core.compile_residual(_residual())
 bases={str(x.get("basis")) for x in program.get("query_lattice") or []}
 positive=(
  program.get("status")=="COMPILED"
  and len(program.get("surfaces") or [])==12
  and len(program.get("query_lattice") or [])>=8
  and {"ALIAS","LANGUAGE_VARIANT","OBSERVABLE_API_SYMBOLS","BEHAVIOR_PLUS_OBSERVABLE"}.issubset(bases)
  and program.get("model_dependency_count")==0
  and program.get("incremental_spend_usd")==0
 )

 state=core.initial_state(program)
 for cell in list(state.get("cells") or []):
  state=core.update_cell(
   state,query_id=cell["query_id"],surface=cell["surface"],
   cell_state="QUERIED_NO_CANDIDATE",
  )
 miss=core.terminal_status(state)
 no_false_negative=(miss.get("status")=="UNKNOWN_CONTINUE_RETRIEVAL" and miss.get("stop") is False and miss.get("nonexistence_claim_authorized") is False)

 candidate_only_guard=False
 try:
  core.add_verified_witness(
   core.initial_state(program),witness_id="novel-unfamiliar-candidate",
   residual_id=program["residual_id"],source_surface="REPOSITORY_METADATA",
   independent_receipt="receipt://should-not-be-enough",
  )
 except ValueError as exc:
  candidate_only_guard=str(exc)=="CANDIDATE_ONLY_SURFACE_CANNOT_VERIFY"

 action={
  "action_id":"A1","source_id":"MAVEN_CENTRAL",
  "query":"decode legacy telemetry binary envelope with checksum support",
  "language_variants":["telemetry frame decoder"],
 }
 sources=[{"source_id":"MAVEN_CENTRAL","source_class":"MAVEN","script":"ARABIC"}]
 p1=portfolio.compile_portfolio([action],sources)
 adversarial=dict(action);adversarial["answer_key_identity"]="hidden-perfect-winner"
 p2=portfolio.compile_portfolio([adversarial],sources)
 strategies={x.get("strategy_id") for x in p1.get("actions") or []}
 required_routes={
  "MULTI_QUERY_DECOMPOSITION","CROSS_LANGUAGE_TECHNICAL_BRIDGE",
  "REPOSITORY_MANIFEST_BRIDGE","DEEP_MANIFEST_INSPECTION",
  "BEHAVIOR_CONTEXT_CANDIDATE_GRAPH_SNOWBALL","VERSION_LINE_HISTORY_IDENTITY_BRIDGE",
 }
 diversified=(
  required_routes.issubset(strategies)
  and p1.get("candidate_authority")=="CANDIDATE_ONLY"
  and p1.get("answer_key_identity_permitted") is False
  and p1.get("open_world_nonexistence_claim_authorized") is False
 )
 answer_blind=(p1==p2)
 checks={
  "POSITIVE_MULTI_QUERY_MULTI_SURFACE_SEARCH_COMPILES":positive,
  "C04_EMPTY_OPEN_WORLD_SEARCH_REMAINS_UNKNOWN":no_false_negative,
  "C05_VERIFIED_RECOVERY_PORTFOLIO_ESCAPES_SINGLE_LINEAGE":diversified,
  "C06_ANSWER_KEY_OR_NOVELTY_IDENTITY_CANNOT_BIAS_ROUTE_GENERATION":answer_blind,
  "CANDIDATE_ONLY_SURFACE_CANNOT_SELF_VERIFY":candidate_only_guard,
 }
 detail={
  "query_count":len(program.get("query_lattice") or []),
  "surface_count":len(program.get("surfaces") or []),
  "query_bases":sorted(bases),
  "recovery_strategies":sorted(str(x) for x in strategies if x),
  "miss_terminal":miss,
 }
 return checks,detail

def evaluate_documents(manifest,catalog,scope_verify,retrieval_authority,v19_verify):
 leaf=_manifest_leaf(manifest)
 if leaf is None:return _fail("R2_EXECUTION_LEAF_NOT_IN_MANIFEST")
 if leaf.get("acceptance")!=ACCEPTANCE:return _fail("R2_EXECUTION_ACCEPTANCE_DRIFT")
 replay=scope_verify.get("independent_replay") or {}
 if replay.get("leaf_count")!=24 or replay.get("scope_complete_count")!=24 or replay.get("property_truth_count")!=0:
  return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_24_OF_24_ZERO_PROPERTY_TRUTH")
 if _catalog_ids(catalog)!=EXPECTED:
  return _fail("R2_DEFEATER_CATALOG_DRIFT",observed=sorted(_catalog_ids(catalog)))
 v19=retrieval_authority.get("v19_verified_route_portfolio") or {}
 if v19.get("mandatory_for_authorized_global_retrieval_plan_compilation") is not True or v19.get("answer_key_identity_permitted") is not False:
  return _fail("CURRENT_RETRIEVAL_V19_AUTHORITY_NOT_BOUND")
 verified=v19_verify.get("verified") or {}
 required_verified={
  "multi_query_decomposition_generic","cross_language_technical_bridge_generic",
  "repository_manifest_bridge_generic","deep_manifest_inspection_generic",
  "behavior_context_candidate_graph_snowball_generic",
  "version_line_history_identity_bridge_generic",
  "answer_key_identity_forbidden_from_route_generation",
  "open_world_unknown_preserved",
 }
 if not all(verified.get(k) is True for k in required_verified):
  return _fail("V19_INDEPENDENT_VERIFICATION_INCOMPLETE")
 checks,detail=_exercise_current_runtime()
 if not all(checks.values()):
  return _fail("R2_EXECUTION_PROPERTY_CHALLENGE_FAILED",checks=checks,detail=detail)
 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R2_CANDIDATE_SEARCH_EXECUTION_ACCEPTANCE_OBSERVED_ON_EXACT_RETRIEVAL_RUNTIME__ONE_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"manifest_acceptance":ACCEPTANCE,
  "checks":checks,"observed_case_detail":detail,
  "canonical_r2_defeater_ids":sorted(EXPECTED),
  "leaf_property_truth_authority":True,
  "property_truth_basis":"CURRENT_MULTI_QUERY_MULTI_SURFACE_RETRIEVAL_PLUS_VERIFIED_V19_RECOVERY_PORTFOLIO_AND_FAIL_CLOSED_OPEN_WORLD_MISS",
  "search_completeness_proved":False,"open_world_completeness_proved":False,
  "r2_semantic_leaf_closed":False,"r2_root_closed":False,
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
  if key in {"manifest","catalog","scope_batch_verify","retrieval_authority","v19_verify"}:
   try:docs[key]=json.loads(p.read_text(encoding="utf-8"))
   except Exception:return _fail(key.upper()+"_JSON_INVALID")
 return evaluate_documents(
  docs["manifest"],docs["catalog"],docs["scope_batch_verify"],
  docs["retrieval_authority"],docs["v19_verify"],
 )
