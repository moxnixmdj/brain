#!/usr/bin/env python3
"""Evidence ledger and calibration for live retrieval actions.

Events are append-only observations from actual retrieval attempts. The ledger
derives source statistics and source-pair overlap without assuming independence.

No event can grant acceptance or capability credit. A candidate may be marked
verified_sufficient only when an independent receipt id is present.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_EVENT_LEDGER_V1"


def _s(x:Any)->str:
    return " ".join(str(x or "").strip().split())


def _valid_event(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping):
        raise ValueError("EVENT_MAPPING_REQUIRED")
    episode=_s(raw.get("episode_id"))
    source=_s(raw.get("source_id"))
    group=_s(raw.get("upstream_group") or source)
    action=_s(raw.get("action_id"))
    if not episode or not source or not action:
        raise ValueError("EVENT_IDENTITY_FIELDS_REQUIRED")
    status=_s(raw.get("status")).upper()
    if status not in {"SUCCESS","FAILED_RETRYABLE","FAILED_PERMANENT"}:
        raise ValueError("EVENT_STATUS_INVALID")
    candidates=sorted({_s(x) for x in (raw.get("candidate_ids") or []) if _s(x)})
    sufficient=sorted({_s(x) for x in (raw.get("verified_sufficient_candidate_ids") or []) if _s(x)})
    receipt=_s(raw.get("independent_receipt"))
    if sufficient and not receipt:
        raise ValueError("SUFFICIENT_EVENT_REQUIRES_INDEPENDENT_RECEIPT")
    outside=set(sufficient)-set(candidates)
    if outside:
        raise ValueError("SUFFICIENT_CANDIDATE_NOT_IN_EVENT_CANDIDATES")
    latency=max(0.0,float(raw.get("latency_seconds") or 0.0))
    requests=max(0,int(raw.get("request_count") or 0))
    sequence=max(0,int(raw.get("sequence") or 0))
    return {
        "episode_id":episode,
        "source_id":source,
        "upstream_group":group,
        "action_id":action,
        "sequence":sequence,
        "status":status,
        "candidate_ids":candidates,
        "verified_sufficient_candidate_ids":sufficient,
        "independent_receipt":receipt or None,
        "latency_seconds":latency,
        "request_count":requests,
    }


def aggregate(events:Sequence[Mapping[str,Any]])->dict[str,Any]:
    rows=[_valid_event(x) for x in events]
    keys=[(x["episode_id"],x["action_id"]) for x in rows]
    if len(keys)!=len(set(keys)):
        raise ValueError("DUPLICATE_EPISODE_ACTION_EVENT")

    # Novelty is defined causally within each episode: candidates not observed
    # by earlier actions in that episode.
    by_episode=defaultdict(list)
    for row in rows:
        by_episode[row["episode_id"]].append(row)
    enriched=[]
    for episode,ers in by_episode.items():
        seen=set()
        seen_groups=set()
        for row in sorted(ers,key=lambda x:(x["sequence"],x["action_id"])):
            item=dict(row)
            cand=set(row["candidate_ids"])
            new=sorted(cand-seen)
            item["novel_candidate_ids"]=new
            item["novel_candidate_action"]=bool(new)
            item["prior_upstream_groups"]=sorted(seen_groups)
            seen|=cand
            seen_groups.add(row["upstream_group"])
            enriched.append(item)

    per_source=defaultdict(lambda:{
        "attempts":0,"failures":0,"novel_candidate_actions":0,
        "sufficient_witness_actions":0,"latencies":[],"requests":[],
        "conditional":defaultdict(lambda:{"attempts":0,"novel_candidate_actions":0}),
    })
    source_episode_candidates=defaultdict(lambda:defaultdict(set))
    for row in enriched:
        s=per_source[row["source_id"]]
        s["attempts"]+=1
        if row["status"]!="SUCCESS":
            s["failures"]+=1
        if row["novel_candidate_action"]:
            s["novel_candidate_actions"]+=1
        if row["verified_sufficient_candidate_ids"]:
            s["sufficient_witness_actions"]+=1
        s["latencies"].append(row["latency_seconds"])
        s["requests"].append(row["request_count"])
        for group in row["prior_upstream_groups"]:
            q=s["conditional"][group]
            q["attempts"]+=1
            if row["novel_candidate_action"]:
                q["novel_candidate_actions"]+=1
        source_episode_candidates[row["source_id"]][row["episode_id"]]|=set(row["candidate_ids"])

    stats={}
    for source,s in per_source.items():
        stats[source]={
            "attempts":s["attempts"],
            "failures":s["failures"],
            "novel_candidate_actions":s["novel_candidate_actions"],
            "sufficient_witness_actions":s["sufficient_witness_actions"],
            "mean_latency_seconds":statistics.fmean(s["latencies"]) if s["latencies"] else 0.0,
            "mean_requests":statistics.fmean(s["requests"]) if s["requests"] else 0.0,
            "conditional_after_upstream_group":{
                group:dict(v) for group,v in sorted(s["conditional"].items())
            },
        }

    sources=sorted(stats)
    overlap=[]
    for i,a in enumerate(sources):
        for b in sources[i+1:]:
            shared_episodes=sorted(set(source_episode_candidates[a])&set(source_episode_candidates[b]))
            inter=union=0
            for ep in shared_episodes:
                aa=source_episode_candidates[a][ep]; bb=source_episode_candidates[b][ep]
                inter+=len(aa&bb); union+=len(aa|bb)
            overlap.append({
                "source_a":a,"source_b":b,
                "shared_episode_count":len(shared_episodes),
                "candidate_jaccard":inter/union if union else None,
                "intersection_candidate_observations":inter,
                "union_candidate_observations":union,
            })

    return {
        "schema":SCHEMA,
        "status":"CALIBRATED_FROM_LIVE_RETRIEVAL_EVENTS",
        "event_count":len(enriched),
        "episode_count":len(by_episode),
        "source_stats":stats,
        "pairwise_candidate_overlap":overlap,
        "events":enriched,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "EVENTS_ARE_APPEND_ONLY_OBSERVATIONS",
            "NOVELTY_IS_COMPUTED_RELATIVE_TO_EARLIER_ACTIONS_IN_THE_SAME_EPISODE",
            "SOURCE_CORRELATION_IS_MEASURED_FROM_CANDIDATE_OVERLAP",
            "SUFFICIENT_WITNESS_EVENTS_REQUIRE_INDEPENDENT_RECEIPTS",
            "NO_RETRIEVAL_EVENT_SELF_GRANTS_ACCEPTANCE_OR_CAPABILITY_CREDIT",
        ],
    }


def load_jsonl(path:Path)->list[dict[str,Any]]:
    if not path.exists():
        return []
    out=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        line=line.strip()
        if line:
            out.append(json.loads(line))
    return out


def main()->int:
    root=Path(__file__).resolve().parents[2]
    path=root/"canonical/state/retrieval_live_events_v1.jsonl"
    print(json.dumps(aggregate(load_jsonl(path)),indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
