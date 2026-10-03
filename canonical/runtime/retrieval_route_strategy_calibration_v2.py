#!/usr/bin/env python3
"""Joint live retrieval calibration by provider route × query strategy.

Consumes only independently receipt-bound live-network observations. Provider
identity and query strategy are calibrated jointly so a weak query family
cannot poison a strong provider. Directional conditional recovery is measured
on shared labeled cases without assuming independence.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_RETRIEVAL_ROUTE_STRATEGY_CALIBRATION_V2"

EVENT_FILES=(
 "canonical/governance/RETRIEVAL_V10_LIVE_PROVIDER_EVENTS_20261004_V1.json",
 "canonical/governance/RETRIEVAL_V10_OPTIMIZED_LIVE_PROVIDER_EVENTS_20261004_V1.json",
 "canonical/governance/RETRIEVAL_V10_MULTI_QUERY_LIVE_PROVIDER_EVENTS_20261004_V1.json",
 "canonical/governance/RETRIEVAL_V10_DEEP_WINDOW_LIVE_PROVIDER_EVENTS_20261004_V1.json",
 "canonical/governance/RETRIEVAL_V10_VERIFIED_BRIDGED_LIVE_EVENTS_20261004_V1.json",
)

def _beta(successes:int,trials:int)->dict[str,float]:
    trials=max(0,int(trials)); successes=max(0,min(trials,int(successes)))
    a=successes+0.5; b=(trials-successes)+0.5
    mean=a/(a+b)
    var=(a*b)/(((a+b)**2)*(a+b+1.0))
    return {"alpha":a,"beta":b,"mean":mean,"stddev":math.sqrt(var)}

def _route_key(row:Mapping[str,Any])->str:
    return f"{row.get('provider_route')}::{row.get('query_family')}"

def _usable(row:Mapping[str,Any])->bool:
    return str(row.get("transport_status") or "").upper() in {"SUCCESS","PARTIAL_RETRYABLE"}

def _hit(row:Mapping[str,Any])->bool|None:
    if isinstance(row.get("hit_at_10"),bool):
        return bool(row["hit_at_10"])
    if isinstance(row.get("hit_at_pool"),bool):
        return bool(row["hit_at_pool"])
    return None

def load_repository_events(root:Path)->list[dict[str,Any]]:
    out=[]
    for rel in EVENT_FILES:
        p=root/rel
        if not p.exists():
            continue
        obj=json.loads(p.read_text(encoding="utf-8"))
        rows=obj.get("observations")
        if not isinstance(rows,list):
            raise ValueError("OBSERVATIONS_LIST_REQUIRED:"+rel)
        for row in rows:
            if not isinstance(row,Mapping):
                raise ValueError("OBSERVATION_MAPPING_REQUIRED:"+rel)
            item=dict(row)
            receipt=str(item.get("independent_receipt") or "").strip()
            authority=str(item.get("observation_authority") or "")
            if not receipt or "INDEPENDENT_PUBLIC_RUNNER_LIVE_NETWORK" not in authority:
                raise ValueError("NON_INDEPENDENT_LIVE_EVENT_REJECTED:"+rel)
            item["_source_file"]=rel
            out.append(item)
    if not out:
        raise ValueError("NO_INDEPENDENT_LIVE_PROVIDER_EVENTS")
    return out

def calibrate(rows:Sequence[Mapping[str,Any]])->dict[str,Any]:
    groups=defaultdict(list)
    case_route={}
    for raw in rows:
        if not isinstance(raw,Mapping):
            raise ValueError("EVENT_MAPPING_REQUIRED")
        row=dict(raw)
        key=_route_key(row)
        groups[key].append(row)
        case=str(row.get("case_id") or "")
        if case:
            case_route[(case,key)]=row

    route_stats={}
    for key,events in sorted(groups.items()):
        usable=[x for x in events if _usable(x)]
        failed=[x for x in events if not _usable(x)]
        labeled=[x for x in usable if _hit(x) is not None]
        hits=[x for x in labeled if _hit(x) is True]
        lat=[float(x.get("latency_ms") or 0.0) for x in usable if float(x.get("latency_ms") or 0.0)>0]
        req=[float(x.get("request_count") or 0.0) for x in usable]
        pools=[]
        for x in usable:
            if isinstance(x.get("candidate_pool_size"),(int,float)):
                pools.append(float(x["candidate_pool_size"]))
            elif isinstance(x.get("candidate_ids"),list):
                pools.append(float(len(x["candidate_ids"])))
        route_stats[key]={
          "provider_route":key.split("::",1)[0],
          "query_family":key.split("::",1)[1],
          "event_count":len(events),
          "usable_transport_count":len(usable),
          "transport_failure_count":len(failed),
          "labeled_recall_trial_count":len(labeled),
          "target_hit_count":len(hits),
          "target_hit_rate":len(hits)/len(labeled) if labeled else None,
          "target_hit_posterior":_beta(len(hits),len(labeled)) if labeled else None,
          "mean_latency_ms":statistics.fmean(lat) if lat else None,
          "mean_request_count":statistics.fmean(req) if req else None,
          "mean_candidate_pool_size":statistics.fmean(pools) if pools else None,
          "open_world_nonexistence_claim_authorized":False,
        }

    # Directional recovery: among cases A misses, how often B hits on the same case?
    keys=sorted(route_stats)
    conditional=[]
    for a in keys:
        for b in keys:
            if a==b:
                continue
            shared=sorted({
                case for (case,key) in case_route
                if key==a and (case,b) in case_route
            })
            labeled=[
                case for case in shared
                if _usable(case_route[(case,a)]) and _usable(case_route[(case,b)])
                and _hit(case_route[(case,a)]) is not None and _hit(case_route[(case,b)]) is not None
            ]
            a_misses=[c for c in labeled if _hit(case_route[(c,a)]) is False]
            recovered=[c for c in a_misses if _hit(case_route[(c,b)]) is True]
            if labeled:
                conditional.append({
                  "route_a":a,"route_b":b,
                  "shared_labeled_case_count":len(labeled),
                  "a_miss_count":len(a_misses),
                  "b_recovery_after_a_miss_count":len(recovered),
                  "b_conditional_recovery_rate_after_a_miss":len(recovered)/len(a_misses) if a_misses else None,
                })

    cases=sorted({str(x.get("case_id") or "") for x in rows if str(x.get("case_id") or "")})
    best_hits=[]
    misses=[]
    for case in cases:
        cr=[row for (c,_),row in case_route.items() if c==case and _usable(row) and _hit(row) is not None]
        if any(_hit(x) is True for x in cr):
            best_hits.append(case)
        elif cr:
            misses.append(case)

    return {
      "schema":SCHEMA,
      "status":"CALIBRATED_PROVIDER_ROUTE_X_QUERY_STRATEGY_FROM_INDEPENDENT_LIVE_EVENTS",
      "event_count":len(rows),
      "case_count":len(cases),
      "route_strategy_stats":route_stats,
      "directional_conditional_recovery":conditional,
      "best_known_strategy_union":{
        "labeled_case_count":len(best_hits)+len(misses),
        "hit_case_count":len(best_hits),
        "miss_case_count":len(misses),
        "hit_rate":len(best_hits)/(len(best_hits)+len(misses)) if (best_hits or misses) else None,
        "miss_case_ids":misses,
      },
      "provider_only_calibration_forbidden":True,
      "open_world_completeness_claim":False,
      "incremental_spend_usd":0,
      "hard_rules":[
        "PROVIDER_AND_QUERY_STRATEGY_ARE_JOINT_CALIBRATION_IDENTITIES",
        "TRANSPORT_FAILURES_ARE_EXCLUDED_FROM_RECALL_DENOMINATORS",
        "DIRECTIONAL_RECOVERY_IS_MEASURED_ON_SHARED_LABELED_CASES",
        "MORE_QUERIES_OR_DEEPER_WINDOWS_ARE_NOT_ASSUMED_BETTER_WITHOUT_EVIDENCE",
        "LIVE_ROUTE_MISS_NEVER_AUTHORIZES_NONEXISTENCE",
        "FINITE_LABELED_TASK_RECALL_IS_NOT_OPEN_WORLD_COMPLETENESS",
      ],
    }

def calibrate_repository(root:Path)->dict[str,Any]:
    return calibrate(load_repository_events(root))

def main()->int:
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(calibrate_repository(root),indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
