"""R12 material-defeater totality route audit.

This adapter does not prove totality. It prevents known bounded evidence from
being laundered into totality and selects the remaining sound proof classes:
claim-specific universal theorem, exact complete universe, exhaustive superset,
or lossless decomposition/generator closure.
"""
from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_R12_MATERIAL_DEFEATER_TOTALITY_ROUTE_AUDIT_V1"
R12_PATH="canonical/governance/PROFESSIONAL_R12_SEMANTIC_CC_R3_TRUTH_RECONCILIATION_20261010_V3.json"
R12_BLOB="56a5f85e6133661dd7afbc8fc5041ad799f0736f"
CATALOG_PATH="canonical/governance/PROFESSIONAL_QUALITY_DOMAIN_DEFEATER_CATALOG_20261009_V2.json"
CATALOG_BLOB="8b92e5cf76f767054f55414b87014e03d43460b8"
ROOT_THEOREM_PATH="canonical/governance/COVERAGE_COMPLETENESS_ROOT_THEOREM_V1.json"
ROOT_THEOREM_BLOB="3d2c89502d94c045d04af04db4cdecc509a08dd8"
OBLIGATION="ALL_ROOT_RELEVANT_MATERIAL_DEFEATERS_RESOLVED_OR_PROVED_DECISION_NULL_BEFORE_POSITIVE_CERTIFICATION"

def _blob(p:Path)->str:
 raw=p.read_bytes();return sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw).hexdigest()
def _fail(reason:str,**extra:Any)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
 "material_defeater_totality_proved":False,"cc_r3_terminal_closure_proved":False,
 "semantic_property_truth_authority":False,"r4_proof_realization_authority":False,
 "new_primitive_required":False,"terminal_authority":False,"terminal_credit_delta":0,**extra}
def _load_bound(root:Path,rel:str,sha:str,label:str):
 p=root/rel
 if not p.is_file() or p.is_symlink():raise ValueError(label+"_MISSING")
 if _blob(p)!=sha:raise ValueError(label+"_BLOB_STALE")
 x=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(x,dict):raise ValueError(label+"_NOT_OBJECT")
 return x

def evaluate_documents(r12:Mapping[str,Any],catalog:Mapping[str,Any],theorem:Mapping[str,Any])->dict[str,Any]:
 stronger=r12.get("stronger_target_residual") or {}
 if stronger.get("obligation")!=OBLIGATION or stronger.get("state")!="OPEN":
  return _fail("R12_STRONGER_RESIDUAL_IDENTITY_DRIFT")
 d=r12.get("derived") or {}
 if d.get("all_eight_root_contract_clauses_verified") is not True or d.get("verified_clause_count")!=8:
  return _fail("R12_EIGHT_CLAUSE_BASE_NOT_VERIFIED")
 if d.get("cc_r3_terminal_closure_proved") is not False:
  return _fail("R12_CC_R3_ALREADY_OR_FALSELY_CLOSED")
 nonclaims=set(catalog.get("hard_nonclaims") or [])
 if "NO_CLAIM_DEFEATER_SET_COMPLETE" not in nonclaims:
  return _fail("CATALOG_COMPLETENESS_BOUNDARY_MISSING")
 if catalog.get("closure_state")!="OPEN":
  return _fail("CATALOG_CLOSURE_STATE_DRIFT")
 newe=theorem.get("new_e_admission") or {}
 if newe.get("default")!="REJECT_AS_PEER_ARCHITECTURE":
  return _fail("NEW_E_DEFAULT_DRIFT")
 hard=set(theorem.get("hard_rules") or [])
 for rule in ("UNKNOWN_NEVER_EQUALS_PROVED","NO_NEW_ROOT_FROM_A_NAMED_CATEGORY_ALONE"):
  if rule not in hard:return _fail("ROOT_THEOREM_FAIL_CLOSED_RULE_MISSING:"+rule)

 routes=[
  {"route":"UNIVERSAL_FORMAL_SCOPE_PROOF","state":"OPEN",
   "reason":"NO_CLAIM_SPECIFIC_UNIVERSAL_THEOREM_FOR_MATERIAL_DEFEATER_TOTALITY_IS_BOUND_BY_THE_PINNED_EVIDENCE"},
  {"route":"EXACT_COMPLETE_TARGET_CASE_UNIVERSE","state":"REJECT_CURRENT_EVIDENCE",
   "reason":"DEFEATER_CATALOG_EXPLICITLY_DENIES_SET_COMPLETENESS"},
  {"route":"EXHAUSTIVE_FINITE_SUPERSET","state":"REJECT_CURRENT_EVIDENCE",
   "reason":"DEFEATER_CATALOG_EXPLICITLY_DENIES_EXHAUSTIVE_DOMAIN_ADVERSARIAL_CLOSURE"},
  {"route":"LOSSLESS_DECOMPOSITION_OR_GENERATOR_CLOSURE","state":"OPEN",
   "reason":"EIGHT_OF_EIGHT_CONTRACT_CLAUSES_ARE_VERIFIED_BUT_STRONGER_TOTALITY_COMPLEMENT_REMAINS_OPEN"},
 ]
 return {"schema":SCHEMA,"pass":True,
  "status":"PASS__R12_TOTALITY_ROUTE_AUDIT__NO_CURRENT_TOTALITY_CERTIFICATE__UNIVERSAL_OR_GENERATOR_CLOSURE_ROUTE_REMAINS",
  "obligation":OBLIGATION,"routes":routes,
  "material_defeater_totality_proved":False,"cc_r3_terminal_closure_proved":False,
  "semantic_property_truth_authority":False,"r4_proof_realization_authority":False,
  "known_defeater_catalog_is_totality_authority":False,
  "eight_clause_reconciliation_is_totality_authority":False,
  "new_primitive_required":False,
  "exact_next":[
   "TRY_CLAIM_SPECIFIC_UNIVERSAL_FORMAL_PROOF_FROM_EXISTING_FOUR_ROOT_SEMANTICS",
   "IN_PARALLEL_ADAPT_EXISTING_GENERATOR_CLOSURE_OR_PROVEN_SUPERSET_MACHINERY_TO_THE_MATERIAL_DEFEATER_COMPLEMENT",
   "IF_A_CONSTRUCTIVE_UNCOVERED_FALSE_CERTIFICATION_PATH_APPEARS__MAP_IT_TO_EXISTING_ROOT_OR_ADMIT_ONLY_A_ROOT_REPAIR_CANDIDATE",
  ],
  "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}

def verify(*,repo_root:str|Path|None=None)->dict[str,Any]:
 root=Path(repo_root).resolve() if repo_root else ROOT
 try:
  return evaluate_documents(
   _load_bound(root,R12_PATH,R12_BLOB,"R12"),
   _load_bound(root,CATALOG_PATH,CATALOG_BLOB,"CATALOG"),
   _load_bound(root,ROOT_THEOREM_PATH,ROOT_THEOREM_BLOB,"ROOT_THEOREM"))
 except Exception as exc:return _fail("CURRENT_INPUT_RESOLUTION_FAILED",detail=type(exc).__name__+":"+str(exc))
if __name__=="__main__":print(json.dumps(verify(),indent=2,sort_keys=True))
