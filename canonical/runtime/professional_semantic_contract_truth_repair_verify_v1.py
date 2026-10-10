"""Professional shared semantic contract truth-repair verifier V1.

Verifies that manifest V2 changes only the shared semantic acceptance contract:
unresolved decision-relevant evidence blocks positive semantic authority and must
fail closed, instead of making universal successful resolution a requirement.

This is a specification repair only. It grants no leaf/property/quality credit.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any,Mapping

SCHEMA="PROJECT_BRAIN_PROFESSIONAL_SEMANTIC_CONTRACT_TRUTH_REPAIR_VERIFY_V1"
OLD_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_V1"
NEW_SCHEMA="PROJECT_BRAIN_PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_V2"
OLD="DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_ROOT_RELEVANT_DEFEATERS_RESOLVED_WITH_TYPED_EVIDENCE"
NEW="FOR_EVERY_ADMISSIBLE_INPUT__POSITIVE_SEMANTIC_AUTHORITY_ONLY_IF_DOMAIN_SPECIFIC_CLAIM_SEMANTICS_GROUNDING_SCOPE_UNCERTAINTY_AND_ALL_DECISION_RELEVANT_ROOT_RELEVANT_DEFEATERS_ARE_RESOLVED_OR_PROVED_DECISION_NULL_WITH_TYPED_EVIDENCE__OTHERWISE_FAIL_CLOSED_NONPOSITIVE_WITH_EXPLICIT_BLOCKING_DIAGNOSTIC__AND_POSITIVE_ROUTE_NONVACUOUS"
OLD_PATH="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261010_V1.json"
NEW_PATH="canonical/governance/PROFESSIONAL_QUALITY_LEAF_BINDING_MANIFEST_20261011_V2.json"

def _fail(reason:str)->dict[str,Any]:
 return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","reason":reason,
 "repaired_semantic_leaf_count":0,"root_contracts_changed":None,"execution_leaves_changed":None,
 "leaf_property_truth_authority":False,"quality_authority":False,"terminal_authority":False,"terminal_credit_delta":0}

def verify(*,root:Path|str|None=None)->dict[str,Any]:
 root=Path(root).resolve() if root is not None else Path(__file__).resolve().parents[2]
 try:
  old=json.loads((root/OLD_PATH).read_text()); new=json.loads((root/NEW_PATH).read_text())
 except Exception as e:return _fail(type(e).__name__)
 if old.get("schema")!=OLD_SCHEMA or new.get("schema")!=NEW_SCHEMA:return _fail("SCHEMA_DRIFT")
 if old.get("root_count")!=12 or new.get("root_count")!=12:return _fail("ROOT_COUNT_DRIFT")
 if old.get("semantic_leaf_count")!=12 or new.get("semantic_leaf_count")!=12:return _fail("SEMANTIC_COUNT_DRIFT")
 if old.get("execution_leaf_count")!=12 or new.get("execution_leaf_count")!=12:return _fail("EXECUTION_COUNT_DRIFT")
 if old.get("total_leaf_count")!=24 or new.get("total_leaf_count")!=24:return _fail("TOTAL_COUNT_DRIFT")
 oldrows=old.get("roots") or []; newrows=new.get("roots") or []
 if len(oldrows)!=12 or len(newrows)!=12:return _fail("ROOT_ROWS_DRIFT")
 repaired=0
 for a,b in zip(oldrows,newrows):
  if a.get("root_id")!=b.get("root_id"):return _fail("ROOT_ID_DRIFT")
  if a.get("contract")!=b.get("contract"):return _fail("ROOT_CONTRACT_CHANGED:"+str(a.get("root_id")))
  if a.get("execution_leaf")!=b.get("execution_leaf"):return _fail("EXECUTION_LEAF_CHANGED:"+str(a.get("root_id")))
  sa=a.get("semantic_leaf") or {}; sb=b.get("semantic_leaf") or {}
  for k in ("id","status","obligation"):
   if sa.get(k)!=sb.get(k):return _fail("SEMANTIC_NONACCEPTANCE_DRIFT:"+str(a.get("root_id"))+":"+k)
  if sa.get("acceptance")!=OLD:return _fail("PREDECESSOR_ACCEPTANCE_DRIFT:"+str(a.get("root_id")))
  if sb.get("acceptance")!=NEW:return _fail("SUCCESSOR_ACCEPTANCE_DRIFT:"+str(a.get("root_id")))
  repaired+=1
 meta=new.get("semantic_contract_truth_repair") or {}
 if meta.get("repaired_semantic_leaf_count")!=12:return _fail("REPAIR_COUNT_METADATA_DRIFT")
 if meta.get("execution_leaves_changed")!=0 or meta.get("root_contracts_changed")!=0 or meta.get("semantic_obligations_changed")!=0:
  return _fail("NONSEMANTIC_CHANGE_METADATA_INVALID")
 if meta.get("no_goal_weakening") is not True or meta.get("nonvacuity_required") is not True:
  return _fail("SAFETY_OR_NONVACUITY_GUARD_MISSING")
 return {"schema":SCHEMA,"pass":True,
 "status":"PASS__12_OF_12_SHARED_SEMANTIC_ACCEPTANCES_TRUTH_REPAIRED__NO_OTHER_LEAF_OR_ROOT_CONTRACT_CHANGE__ZERO_PROPERTY_CREDIT",
 "repaired_semantic_leaf_count":repaired,"root_contracts_changed":0,"execution_leaves_changed":0,
 "semantic_obligations_changed":0,
 "old_acceptance":OLD,"new_acceptance":NEW,
 "old_unconditional_success_schedulable":False,
 "successor_requires_fail_closed_on_unresolved":True,"successor_requires_positive_nonvacuity":True,
 "leaf_property_truth_authority":False,"semantic_truth_authority":False,
 "quality_authority":False,"acceptance_authority":False,"promotion_authority":False,
 "terminal_authority":False,"terminal_credit_delta":0,"incremental_spend_usd":0}
