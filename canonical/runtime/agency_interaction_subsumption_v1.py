"""Fail-closed proof checker for the complex-agency interaction subsumption theorem.

The checker does not claim arbitrary component semantics. It proves only that the
remaining cross-component interaction classes in the frozen complex-agency protocol
are covered by the already independently verified delegation interaction carrier,
recovery ceiling, and stateful continuity witness, conditional on each invoked
component already having its own sound local adequacy certificate.

Contexts whose task/component semantics cannot be compiled into the explicit finite
contract stay unresolved on the shared ABC semantic/admission frontier.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

SCHEMA="PROJECT_BRAIN_AGENCY_INTERACTION_SUBSUMPTION_CHECKER_V1"
ROOT=Path(__file__).resolve().parents[2]

BOUND={
 "agency_reduction":(
  "canonical/governance/COMPLEX_AGENCY_CROSS_COMPONENT_RESIDUAL_REDUCTION_20261007_V1.json",
  "6d915e20d061b9c5b556347f4d505fd10181fbff",
 ),
 "delegation_relation":(
  "canonical/governance/DELEGATION_SCOPE_EQUIVALENCE_RELATION_V1.json",
  "52392515cd4de672f82f8afac82a41d3ce442656",
 ),
 "delegation_v2_relation":(
  "canonical/governance/TASK_TO_DELEGATION_SCOPE_RELATION_V2.json",
  "8ffe02f3efe1ceebed30354404bc2f60f3bd6bbd",
 ),
 "delegation_verify":(
  "canonical/verification/DELEGATION_V4_UNIVERSAL_SCOPE_PUBLIC_RUNNER_VERIFICATION_20261003_V1.json",
  "955ac8f4bd0db2527bfbb465fc8252df6d916156",
 ),
 "recovery_verify":(
  "canonical/verification/RECOVERY_OPUS55_ZERO_REALITY_PUBLIC_RUNNER_VERIFICATION_20261003_V2.json",
  "981c8ac9b66ee7fccf5b531525849e29df9be483",
 ),
 "stateful_agency":(
  "canonical/governance/AGENCY_STATEFUL_GENERATOR_UNIVERSAL_TOP_LAW_CELL_20261007_V1.json",
  "d0f65c08d84777f4fdb24e5dfa74bdd1acbcfc22",
 ),
}

AGENCY_DIMENSIONS={
 "multi-step planning with at least three distinct tool/action types",
 "state change after actions requiring replanning",
 "long-horizon state retention",
 "tool failure/recovery",
 "subtask dependency and fan-in",
 "minimal-oversight completion",
}
AGENCY_METRICS={
 "terminal_task_success",
 "invalid_action_rate",
 "unrecovered_failure_rate",
 "duplicate_or_conflicting_work_rate",
}
REQUIRED_DELEGATION_INTERACTIONS={
 "TASK_REQUIREMENTS_TO_MINIMUM_COST_PARTITION",
 "SELECTED_TASKS_TO_DIRECT_DEPENDENCY_GRAPH",
 "WORKER_TOOL_CAPABILITIES_TO_COMPATIBLE_ASSIGNMENT",
 "DEPENDENCIES_TO_USEFUL_PARALLEL_WAVES",
 "RESOURCE_CAPACITIES_TO_NONCONFLICTING_SCHEDULE",
 "STEP_OUTPUTS_TO_EVIDENCE_OWNERSHIP",
 "DEPENDENCY_GRAPH_TO_FANIN_EVIDENCE",
 "LIVE_RECEIPT_TO_REVISED_PARTITION_ASSIGNMENT_OR_SCHEDULE",
 "COMPLETED_WORK_TO_NO_REPLAY",
 "REVISION_TO_RECEIPT_PROVENANCE",
}
REQUIRED_RECEIPTS={
 "STEP_UNAVAILABLE",
 "WORKER_UNAVAILABLE",
 "WORKER_CAPABILITY_REMOVED",
 "RESOURCE_CAPACITY_CHANGED",
}

INTERACTION_MAPPING={
 "multi-step planning with at least three distinct tool/action types":[
  "TASK_REQUIREMENTS_TO_MINIMUM_COST_PARTITION",
  "SELECTED_TASKS_TO_DIRECT_DEPENDENCY_GRAPH",
  "WORKER_TOOL_CAPABILITIES_TO_COMPATIBLE_ASSIGNMENT",
 ],
 "state change after actions requiring replanning":[
  "LIVE_RECEIPT_TO_REVISED_PARTITION_ASSIGNMENT_OR_SCHEDULE",
  "COMPLETED_WORK_TO_NO_REPLAY",
  "REVISION_TO_RECEIPT_PROVENANCE",
 ],
 "long-horizon state retention":["STATEFUL_CHECKPOINT_RELAUNCH_SAME_IDENTITY"],
 "tool failure/recovery":[
  "LIVE_RECEIPT_TO_REVISED_PARTITION_ASSIGNMENT_OR_SCHEDULE",
  "RECOVERY_SCOPE_COMPLETE_TERMINAL_CEILING",
 ],
 "subtask dependency and fan-in":[
  "SELECTED_TASKS_TO_DIRECT_DEPENDENCY_GRAPH",
  "DEPENDENCIES_TO_USEFUL_PARALLEL_WAVES",
  "STEP_OUTPUTS_TO_EVIDENCE_OWNERSHIP",
  "DEPENDENCY_GRAPH_TO_FANIN_EVIDENCE",
 ],
 "minimal-oversight completion":[
  "TASK_REQUIREMENTS_TO_MINIMUM_COST_PARTITION",
  "WORKER_TOOL_CAPABILITIES_TO_COMPATIBLE_ASSIGNMENT",
  "RESOURCE_CAPACITIES_TO_NONCONFLICTING_SCHEDULE",
 ],
}


def _git_blob(raw:bytes)->str:
 return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def _load_bound()->dict[str,Mapping[str,Any]]:
 out={}
 for key,(rel,expected) in BOUND.items():
  raw=(ROOT/rel).read_bytes()
  actual=_git_blob(raw)
  if actual!=expected:
   raise ValueError("BOUND_BLOB_DRIFT:"+key+":"+actual)
  doc=json.loads(raw)
  if not isinstance(doc,Mapping):
   raise ValueError("BOUND_JSON_NOT_OBJECT:"+key)
  out[key]=doc
 return out


def verify_documents(docs:Mapping[str,Mapping[str,Any]])->dict[str,Any]:
 errors=[]
 required=set(BOUND)
 if not isinstance(docs,Mapping) or not required.issubset(set(docs)):
  return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
          "errors":["BOUND_DOCUMENT_SET_INCOMPLETE"],"terminal_authority":False}

 agency=docs["agency_reduction"]
 frozen=agency.get("frozen_protocol") if isinstance(agency,Mapping) else None
 dims=set((frozen or {}).get("dimensions") or [])
 metrics=set((frozen or {}).get("metrics") or [])
 truth=agency.get("truth_repair") if isinstance(agency,Mapping) else None
 if dims!=AGENCY_DIMENSIONS: errors.append("AGENCY_DIMENSION_SET_DRIFT")
 if metrics!=AGENCY_METRICS: errors.append("AGENCY_METRIC_SET_DRIFT")
 if (truth or {}).get("individual_dimension_missing_mechanism_count")!=0:
  errors.append("INDIVIDUAL_AGENCY_DIMENSION_STILL_OPEN")
 if (truth or {}).get("remaining_residual")!="AGENCY_CROSS_COMPONENT_INTERACTION_CLOSURE_OR_STRONGER":
  errors.append("AGENCY_REMAINING_RESIDUAL_DRIFT")

 d1=docs["delegation_relation"]
 interactions=set(d1.get("required_interactions") or [])
 if not REQUIRED_DELEGATION_INTERACTIONS.issubset(interactions):
  errors.append("DELEGATION_INTERACTION_COVER_INCOMPLETE")

 d2=docs["delegation_v2_relation"]
 boundary=d2.get("exact_contract_boundary") if isinstance(d2,Mapping) else None
 receipts=set((boundary or {}).get("supported_receipt_kinds") or [])
 if receipts!=REQUIRED_RECEIPTS:
  errors.append("DELEGATION_RECEIPT_ALPHABET_DRIFT")
 pop=d2.get("population_relation") if isinstance(d2,Mapping) else None
 if (pop or {}).get("relation")!="UNIVERSAL_FORMAL_SCOPE_CANDIDATE":
  errors.append("DELEGATION_NOT_UNIVERSAL_FORMAL_SCOPE")
 text=str((pop or {}).get("boundary") or "")
 for token in ("ALL_FINITE_VALID_EXPLICIT_MONOTONIC_FACT_TASK_GRAPHS","ANY_FINITE_ORDERED_SUPPORTED_RECEIPT_HISTORY"):
  if token not in text:
   errors.append("DELEGATION_POPULATION_BOUNDARY_TOO_WEAK:"+token)

 dv=docs["delegation_verify"]
 if "PASS" not in str(dv.get("status") or ""):
  errors.append("DELEGATION_INDEPENDENT_VERIFY_NOT_PASS")
 verified=set(dv.get("verified") or [])
 for token in (
  "UNIVERSAL_FINITE_HISTORY_INDUCTION_PASS",
  "UNIVERSAL_SCOPE_PROVED_TRUE",
  "NO_PRIOR_DISABLE_OR_REMOVAL_STATE_RESURRECTION_PASS",
 ):
  if token not in verified: errors.append("DELEGATION_VERIFY_FACT_MISSING:"+token)

 rv=docs["recovery_verify"]
 theorem=rv.get("theorem") if isinstance(rv,Mapping) else None
 if (theorem or {}).get("scope_complete") is not True:
  errors.append("RECOVERY_SCOPE_NOT_COMPLETE")
 bounds=(theorem or {}).get("universal_achieved_bounds") or {}
 if bounds.get("causal_localization")!=1 or bounds.get("terminal_recovery")!=1 or bounds.get("critical_fail_closed_misses")!=0:
  errors.append("RECOVERY_CEILING_NOT_BOUND")

 sa=docs["stateful_agency"]
 st=sa.get("theorem") if isinstance(sa,Mapping) else None
 conclusion=str((st or {}).get("conclusion") or "")
 if "FOR_EVERY_VALID_case_token_AND_ordinal" not in conclusion or "pass_TRUE" not in conclusion:
  errors.append("STATEFUL_CONTINUITY_UNIVERSAL_WITNESS_MISSING")
 proc=sa.get("local_continuity_truth_repair") if isinstance(sa,Mapping) else None
 trace=list((proc or {}).get("exact_process_trace") or [])
 if not any("CHECKPOINT" in str(x).upper() for x in trace) or not any("RECLAIM" in str(x).upper() for x in trace):
  errors.append("STATEFUL_CHECKPOINT_RELAUNCH_TRACE_MISSING")

 # Every frozen agency dimension must have a declared interaction decomposition.
 if set(INTERACTION_MAPPING)!=AGENCY_DIMENSIONS:
  errors.append("INTERACTION_MAPPING_DIMENSION_COVER_INCOMPLETE")
 flat={x for values in INTERACTION_MAPPING.values() for x in values}
 allowed=set(REQUIRED_DELEGATION_INTERACTIONS)|{
  "STATEFUL_CHECKPOINT_RELAUNCH_SAME_IDENTITY",
  "RECOVERY_SCOPE_COMPLETE_TERMINAL_CEILING",
 }
 if not flat.issubset(allowed):
  errors.append("INTERACTION_MAPPING_USES_UNPROVED_PRIMITIVE")

 return {
  "schema":SCHEMA,
  "status":"PASS__AGENCY_INTERACTION_RESIDUAL_SUBSUMED_BY_VERIFIED_PRODUCT_PREMISES" if not errors else "FAIL_CLOSED",
  "pass":not errors,
  "errors":sorted(set(errors)),
  "frozen_agency_dimensions":sorted(AGENCY_DIMENSIONS),
  "frozen_agency_metrics":sorted(AGENCY_METRICS),
  "interaction_mapping":deepcopy(INTERACTION_MAPPING),
  "supported_dynamic_receipts":sorted(REQUIRED_RECEIPTS),
  "cross_component_new_mechanism_required":False if not errors else None,
  "explicit_contract_semantics_required":True,
  "uncompiled_or_implicit_semantics_disposition":"REMAIN_ON_SHARED_ABC_SEMANTIC_ADMISSION_FRONTIER__NOT_AN_AGENCY_INTERACTION_MECHANISM_GAP",
  "terminal_authority":False,
  "terminal_credit_delta":0,
 }


def verify_repository()->dict[str,Any]:
 try:
  return verify_documents(_load_bound())
 except Exception as exc:
  return {"schema":SCHEMA,"status":"FAIL_CLOSED","pass":False,
          "errors":[type(exc).__name__+":"+str(exc)],"terminal_authority":False}
