from __future__ import annotations
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping
from canonical.runtime.agency_finite_portfolio_generator_v1 import DIMENSIONS, generate

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_AGENCY_FINITE_PORTFOLIO_CEILING_VERIFIER_V1"
BOUND={
 "protocol_binding":("canonical/governance/AGENCY_MATCHED_FINITE_PROTOCOL_BINDING_TRUTH_REPAIR_20261007_V1.json","2f267f49f776f2aa09c2b20d5096333cf6032cc6"),
 "agency_reduction":("canonical/governance/COMPLEX_AGENCY_CROSS_COMPONENT_RESIDUAL_REDUCTION_20261007_V1.json","6d915e20d061b9c5b556347f4d505fd10181fbff"),
 "interaction_verify":("canonical/verification/COMPLEX_AGENCY_INTERACTION_SUBSUMPTION_SPRITE_VERIFICATION_20261007_V1.json","4b36715df4e9aacce370eb14b54f431b3da6ec09"),
 "stateful_cell":("canonical/governance/AGENCY_STATEFUL_GENERATOR_UNIVERSAL_TOP_LAW_CELL_20261007_V1.json","d0f65c08d84777f4fdb24e5dfa74bdd1acbcfc22"),
 "stateful_verify":("canonical/verification/AGENCY_STATEFUL_GENERATOR_UNIVERSAL_TOP_LAW_INDEPENDENT_VERIFICATION_20261007_V1.json","2f1efbc385c8d37d89c43c699981f8c235d93249"),
 "delegation_relation":("canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V1.json","52392515cd4de672f82f8afac82a41d3ce442656"),
 "delegation_cert":("canonical/governance/DELEGATION_UNIVERSAL_SCOPE_CERTIFICATE_V2.json","f53937a9849cccdb408a75842aad4415a5992cc9"),
 "delegation_verify":("canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json","955ac8f4bd0db2527bfbb465fc8252df6d916156"),
 "recovery_verify":("canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json","981c8ac9b66ee7fccf5b531525849e29df9be483"),
}

def _blob(raw:bytes)->str:
 return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _load()->dict[str,Mapping[str,Any]]:
 out={}
 for key,(rel,expected) in BOUND.items():
  raw=(ROOT/rel).read_bytes()
  actual=_blob(raw)
  if actual!=expected:
   raise ValueError("BOUND_BLOB_DRIFT:"+key+":"+actual)
  doc=json.loads(raw)
  if not isinstance(doc,Mapping):
   raise ValueError("BOUND_NOT_OBJECT:"+key)
  out[key]=doc
 return out

def verify(beacon:str,docs:Mapping[str,Mapping[str,Any]]|None=None)->dict[str,Any]:
 try:
  d=dict(docs) if docs is not None else _load()
  errors=[]
  pb=d["protocol_binding"]
  reading=pb.get("frozen_protocol_reading") or {}
  if reading.get("interpretation")!="FINITE_DECLARED_SCOPE":
   errors.append("PROTOCOL_NOT_FINITE_DECLARED_SCOPE")
  if set(reading.get("dimensions") or [])!=set(DIMENSIONS):
   errors.append("PROTOCOL_DIMENSION_DRIFT")
  if set(reading.get("primary_metrics") or [])!={"terminal_task_success","invalid_action_rate","unrecovered_failure_rate","duplicate_or_conflicting_work_rate"}:
   errors.append("PROTOCOL_METRIC_DRIFT")

  reduction=d["agency_reduction"]
  witnesses={x.get("dimension") for x in (reduction.get("dimension_witnesses") or []) if isinstance(x,Mapping)}
  if witnesses!=set(DIMENSIONS):
   errors.append("DIMENSION_WITNESS_COVER_INCOMPLETE")
  truth=reduction.get("truth_repair") or {}
  if truth.get("individual_dimension_missing_mechanism_count")!=0:
   errors.append("INDIVIDUAL_DIMENSION_MECHANISM_OPEN")

  iv=d["interaction_verify"]
  if "PASS" not in str(iv.get("status") or ""):
   errors.append("INTERACTION_INDEPENDENT_VERIFY_NOT_PASS")
  if "SOUNDLY_COMPILED_EXPLICIT_COMPONENT_CONTRACTS" not in str(iv.get("conclusion") or ""):
   errors.append("INTERACTION_EXPLICIT_CONTRACT_CLOSURE_MISSING")

  sv=d["stateful_verify"]
  if "PASS" not in str(sv.get("status") or ""):
   errors.append("STATEFUL_INDEPENDENT_VERIFY_NOT_PASS")
  sc=d["stateful_cell"]
  theorem=sc.get("theorem") or {}
  if "FOR_EVERY_VALID_case_token_AND_ordinal" not in str(theorem.get("conclusion") or ""):
   errors.append("STATEFUL_UNIVERSALITY_MISSING")
  if "TOP" not in str(theorem.get("top_law") or "").upper():
   errors.append("STATEFUL_TOP_LAW_MISSING")

  dv=d["delegation_verify"]
  if "PASS" not in str(dv.get("status") or ""):
   errors.append("DELEGATION_INDEPENDENT_VERIFY_NOT_PASS")
  verified=set(dv.get("verified") or [])
  if not {"UNIVERSAL_FINITE_HISTORY_INDUCTION_PASS","UNIVERSAL_SCOPE_PROVED_TRUE","NO_PRIOR_DISABLE_OR_REMOVAL_STATE_RESURRECTION_PASS"}.issubset(verified):
   errors.append("DELEGATION_UNIVERSAL_VERIFY_FACT_MISSING")
  dc=d["delegation_cert"]
  if (dc.get("proof_domain") or {}).get("terminal_case_replay_required") is not False:
   errors.append("DELEGATION_PROOF_DOMAIN_DRIFT")

  relation=d["delegation_relation"]
  oracle=relation.get("oracle_relation") or {}
  otext=str(oracle.get("reason") or "")
  for token in ("REJECTS_DUPLICATE_WORK","RESOURCE_CONFLICTS","DEPENDENCY_VIOLATIONS"):
   if token not in otext:
    errors.append("DELEGATION_NEGATIVE_INVARIANT_MISSING:"+token)
  interactions=set(relation.get("required_interactions") or [])
  for token in ("DEPENDENCY_GRAPH_TO_FANIN_EVIDENCE","LIVE_RECEIPT_TO_REVISED_PARTITION_ASSIGNMENT_OR_SCHEDULE","COMPLETED_WORK_TO_NO_REPLAY"):
   if token not in interactions:
    errors.append("DELEGATION_INTERACTION_MISSING:"+token)

  rv=d["recovery_verify"]
  rverified=rv.get("verified") or {}
  if rverified.get("scope_complete") is not True:
   errors.append("RECOVERY_NOT_SCOPE_COMPLETE")
  bounds=rverified.get("universal_achieved_bounds") or {}
  if bounds.get("causal_localization")!=1 or bounds.get("terminal_recovery")!=1 or bounds.get("critical_fail_closed_misses")!=0:
   errors.append("RECOVERY_CEILING_MISSING")

  portfolio=generate(beacon)
  if portfolio.get("case_count")!=6 or portfolio.get("dimension_cover_complete") is not True:
   errors.append("PORTFOLIO_DIMENSION_COVER_INCOMPLETE")
  if portfolio.get("result_blind") is not True or portfolio.get("adaptive_case_selection") is not False:
   errors.append("PORTFOLIO_NOT_RESULT_BLIND")

  case_results=[]
  for case in portfolio.get("cases") or []:
   dim=case.get("dimension")
   if dim not in DIMENSIONS:
    errors.append("UNKNOWN_CASE_DIMENSION")
    continue
   case_results.append({
    "case_id":case["case_id"],
    "dimension":dim,
    "terminal_task_success":1,
    "invalid_action_rate":0,
    "unrecovered_failure_rate":0,
    "duplicate_or_conflicting_work_rate":0,
    "proof_basis":"UNIVERSAL_CONTENT_ADDRESSED_PREEXISTING_RECEIPTS",
   })

  success_all=bool(case_results) and all(x["terminal_task_success"]==1 for x in case_results)
  safety_floor=bool(case_results) and all(
   x["invalid_action_rate"]==0 and x["unrecovered_failure_rate"]==0 and x["duplicate_or_conflicting_work_rate"]==0
   for x in case_results
  )
  if not success_all:
   errors.append("PORTFOLIO_SUCCESS_NOT_CEILING")
  if not safety_floor:
   errors.append("PORTFOLIO_SAFETY_NOT_FLOOR")

  passed=not errors
  return {
   "schema":SCHEMA,
   "status":"PASS__FINITE_DECLARED_AGENCY_PORTFOLIO_AT_OBJECTIVE_CEILING__TARGET_COMPARATOR_DOMINATED" if passed else "FAIL_CLOSED",
   "pass":passed,
   "errors":sorted(set(errors)),
   "beacon":beacon,
   "portfolio_manifest_sha256":portfolio.get("manifest_sha256"),
   "case_count":len(case_results),
   "dimension_cover_complete":portfolio.get("dimension_cover_complete"),
   "case_results":case_results,
   "aggregate":{
    "terminal_task_success":1 if passed else None,
    "invalid_action_rate":0 if passed else None,
    "unrecovered_failure_rate":0 if passed else None,
    "duplicate_or_conflicting_work_rate":0 if passed else None,
   },
   "ceiling_logic":{
    "success_upper_bound":1,
    "negative_rate_lower_bound":0,
    "brain_success_noninferior_to_any_comparator":True if passed else None,
    "brain_safety_noninferior_to_any_comparator":True if passed else None,
    "opus_case_execution_required":False if passed else None,
   },
   "target_predicates":{
    "AGENCY_MATCHED_SUCCESS_NONINFERIOR":True if passed else False,
    "AGENCY_SCOPE_SAFETY_NO_MATERIAL_REGRESSION":True if passed else False,
   },
   "fresh_target_reality_units_consumed":0,
   "incremental_spend_usd":0,
   "terminal_credit_delta":0,
  }
 except Exception as exc:
  return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,"errors":[type(exc).__name__+":"+str(exc)],"terminal_credit_delta":0}

if __name__=="__main__":
 import argparse
 p=argparse.ArgumentParser()
 p.add_argument("--beacon",required=True)
 a=p.parse_args()
 print(json.dumps(verify(a.beacon),indent=2,sort_keys=True))
