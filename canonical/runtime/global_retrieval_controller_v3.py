#!/usr/bin/env python3
"""Context-conditioned empirical global retrieval controller V3."""
from __future__ import annotations
import statistics
from typing import Any,Mapping,Sequence
from canonical.runtime import global_retrieval_controller_v1 as base
from canonical.runtime import global_retrieval_controller_v2 as v2
SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_CONTROLLER_V3"

def _stats_for(source:str,task_class:str,cal:Mapping[str,Any])->tuple[Mapping[str,Any],str]:
 task_class=str(task_class or "").upper()
 by_class=cal.get("task_class_source_stats") if isinstance(cal,Mapping) else {}
 if task_class and isinstance(by_class,Mapping):
  cs=by_class.get(task_class)
  if isinstance(cs,Mapping):
   row=cs.get(source)
   if isinstance(row,Mapping) and int(row.get("attempts") or 0)>0:
    return row,"TASK_CLASS_MEASURED"
 glob=cal.get("source_stats") if isinstance(cal,Mapping) else {}
 row=glob.get(source) if isinstance(glob,Mapping) else None
 if isinstance(row,Mapping) and int(row.get("attempts") or 0)>0:return row,"GLOBAL_FALLBACK_MEASURED"
 return {},"JEFFREYS_COLD_START"

def rank_actions_contextual(actions:Sequence[Mapping[str,Any]],*,live_calibration:Mapping[str,Any]|None=None,default_task_class:str="",consumed_upstream_groups:Sequence[str]=())->list[dict[str,Any]]:
 cal=live_calibration or {}
 # imputation uses all measured global sources only, never invented per-source constants.
 glob=cal.get("source_stats") if isinstance(cal,Mapping) else {}
 lats=[float(x.get("mean_latency_seconds") or 0) for x in glob.values() if isinstance(x,Mapping) and int(x.get("attempts") or 0)>0 and float(x.get("mean_latency_seconds") or 0)>0]
 reqs=[float(x.get("mean_requests") or 0) for x in glob.values() if isinstance(x,Mapping) and int(x.get("attempts") or 0)>0]
 il=statistics.median(lats) if lats else 1.0;ir=statistics.median(reqs) if reqs else 1.0
 out=[]
 for raw in actions:
  row=dict(raw);source=base._canon(row.get("source_id") or row.get("domain") or row.get("backend_id"))
  group=base._canon(row.get("upstream_group") or source);tc=str(row.get("task_class") or default_task_class or "UNCLASSIFIED").upper()
  stats,basis=_stats_for(source,tc,cal)
  comp=v2.empirical_components(stats,consumed_upstream_groups=consumed_upstream_groups,upstream_group=group,imputed_latency_seconds=il,imputed_requests=ir)
  comp["calibration_basis"]=basis;comp["task_class"]=tc
  row["task_class"]=tc;row["retrieval_priority_v3"]=comp;out.append(row)
 out.sort(key=lambda x:(-float(x["retrieval_priority_v3"]["expected_sufficient_witness_per_second"]),float(x["retrieval_priority_v3"]["mean_requests"]),str(x.get("action_id") or "")))
 return out

def compile_global_plan(*,query_actions:Sequence[Mapping[str,Any]],sources:Sequence[Mapping[str,Any]],live_calibration:Mapping[str,Any]|None=None,state:Mapping[str,Any]|None=None,task_class:str="")->dict[str,Any]:
 state=state or base.new_state();cal=live_calibration or {}
 source_by_id={base._canon(x.get("source_id")):x for x in sources if isinstance(x,Mapping) and base._canon(x.get("source_id"))}
 actions=[]
 for raw in query_actions:
  row=dict(raw);sid=base._canon(row.get("source_id") or row.get("domain") or row.get("backend_id"));src=source_by_id.get(sid,{})
  row.setdefault("action","QUERY_SOURCE");row.setdefault("source_id",sid);row.setdefault("upstream_group",base._canon(src.get("upstream_group")) or sid)
  row.setdefault("candidate_authority","CANDIDATE_ONLY");row["nonexistence_claim_authorized"]=False
  if not row.get("task_class") and src.get("task_class"):row["task_class"]=str(src.get("task_class")).upper()
  actions.append(row)
 for row in base.compile_queryless_enumeration(sources):
  src=source_by_id.get(base._canon(row.get("source_id")),{})
  if src.get("task_class"):row["task_class"]=str(src.get("task_class")).upper()
  actions.append(row)
 ranked=rank_actions_contextual(actions,live_calibration=cal,default_task_class=task_class,consumed_upstream_groups=state.get("consumed_upstream_groups") or [])
 return {"schema":SCHEMA,"status":"COMPILED_CONTEXT_CONDITIONED_EMPIRICAL_RETRIEVAL_PLAN","actions":ranked,
  "task_class":str(task_class or "UNCLASSIFIED").upper(),"live_event_count":int(cal.get("event_count") or 0),
  "task_class_count":int(cal.get("task_class_count") or 0),"candidate_memory_monotonic":True,
  "open_world_nonexistence_claim_authorized":False,"fixed_source_multipliers_used":False,"incremental_spend_usd":0,
  "hard_rules":["TASK_CLASS_MEASURED_STATS_OVERRIDE_GLOBAL_SOURCE_AVERAGES","GLOBAL_SOURCE_STATS_ARE_ONLY_FALLBACK_FOR_UNMEASURED_TASK_CLASSES",
   "COLD_START_USES_JEFFREYS_PRIOR_NOT_FAKE_INDEPENDENCE","NO_SINGLE_SEARCH_ENGINE_IS_COMPLETENESS_AUTHORITY","OPEN_WORLD_MISS_REMAINS_UNKNOWN",
   "STOP_ON_FIRST_INDEPENDENTLY_VERIFIED_SUFFICIENT_WITNESS"]}
