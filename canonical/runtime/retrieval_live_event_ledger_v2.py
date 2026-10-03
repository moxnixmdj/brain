#!/usr/bin/env python3
"""Append-only live retrieval evidence ledger V2.

V2 separates retrieval attempts from later independent witness verification.

RETRIEVAL events measure:
- execution success/failure,
- latency and request burden,
- discovered candidate identities,
- conditional novelty after earlier actions in the same episode.

VERIFICATION events later bind an independently verified sufficient/non-sufficient
verdict back to the exact retrieval action that discovered the candidate. They
do not create another retrieval attempt, so source yield is not diluted or
inflated by delayed verification bookkeeping.

The ledger is append-only. Durable append uses an exclusive file lock when the
host supports fcntl and fsync before releasing it.
"""
from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_EVENT_LEDGER_V2"
RETRIEVAL="RETRIEVAL"
VERIFICATION="VERIFICATION"


def _s(x:Any)->str:
    return " ".join(str(x or "").strip().split())


def _retrieval(raw:Mapping[str,Any])->dict[str,Any]:
    episode=_s(raw.get("episode_id"))
    source=_s(raw.get("source_id"))
    group=_s(raw.get("upstream_group") or source)
    action=_s(raw.get("action_id"))
    if not episode or not source or not action:
        raise ValueError("RETRIEVAL_EVENT_IDENTITY_FIELDS_REQUIRED")
    status=_s(raw.get("status")).upper()
    if status not in {"SUCCESS","FAILED_RETRYABLE","FAILED_PERMANENT"}:
        raise ValueError("RETRIEVAL_EVENT_STATUS_INVALID")
    candidates=sorted({_s(x) for x in (raw.get("candidate_ids") or []) if _s(x)})
    return {
        "event_type":RETRIEVAL,
        "episode_id":episode,
        "source_id":source,
        "upstream_group":group,
        "action_id":action,
        "sequence":max(0,int(raw.get("sequence") or 0)),
        "status":status,
        "candidate_ids":candidates,
        "latency_seconds":max(0.0,float(raw.get("latency_seconds") or 0.0)),
        "request_count":max(0,int(raw.get("request_count") or 0)),
    }


def _verification(raw:Mapping[str,Any])->dict[str,Any]:
    episode=_s(raw.get("episode_id") or raw.get("parent_episode_id"))
    action=_s(raw.get("parent_action_id"))
    candidate=_s(raw.get("candidate_id"))
    receipt=_s(raw.get("independent_receipt"))
    verdict=_s(raw.get("verdict")).upper()
    if not episode or not action or not candidate or not receipt:
        raise ValueError("VERIFICATION_EVENT_BINDING_FIELDS_REQUIRED")
    if verdict not in {"SUFFICIENT","NOT_SUFFICIENT"}:
        raise ValueError("VERIFICATION_EVENT_VERDICT_INVALID")
    return {
        "event_type":VERIFICATION,
        "episode_id":episode,
        "parent_action_id":action,
        "candidate_id":candidate,
        "independent_receipt":receipt,
        "verdict":verdict,
    }


def normalize_event(raw:Mapping[str,Any])->dict[str,Any]:
    if not isinstance(raw,Mapping):
        raise ValueError("EVENT_MAPPING_REQUIRED")
    typ=_s(raw.get("event_type") or RETRIEVAL).upper()
    if typ==RETRIEVAL:
        return _retrieval(raw)
    if typ==VERIFICATION:
        return _verification(raw)
    raise ValueError("EVENT_TYPE_INVALID")


def aggregate(events:Sequence[Mapping[str,Any]])->dict[str,Any]:
    rows=[normalize_event(x) for x in events]
    retrievals=[x for x in rows if x["event_type"]==RETRIEVAL]
    verifications=[x for x in rows if x["event_type"]==VERIFICATION]

    rkeys=[(x["episode_id"],x["action_id"]) for x in retrievals]
    if len(rkeys)!=len(set(rkeys)):
        raise ValueError("DUPLICATE_RETRIEVAL_EPISODE_ACTION")
    vkeys=[(x["episode_id"],x["parent_action_id"],x["candidate_id"],x["independent_receipt"]) for x in verifications]
    if len(vkeys)!=len(set(vkeys)):
        raise ValueError("DUPLICATE_VERIFICATION_BINDING")

    retrieval_index={(x["episode_id"],x["action_id"]):x for x in retrievals}
    sufficient_actions:set[tuple[str,str]]=set()
    verification_bindings=[]
    for v in verifications:
        key=(v["episode_id"],v["parent_action_id"])
        parent=retrieval_index.get(key)
        if parent is None:
            raise ValueError("VERIFICATION_PARENT_RETRIEVAL_NOT_FOUND")
        if v["candidate_id"] not in set(parent["candidate_ids"]):
            raise ValueError("VERIFIED_CANDIDATE_NOT_DISCOVERED_BY_PARENT")
        if v["verdict"]=="SUFFICIENT":
            sufficient_actions.add(key)
        verification_bindings.append({
            **v,
            "source_id":parent["source_id"],
            "upstream_group":parent["upstream_group"],
        })

    by_episode=defaultdict(list)
    for row in retrievals:
        by_episode[row["episode_id"]].append(row)

    enriched=[]
    for episode,ers in by_episode.items():
        seen=set()
        seen_groups=set()
        for row in sorted(ers,key=lambda x:(x["sequence"],x["action_id"])):
            item=dict(row)
            cand=set(row["candidate_ids"])
            novel=sorted(cand-seen)
            item["novel_candidate_ids"]=novel
            item["novel_candidate_action"]=bool(novel)
            item["prior_upstream_groups"]=sorted(seen_groups)
            item["verified_sufficient_action"]=(row["episode_id"],row["action_id"]) in sufficient_actions
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
        if row["verified_sufficient_action"]:
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
            shared=sorted(set(source_episode_candidates[a])&set(source_episode_candidates[b]))
            inter=union=0
            for ep in shared:
                aa=source_episode_candidates[a][ep]; bb=source_episode_candidates[b][ep]
                inter+=len(aa&bb); union+=len(aa|bb)
            overlap.append({
                "source_a":a,"source_b":b,
                "shared_episode_count":len(shared),
                "candidate_jaccard":inter/union if union else None,
                "intersection_candidate_observations":inter,
                "union_candidate_observations":union,
            })

    return {
        "schema":SCHEMA,
        "status":"CALIBRATED_FROM_APPEND_ONLY_RETRIEVAL_AND_VERIFICATION_EVENTS",
        "event_count":len(rows),
        "retrieval_event_count":len(retrievals),
        "verification_event_count":len(verifications),
        "episode_count":len(by_episode),
        "source_stats":stats,
        "pairwise_candidate_overlap":overlap,
        "retrieval_events":enriched,
        "verification_bindings":verification_bindings,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "RETRIEVAL_AND_VERIFICATION_EVENTS_ARE_APPEND_ONLY",
            "NOVELTY_IS_CAUSAL_WITHIN_EPISODE_ORDER",
            "VERIFICATION_EVENTS_DO_NOT_COUNT_AS_NEW_RETRIEVAL_ATTEMPTS",
            "SUFFICIENT_WITNESS_YIELD_IS_ATTRIBUTED_TO_THE_DISCOVERY_SOURCE_ONLY_WITH_AN_INDEPENDENT_RECEIPT",
            "SOURCE_CORRELATION_IS_MEASURED_FROM_CANDIDATE_OVERLAP",
            "NO_EVENT_SELF_GRANTS_ACCEPTANCE_OR_CAPABILITY_CREDIT",
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


def append_event(path:Path,event:Mapping[str,Any])->dict[str,Any]:
    normalized=normalize_event(event)
    path.parent.mkdir(parents=True,exist_ok=True)
    # Locking is deliberately local to the file append. Hosts without fcntl
    # still receive append+flush+fsync semantics, but Linux is the verified path.
    with path.open("a+",encoding="utf-8") as fh:
        try:
            import fcntl
            fcntl.flock(fh.fileno(),fcntl.LOCK_EX)
        except ImportError:
            fcntl=None
        fh.seek(0)
        existing=[]
        for line in fh.read().splitlines():
            if line.strip():
                existing.append(json.loads(line))
        # Validate the entire future ledger before committing bytes.
        aggregate([*existing,normalized])
        fh.seek(0,os.SEEK_END)
        fh.write(json.dumps(normalized,sort_keys=True,separators=(",",":"))+"\n")
        fh.flush()
        os.fsync(fh.fileno())
        if fcntl is not None:
            fcntl.flock(fh.fileno(),fcntl.LOCK_UN)
    return normalized


def main()->int:
    root=Path(__file__).resolve().parents[2]
    path=root/"canonical/state/retrieval_live_events_v2.jsonl"
    print(json.dumps(aggregate(load_jsonl(path)),indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
