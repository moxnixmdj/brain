#!/usr/bin/env python3
"""Generic executor for verified retrieval recovery routes.

Executes the target-blind V19 portfolio actions using independently verified
V13/V14/V16/V18 primitives. It grants no sufficiency or acceptance credit.

Network-backed execution is currently strongest for Maven-like repository/package
routes because that is where live residual evidence justified the nontrivial
manifest, graph, and version-history mechanisms.
"""
from __future__ import annotations

import hashlib
from typing import Any, Mapping

from canonical.runtime import retrieval_live_provider_arena_v13 as v13
from canonical.runtime import retrieval_live_provider_arena_v14 as v14
from canonical.runtime import retrieval_live_provider_arena_v16 as v16
from canonical.runtime import retrieval_live_provider_arena_v18 as v18

SCHEMA="PROJECT_BRAIN_RETRIEVAL_VERIFIED_ROUTE_EXECUTOR_V1"
ALLOWED={
    "MULTI_QUERY_DECOMPOSITION",
    "CROSS_LANGUAGE_TECHNICAL_BRIDGE",
    "REPOSITORY_MANIFEST_BRIDGE",
    "DEEP_MANIFEST_INSPECTION",
    "BEHAVIOR_CONTEXT_CANDIDATE_GRAPH_SNOWBALL",
    "VERSION_LINE_HISTORY_IDENTITY_BRIDGE",
}

def _canon(x:Any)->str:
    return " ".join(str(x or "").strip().split())

def _candidate_rows(coords:list[str],route:str)->list[dict[str,Any]]:
    out=[];seen=set()
    for raw in coords:
        c=_canon(raw)
        if not c or c.casefold() in seen:continue
        seen.add(c.casefold())
        out.append({
            "candidate_id":c,
            "package_coordinate":c,
            "retrieval_route":route,
            "sufficiency_status":"UNVERIFIED",
            "authority":"CANDIDATE_ONLY",
        })
    return out

def generic_query_decomposition(query:str)->list[str]:
    base=_canon(query)
    rows=[base]
    tokens=base.split()
    if len(tokens)>=6:
        # Overlapping behavior windows reduce conjunction pressure without
        # inventing new domain words.
        mid=max(3,len(tokens)//2)
        rows.append(" ".join(tokens[:mid+1]))
        rows.append(" ".join(tokens[max(0,mid-2):]))
    # Maven's verified behavior aliases are permitted because they were
    # independently validated live and remain target-identity-free.
    for q in v14.maven_behavior_queries(base):
        stripped=v13._strip_github_qualifiers(q)
        if stripped and stripped not in rows:rows.append(stripped)
    return rows[:8]

def _manifest_bridge(query:str,*,timeout:float,deep:bool)->dict[str,Any]:
    b=v14.bridge(
        query,
        timeout=timeout,
        max_repos=16 if deep else 12,
        max_poms=20 if deep else 12,
    )
    return {
        "candidate_ids":[_canon(x) for x in b["coordinates"]],
        "trace":b,
    }

def _graph_snowball(query:str,*,timeout:float)->dict[str,Any]:
    queries=v14.maven_behavior_queries(query)
    seed_repos,search_traces=v14.repo_union(
        queries,limit_per_query=10,timeout=timeout
    )
    linked,graph_traces=v16.graph_snowball(
        query,seed_repos,timeout=timeout,max_seed_repos=8,max_links_per_seed=24
    )
    inspection=[];seen=set()
    for repo in linked+seed_repos:
        k=repo.casefold()
        if k not in seen:
            seen.add(k);inspection.append(repo)
    coords=[];coord_seen=set();manifest=[]
    for repo in inspection[:32]:
        try:
            got,trace=v13.repository_pom_coordinates(repo,timeout=timeout,max_poms=20)
            status="SUCCESS";err=None
        except Exception as exc:
            got=[];trace={"repository":repo,"pom_files":[]}
            status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:300]}"
        trace["status"]=status;trace["error"]=err
        manifest.append(trace)
        for coord in got:
            k=coord.casefold()
            if k not in coord_seen:
                coord_seen.add(k);coords.append(coord)
    return {
        "candidate_ids":[_canon(x) for x in coords],
        "trace":{
            "seed_queries":queries,
            "seed_repositories":seed_repos,
            "linked_repositories":linked,
            "inspection_repositories":inspection,
            "search_traces":search_traces,
            "graph_traces":graph_traces,
            "manifest_traces":manifest,
        },
    }

def _version_history(query:str,*,timeout:float)->dict[str,Any]:
    queries=v14.maven_behavior_queries(query)
    repos,search_traces=v14.repo_union(
        queries,limit_per_query=10,timeout=timeout
    )
    coords=[];seen=set();history=[]
    for repo in repos[:12]:
        try:
            trace=v18.historical_coordinates(
                repo,timeout=timeout,max_pages=3,max_per_major=2,max_poms=20
            )
            status="SUCCESS";err=None
        except Exception as exc:
            trace={"repository":repo,"coordinates":[],"selected_tags":[],"probes":[]}
            status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:300]}"
        trace["status"]=status;trace["error"]=err
        history.append(trace)
        for coord in trace.get("coordinates") or []:
            c=_canon(coord)
            if c.casefold() not in seen:
                seen.add(c.casefold());coords.append(c)
    return {
        "candidate_ids":coords,
        "trace":{
            "queries":queries,
            "repository_candidates":repos,
            "search_traces":search_traces,
            "history_traces":history,
        },
    }

def execute(
    action:Mapping[str,Any],
    *,
    timeout:float=20.0,
)->dict[str,Any]:
    if not isinstance(action,Mapping):
        raise ValueError("ACTION_MAPPING_REQUIRED")
    if action.get("action")!="VERIFIED_RECOVERY_ROUTE":
        raise ValueError("VERIFIED_RECOVERY_ROUTE_ACTION_REQUIRED")
    route=_canon(action.get("strategy_id"))
    if route not in ALLOWED:
        raise ValueError("UNVERIFIED_ROUTE_FORBIDDEN:"+route)
    if action.get("answer_key_identity_permitted") is not False:
        raise ValueError("ANSWER_KEY_IDENTITY_POLICY_REQUIRED")
    query=_canon(action.get("query"))
    if not query:
        raise ValueError("ROUTE_QUERY_REQUIRED")

    if route=="MULTI_QUERY_DECOMPOSITION":
        qs=generic_query_decomposition(query)
        return {
            "schema":SCHEMA,"status":"CHILD_QUERY_ACTIONS_COMPILED",
            "route":route,
            "child_query_actions":[
                {
                    "action":"QUERY_SOURCE",
                    "action_id":"CHILD:"+hashlib.sha256(
                        f"{action.get('action_id')}\0{q}".encode()
                    ).hexdigest()[:24],
                    "source_id":_canon(action.get("source_id")),
                    "provider_route":_canon(action.get("provider_route") or action.get("source_id")),
                    "strategy_id":"DECOMPOSED_BEHAVIOR_QUERY",
                    "query":q,
                    "candidate_authority":"CANDIDATE_ONLY",
                    "nonexistence_claim_authorized":False,
                } for q in qs
            ],
            "candidates":[],
            "execution_authority":False,"promotion_authority":False,
            "acceptance_credit_delta":0,"family_credit_delta":0,
            "capability_credit_delta":0,"ownership_credit_delta":0,
        }

    if route=="CROSS_LANGUAGE_TECHNICAL_BRIDGE":
        variants=action.get("bridge_variants") or action.get("language_variants") or []
        rows=[]
        for raw in variants:
            text=_canon(raw.get("text") if isinstance(raw,Mapping) else raw)
            if text and text.casefold()!=query.casefold():
                rows.append(text)
        return {
            "schema":SCHEMA,
            "status":"CHILD_QUERY_ACTIONS_COMPILED" if rows else "NO_EXPLICIT_LANGUAGE_VARIANTS__RETRYABLE_UNKNOWN",
            "route":route,
            "child_query_actions":[
                {
                    "action":"QUERY_SOURCE",
                    "action_id":"LANG:"+hashlib.sha256(
                        f"{action.get('action_id')}\0{q}".encode()
                    ).hexdigest()[:24],
                    "source_id":_canon(action.get("source_id")),
                    "provider_route":_canon(action.get("provider_route") or action.get("source_id")),
                    "strategy_id":"MULTILINGUAL_BRIDGE_VARIANT",
                    "query":q,
                    "candidate_authority":"CANDIDATE_ONLY",
                    "nonexistence_claim_authorized":False,
                } for q in rows
            ],
            "candidates":[],
            "execution_authority":False,"promotion_authority":False,
            "acceptance_credit_delta":0,"family_credit_delta":0,
            "capability_credit_delta":0,"ownership_credit_delta":0,
        }

    if route=="REPOSITORY_MANIFEST_BRIDGE":
        raw=_manifest_bridge(query,timeout=timeout,deep=False)
    elif route=="DEEP_MANIFEST_INSPECTION":
        raw=_manifest_bridge(query,timeout=timeout,deep=True)
    elif route=="BEHAVIOR_CONTEXT_CANDIDATE_GRAPH_SNOWBALL":
        raw=_graph_snowball(query,timeout=timeout)
    elif route=="VERSION_LINE_HISTORY_IDENTITY_BRIDGE":
        raw=_version_history(query,timeout=timeout)
    else:
        raise AssertionError(route)

    cands=_candidate_rows(raw["candidate_ids"],route)
    return {
        "schema":SCHEMA,
        "status":"ROUTE_EXECUTED_CANDIDATE_ONLY",
        "route":route,
        "candidate_count":len(cands),
        "candidates":cands,
        "trace":raw["trace"],
        "nonexistence_claim_authorized":False,
        "execution_authority":False,
        "promotion_authority":False,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "incremental_spend_usd":0,
        "hard_rules":[
            "ROUTE_EXECUTION_IS_ANSWER_KEY_BLIND",
            "ROUTE_OUTPUT_IS_CANDIDATE_ONLY",
            "FAILED_PROVIDER_OPERATIONS_DO_NOT_AUTHORIZE_NONEXISTENCE",
            "CANDIDATES_REQUIRE_INDEPENDENT_SUFFICIENCY_VERIFICATION",
        ],
    }
