#!/usr/bin/env python3
"""Entity-resolution-aware, task-conditioned live retrieval ledger V3."""
from __future__ import annotations
import json,statistics
from collections import defaultdict
from pathlib import Path
from typing import Any,Mapping,Sequence
SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_EVENT_LEDGER_V3"
def _s(x:Any)->str:return " ".join(str(x or "").strip().split())
def _valid(raw:Mapping[str,Any])->dict[str,Any]:
 if not isinstance(raw,Mapping):raise ValueError("EVENT_MAPPING_REQUIRED")
 ep=_s(raw.get("episode_id"));tc=_s(raw.get("task_class")).upper();src=_s(raw.get("source_id"));grp=_s(raw.get("upstream_group") or src);act=_s(raw.get("action_id"))
 if not all((ep,tc,src,act)):raise ValueError("EVENT_IDENTITY_FIELDS_REQUIRED")
 st=_s(raw.get("status")).upper()
 if st not in {"SUCCESS","FAILED_RETRYABLE","FAILED_PERMANENT"}:raise ValueError("EVENT_STATUS_INVALID")
 cand=sorted({_s(x) for x in raw.get("candidate_ids",[]) if _s(x)});suff=sorted({_s(x) for x in raw.get("verified_sufficient_candidate_ids",[]) if _s(x)})
 receipt=_s(raw.get("independent_receipt"))
 if suff and not receipt:raise ValueError("SUFFICIENT_EVENT_REQUIRES_INDEPENDENT_RECEIPT")
 if set(suff)-set(cand):raise ValueError("SUFFICIENT_CANDIDATE_NOT_IN_EVENT_CANDIDATES")
 em=raw.get("candidate_entities") or {}
 if not isinstance(em,Mapping):raise ValueError("CANDIDATE_ENTITIES_MAPPING_REQUIRED")
 entities={_s(k):_s(v) for k,v in em.items() if _s(k) and _s(v)}
 if set(entities)-set(cand):raise ValueError("ENTITY_MAPPING_CANDIDATE_NOT_IN_EVENT")
 return {"episode_id":ep,"task_class":tc,"source_id":src,"upstream_group":grp,"action_id":act,"sequence":max(0,int(raw.get("sequence") or 0)),"status":st,
  "candidate_ids":cand,"candidate_entities":entities,"verified_sufficient_candidate_ids":suff,"independent_receipt":receipt or None,
  "latency_seconds":max(0.0,float(raw.get("latency_seconds") or 0)),"request_count":max(0,int(raw.get("request_count") or 0))}
def _entities(row):return {row["candidate_entities"].get(cid,cid) for cid in row["candidate_ids"]}
def _agg(rows):
 by=defaultdict(list)
 for r in rows:by[r["episode_id"]].append(dict(r))
 enr=[]
 for ep,ers in by.items():
  if len({x["task_class"] for x in ers})!=1:raise ValueError("EPISODE_TASK_CLASS_MISMATCH:"+ep)
  seen=set();groups=set()
  for r in sorted(ers,key=lambda x:(x["sequence"],x["action_id"])):
   x=dict(r);es=_entities(r);new=sorted(es-seen);x["candidate_entity_ids"]=sorted(es);x["novel_entity_ids"]=new;x["novel_candidate_action"]=bool(new);x["prior_upstream_groups"]=sorted(groups)
   seen|=es;groups.add(r["upstream_group"]);enr.append(x)
 per=defaultdict(lambda:{"attempts":0,"failures":0,"novel_candidate_actions":0,"sufficient_witness_actions":0,"latencies":[],"requests":[],"conditional":defaultdict(lambda:{"attempts":0,"novel_candidate_actions":0})})
 sec=defaultdict(lambda:defaultdict(set))
 for r in enr:
  s=per[r["source_id"]];s["attempts"]+=1;s["failures"]+=int(r["status"]!="SUCCESS");s["novel_candidate_actions"]+=int(r["novel_candidate_action"]);s["sufficient_witness_actions"]+=int(bool(r["verified_sufficient_candidate_ids"]));s["latencies"].append(r["latency_seconds"]);s["requests"].append(r["request_count"])
  for g in r["prior_upstream_groups"]:
   q=s["conditional"][g];q["attempts"]+=1;q["novel_candidate_actions"]+=int(r["novel_candidate_action"])
  sec[r["source_id"]][r["episode_id"]]|=set(r["candidate_entity_ids"])
 stats={}
 for src,s in per.items():
  stats[src]={"attempts":s["attempts"],"failures":s["failures"],"novel_candidate_actions":s["novel_candidate_actions"],"sufficient_witness_actions":s["sufficient_witness_actions"],
   "mean_latency_seconds":statistics.fmean(s["latencies"]) if s["latencies"] else 0.0,"mean_requests":statistics.fmean(s["requests"]) if s["requests"] else 0.0,
   "conditional_after_upstream_group":{g:dict(v) for g,v in sorted(s["conditional"].items())}}
 sources=sorted(stats);overlap=[]
 for i,a in enumerate(sources):
  for b in sources[i+1:]:
   shared=sorted(set(sec[a])&set(sec[b]));inter=union=0
   for ep in shared:
    aa=sec[a][ep];bb=sec[b][ep];inter+=len(aa&bb);union+=len(aa|bb)
   overlap.append({"source_a":a,"source_b":b,"shared_episode_count":len(shared),"candidate_entity_jaccard":inter/union if union else None,"intersection_entity_observations":inter,"union_entity_observations":union})
 return {"event_count":len(enr),"episode_count":len(by),"source_stats":stats,"pairwise_candidate_overlap":overlap,"events":enr}
def aggregate(events:Sequence[Mapping[str,Any]])->dict[str,Any]:
 rows=[_valid(x) for x in events];keys=[(x["episode_id"],x["action_id"]) for x in rows]
 if len(keys)!=len(set(keys)):raise ValueError("DUPLICATE_EPISODE_ACTION_EVENT")
 glob=_agg(rows);by=defaultdict(list)
 for r in rows:by[r["task_class"]].append(r)
 ca={tc:_agg(rs) for tc,rs in sorted(by.items())}
 return {"schema":SCHEMA,"status":"CALIBRATED_FROM_ENTITY_RESOLVED_CONTEXT_CONDITIONED_LIVE_EVENTS","event_count":glob["event_count"],"episode_count":glob["episode_count"],"task_class_count":len(ca),
  "source_stats":glob["source_stats"],"pairwise_candidate_overlap":glob["pairwise_candidate_overlap"],"task_class_source_stats":{tc:x["source_stats"] for tc,x in ca.items()},
  "task_class_pairwise_candidate_overlap":{tc:x["pairwise_candidate_overlap"] for tc,x in ca.items()},"task_class_episode_counts":{tc:x["episode_count"] for tc,x in ca.items()},"events":glob["events"],
  "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,"ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,
  "hard_rules":["NOVELTY_AND_SOURCE_OVERLAP_USE_RESOLVED_ENTITY_IDS_WHERE_EXPLICITLY_VERIFIED","UNRESOLVED_CANDIDATES_REMAIN_SOURCE_SCOPED_AND_ARE_NEVER_HEURISTICALLY_MERGED",
   "TASK_CLASS_STATS_OVERRIDE_GLOBAL_STATS_WHEN_MEASURED","GLOBAL_STATS_ONLY_FALLBACK_FOR_UNMEASURED_TASK_CLASSES","SUFFICIENT_EVENTS_REQUIRE_INDEPENDENT_RECEIPTS","NO_EVENT_SELF_GRANTS_ACCEPTANCE_OR_CAPABILITY_CREDIT"]}
def load_jsonl(path:Path):
 if not path.exists():return []
 return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
if __name__=="__main__":
 root=Path(__file__).resolve().parents[2];print(json.dumps(aggregate(load_jsonl(root/"canonical/state/retrieval_live_events_v3.jsonl")),indent=2,sort_keys=True))
