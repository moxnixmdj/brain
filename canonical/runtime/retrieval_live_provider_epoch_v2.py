#!/usr/bin/env python3
"""Concurrent zero-cost live provider calibration epoch V2.

Runs independent public-provider calls concurrently while preserving the frozen
per-episode sequence numbers used for causal novelty calibration.
"""
from __future__ import annotations
import concurrent.futures,json,time,urllib.error
from typing import Any
from canonical.runtime import retrieval_live_provider_epoch_v1 as base
SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_EPOCH_V2"

def _call(ep:dict[str,Any],seq:int,source:str)->tuple[int,dict[str,Any],dict[str,Any]]:
 start=time.perf_counter();rows=[];status="SUCCESS";err=None
 try:
  rows=base.provider(source,ep["query"])
 except urllib.error.HTTPError as exc:
  status="FAILED_RETRYABLE" if exc.code in {403,408,409,425,429,500,502,503,504} else "FAILED_PERMANENT"
  err=f"HTTPError:{exc.code}"
 except Exception as exc:
  status="FAILED_RETRYABLE";err=type(exc).__name__+":"+str(exc)[:240]
 latency=time.perf_counter()-start
 ids=[x["id"] for x in rows if x.get("id")]
 sufficient=[]
 expected=(ep.get("targets") or {}).get(source,set())
 if expected:sufficient=sorted(set(ids)&set(expected))
 target_title=base._canon(ep.get("target_title"))
 if target_title:
  for x in rows:
   if base._canon(x.get("title"))==target_title:sufficient.append(x["id"])
 sufficient=sorted(set(sufficient))
 event={"episode_id":ep["episode_id"],"task_class":ep["task_class"],"source_id":source,
  "upstream_group":source+"_PUBLIC_API","action_id":ep["episode_id"]+":"+source,"sequence":seq,"status":status,
  "candidate_ids":ids,"verified_sufficient_candidate_ids":sufficient,
  "independent_receipt":base.RECEIPT if sufficient else None,"latency_seconds":round(latency,6),"request_count":1}
 raw={"episode_id":ep["episode_id"],"source_id":source,"query":ep["query"],"status":status,"error":err,"rows":rows}
 return seq,event,raw

def run(max_workers:int=12)->dict[str,Any]:
 jobs=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(int(max_workers),24))) as ex:
  future_map={}
  for epi,ep in enumerate(base.EPISODES):
   for seq,source in enumerate(ep["sources"],1):
    fut=ex.submit(_call,ep,seq,source)
    future_map[fut]=(epi,seq)
  for fut,order in future_map.items():
   seq,event,raw=fut.result()
   jobs.append((order,event,raw))
 jobs.sort(key=lambda x:x[0])
 events=[x[1] for x in jobs];raw=[x[2] for x in jobs]
 return {"schema":SCHEMA,"status":"LIVE_CONCURRENT_EPOCH_COMPLETED","episode_count":len(base.EPISODES),
  "event_count":len(events),"source_count":len({x["source_id"] for x in events}),
  "task_class_count":len({x["task_class"] for x in events}),"events":events,"raw_results":raw,
  "incremental_spend_usd":0,"parallel_execution":True,
  "hard_rules":["PUBLIC_ZERO_COST_APIS_ONLY","PROVIDER_CALLS_EXECUTE_CONCURRENTLY_BUT_CAUSAL_SEQUENCE_IS_FROZEN",
   "FAILED_PROVIDER_CALLS_REMAIN_FAILURE_EVENTS","SUFFICIENT_LABELS_ONLY_MATCH_FROZEN_EXPECTED_IDENTITIES_OR_EXACT_FROZEN_TITLES",
   "LIVE_RESULTS_ARE_NOT_COMPLETENESS_PROOFS"]}
if __name__=="__main__":print(json.dumps(run(),ensure_ascii=False,sort_keys=True))
