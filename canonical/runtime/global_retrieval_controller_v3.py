#!/usr/bin/env python3
"""Route × strategy empirical global retrieval controller V3.

V3 fixes a core identification error: a provider is not a retrieval strategy.
Performance is calibrated on provider_route::query_strategy. A weak raw query
therefore cannot poison a provider whose structured/anchor route works well.

Unknown strategies receive explicit Jeffreys cold-start priors. Directional
conditional recovery is used only when measured on shared labeled cases.
"""
from __future__ import annotations

import statistics
from typing import Any, Mapping, Sequence

from canonical.runtime import global_retrieval_controller_v1 as base

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_CONTROLLER_V3"

def _beta_mean(successes:int,trials:int)->float:
    trials=max(0,int(trials)); successes=max(0,min(trials,int(successes)))
    return (successes+0.5)/(trials+1.0)

def route_key(action:Mapping[str,Any])->str:
    provider=base._canon(
        action.get("provider_route")
        or action.get("source_id")
        or action.get("domain")
        or action.get("backend_id")
    )
    strategy=base._canon(action.get("strategy_id") or action.get("query_family") or "RAW_UNSPECIFIED")
    return f"{provider}::{strategy}"

def _conditional_recovery(
    calibration:Mapping[str,Any],
    *,
    candidate_route:str,
    consumed_route_keys:Sequence[str],
)->dict[str,Any]:
    rows=calibration.get("directional_conditional_recovery") or []
    by_pair={}
    for row in rows:
        if isinstance(row,Mapping):
            by_pair[(str(row.get("route_a")),str(row.get("route_b")))]=row
    measured=[]
    for prior in consumed_route_keys:
        row=by_pair.get((str(prior),candidate_route))
        if not isinstance(row,Mapping):
            measured.append({
                "after_route":str(prior),"measured":False,
                "a_miss_count":0,"recovered":0,"posterior_mean":0.5,
            })
            continue
        trials=max(0,int(row.get("a_miss_count") or 0))
        successes=max(0,min(trials,int(row.get("b_recovery_after_a_miss_count") or 0)))
        measured.append({
            "after_route":str(prior),"measured":trials>0,
            "a_miss_count":trials,"recovered":successes,
            "posterior_mean":_beta_mean(successes,trials) if trials>0 else 0.5,
        })
    factor=min((x["posterior_mean"] for x in measured),default=1.0)
    return {"factor":factor,"rows":measured}

def empirical_components(
    action:Mapping[str,Any],
    calibration:Mapping[str,Any],
    *,
    consumed_route_keys:Sequence[str]=(),
    default_latency_seconds:float=1.0,
)->dict[str,Any]:
    key=route_key(action)
    stats=calibration.get("route_strategy_stats") or {}
    row=stats.get(key) if isinstance(stats,Mapping) else None

    if isinstance(row,Mapping) and int(row.get("labeled_recall_trial_count") or 0)>0:
        trials=int(row["labeled_recall_trial_count"])
        hits=int(row.get("target_hit_count") or 0)
        p_hit=_beta_mean(hits,trials)
        evidence_state="MEASURED_ROUTE_STRATEGY"
    else:
        trials=0; hits=0; p_hit=0.5
        evidence_state="COLD_START_JEFFREYS_ROUTE_STRATEGY"

    if isinstance(row,Mapping):
        usable=max(0,int(row.get("usable_transport_count") or 0))
        failures=max(0,int(row.get("transport_failure_count") or 0))
        transport_trials=usable+failures
        p_reliable=_beta_mean(usable,transport_trials) if transport_trials else 0.5
        latency_ms=row.get("mean_latency_ms")
        latency=float(latency_ms)/1000.0 if isinstance(latency_ms,(int,float)) and float(latency_ms)>0 else default_latency_seconds
        requests=float(row.get("mean_request_count") or 1.0)
        pool=float(row.get("mean_candidate_pool_size") or 0.0)
    else:
        p_reliable=0.5; latency=default_latency_seconds; requests=1.0; pool=0.0

    cond=_conditional_recovery(
        calibration,candidate_route=key,consumed_route_keys=consumed_route_keys
    )
    expected=p_hit*p_reliable*float(cond["factor"])
    return {
        "route_key":key,
        "evidence_state":evidence_state,
        "labeled_trials":trials,
        "labeled_hits":hits,
        "p_target_hit":p_hit,
        "p_reliable_transport":p_reliable,
        "conditional_recovery_factor":cond["factor"],
        "conditional_recovery_rows":cond["rows"],
        "expected_recovery_factor":expected,
        "latency_seconds":latency,
        "mean_request_count":requests,
        "mean_candidate_pool_size":pool,
        "expected_recovery_per_second":expected/max(latency,1e-6),
    }

def rank_actions(
    actions:Sequence[Mapping[str,Any]],
    *,
    calibration:Mapping[str,Any],
    consumed_route_keys:Sequence[str]=(),
)->list[dict[str,Any]]:
    observed=[
        float(x.get("mean_latency_ms"))/1000.0
        for x in (calibration.get("route_strategy_stats") or {}).values()
        if isinstance(x,Mapping) and isinstance(x.get("mean_latency_ms"),(int,float))
        and float(x.get("mean_latency_ms"))>0
    ]
    default_latency=statistics.median(observed) if observed else 1.0
    out=[]
    for raw in actions:
        row=dict(raw)
        comp=empirical_components(
            row,calibration,
            consumed_route_keys=consumed_route_keys,
            default_latency_seconds=default_latency,
        )
        row["retrieval_priority_v3"]=comp
        out.append(row)
    out.sort(key=lambda x:(
        -float(x["retrieval_priority_v3"]["expected_recovery_per_second"]),
        float(x["retrieval_priority_v3"]["mean_request_count"]),
        float(x["retrieval_priority_v3"]["mean_candidate_pool_size"]),
        str(x.get("action_id") or ""),
    ))
    return out

def compile_global_plan(
    *,
    query_actions:Sequence[Mapping[str,Any]],
    sources:Sequence[Mapping[str,Any]],
    route_strategy_calibration:Mapping[str,Any],
    state:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    state=state or base.new_state()
    source_by_id={
        base._canon(x.get("source_id")):x
        for x in sources if isinstance(x,Mapping) and base._canon(x.get("source_id"))
    }
    actions=[]
    for raw in query_actions:
        row=dict(raw)
        source=base._canon(row.get("source_id") or row.get("domain") or row.get("backend_id"))
        src=source_by_id.get(source,{})
        row.setdefault("action","QUERY_SOURCE")
        row.setdefault("source_id",source)
        row.setdefault("provider_route",source)
        row.setdefault("strategy_id",base._canon(row.get("query_family")) or "RAW_UNSPECIFIED")
        row.setdefault("upstream_group",base._canon(src.get("upstream_group")) or source)
        row.setdefault("candidate_authority","CANDIDATE_ONLY")
        row["nonexistence_claim_authorized"]=False
        actions.append(row)

    queryless=base.compile_queryless_enumeration(sources)
    for row in queryless:
        row["provider_route"]=row.get("source_id")
        row["strategy_id"]="QUERYLESS_BOUNDED_ENUMERATION"
    actions.extend(queryless)

    consumed_routes=state.get("consumed_route_keys") or []
    ranked=rank_actions(
        actions,
        calibration=route_strategy_calibration,
        consumed_route_keys=consumed_routes,
    )
    return {
        "schema":SCHEMA,
        "status":"COMPILED_ROUTE_STRATEGY_EMPIRICAL_GLOBAL_RETRIEVAL_PLAN",
        "actions":ranked,
        "query_action_count":len(actions)-len(queryless),
        "queryless_enumeration_action_count":len(queryless),
        "route_strategy_event_count":int(route_strategy_calibration.get("event_count") or 0),
        "provider_only_calibration_forbidden":True,
        "fixed_provider_multiplier_used":False,
        "fixed_strategy_multiplier_used":False,
        "open_world_nonexistence_claim_authorized":False,
        "incremental_spend_usd":0,
        "hard_rules":[
            "PROVIDER_ROUTE_AND_QUERY_STRATEGY_ARE_JOINT_ROUTING_IDENTITIES",
            "UNKNOWN_ROUTE_STRATEGIES_USE_EXPLICIT_JEFFREYS_COLD_START",
            "DIRECTIONAL_CONDITIONAL_RECOVERY_USES_ONLY_SHARED_LABELED_LIVE_CASES",
            "PAIRWISE_RECOVERY_IS_NOT_MISREPRESENTED_AS_EXACT_JOINT_PROBABILITY",
            "MORE_QUERIES_OR_DEEPER_WINDOWS_REQUIRE_EMPIRICAL_JUSTIFICATION",
            "QUERYLESS_ENUMERATION_REMAINS_AVAILABLE_FOR_BOUNDED_AUTHORITATIVE_SOURCES",
            "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
            "STOP_ON_FIRST_INDEPENDENTLY_VERIFIED_SUFFICIENT_WITNESS",
        ],
    }
