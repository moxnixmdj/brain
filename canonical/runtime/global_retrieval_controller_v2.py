#!/usr/bin/env python3
"""Empirically calibrated global retrieval controller V2.

V2 preserves V1's monotonic candidate memory, bounded queryless enumeration and
open-world UNKNOWN firewall, but replaces fixed source-correlation multipliers
with measured event statistics when available.

Live-provider routing is calibrated only from live provider events. The finite
hidden-witness arena is a regression/architecture benchmark and is not silently
treated as a provider-performance oracle.
"""
from __future__ import annotations

import math
import statistics
from typing import Any, Mapping, Sequence

from canonical.runtime import global_retrieval_controller_v1 as base

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_CONTROLLER_V2"


def _beta_mean(successes:int,trials:int)->float:
    successes=max(0,min(int(successes),int(trials)))
    trials=max(0,int(trials))
    return (successes+0.5)/(trials+1.0)


def empirical_components(
    stats: Mapping[str,Any],
    *,
    consumed_upstream_groups: Sequence[str]=(),
    upstream_group: str="",
    imputed_latency_seconds: float=1.0,
    imputed_requests: float=1.0,
)->dict[str,Any]:
    attempts=max(0,int(stats.get("attempts") or 0))
    failures=max(0,min(attempts,int(stats.get("failures") or 0)))
    novel=max(0,min(attempts,int(stats.get("novel_candidate_actions") or 0)))
    sufficient=max(0,min(attempts,int(stats.get("sufficient_witness_actions") or 0)))

    p_novel=_beta_mean(novel,attempts)
    # A sufficient-witness action may occasionally be useful even if its
    # candidate was previously seen, so condition on attempts rather than
    # falsely forcing sufficient<=novel.
    p_sufficient=_beta_mean(sufficient,attempts)
    p_reliable=_beta_mean(attempts-failures,attempts)

    consumed={str(x) for x in consumed_upstream_groups if str(x)}
    conditional=stats.get("conditional_after_upstream_group") or {}
    conditional_rows=[]
    if consumed:
        for group in sorted(consumed):
            row=conditional.get(group) if isinstance(conditional,Mapping) else None
            if isinstance(row,Mapping):
                tr=max(0,int(row.get("attempts") or 0))
                su=max(0,min(tr,int(row.get("novel_candidate_actions") or 0)))
                mean=_beta_mean(su,tr)
                conditional_rows.append({
                    "upstream_group":group,
                    "attempts":tr,
                    "novel_candidate_actions":su,
                    "posterior_mean":mean,
                    "measured":tr>0,
                })
            else:
                conditional_rows.append({
                    "upstream_group":group,
                    "attempts":0,
                    "novel_candidate_actions":0,
                    "posterior_mean":0.5,
                    "measured":False,
                })
        # Pairwise conditionals are not a joint probability. Using the minimum
        # measured/Jeffreys value is conservative and explicitly approximate.
        conditional_factor=min(x["posterior_mean"] for x in conditional_rows)
    else:
        conditional_factor=1.0

    expected=p_novel*p_sufficient*p_reliable*conditional_factor
    measured_latency=float(stats.get("mean_latency_seconds") or 0.0)
    measured_requests=float(stats.get("mean_requests") or 0.0)
    latency=measured_latency if attempts>0 and measured_latency>0 else max(1e-6,float(imputed_latency_seconds))
    requests=measured_requests if attempts>0 else max(0.0,float(imputed_requests))

    return {
        "attempts":attempts,
        "p_novel_candidate_action":p_novel,
        "p_sufficient_witness_action":p_sufficient,
        "p_reliable_execution":p_reliable,
        "conditional_novelty_factor":conditional_factor,
        "conditional_rows":conditional_rows,
        "expected_sufficient_witness_factor":expected,
        "latency_seconds":latency,
        "latency_measured":bool(attempts>0 and measured_latency>0),
        "mean_requests":requests,
        "requests_measured":bool(attempts>0),
        "expected_sufficient_witness_per_second":expected/latency,
        "cold_start":attempts==0,
        "upstream_group":upstream_group,
    }


def rank_actions_empirical(
    actions: Sequence[Mapping[str,Any]],
    *,
    source_stats: Mapping[str,Mapping[str,Any]]|None=None,
    consumed_upstream_groups: Sequence[str]=(),
)->list[dict[str,Any]]:
    source_stats=source_stats or {}
    observed_latencies=[
        float(x.get("mean_latency_seconds") or 0.0)
        for x in source_stats.values()
        if isinstance(x,Mapping) and int(x.get("attempts") or 0)>0 and float(x.get("mean_latency_seconds") or 0.0)>0
    ]
    observed_requests=[
        float(x.get("mean_requests") or 0.0)
        for x in source_stats.values()
        if isinstance(x,Mapping) and int(x.get("attempts") or 0)>0
    ]
    imputed_latency=statistics.median(observed_latencies) if observed_latencies else 1.0
    imputed_requests=statistics.median(observed_requests) if observed_requests else 1.0

    ranked=[]
    for raw in actions:
        row=dict(raw)
        source=base._canon(row.get("source_id") or row.get("domain") or row.get("backend_id"))
        group=base._canon(row.get("upstream_group") or source)
        stat=source_stats.get(source) or source_stats.get(group) or {}
        comp=empirical_components(
            stat,
            consumed_upstream_groups=consumed_upstream_groups,
            upstream_group=group,
            imputed_latency_seconds=imputed_latency,
            imputed_requests=imputed_requests,
        )
        row["retrieval_priority_v2"]=comp
        ranked.append(row)

    # Probability/time is the primary quantity. Request count is a zero-spend
    # rate-limit burden and is used as a deterministic tiebreak, not blended
    # through an invented conversion constant.
    ranked.sort(key=lambda x:(
        -float(x["retrieval_priority_v2"]["expected_sufficient_witness_per_second"]),
        float(x["retrieval_priority_v2"]["mean_requests"]),
        str(x.get("action_id") or ""),
    ))
    return ranked


def compile_global_plan(
    *,
    query_actions: Sequence[Mapping[str,Any]],
    sources: Sequence[Mapping[str,Any]],
    live_calibration: Mapping[str,Any]|None=None,
    state: Mapping[str,Any]|None=None,
)->dict[str,Any]:
    state=state or base.new_state()
    live_calibration=live_calibration or {}
    source_stats=live_calibration.get("source_stats") if isinstance(live_calibration,Mapping) else {}
    if not isinstance(source_stats,Mapping):
        source_stats={}

    queryless=base.compile_queryless_enumeration(sources)
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
        row.setdefault("upstream_group",base._canon(src.get("upstream_group")) or source)
        row.setdefault("candidate_authority","CANDIDATE_ONLY")
        row["nonexistence_claim_authorized"]=False
        actions.append(row)
    actions.extend(queryless)

    ranked=rank_actions_empirical(
        actions,
        source_stats=source_stats,
        consumed_upstream_groups=state.get("consumed_upstream_groups") or [],
    )
    event_count=int(live_calibration.get("event_count") or 0) if isinstance(live_calibration,Mapping) else 0
    return {
        "schema":SCHEMA,
        "status":"COMPILED_EMPIRICALLY_CALIBRATED_GLOBAL_RETRIEVAL_PLAN",
        "actions":ranked,
        "query_action_count":len(actions)-len(queryless),
        "queryless_enumeration_action_count":len(queryless),
        "candidate_memory_monotonic":True,
        "open_world_nonexistence_claim_authorized":False,
        "live_event_count":event_count,
        "live_calibration_state":"MEASURED" if event_count>0 else "COLD_START_JEFFREYS_PRIOR",
        "fixed_correlation_multiplier_used":False,
        "fixed_source_independence_multiplier_used":False,
        "incremental_spend_usd":0,
        "hard_rules":[
            "NO_SINGLE_SEARCH_ENGINE_IS_COMPLETENESS_AUTHORITY",
            "QUERYLESS_ENUMERATION_ONLY_FOR_BOUNDED_AUTHORITATIVE_INTERFACES",
            "DISCOVERED_CANDIDATES_REMAIN_MONOTONIC",
            "SOURCE_CORRELATION_COMES_FROM_LIVE_EVENT_EVIDENCE_WHEN_AVAILABLE",
            "UNMEASURED_SOURCE_RELATIONS_USE_EXPLICIT_JEFFREYS_COLD_START_NOT_FAKE_INDEPENDENCE",
            "PAIRWISE_CONDITIONALS_ARE_NOT_MISREPRESENTED_AS_EXACT_JOINT_PROBABILITIES",
            "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
            "STOP_ON_FIRST_INDEPENDENTLY_VERIFIED_SUFFICIENT_WITNESS",
        ],
    }
