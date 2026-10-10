"""R1 execution-leaf property-truth verifier V1. Zero root/global credit."""
from __future__ import annotations
from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any,Mapping
from canonical.runtime import adequacy_basis_structural_completeness_gate_v1 as base
from canonical.runtime import behavioral_contract_extension_gate_v1 as ext

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_R1_EXECUTION_PROPERTY_TRUTH_VERIFY_V1"
LEAF_ID="PQ::R1_TARGET_SPECIFICATION::EXECUTION"
ROOT_ID="R1_TARGET_SPECIFICATION"
ACCEPTANCE="RUN_ROOT_RELEVANT_POSITIVE_NEAR_MISS_AND_ADVERSARIAL_CASES_ON_EXACT_ARTIFACT_OR_RUNTIME_BYTES_AND_BIND_OBSERVED_OUTCOMES_TO_THE_ROOT_CONTRACT"
PINS={
"manifest":("canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json","a7cad32c9fd969ff2c3857bb924c7bd746237ec2"),
"catalog":("canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json","8b92e5cf76f767054f55414b87014e03d43460b8"),
"structural_verify":("canonical/verification/PROFESSIONAL_QUALITY_R1_STRUCTURAL_TARGET_VERIFY_20261010_V1.json","dcee55ba17d15154117100de6aebd34716ad3e3e"),
"scope_batch_verify":("canonical/verification/PROFESSIONAL_QUALITY_WHOLE_LEAF_SCOPE_BATCH_VERIFY_20261010_V1.json","4c2d40a262f18f34bb35f94b59660d60972d45ef"),
"schema":("canonical/governance/BEHAVIORAL_CONTRACT_SCHEMA_V1.json","b173d8fc6e29df3cec3579954bb17c594308b151"),
"registry":("canonical/governance/BEHAVIORAL_CONTRACT_REGISTRY_V2.json","ae250d5bc5da73b23600670be354ffba31e65e53"),
"base_runtime":("canonical/runtime/adequacy_basis_structural_completeness_gate_v1.py","46d01dc945ae7036efc27b6c3740f2e0ac8ff9c0"),
"extension_runtime":("canonical/runtime/behavioral_contract_extension_gate_v1.py","3d8538389af1a3dc46ef74c79b70531511a1f4ec")}
EXPECTED={"C01_GOAL_SUBSTITUTION","C02_DECISION_RELEVANT_SPEC_AMBIGUITY","C03_AGENDA_OMISSION","C72_UNGROUNDED_RISK_TOLERANCE","C78_CONTEXT_TRUNCATION_OBLIGATION_DROP"}

def _blob(p:Path)->str:
 r=p.read_bytes();return sha1(b"blob "+str(len(r)).encode()+b"\0"+r).hexdigest()
def _fail(reason:str,**x:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,"leaf_id":LEAF_ID,"root_id":ROOT_ID,"leaf_property_truth_authority":False,"detection_completeness_proved":False,"r1_semantic_leaf_closed":False,"r1_root_closed":False,"quality_authority":False,"terminal_authority":False,"terminal_credit_delta":0,**x}
def _acceptance(m:Mapping[str,Any]):
 for r in m.get("roots") or []:
  if isinstance(r,Mapping) and r.get("root_id")==ROOT_ID:
   l=r.get("execution_leaf") or {}
   if l.get("id")==LEAF_ID:return l.get("acceptance")
def _catalog(c:Mapping[str,Any])->set[str]:
 return {x["id"] for x in c.get("challenges") or [] if isinstance(x,Mapping) and ROOT_ID in (x.get("root_ids") or []) and isinstance(x.get("id"),str)}

def evaluate_documents(manifest,catalog,scope_batch_verify,structural_verify,contract_schema,registry):
 if _acceptance(manifest)!=ACCEPTANCE:return _fail("R1_EXECUTION_ACCEPTANCE_DRIFT")
 rep=scope_batch_verify.get("independent_replay") or {}
 if rep.get("leaf_count")!=24 or rep.get("scope_complete_count")!=24 or rep.get("property_truth_count")!=0:return _fail("WHOLE_LEAF_SCOPE_BATCH_NOT_24_OF_24_ZERO_PROPERTY_TRUTH")
 sr=structural_verify.get("replay") or {}
 if sr.get("tests_run")!=21 or sr.get("tests_passed")!=21 or sr.get("tests_failed")!=0:return _fail("R1_STRUCTURAL_REPLAY_NOT_21_OF_21")
 if _catalog(catalog)!=EXPECTED:return _fail("R1_DEFEATER_CATALOG_DRIFT")
 rows=registry.get("active_contracted_residuals")
 if not isinstance(rows,list) or len(rows)!=13:return _fail("R1_LIVE_CONTRACT_REGISTRY_NOT_13")
 for r in rows:
  if base.compile_contract_basis(r,contract_schema).get("pass") is not True or ext.compile_extensions(r).get("pass") is not True:
   return _fail("R1_LIVE_CONTRACT_POSITIVE_RECOMPUTE_FAILED")
 required=contract_schema.get("required_behavior_fields") or []
 omission={}
 for f in required:
  r=deepcopy(rows[0]);r.pop(f,None);o=base.compile_contract_basis(r,contract_schema)
  omission[f]=o.get("pass") is False
 r=deepcopy(rows[0]);r["mystery_extension"]={"material":True};o=ext.compile_extensions(r)
 unknown=o.get("pass") is False and "UNCLASSIFIED_EXTENSION_FIELD:mystery_extension" in (o.get("errors") or [])
 checks={"ALL_13_CURRENT_CONTRACTS_RECOMPUTE":True,"ALL_REQUIRED_FIELD_OMISSIONS_FAIL_CLOSED":bool(required) and all(omission.values()),"UNKNOWN_EXTENSION_FAILS_CLOSED":unknown}
 if not all(checks.values()):return _fail("R1_EXECUTION_PROPERTY_CHALLENGE_FAILED",checks=checks)
 return {"schema":SCHEMA,"pass":True,"status":"PASS__R1_EXECUTION_MANIFEST_ACCEPTANCE_OBSERVED__ONE_LEAF_PROPERTY_TRUTH_ONLY","leaf_id":LEAF_ID,"root_id":ROOT_ID,"leaf_property_truth_authority":True,"observed_case_counts":{"positive_live_contracts":13,"required_field_omissions":len(required),"unknown_extension":1,"prior_independent_structural_cases":21,"total":13+len(required)+1+21},"canonical_r1_defeater_ids":sorted(EXPECTED),"detection_completeness_proved":False,"semantic_truth_authority":False,"source_extraction_completeness_proved":False,"policy_adequacy_proved":False,"r1_semantic_leaf_closed":False,"r1_root_closed":False,"quality_authority":False,"acceptance_authority":False,"promotion_authority":False,"terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

def verify(repo_root=None):
 root=Path(repo_root).resolve() if repo_root else ROOT;d={}
 for k,(rel,h) in PINS.items():
  p=root/rel
  if not p.is_file() or _blob(p)!=h:return _fail(k.upper()+"_BLOB_STALE_OR_MISSING")
  if k in {"manifest","catalog","structural_verify","scope_batch_verify","schema","registry"}:d[k]=json.loads(p.read_text())
 return evaluate_documents(d["manifest"],d["catalog"],d["scope_batch_verify"],d["structural_verify"],d["schema"],d["registry"])
