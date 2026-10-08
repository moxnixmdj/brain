"""Objective fixed-bar pass-lock reconciliation V1.

Recomputes conservative stopping semantics for currently bound objective public-bar
surfaces.  It is deliberately scheduling-only: no benchmark case is read or run.

The key rule is monotone and exact for frozen binary-rate populations:
  PASS_LOCKED iff observed successes already meet the required integer count.
  FAIL_LOCKED iff even every remaining executable slot succeeding cannot meet it.

Unavailable, unexecuted, contaminated, or irreversibly-zero slots are assigned zero.
"""
from __future__ import annotations

from hashlib import sha1
import json
from pathlib import Path
from typing import Any, Mapping

from canonical.runtime.acceptance_bound_compiler_v1 import evaluate as compile_bound

ROOT=Path(__file__).resolve().parents[2]
SCHEMA="PROJECT_BRAIN_OBJECTIVE_FIXED_BAR_PASS_LOCK_RECONCILIATION_V1"

BOUND={
 "tb4_cut":(
   "canonical/verification/TB4_CONSERVATIVE_THRESHOLD_CUT_PUBLIC_RUNNER_VERIFICATION_20261002_V1.json",
   "99721d680c57a1848fcf87ca8036770a6a4b9a0e",
 ),
 "tb4_attainability":(
   "canonical/governance/TB4_ATTAINABILITY_EVIDENCE_MANIFEST_V1.json",
   "36cfd7b29465a2da6c05667b18848bdcabcd22e6",
 ),
 "automation":(
   "canonical/governance/AUTOMATIONBENCH_PUBLIC_SCOPE_BINDING_V1.json",
   "1cb9b4ca93699e4db965dd2a682017eebd6649be",
 ),
 "hle":(
   "canonical/governance/HLE_TOOLS_OFFICIAL_PROTOCOL_BOUNDARY_V1.json",
   "7cd2e071c6844a13d9e5d2b2d696ac5d56180481",
 ),
 "chartography":(
   "canonical/governance/CHARTOGRAPHY_ADAPTER_ROUTE_TRUTH_20261005_V1.json",
   "8435a22892907191769d26155ff64e8a706bf10a",
 ),
}

def _blob(raw:bytes)->str:
 return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def _load()->dict[str,Mapping[str,Any]]:
 out={}
 for key,(path,want) in BOUND.items():
  raw=(ROOT/path).read_bytes()
  got=_blob(raw)
  if got!=want:
   raise ValueError("BOUND_BLOB_DRIFT:"+key+":"+got)
  doc=json.loads(raw)
  if not isinstance(doc,Mapping):
   raise ValueError("BOUND_JSON_INVALID:"+key)
  out[key]=doc
 return out

def _binary(total:int, executable:int, threshold_percent:float, *, successes:int=0, failures:int=0)->dict[str,Any]:
 return compile_bound({
   "metric_semantics_frozen":True,
   "population_frozen":True,
   "worst_case_assignment_admissible":True,
   "metric_type":"BINARY_RATE",
   "total_slots":total,
   "executable_slots":executable,
   "observed_successes":successes,
   "observed_failures":failures,
   "threshold_percent":threshold_percent,
 })

def verify_documents(docs:Mapping[str,Mapping[str,Any]])->dict[str,Any]:
 errors=[]
 if not isinstance(docs,Mapping) or not set(BOUND).issubset(docs):
  return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":["BOUND_DOCUMENT_SET_INCOMPLETE"],"terminal_authority":False}

 tb4=docs["tb4_cut"]; attain=docs["tb4_attainability"]
 try:
  tb4_total=int((tb4.get("frozen_benchmark") or {}).get("full_population_trial_slots"))
  tb4_target=float((tb4.get("threshold") or {}).get("target_percent"))
  required=int((tb4.get("threshold") or {}).get("required_successes"))
  max_success=int((attain.get("derived") or {}).get("maximum_attainable_successes"))
 except Exception:
  errors.append("TB4_BINDING_PARSE_FAIL")
  tb4_total,tb4_target,required,max_success=330,66.4,-1,-1
 tb4_bound=_binary(tb4_total,max_success,tb4_target) if max_success>=0 else {"decision":"UNRESOLVED","required_successes":None}
 if required!=220 or tb4_bound.get("required_successes")!=220:
  errors.append("TB4_REQUIRED_SUCCESS_DRIFT")
 if max_success!=180:
  errors.append("TB4_MAX_ATTAINABLE_SUCCESS_DRIFT")
 if tb4_bound.get("decision")!="FAIL_LOCKED":
  errors.append("TB4_CURRENT_FROZEN_ROUTE_NOT_FAIL_LOCKED")

 auto=docs["automation"]
 rep=auto.get("represented_scope") or {}
 try:
  auto_total=int(rep.get("documented_public_scored_task_count"))
  auto_threshold=100*float(rep.get("target_threshold"))
 except Exception:
  errors.append("AUTOMATION_BINDING_PARSE_FAIL")
  auto_total,auto_threshold=600,40.0
 if rep.get("per_task_metric")!="task_completed_correctly":
  errors.append("AUTOMATION_PER_TASK_METRIC_DRIFT")
 if "MEAN_TASK_COMPLETED_CORRECTLY" not in str(rep.get("portfolio_metric") or ""):
  errors.append("AUTOMATION_PORTFOLIO_METRIC_DRIFT")
 auto_bound=_binary(auto_total,auto_total,auto_threshold)
 if auto_bound.get("required_successes")!=240:
  errors.append("AUTOMATION_REQUIRED_SUCCESS_DRIFT")

 hle=docs["hle"]
 hpop=hle.get("official_population_observation") or {}
 hproto=hle.get("verified_protocol") or {}
 if hpop.get("question_count")!=1000:
  errors.append("HLE_DIAMOND_COUNT_DRIFT")
 if hproto.get("judge_gold_source")!="question.answer":
  errors.append("HLE_JUDGE_GOLD_SOURCE_DRIFT")
 # Exact public scorer source is content-addressed by HLE boundary but the
 # arithmetic extraction itself has not yet received a separate Brain replay.
 hle_candidate_required=677

 chart=docs["chartography"]
 contract=(chart.get("official_chartography") or {}).get("task_contract") or []
 if not any("10_EPOCHS_PER_100_TASKS" in str(x) for x in contract):
  errors.append("CHARTOGRAPHY_1000_TRIAL_CONTRACT_NOT_BOUND")
 chart_candidate_required=890

 return {
  "schema":SCHEMA,
  "pass":not errors,
  "status":"PASS__OBJECTIVE_FIXED_BAR_STOPPING_FRONTIER_RECONCILED__ZERO_CREDIT" if not errors else "FAIL_CLOSED",
  "errors":sorted(set(errors)),
  "surfaces":{
   "TB4":{
    "population_slots":tb4_total,
    "threshold_percent":tb4_target,
    "required_successes":220,
    "current_maximum_attainable_successes":max_success,
    "decision":tb4_bound.get("decision"),
    "scheduler_action":"DELETE_CURRENT_FROZEN_DIRECT_EXECUTION_ROUTE_UNTIL_LEGITIMATE_REOPEN_CONDITION",
    "reason":"MAXIMUM_ATTAINABLE_180_LT_REQUIRED_220",
   },
   "AUTOMATIONBENCH":{
    "population_slots":auto_total,
    "threshold_percent":auto_threshold,
    "required_successes":auto_bound.get("required_successes"),
    "decision":auto_bound.get("decision"),
    "pass_lock_rule":"OBSERVED_VALID_SUCCESSES_GE_240",
    "scheduler_action":"IF_AND_ONLY_IF_CLEAN_TERMINAL_WAVE_AUTHORIZED__EXECUTE_RESULT_BLIND_AND_STOP_IMMEDIATELY_AT_240_SUCCESSES",
   },
   "HLE_DIAMOND_TOOLS":{
    "population_questions":1000,
    "threshold_percent":67.7,
    "candidate_required_correct_judgments":hle_candidate_required,
    "promotion_state":"ARITHMETIC_CANDIDATE__EXACT_SCORER_AGGREGATION_SOURCE_BOUND_BUT_SEPARATE_BRAIN_REPLAY_REQUIRED",
    "scheduler_action":"DO_NOT_RUN_CASES_BEFORE_DATASET_JUDGE_AND_ADAPTER_GATES_CLOSE",
   },
   "CHARTOGRAPHY":{
    "scheduled_trials":1000,
    "threshold_percent":89.0,
    "candidate_required_successes":chart_candidate_required,
    "promotion_state":"ARITHMETIC_CANDIDATE__OFFICIAL_TASK_CONTRACT_BINDS_100_X_10__SCORER_ZERO_NAN_LOWER_BOUND_NEEDS_SEPARATE_REPLAY",
    "scheduler_action":"DO_NOT_RUN_CASES_BEFORE_VISION_AND_JUDGE_CAPACITY_GATES_CLOSE",
   },
  },
  "deleted_work":[
   "RUN_ADDITIONAL_CURRENT_FROZEN_TB4_DIRECT_CREDIT_CASES_WHILE_MAX_ATTAINABLE_REMAINS_180",
   "RUN_ALL_600_AUTOMATIONBENCH_CASES_AFTER_240_VALID_SUCCESSES_HAVE_ALREADY_BEEN_RECEIPTED",
  ],
  "hard_nonclaims":[
   "NO_AUTOMATIONBENCH_SCORE_EXISTS_YET",
   "NO_HLE_SCORE_EXISTS_YET",
   "NO_CHARTOGRAPHY_SCORE_EXISTS_YET",
   "NO_NEW_BENCHMARK_CASE_EXPOSURE",
   "NO_ACCEPTANCE_CAPABILITY_FAMILY_OR_TERMINAL_CREDIT",
  ],
  "fresh_reality_authority":False,
  "execution_authority":False,
  "promotion_authority":False,
  "terminal_authority":False,
  "terminal_credit_delta":0,
 }

def verify_repository()->dict[str,Any]:
 try:return verify_documents(_load())
 except Exception as exc:
  return {"schema":SCHEMA,"pass":False,"status":"FAIL_CLOSED","errors":[type(exc).__name__+":"+str(exc)],"terminal_authority":False}

def run(args:Mapping[str,Any]|None=None,root:Any=None)->dict[str,Any]:
 return verify_repository()
