#!/usr/bin/env python3
"""Global retrieval controller V3: live novelty + labeled provider recovery.

V3 preserves V2's append-only live-event novelty calibration and adds a second,
orthogonal signal: frozen labeled hidden-target recovery by provider×query
family. This prevents a route that returns many irrelevant candidates from
looking useful merely because it is novel.

Unmeasured provider×query families retain the explicit Jeffreys prior (0.5).
Measured poor routes are demoted, never disabled. Open-world misses remain
UNKNOWN.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

from canonical.runtime import global_retrieval_controller_v1 as base
from canonical.runtime import global_retrieval_controller_v2 as v2

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_CONTROLLER_V3"

def _labeled_key(action:Mapping[str,Any])->str:
    provider=base._canon(action.get("provider_route") or action.get("source_id") or action.get("domain") or action.get("backend_id"))
    family=base._canon(action.get("query_family") or "UNMEASURED")
    return f"{provider}::{family}"

def _posterior_mean(stat:Mapping[str,Any]|None)->tuple[float,int,bool]:
    if not isinstance(stat,Mapping):
        return 0.5,0,False
    trials=max(0,int(stat.get("recall_trial_count") or 0))
    post=stat.get("hit_at_10_posterior")
    if trials>0 and isinstance(post,Mapping):
        return float(post.get("mean") or 0.5),trials,True
    return 0.5,0,False

def rank_actions_dual_empirical(
    actions:Sequence[Mapping[str,Any]],
    *,
    source_stats:Mapping[str,Mapping[str,Any]]|None=None,
    labeled_stats:Mapping[str,Mapping[str,Any]]|None=None,
    consumed_upstream_groups:Sequence[str]=(),
)->list[dict[str,Any]]:
    labeled_stats=labeled_stats or {}
    ranked=v2.rank_actions_empirical(
        actions,
        source_stats=source_stats or {},
        consumed_upstream_groups=consumed_upstream_groups,
    )
    out=[]
    for raw in ranked:
        row=dict(raw)
        key=_labeled_key(row)
        mean,trials,measured=_posterior_mean(labeled_stats.get(key))
        base_score=float(row["retrieval_priority_v2"]["expected_sufficient_witness_per_second"])
        row["retrieval_priority_v3"]={
            "provider_query_family_key":key,
            "labeled_recovery_posterior_mean":mean,
            "labeled_recovery_trials":trials,
            "labeled_recovery_measured":measured,
            "v2_open_world_novelty_sufficiency_per_second":base_score,
            "dual_empirical_score":base_score*mean,
            "hard_disable":False,
            "cold_start_prior":"JEFFREYS_BETA_0_5_0_5" if not measured else None,
        }
        out.append(row)
    out.sort(key=lambda x:(
        -float(x["retrieval_priority_v3"]["dual_empirical_score"]),
        float(x["retrieval_priority_v2"]["mean_requests"]),
        str(x.get("action_id") or ""),
    ))
    return out

def compile_global_plan(
    *,
    query_actions:Sequence[Mapping[str,Any]],
    sources:Sequence[Mapping[str,Any]],
    live_calibration:Mapping[str,Any]|None=None,
    labeled_calibration:Mapping[str,Any]|None=None,
    state:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    state=state or base.new_state()
    live_calibration=live_calibration or {}
    labeled_calibration=labeled_calibration or {}
    source_stats=live_calibration.get("source_stats") if isinstance(live_calibration,Mapping) else {}
    labeled_stats=labeled_calibration.get("route_query_family_stats") if isinstance(labeled_calibration,Mapping) else {}
    if not isinstance(source_stats,Mapping): source_stats={}
    if not isinstance(labeled_stats,Mapping): labeled_stats={}

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
        row.setdefault("provider_route",source)
        row.setdefault("query_family","UNMEASURED")
        row.setdefault("candidate_authority","CANDIDATE_ONLY")
        row["nonexistence_claim_authorized"]=False
        actions.append(row)
    for raw in queryless:
        row=dict(raw)
        row.setdefault("provider_route",row.get("source_id") or "BOUNDED_ENUMERATION")
        row.setdefault("query_family","QUERYLESS_BOUNDED_ENUMERATION")
        actions.append(row)

    ranked=rank_actions_dual_empirical(
        actions,
        source_stats=source_stats,
        labeled_stats=labeled_stats,
        consumed_upstream_groups=state.get("consumed_upstream_groups") or [],
    )
    return {
        "schema":SCHEMA,
        "status":"COMPILED_DUAL_EMPIRICALLY_CALIBRATED_GLOBAL_RETRIEVAL_PLAN",
        "actions":ranked,
        "query_action_count":len(actions)-len(queryless),
        "queryless_enumeration_action_count":len(queryless),
        "live_open_world_event_count":int(live_calibration.get("event_count") or 0),
        "labeled_route_query_family_count":len(labeled_stats),
        "labeled_provider_calibration_complete":bool(labeled_stats),
        "fixed_correlation_multiplier_used":False,
        "fixed_source_independence_multiplier_used":False,
        "candidate_memory_monotonic":True,
        "open_world_nonexistence_claim_authorized":False,
        "incremental_spend_usd":0,
        "hard_rules":[
            "OPEN_WORLD_NOVELTY_AND_LABELED_TARGET_RECOVERY_ARE_DISTINCT_EMPIRICAL_SIGNALS",
            "PROVIDER_AND_QUERY_FAMILY_ARE_CALIBRATED_JOINTLY",
            "UNMEASURED_PROVIDER_QUERY_FAMILIES_KEEP_EXPLICIT_JEFFREYS_COLD_START",
            "MEASURED_POOR_ROUTES_ARE_DEMOTED_NOT_DISABLED",
            "TRANSPORT_FAILURES_DO_NOT_ENTER_LABELED_RECALL_DENOMINATORS",
            "NO_FINITE_OR_LIVE_PROVIDER_MISS_TO_NONEXISTENCE_INFERENCE",
            "STOP_ON_FIRST_INDEPENDENTLY_VERIFIED_SUFFICIENT_WITNESS",
        ],
    }
