"""R6 execution-leaf property-truth verifier V1.

Discharges only PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::EXECUTION by replaying
positive, near-miss, and adversarial cases on the exact UVCK V2 runtime bytes.
Unknown-defeater completeness and the R6 semantic leaf remain open.
"""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime import assurance_closure_compiler_v1 as uvck

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R6_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
LEAF_ID="PQ::R6_EVIDENCE_GROUNDING_DEPENDENCE::EXECUTION"
ROOT_ID="R6_EVIDENCE_GROUNDING_DEPENDENCE"
OBLIGATION_ID="O_R6_EVIDENCE_GROUNDING_DEPENDENCE"
ACCEPTANCE="RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"

PINS={
 "manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
 "graph":("canonical/governance/PROFESSIONAL_QUALITY_ASSURANCE_GRAPH_20261009_V2.json","03530e29d70206b46b690b33a04c66765ff86ad7"),
 "catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
 "scope_batch_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
 "r6_binding_verify":("canonical/verification/PROFESSIONAL_QUALITY_R6_V7_ROOT_SUBJECT_BINDING_VERIFY_20261010_V1.json","abb4a251345e2701dc42578a1695f5e59f4bb665"),
 "uvck_runtime":("canonical/runtime/assurance_closure_compiler_v1.py","b4274a48edbe626a9ae9fd33da2f2227ca4dd5e8"),
}

def _blob(path:Path)->str:
 raw=path.read_bytes(); return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _load(path:Path)->dict[str,Any]:
 value=json.loads(path.read_text(encoding="utf-8"))
 if not isinstance(value,dict): raise ValueError("NOT_OBJECT")
 return value

def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {
  "schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"leaf_property_truth_authority":False,
  "r6_semantic_leaf_closed":False,"r6_root_closed":False,
  "unknown_defeater_completeness_proved":False,"quality_authority":False,
  "acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,**extra,
 }

def _manifest_row(manifest:Mapping[str,Any])->Mapping[str,Any]|None:
 for row in manifest.get("roots") or []:
  if isinstance(row,Mapping) and row.get("root_id")==ROOT_ID: return row
 return None

def _catalog_r6(catalog:Mapping[str,Any])->set[str]:
 return {
  str(row.get("id")) for row in (catalog.get("challenges") or [])
  if isinstance(row,Mapping) and ROOT_ID in set(row.get("root_ids") or [])
 }

def _nodes(graph:Mapping[str,Any])->dict[str,dict[str,Any]]:
 return {str(x.get("id")):x for x in (graph.get("nodes") or []) if isinstance(x,dict) and x.get("id")}

def _positive_graph(graph:Mapping[str,Any], r6_defeaters:set[str])->dict[str,Any]:
 g=deepcopy(dict(graph)); g["root_ids"]=[ROOT_ID]
 nodes=_nodes(g)
 obligation=nodes.get(OBLIGATION_ID)
 if not obligation: raise ValueError("R6_OBLIGATION_MISSING")
 obligation["type"]="EVIDENCE"; obligation["status"]="SUPPORTED"; obligation["authoritative_leaf"]=True
 obligation["depends_on"]=[]; obligation["defeated_by"]=[]
 for did in r6_defeaters:
  node=nodes.get(did)
  if not node: raise ValueError("R6_DEFEATER_MISSING:"+did)
  node["status"]="PROVEN_IRRELEVANT"
 return g

def evaluate_documents(
 manifest:Mapping[str,Any],graph:Mapping[str,Any],catalog:Mapping[str,Any],
 scope_batch_verify:Mapping[str,Any],r6_binding_verify:Mapping[str,Any],
)->dict[str,Any]:
 row=_manifest_row(manifest)
 if not row: return _fail("R6_MANIFEST_ROOT_MISSING")
 leaf=row.get("execution_leaf") or {}
 if leaf.get("id")!=LEAF_ID or leaf.get("acceptance")!=ACCEPTANCE:
  return _fail("R6_EXECUTION_ACCEPTANCE_DRIFT")
 nodes=_nodes(graph); root=nodes.get(ROOT_ID)
 if not root or root.get("contract")!=row.get("contract"):
  return _fail("R6_ROOT_CONTRACT_DRIFT")
 catalog_ids=_catalog_r6(catalog)
 graph_ids=set(root.get("defeated_by") or [])
 if catalog_ids!=graph_ids or len(catalog_ids)!=15:
  return _fail("R6_DEFEATER_BINDING_DRIFT",catalog_count=len(catalog_ids),graph_count=len(graph_ids))
 if not str(scope_batch_verify.get("status") or "").startswith("PASS__"):
  return _fail("R6_SCOPE_BATCH_NOT_PASS")
 replay=scope_batch_verify.get("independent_replay") or {}
 if replay.get("scope_complete_count")!=24 or replay.get("domain_equivalence_pass_count")!=24:
  return _fail("R6_SCOPE_BATCH_INCOMPLETE")
 if not str(r6_binding_verify.get("status") or "").startswith("PASS__"):
  return _fail("R6_SUBJECT_BINDING_NOT_PASS")
 if r6_binding_verify.get("root_id")!=ROOT_ID:
  return _fail("R6_SUBJECT_BINDING_IDENTITY_DRIFT")

 try: positive_graph=_positive_graph(graph,catalog_ids)
 except ValueError as exc: return _fail(str(exc))
 positive=uvck.evaluate(positive_graph)
 positive_ok=(
  positive.get("closure_gates",{}).get("representation_closure") is True
  and positive.get("closure_gates",{}).get("proof_closure") is True
  and positive.get("root_closed",{}).get(ROOT_ID) is True
  and positive.get("status")=="OPEN__EXECUTION_CLOSURE_REQUIRED"
  and positive.get("pass") is False
 )
 adversarial={}
 near_miss={}
 for did in sorted(catalog_ids):
  g=deepcopy(positive_graph); n=_nodes(g); n[did]["status"]="SUPPORTED"
  out=uvck.evaluate(g)
  adversarial[did]=(
   out.get("status")=="COUNTERPROVED"
   and did in set(out.get("active_defeater_ids") or [])
   and out.get("root_closed",{}).get(ROOT_ID) is False
  )
  g=deepcopy(positive_graph); n=_nodes(g); n[did]["status"]="OPEN"
  out=uvck.evaluate(g)
  near_miss[did]=(
   out.get("status")=="OPEN__ASSURANCE_RESIDUAL"
   and did in set(out.get("unresolved_defeater_ids") or [])
   and out.get("root_closed",{}).get(ROOT_ID) is False
  )

 checks={
  "POSITIVE_R6_PATH_REACHES_PROOF_CLOSURE":positive_ok,
  "ALL_15_R6_KNOWN_DEFEATERS_COUNTERPROVE":all(adversarial.values()) and len(adversarial)==15,
  "ALL_15_R6_OPEN_DEFEATERS_REMAIN_NEAR_MISS_RESIDUALS":all(near_miss.values()) and len(near_miss)==15,
 }
 if not all(checks.values()):
  return _fail("R6_EXECUTION_PROPERTY_CHALLENGE_FAILED",checks=checks,adversarial=adversarial,near_miss=near_miss)
 return {
  "schema":SCHEMA,"pass":True,
  "status":"PASS__R6_EXECUTION_MANIFEST_ACCEPTANCE_OBSERVED_ON_EXACT_UVCK_RUNTIME__ONE_LEAF_PROPERTY_TRUTH_ONLY",
  "leaf_id":LEAF_ID,"root_id":ROOT_ID,"manifest_acceptance":ACCEPTANCE,
  "checks":checks,"observed_case_counts":{"positive":1,"known_adversarial":15,"near_miss":15,"total":31},
  "leaf_property_truth_authority":True,
  "property_truth_basis":"EXACT_UVCK_V2_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_R6_CASE_REPLAY",
  "unknown_defeater_completeness_proved":False,
  "r6_semantic_leaf_closed":False,"r6_root_closed":False,
  "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0,
 }

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root is not None else ROOT
 docs={}
 for key,(rel,sha) in PINS.items():
  p=root/rel
  if not p.is_file() or p.is_symlink(): return _fail(key.upper()+"_MISSING")
  actual=_blob(p)
  if actual!=sha: return _fail(key.upper()+"_BLOB_STALE",observed_blob=actual)
  if key!="uvck_runtime":
   try: docs[key]=_load(p)
   except Exception: return _fail(key.upper()+"_JSON_INVALID")
 return evaluate_documents(docs["manifest"],docs["graph"],docs["catalog"],docs["scope_batch_verify"],docs["r6_binding_verify"])

if __name__=="__main__":
 print(json.dumps(verify(),indent=2,sort_keys=True))
