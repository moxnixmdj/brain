#!/usr/bin/env python3
"""Context-conditioned append-only live retrieval ledger."""
from __future__ import annotations
import json,statistics
from collections import defaultdict
from pathlib import Path
from typing import Any,Mapping,Sequence
SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_EVENT_LEDGER_V2"
def _s(x:Any)->str:return " ".join(str(x or "").strip().split())
def _valid_event(raw:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(raw,Mapping):raise ValueError("EVENT_MAPPING_REQUIRED")
 ep=_s(raw.get("episode_id"));tc=_s(raw.get("task_class")).upper();src=_s(raw.get("source_id"))
 grp=_s(raw.get("upstream_group") or src);act=_s(raw.get("action_id"))
 if not ep or not tc or not src or not act:raise ValueError("EVENT_IDENTITY_FIELDS_REQUIRED")
 status=_s(raw.get("status")).upper()
 if status not in {"SUCCESS","FAILED_RETRYABLE","FAILED_PERMANENT"}:raise ValueError("EVENT_STATUS_INVALID")
 cand=sorted({_s(x) for x in raw.get("candidate_ids",[]) if _s(x)})
 suff=sorted({_s(x) for x in raw.get("verified_sufficient_candidate_ids",[]) if _s(x)})
 receipt=_s(raw.get("independent_receipt"))
 if suff and not receipt:raise ValueError("SUFFICIENT_EVENT_REQUIRES_INDEPENDENT_RECEIPT")
 if set(suff)-set(cand):raise ValueError("SUFFICIENT_CANDIDATE_NOT_IN_EVENT_CANDIDATES")
 return {"episode_id":ep,"task_class":tc,"source_id":src,"upstream_group":grp,"action_id":act,
  "sequence":max(0,int(raw.get("sequence") or 0)),"status":status,"candidate_ids":cand,
  "verified_sufficient_candidate_ids":suff,"independent_receipt":receipt or None,
  "latency_seconds":max(0.0,float(raw.get("latency_seconds") or 0.0)),
  "request_count":max(0,int(raw.get("request_count") or 0))}
def _aggregate_rows(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
 by_ep=defaultdict(list)
 for r in rows:by_ep[r["episode_id"]].append(dict(r))
 enriched=[]
 for ep,ers in by_ep.items():
  classes={x["task_class"] for x in ers}
  if len(classes)!=1:raise ValueError("EPISODE_TASK_CLASS_MISMATCH:"+ep)
  seen=set();groups=set()
  for r in sorted(ers,key=lambda x:(x["sequence"],x["action_id"])):
   x=dict(r);c=set(r["candidate_ids"]);new=sorted(c-seen)
   x["novel_candidate_ids"]=new;x["novel_candidate_action"]=bool(new);x["prior_upstream_groups"]=sorted(groups)
   seen|=c;groups.add(r["upstream_group"]);enriched.append(x)
 per=defaultdict(lambda:{"attempts":0,"failures":0,"novel_candidate_actions":0,"sufficient_witness_actions":0,"latencies":[],"requests":[],"conditional":defaultdict(lambda:{"attempts":0,"novel_candidate_actions":0})})
 sec=defaultdict(lambda:defaultdict(set))
 for r in enriched:
  s=per[r["source_id"]];s["attempts"]+=1
  if r["status"]!="SUCCESS":s["failures"]+=1
  if r["novel_candidate_action"]:s["novel_candidate_actions"]+=1
  if r["verified_sufficient_candidate_ids"]:s["sufficient_witness_actions"]+=1
  s["latencies"].append(r["latency_seconds"]);s["requests"].append(r["request_count"])
  for g in r["prior_upstream_groups"]:
   q=s["conditional"][g];q["attempts"]+=1;q["novel_candidate_actions"]+=int(r["novel_candidate_action"])
  sec[r["source_id"]][r["episode_id"]]|=set(r["candidate_ids"])
 stats={}
 for src,s in per.items():
  stats[src]={"attempts":s["attempts"],"failures":s["failures"],"novel_candidate_actions":s["novel_candidate_actions"],
   "sufficient_witness_actions":s["sufficient_witness_actions"],
   "mean_latency_seconds":statistics.fmean(s["latencies"]) if s["latencies"] else 0.0,
   "mean_requests":statistics.fmean(s["requests"]) if s["requests"] else 0.0,
   "conditional_after_upstream_group":{g:dict(v) for g,v in sorted(s["conditional"].items())}}
 sources=sorted(stats);overlap=[]
 for i,a in enumerate(sources):
  for b in sources[i+1:]:
   shared=sorted(set(sec[a])&set(sec[b]));inter=union=0
   for ep in shared:
    aa=sec[a][ep];bb=sec[b][ep];inter+=len(aa&bb);union+=len(aa|bb)
   overlap.append({"source_a":a,"source_b":b,"shared_episode_count":len(shared),"candidate_jaccard":inter/union if union else None,"intersection_candidate_observations":inter,"union_candidate_observations":union})
 return {"event_count":len(enriched),"episode_count":len(by_ep),"source_stats":stats,"pairwise_candidate_overlap":overlap,"events":enriched}
def aggregate(events:Sequence[Mapping[str,Any]])->dict[str,Any]:
 rows=[_valid_event(x) for x in events];keys=[(x["episode_id"],x["action_id"]) for x in rows]
 if len(keys)!=len(set(keys)):raise ValueError("DUPLICATE_EPISODE_ACTION_EVENT")
 glob=_aggregate_rows(rows);by=defaultdict(list)
 for r in rows:by[r["task_class"]].append(r)
 ca={tc:_aggregate_rows(rs) for tc,rs in sorted(by.items())}
 return {"schema":SCHEMA,"status":"CALIBRATED_FROM_CONTEXT_CONDITIONED_LIVE_RETRIEVAL_EVENTS",
  "event_count":glob["event_count"],"episode_count":glob["episode_count"],"task_class_count":len(ca),
  "source_stats":glob["source_stats"],"pairwise_candidate_overlap":glob["pairwise_candidate_overlap"],
  "task_class_source_stats":{tc:x["source_stats"] for tc,x in ca.items()},
  "task_class_pairwise_candidate_overlap":{tc:x["pairwise_candidate_overlap"] for tc,x in ca.items()},
  "task_class_episode_counts":{tc:x["episode_count"] for tc,x in ca.items()},"events":glob["events"],
  "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,
  "execution_authority":False,"promotion_authority":False,
  "hard_rules":["EVENTS_ARE_APPEND_ONLY_OBSERVATIONS","EVERY_EPISODE_HAS_EXACTLY_ONE_TASK_CLASS",
   "LIVE_SOURCE_QUALITY_IS_MEASURED_GLOBALLY_AND_BY_TASK_CLASS",
   "TASK_CLASS_STATS_OVERRIDE_GLOBAL_STATS_WHEN_TASK_CLASS_HAS_MEASURED_ATTEMPTS",
   "GLOBAL_STATS_ARE_ONLY_A_COLD_START_FALLBACK_FOR_UNMEASURED_TASK_CLASSES",
   "NOVELTY_IS_CAUSAL_RELATIVE_TO_EARLIER_ACTIONS_IN_THE_SAME_EPISODE",
   "SOURCE_CORRELATION_IS_MEASURED_FROM_CANDIDATE_OVERLAP","SUFFICIENT_WITNESS_EVENTS_REQUIRE_INDEPENDENT_RECEIPTS",
   "NO_RETRIEVAL_EVENT_SELF_GRANTS_ACCEPTANCE_OR_CAPABILITY_CREDIT"]}
def load_jsonl(path:Path)->list[dict[str,Any]]:
 if not path.exists():return []
 return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
if __name__=="__main__":
 root=Path(__file__).resolve().parents[2]
 print(json.dumps(aggregate(load_jsonl(root/"canonical/state/retrieval_live_events_v2.jsonl")),indent=2,sort_keys=True))
