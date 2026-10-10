#!/usr/bin/env python3
"""Verified recovery-route portfolio for global retrieval.

This compiler converts independently verified V11-V18 recovery mechanisms into
generic, answer-key-blind candidate-discovery actions. It does not execute them
or grant sufficiency. Applicability is derived only from request/source shape.

The portfolio exists so the 30/30 recovery evidence is not stranded in bespoke
arena scripts. Current empirical controller V3 remains the ranker.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

SCHEMA="PROJECT_BRAIN_RETRIEVAL_VERIFIED_ROUTE_PORTFOLIO_V1"

ROUTES=(
    "MULTI_QUERY_DECOMPOSITION",
    "CROSS_LANGUAGE_TECHNICAL_BRIDGE",
    "REPOSITORY_MANIFEST_BRIDGE",
    "DEEP_MANIFEST_INSPECTION",
    "BEHAVIOR_CONTEXT_CANDIDATE_GRAPH_SNOWBALL",
    "VERSION_LINE_HISTORY_IDENTITY_BRIDGE",
)

def _canon(x:Any)->str:
    return " ".join(str(x or "").strip().split())

def _route_id(route:str,parent_id:str,source_id:str)->str:
    raw=f"{route}\0{parent_id}\0{source_id}"
    return "VRP:"+hashlib.sha256(raw.encode()).hexdigest()[:24]

def _is_maven(source_id:str,src:Mapping[str,Any],action:Mapping[str,Any])->bool:
    hay=" ".join([
        source_id,
        _canon(src.get("ecosystem")),
        _canon(src.get("registry")),
        _canon(action.get("ecosystem")),
        _canon(action.get("provider_route")),
    ]).casefold()
    return "maven" in hay or "java_package" in hay

def _is_repo(source_id:str,src:Mapping[str,Any],action:Mapping[str,Any])->bool:
    hay=" ".join([
        source_id,
        _canon(src.get("source_class")),
        _canon(src.get("kind")),
        _canon(action.get("surface")),
        _canon(action.get("provider_route")),
    ]).casefold()
    return any(t in hay for t in ("github","gitlab","gitee","codeberg","repository","repo"))

def _long_behavior_query(action:Mapping[str,Any])->bool:
    q=_canon(action.get("query") or action.get("text"))
    return len(q.split())>=5

def _multilingual_signal(action:Mapping[str,Any],src:Mapping[str,Any])->bool:
    if action.get("language_variants") or action.get("bridge_variants"):
        return True
    script=_canon(action.get("script") or src.get("script"))
    return bool(script and script.upper() not in {"LATIN","UNKNOWN"})

def compile_portfolio_actions(
    query_actions:Sequence[Mapping[str,Any]],
    sources:Sequence[Mapping[str,Any]],
)->list[dict[str,Any]]:
    source_by_id={
        _canon(x.get("source_id")):x
        for x in sources if isinstance(x,Mapping) and _canon(x.get("source_id"))
    }
    out=[];seen=set()

    def add(route:str,parent:Mapping[str,Any],source_id:str,*,requires:Sequence[str]=()):
        parent_id=_canon(parent.get("action_id")) or "UNSPECIFIED_PARENT"
        aid=_route_id(route,parent_id,source_id)
        if aid in seen:return
        seen.add(aid)
        out.append({
            "action":"VERIFIED_RECOVERY_ROUTE",
            "action_id":aid,
            "parent_action_id":parent_id,
            "source_id":source_id,
            "provider_route":source_id,
            "strategy_id":route,
            "query":_canon(parent.get("query") or parent.get("text")),
            "upstream_group":_canon(parent.get("upstream_group")) or source_id,
            "requires_prior_miss_of":[parent_id,*[str(x) for x in requires]],
            "candidate_authority":"CANDIDATE_ONLY",
            "nonexistence_claim_authorized":False,
            "answer_key_identity_permitted":False,
            "route_evidence":"INDEPENDENT_LIVE_RECOVERY_V11_TO_V18",
        })

    for raw in query_actions:
        if not isinstance(raw,Mapping):continue
        action=dict(raw)
        source_id=_canon(
            action.get("source_id") or action.get("domain") or action.get("backend_id")
        )
        src=source_by_id.get(source_id,{})
        if not source_id:continue

        if _long_behavior_query(action):
            add("MULTI_QUERY_DECOMPOSITION",action,source_id)

        if _multilingual_signal(action,src):
            add("CROSS_LANGUAGE_TECHNICAL_BRIDGE",action,source_id)

        if _is_repo(source_id,src,action) or _is_maven(source_id,src,action):
            add("BEHAVIOR_CONTEXT_CANDIDATE_GRAPH_SNOWBALL",action,source_id)

        if _is_maven(source_id,src,action):
            add("REPOSITORY_MANIFEST_BRIDGE",action,source_id)
            add("DEEP_MANIFEST_INSPECTION",action,source_id,
                requires=(_route_id("REPOSITORY_MANIFEST_BRIDGE",
                                    _canon(action.get("action_id")) or "UNSPECIFIED_PARENT",
                                    source_id),))
            add("VERSION_LINE_HISTORY_IDENTITY_BRIDGE",action,source_id,
                requires=(_route_id("REPOSITORY_MANIFEST_BRIDGE",
                                    _canon(action.get("action_id")) or "UNSPECIFIED_PARENT",
                                    source_id),))

    return out

def compile_portfolio(
    query_actions:Sequence[Mapping[str,Any]],
    sources:Sequence[Mapping[str,Any]],
)->dict[str,Any]:
    actions=compile_portfolio_actions(query_actions,sources)
    return {
        "schema":SCHEMA,
        "status":"COMPILED_VERIFIED_RECOVERY_ROUTE_PORTFOLIO",
        "actions":actions,
        "action_count":len(actions),
        "route_set":list(ROUTES),
        "answer_key_identity_permitted":False,
        "candidate_authority":"CANDIDATE_ONLY",
        "open_world_nonexistence_claim_authorized":False,
        "incremental_spend_usd":0,
        "hard_rules":[
            "RECOVERY_ROUTES_ARE_DERIVED_ONLY_FROM_REQUEST_AND_SOURCE_SHAPE",
            "ANSWER_KEY_IDENTITIES_ARE_FORBIDDEN_FROM_ROUTE_GENERATION",
            "ROUTES_EXECUTE_ONLY_AFTER_THEIR_DECLARED_PRIOR_ROUTE_MISS",
            "ROUTE_OUTPUT_REMAINS_CANDIDATE_ONLY_UNTIL_INDEPENDENT_SUFFICIENCY_VERIFICATION",
            "FAILED_ROUTE_REMAINS_RETRYABLE",
            "OPEN_WORLD_MISS_REMAINS_UNKNOWN",
        ],
    }
