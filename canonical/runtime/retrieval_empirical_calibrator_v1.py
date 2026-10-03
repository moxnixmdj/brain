#!/usr/bin/env python3
"""Empirical Bayesian calibration for retrieval routes.

Consumes completed retrieval attempts and produces source statistics compatible
with the global Retrieval V6 controller. The estimates are measured from actual
outcomes instead of fixed route priors.

Each observation:
{
  "action_id": str,
  "source_id": str,
  "upstream_group": str,
  "latency_seconds": float,
  "request_count": int,
  "failed": bool,
  "candidate_ids": [str,...],
  "verified_sufficient_candidate_ids": [str,...]
}

Conditional novelty is measured against the candidate set already exposed by
earlier observations in the supplied execution order. Pairwise overlap provides
an empirical correlation signal for sources sharing similar discoveries.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_RETRIEVAL_EMPIRICAL_CALIBRATOR_V1"


def _canon(x:Any)->str:
 return " ".join(str(x or "").strip().split())


def _mean(xs:list[float],default:float)->float:
 return sum(xs)/len(xs) if xs else default


def calibrate(observations:Sequence[Mapping[str,Any]])->dict[str,Any]:
 seen_global:set[str]=set()
 by_source:dict[str,dict[str,Any]]=defaultdict(lambda:{
  "attempts":0,
  "novel_candidate_actions":0,
  "sufficient_witness_actions":0,
  "failures":0,
  "latencies":[],
  "requests":[],
  "candidate_union":set(),
  "novel_candidate_count":0,
  "total_candidate_count":0,
  "upstream_groups":set(),
 })
 ordered=[]
 for idx,raw in enumerate(observations):
  if not isinstance(raw,Mapping):
   raise ValueError("OBSERVATION_MAPPING_REQUIRED")
  sid=_canon(raw.get("source_id"))
  aid=_canon(raw.get("action_id"))
  if not sid or not aid:
   raise ValueError("SOURCE_AND_ACTION_ID_REQUIRED")
  candidates={_canon(x) for x in (raw.get("candidate_ids") or []) if _canon(x)}
  sufficient={_canon(x) for x in (raw.get("verified_sufficient_candidate_ids") or []) if _canon(x)}
  if not sufficient.issubset(candidates):
   raise ValueError("SUFFICIENT_IDS_MUST_BE_SUBSET_OF_CANDIDATES")
  novel=candidates-seen_global
  stat=by_source[sid]
  stat["attempts"]+=1
  if novel: stat["novel_candidate_actions"]+=1
  if sufficient: stat["sufficient_witness_actions"]+=1
  if raw.get("failed") is True: stat["failures"]+=1
  stat["latencies"].append(max(0.001,float(raw.get("latency_seconds") or 0.001)))
  stat["requests"].append(max(0,int(raw.get("request_count") or 0)))
  stat["candidate_union"].update(candidates)
  stat["novel_candidate_count"]+=len(novel)
  stat["total_candidate_count"]+=len(candidates)
  group=_canon(raw.get("upstream_group") or sid)
  stat["upstream_groups"].add(group)
  ordered.append({
   "index":idx,"action_id":aid,"source_id":sid,"upstream_group":group,
   "candidate_ids":sorted(candidates),"novel_candidate_ids":sorted(novel),
   "verified_sufficient_candidate_ids":sorted(sufficient),
   "failed":raw.get("failed") is True,
  })
  if raw.get("failed") is not True:
   seen_global.update(candidates)

 # Pairwise empirical overlap/correlation.
 sources=sorted(by_source)
 pairwise=[]
 corr_by_source:dict[str,list[float]]=defaultdict(list)
 for i,a in enumerate(sources):
  A=by_source[a]["candidate_union"]
  for b in sources[i+1:]:
   B=by_source[b]["candidate_union"]
   union=A|B
   j=(len(A&B)/len(union)) if union else 0.0
   pairwise.append({"source_a":a,"source_b":b,"jaccard_candidate_overlap":j})
   corr_by_source[a].append(j); corr_by_source[b].append(j)

 source_stats={}
 for sid in sources:
  s=by_source[sid]
  attempts=s["attempts"]
  novel_actions=s["novel_candidate_actions"]
  sufficient_actions=s["sufficient_witness_actions"]
  failures=s["failures"]
  # Beta(1,1) posterior means. These are empirical and uncertainty-aware.
  p_novel=(novel_actions+1)/(attempts+2)
  p_sufficient=(sufficient_actions+1)/(novel_actions+2)
  failure_rate=(failures+1)/(attempts+2)
  mean_corr=_mean(corr_by_source[sid],0.0)
  # Controller-compatible raw fields plus calibrated diagnostics.
  source_stats[sid]={
   "attempts":attempts,
   "novel_candidate_actions":novel_actions,
   "sufficient_witness_actions":sufficient_actions,
   "failures":failures,
   "mean_latency_seconds":_mean(s["latencies"],1.0),
   "mean_requests":_mean([float(x) for x in s["requests"]],1.0),
   "risk":min(1.0,failure_rate+0.5*mean_corr),
   "posterior_p_novel_mean":p_novel,
   "posterior_p_sufficient_given_novel_mean":p_sufficient,
   "posterior_failure_rate_mean":failure_rate,
   "mean_pairwise_candidate_overlap":mean_corr,
   "conditional_novel_candidate_fraction":(
    s["novel_candidate_count"]/s["total_candidate_count"]
    if s["total_candidate_count"] else 0.0
   ),
   "upstream_groups":sorted(s["upstream_groups"]),
  }

 return {
  "schema":SCHEMA,
  "status":"CALIBRATED",
  "observation_count":len(ordered),
  "unique_candidate_count":len(seen_global),
  "source_stats":source_stats,
  "pairwise_source_overlap":pairwise,
  "ordered_observations":ordered,
  "uses_empirical_conditional_novelty":True,
  "uses_fixed_source_quality_constants":False,
  "complete":False,
  "open_world_recall_claim":False,
  "incremental_spend_usd":0,
  "hard_rules":[
   "SOURCE_UTILITY_MUST_BE_UPDATED_FROM_OBSERVED_OUTCOMES",
   "SHARED_CANDIDATE_OVERLAP_IS_CORRELATION_EVIDENCE_NOT_INDEPENDENT_RECALL",
   "FAILED_ACTIONS_DO_NOT_ADD_CANDIDATES_TO_GLOBAL_SEEN_SET",
   "NO_ZERO_HISTORY_SOURCE_IS_ASSIGNED_ZERO_SUCCESS_PROBABILITY",
   "CALIBRATION_IS_NOT_OPEN_WORLD_COMPLETENESS_PROOF",
  ],
 }


def controller_stats(calibration:Mapping[str,Any])->dict[str,Mapping[str,Any]]:
 if calibration.get("schema")!=SCHEMA:
  raise ValueError("CALIBRATION_SCHEMA_REQUIRED")
 stats=calibration.get("source_stats")
 if not isinstance(stats,Mapping):
  raise ValueError("SOURCE_STATS_MAPPING_REQUIRED")
 return {str(k):dict(v) for k,v in stats.items()}


if __name__=="__main__":
 import json
 demo=[
  {"action_id":"a1","source_id":"engine","upstream_group":"web","latency_seconds":0.8,"request_count":1,"failed":False,"candidate_ids":["x","y"],"verified_sufficient_candidate_ids":[]},
  {"action_id":"a2","source_id":"registry","upstream_group":"registry","latency_seconds":0.2,"request_count":1,"failed":False,"candidate_ids":["y","z"],"verified_sufficient_candidate_ids":["z"]},
 ]
 print(json.dumps(calibrate(demo),indent=2,sort_keys=True))
