#!/usr/bin/env python3
"""Empirical calibration for retrieval-route ordering.

Replaces hand-tuned independence/novelty multipliers with measurements whenever
a labeled replay or live event stream exists.  It supports:
- Beta posterior success estimates;
- conditional recovery after already-selected routes;
- measured overlap/correlation of route hits;
- greedy next-route ordering by posterior conditional recovery per measured
  latency/request burden.

This module does not claim that finite-arena calibration transfers perfectly to
open-world providers.  Live provider events must eventually supersede arena
priors for live routing.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import retrieval_real_hidden_witness_arena_v1 as arena

SCHEMA="PROJECT_BRAIN_RETRIEVAL_EMPIRICAL_CALIBRATION_V1"


def _beta(successes:int, trials:int, *, alpha:float=0.5, beta:float=0.5)->dict[str,float]:
    if trials < 0 or successes < 0 or successes > trials:
        raise ValueError("INVALID_BINOMIAL_COUNTS")
    a=successes+alpha
    b=(trials-successes)+beta
    mean=a/(a+b)
    # Variance of Beta(a,b).
    var=(a*b)/(((a+b)**2)*(a+b+1.0))
    return {
        "alpha":a,
        "beta":b,
        "mean":mean,
        "stddev":math.sqrt(var),
    }


def calibrate_hit_sets(
    *,
    case_ids: Sequence[str],
    route_hit_case_ids: Mapping[str,Sequence[str]],
    route_mean_latency_ms: Mapping[str,float],
    route_mean_requests: Mapping[str,float] | None=None,
)->dict[str,Any]:
    cases={str(x) for x in case_ids}
    if not cases:
        raise ValueError("NONEMPTY_CASE_UNIVERSE_REQUIRED")
    route_mean_requests=route_mean_requests or {}
    routes=sorted(str(x) for x in route_hit_case_ids)
    hits:dict[str,set[str]]={}
    for route in routes:
        hs={str(x) for x in route_hit_case_ids.get(route) or []}
        outside=hs-cases
        if outside:
            raise ValueError("HIT_OUTSIDE_CASE_UNIVERSE:"+route)
        hits[route]=hs

    standalone={}
    for route in routes:
        n=len(cases); s=len(hits[route])
        post=_beta(s,n)
        standalone[route]={
            "successes":s,
            "trials":n,
            "posterior":post,
            "mean_latency_ms":max(0.000001,float(route_mean_latency_ms.get(route) or 0.000001)),
            "mean_requests":max(0.0,float(route_mean_requests.get(route) or 0.0)),
        }

    overlap=[]
    for i,a in enumerate(routes):
        for b in routes[i+1:]:
            union=hits[a]|hits[b]
            inter=hits[a]&hits[b]
            overlap.append({
                "route_a":a,
                "route_b":b,
                "jaccard_success_overlap":len(inter)/len(union) if union else 0.0,
                "shared_successes":len(inter),
                "a_unique_successes":len(hits[a]-hits[b]),
                "b_unique_successes":len(hits[b]-hits[a]),
            })

    remaining=set(cases)
    unused=set(routes)
    order=[]
    covered=set()
    while unused:
        choices=[]
        for route in sorted(unused):
            cond_hits=hits[route]&remaining
            trials=len(remaining)
            post=_beta(len(cond_hits),trials) if trials else _beta(0,0)
            latency=max(0.000001,float(route_mean_latency_ms.get(route) or 0.000001))
            requests=max(0.0,float(route_mean_requests.get(route) or 0.0))
            # All weights are observable quantities except the transparent unit
            # conversion of one request to one millisecond-equivalent burden.
            burden=latency+requests
            utility=post["mean"]/burden
            choices.append((utility,route,cond_hits,post,burden))
        choices.sort(key=lambda x:(-x[0],x[1]))
        utility,route,cond_hits,post,burden=choices[0]
        order.append({
            "position":len(order)+1,
            "route":route,
            "remaining_before":len(remaining),
            "new_successes":len(cond_hits),
            "conditional_recovery_posterior":post,
            "measured_burden":burden,
            "utility":utility,
        })
        covered|=cond_hits
        remaining-=cond_hits
        unused.remove(route)

    return {
        "schema":SCHEMA,
        "status":"CALIBRATED_FROM_LABELED_HIT_SETS",
        "case_count":len(cases),
        "routes":routes,
        "standalone":standalone,
        "pairwise_success_overlap":overlap,
        "empirical_route_order":order,
        "covered_case_count":len(covered),
        "uncovered_case_count":len(remaining),
        "coverage":len(covered)/len(cases),
        "prior":"JEFFREYS_BETA_0_5_0_5",
        "hard_rules":[
            "ROUTE_CORRELATION_IS_MEASURED_FROM_SHARED_SUCCESSES_NOT_ASSUMED",
            "CONDITIONAL_RECOVERY_IS_MEASURED_ON_REMAINING_CASES",
            "ARENA_LATENCY_IS_LOCAL_RANKING_LATENCY_NOT_PROVIDER_NETWORK_LATENCY",
            "LIVE_PROVIDER_EVENTS_MUST_SUPERSEDE_ARENA_PRIORS_FOR_LIVE_PROVIDER_ROUTING",
            "NO_FINITE_CALIBRATION_TO_OPEN_WORLD_COMPLETENESS_INFERENCE",
        ],
    }


def calibrate_arena(root:Path)->dict[str,Any]:
    result=arena.evaluate(root)
    case_ids=[]
    # The hit-id union does not include cases missed by all routes, so reconstruct
    # the full finite case universe deterministically from catalog size/profiles/
    # query count.
    catalog=arena.load_catalog(root)["targets"]
    for profile in arena.PROFILES:
        for target in catalog:
            for qi,_ in enumerate(target.get("behavioral_queries") or []):
                case_ids.append(f"{profile}:{target['id']}:Q{qi}")
    latencies={
        route:float(result["metrics"][route]["mean_local_ranking_latency_ms"])
        for route in arena.ROUTES
    }
    calibrated=calibrate_hit_sets(
        case_ids=case_ids,
        route_hit_case_ids=result["route_top1_hit_case_ids"],
        route_mean_latency_ms=latencies,
    )
    return {
        "schema":"PROJECT_BRAIN_RETRIEVAL_REAL_HIDDEN_WITNESS_CALIBRATION_V1",
        "status":"MEASURED_FROM_REAL_PINNED_TARGET_REPLAY",
        "arena":{
            "target_count":result["catalog_target_count"],
            "case_count":result["case_count"],
            "hybrid_top1_misses":result["hybrid_top1_misses"],
            "hybrid_top3_misses":result["hybrid_top3_misses"],
            "metrics":result["metrics"],
            "profile_metrics":result["profile_metrics"],
            "monotonic_pooled_candidate_metrics":result["monotonic_pooled_candidate_metrics"],
        },
        "calibration":calibrated,
        "open_world_completeness_claim":False,
        "live_provider_calibration_complete":False,
        "incremental_spend_usd":0,
    }


def main()->int:
    root=Path(__file__).resolve().parents[2]
    print(json.dumps(calibrate_arena(root),indent=2,sort_keys=True,ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
