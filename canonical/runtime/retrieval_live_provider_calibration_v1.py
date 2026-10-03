#!/usr/bin/env python3
"""Live-provider calibration for Brain retrieval.

Consumes recorded provider/query-family observations and computes:
- transport reliability separately from retrieval recall;
- hit@10 Beta posteriors for successful transports only;
- target-level coverage;
- measured latency where available;
- cross-route conditional recovery on overlapping labeled targets.

The module refuses to convert provider misses into nonexistence and keeps
provisional chat-tool observations separate from independently reproducible
provider truth.
"""
from __future__ import annotations
import json, math, statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_CALIBRATION_V1"

def beta(successes:int,trials:int,alpha:float=0.5,beta_:float=0.5)->dict[str,float]:
    if trials<0 or successes<0 or successes>trials:
        raise ValueError("INVALID_BINOMIAL_COUNTS")
    a=successes+alpha; b=(trials-successes)+beta_
    mean=a/(a+b)
    var=(a*b)/(((a+b)**2)*(a+b+1.0))
    return {"alpha":a,"beta":b,"mean":mean,"stddev":math.sqrt(var)}

def load_events(root:Path)->dict[str,Any]:
    p=root/"canonical/governance/RETRIEVAL_LIVE_PROVIDER_EVENTS_20261003_V1.json"
    obj=json.loads(p.read_text(encoding="utf-8"))
    if obj.get("schema")!="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_EVENTS_20261003_V1":
        raise ValueError("LIVE_EVENT_SCHEMA_INVALID")
    rows=obj.get("observations")
    if not isinstance(rows,list) or not rows:
        raise ValueError("LIVE_EVENTS_REQUIRED")
    return obj

def _key(row:Mapping[str,Any])->str:
    return f"{row.get('provider_route')}::{row.get('query_family')}"

def calibrate(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
    groups=defaultdict(list)
    for raw in rows:
        if not isinstance(raw,Mapping):
            raise ValueError("EVENT_MAPPING_REQUIRED")
        groups[_key(raw)].append(dict(raw))

    route_stats={}
    target_hits={}
    for key,events in sorted(groups.items()):
        success=[x for x in events if x.get("transport_status")=="SUCCESS"]
        failures=[x for x in events if x.get("transport_status")!="SUCCESS"]
        labeled=[x for x in success if isinstance(x.get("hit_at_10"),bool)]
        hits=[x for x in labeled if x.get("hit_at_10") is True]
        lat=[float(x["latency_ms"]) for x in success if isinstance(x.get("latency_ms"),(int,float))]
        reproducible=all(
            "NOT_INDEPENDENTLY_REPRODUCED" not in str(x.get("observation_authority") or "")
            and "PROVISIONAL" not in str(x.get("observation_authority") or "")
            for x in success
        ) if success else False
        route_stats[key]={
            "event_count":len(events),
            "transport_success_count":len(success),
            "transport_failure_count":len(failures),
            "transport_success_rate":len(success)/len(events) if events else 0.0,
            "recall_trial_count":len(labeled),
            "hit_at_10_count":len(hits),
            "hit_at_10_rate":len(hits)/len(labeled) if labeled else None,
            "hit_at_10_posterior":beta(len(hits),len(labeled)) if labeled else None,
            "mean_latency_ms":statistics.mean(lat) if lat else None,
            "median_latency_ms":statistics.median(lat) if lat else None,
            "latency_sample_count":len(lat),
            "independently_reproducible_provider_truth":reproducible,
            "miss_scope":"THIS_PROVIDER_X_QUERY_FAMILY_X_EPOCH_ONLY",
            "nonexistence_claim_authorized":False,
        }
        by_target=defaultdict(bool)
        for x in labeled:
            tid=str(x.get("target_id") or str(x.get("case_id") or "").split(":")[0])
            by_target[tid]=by_target[tid] or bool(x.get("hit_at_10"))
        target_hits[key]=dict(by_target)

    # Cross-route conditional recovery only over shared target IDs.
    pairs=[]
    keys=sorted(target_hits)
    for i,a in enumerate(keys):
        for b in keys[i+1:]:
            universe=set(target_hits[a]) & set(target_hits[b])
            if not universe:
                continue
            ah={t for t in universe if target_hits[a].get(t)}
            bh={t for t in universe if target_hits[b].get(t)}
            remaining=universe-ah
            recovered=bh & remaining
            pairs.append({
                "route_a":a,"route_b":b,
                "shared_target_count":len(universe),
                "a_hit_count":len(ah),"b_hit_count":len(bh),
                "shared_success_count":len(ah&bh),
                "b_unique_recovery_after_a":len(recovered),
                "b_conditional_recovery_rate_after_a":len(recovered)/len(remaining) if remaining else None,
                "success_jaccard":len(ah&bh)/len(ah|bh) if (ah|bh) else 0.0,
            })

    return {
        "schema":SCHEMA,
        "status":"CALIBRATED_FROM_RECORDED_LIVE_PROVIDER_EVENTS",
        "route_query_family_stats":route_stats,
        "pairwise_conditional_recovery":pairs,
        "hard_findings":{
            "transport_failures_excluded_from_recall_denominator":True,
            "provider_and_query_family_are_jointly_calibrated":True,
            "provider_miss_to_nonexistence_inference":False,
        },
        "routing_recommendations":[],
        "live_provider_calibration_complete":False,
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
    }

def derive_recommendations(cal:Mapping[str,Any])->list[dict[str,Any]]:
    stats=cal.get("route_query_family_stats") or {}
    out=[]
    for key,s in stats.items():
        trials=int(s.get("recall_trial_count") or 0)
        hits=int(s.get("hit_at_10_count") or 0)
        if trials>=10 and hits==0:
            out.append({
                "route_query_family":key,
                "action":"DEMOTE_AS_PRIMARY_UNKNOWN_IDENTITY_DISCOVERY_ROUTE",
                "reason":"ZERO_HITS_ON_AT_LEAST_10_SUCCESSFUL_TRANSPORT_LABELED_TRIALS",
                "retain_for":"KNOWN_IDENTITY_CONTENT_INSPECTION_OR_FUTURE_MATERIAL_WAKE",
                "disable":False,
            })
        elif trials>=10 and hits>0:
            out.append({
                "route_query_family":key,
                "action":"RETAIN_AS_CANDIDATE_GENERATOR",
                "reason":"NONZERO_LIVE_RECOVERY",
                "disable":False,
            })
        if int(s.get("transport_success_count") or 0)==0 and int(s.get("transport_failure_count") or 0)>0:
            out.append({
                "route_query_family":key,
                "action":"MARK_TRANSPORT_UNAVAILABLE_FOR_THIS_INTERFACE",
                "reason":"NO_SUCCESSFUL_TRANSPORTS",
                "disable":False,
            })
    return out

def calibrate_repository(root:Path)->dict[str,Any]:
    obj=load_events(root)
    out=calibrate(obj["observations"])
    out["catalog"]=obj.get("catalog")
    out["routing_recommendations"]=derive_recommendations(out)
    return out

def main()->int:
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(calibrate_repository(root),indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
