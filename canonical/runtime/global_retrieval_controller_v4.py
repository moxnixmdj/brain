#!/usr/bin/env python3
"""Scope-aware empirical retrieval controller V4.

V4 preserves V3 first-pass route×strategy ranking, calibrated from V10+V11,
and adds independently measured conditional recovery mechanisms from V12-V18.

Critical rule: fallback mechanisms are eligible only when the current residual
matches the scope that was actually measured. A one-case Maven graph success
is not silently generalized to arbitrary domains.
"""
from __future__ import annotations
from typing import Any, Mapping, Sequence

from canonical.runtime import global_retrieval_controller_v3 as v3

SCHEMA="PROJECT_BRAIN_GLOBAL_RETRIEVAL_CONTROLLER_V4"

def _ctx(context:Mapping[str,Any]|None,key:str)->bool:
    return bool((context or {}).get(key))

def _ecosystem(context:Mapping[str,Any]|None)->str:
    return str((context or {}).get("ecosystem") or "").strip().upper()

def eligible_recovery_mechanisms(
    calibration:Mapping[str,Any],
    context:Mapping[str,Any]|None,
)->list[dict[str,Any]]:
    rows=calibration.get("mechanisms") or {}
    if not isinstance(rows,Mapping):
        raise ValueError("RECOVERY_MECHANISM_CALIBRATION_REQUIRED")
    eco=_ecosystem(context)
    eligible=[]

    def add(mid:str,reason:str):
        raw=rows.get(mid)
        if not isinstance(raw,Mapping):
            return
        post=raw.get("conditional_recovery_posterior") or {}
        reliability=raw.get("transport_reliability_posterior") or {}
        p=float(post.get("mean") or 0.0)
        r=float(reliability.get("mean") or 0.0)
        eligible.append({
            "action":"TRY_CONDITIONAL_RECOVERY_MECHANISM",
            "mechanism_id":mid,
            "measured_scope":raw.get("scope"),
            "eligibility_reason":reason,
            "empirical_conditional_recovery_posterior_mean":p,
            "empirical_transport_reliability_posterior_mean":r,
            "priority_score":p*r,
            "candidate_authority":"CANDIDATE_ONLY",
            "nonexistence_claim_authorized":False,
            "open_world_completeness_claim":False,
        })

    if _ctx(context,"prior_first_pass_miss"):
        add("MULTI_QUERY_DECOMPOSITION_V12","PRIOR_FIRST_PASS_MISS")

    if _ctx(context,"prior_multi_query_miss") or _ctx(context,"residual_root_unknown"):
        add("RESIDUAL_ROOT_FIX_V13","UNRESOLVED_AFTER_MULTI_QUERY_OR_ROOT_UNKNOWN")

    if eco=="MAVEN" and _ctx(context,"repository_candidates_available"):
        add("MAVEN_DEEP_MANIFEST_V14","MAVEN_REPOSITORY_CANDIDATES_AVAILABLE")

    if eco=="MAVEN" and _ctx(context,"behavior_context_links_available"):
        add("BEHAVIOR_CONTEXT_GRAPH_SNOWBALL_V16","MAVEN_BEHAVIOR_CONTEXT_LINKS_AVAILABLE")

    if (
        eco=="MAVEN"
        and _ctx(context,"current_manifest_identity_observed")
        and _ctx(context,"versioned_identity_drift_suspected")
    ):
        add("VERSION_HISTORY_IDENTITY_V18","MAVEN_CURRENT_IDENTITY_OBSERVED_AND_HISTORICAL_DRIFT_SUSPECTED")

    eligible.sort(key=lambda x:(-float(x["priority_score"]),str(x["mechanism_id"])))
    return eligible

def compile_global_plan(
    *,
    query_actions:Sequence[Mapping[str,Any]],
    sources:Sequence[Mapping[str,Any]],
    route_strategy_calibration:Mapping[str,Any],
    recovery_mechanism_calibration:Mapping[str,Any],
    state:Mapping[str,Any]|None=None,
    recovery_context:Mapping[str,Any]|None=None,
)->dict[str,Any]:
    first=v3.compile_global_plan(
        query_actions=query_actions,
        sources=sources,
        route_strategy_calibration=route_strategy_calibration,
        state=state,
    )
    fallbacks=eligible_recovery_mechanisms(
        recovery_mechanism_calibration,
        recovery_context,
    )
    return {
        "schema":SCHEMA,
        "status":"COMPILED_SCOPE_AWARE_EMPIRICAL_GLOBAL_RETRIEVAL_PLAN",
        "first_pass_plan":first,
        "conditional_recovery_actions":fallbacks,
        "conditional_recovery_action_count":len(fallbacks),
        "recovery_context":dict(recovery_context or {}),
        "first_pass_calibration_schema":route_strategy_calibration.get("schema"),
        "recovery_mechanism_calibration_schema":recovery_mechanism_calibration.get("schema"),
        "open_world_nonexistence_claim_authorized":False,
        "incremental_spend_usd":0,
        "hard_rules":[
            "FIRST_PASS_PROVIDER_ROUTE_X_STRATEGY_RANKING_USES_V10_PLUS_V11_LIVE_EVENTS",
            "CONDITIONAL_RECOVERY_MECHANISMS_ARE_SEPARATE_FROM_FIRST_PASS_STATS",
            "RECOVERY_MECHANISMS_ARE_ELIGIBLE_ONLY_ON_MEASURED_OR_EXPLICITLY_MATCHED_RESIDUAL_SCOPE",
            "MAVEN_GRAPH_AND_VERSION_HISTORY_EVIDENCE_DOES_NOT_AUTO_GENERALIZE_TO_OTHER_ECOSYSTEMS",
            "UNKNOWN_DOMAIN_TRANSFER_REQUIRES_NEW_EVIDENCE_OR_COLD_START",
            "FAILED_OR_EMPTY_OPEN_WORLD_RETRIEVAL_REMAINS_UNKNOWN",
            "STOP_ON_FIRST_INDEPENDENTLY_VERIFIED_SUFFICIENT_WITNESS",
        ],
    }
