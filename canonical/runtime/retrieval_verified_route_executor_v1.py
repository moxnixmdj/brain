#!/usr/bin/env python3
"""Answer-key-blind live executor for the frozen V19 retrieval plan.

The executor accepts only a request and source description. It invokes the
current authorized V19/entrypoint-v4 planner, then executes every emitted route
in measurement mode. It deliberately accepts no expected target identity.

A separate scorer may compare the resulting candidate sets to a hidden answer
key after all retrieval calls finish. This prevents holdout identities from
influencing query generation, provider choice, route generation, or route
execution.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from canonical.runtime import global_retrieval_entrypoint_v4 as entrypoint
from canonical.runtime import retrieval_live_provider_arena_v11 as v11
from canonical.runtime import retrieval_live_provider_arena_v12 as v12
from canonical.runtime import retrieval_live_provider_arena_v13 as v13
from canonical.runtime import retrieval_live_provider_arena_v14 as v14
from canonical.runtime import retrieval_live_provider_arena_v16 as v16
from canonical.runtime import retrieval_live_provider_arena_v18 as v18

SCHEMA="PROJECT_BRAIN_RETRIEVAL_VERIFIED_ROUTE_EXECUTOR_V1"

SOURCE_PROVIDER={
    "GITHUB_REPOSITORY_SEARCH":"github",
    "NPM_REGISTRY_SEARCH":"npm",
    "CRATES_IO_SEARCH":"crates",
    "HUGGINGFACE_MODEL_PIPELINE_ENUM":"huggingface_pipeline",
    "MAVEN_CENTRAL_SEARCH":"maven",
    "NUGET_SEARCH":"nuget",
    "RUBYGEMS_SEARCH":"rubygems",
    "PACKAGIST_SEARCH":"packagist",
}

def _canon(x:Any)->str:
    return " ".join(str(x or "").strip().split())

def _norm(x:Any)->str:
    return _canon(x).casefold()

def _dedupe(rows:Sequence[Any],limit:int|None=None)->list[str]:
    out=[];seen=set()
    for raw in rows:
        s=_canon(raw)
        if not s or s.casefold() in seen:
            continue
        seen.add(s.casefold());out.append(s)
        if limit is not None and len(out)>=limit:
            break
    return out

def _provider(source_id:str,source:Mapping[str,Any]):
    name=_canon(source.get("provider")) or SOURCE_PROVIDER.get(source_id,"")
    fn=v11.PROVIDERS.get(name)
    if not callable(fn):
        raise ValueError("UNSUPPORTED_LIVE_PROVIDER:"+source_id+":"+name)
    return name,fn

def _run_queries(
    provider,
    queries:Sequence[str],
    *,
    limit:int,
    timeout:float,
)->dict[str,Any]:
    union=[];seen=set();traces=[];failures=0
    for q in _dedupe(queries):
        start=time.perf_counter()
        try:
            ids=provider(q,limit=limit,timeout=timeout)
            status="SUCCESS";err=None
        except Exception as exc:
            ids=[];status="FAILED_RETRYABLE";failures+=1
            err=f"{type(exc).__name__}:{str(exc)[:500]}"
        normalized=[_norm(x) for x in ids if _norm(x)]
        for cid in normalized:
            if cid not in seen:
                seen.add(cid);union.append(cid)
        traces.append({
            "query":q,"status":status,"candidate_count":len(normalized),
            "latency_seconds":max(0.0,time.perf_counter()-start),"error":err,
        })
    return {
        "candidate_ids":union,
        "request_count":len(traces),
        "failed_request_count":failures,
        "traces":traces,
        "status":"FAILED_RETRYABLE" if traces and failures==len(traces) else "SUCCESS",
    }

def _bridge_texts(original:Mapping[str,Any])->list[str]:
    out=[]
    for key in ("language_variants","bridge_variants"):
        rows=original.get(key) or []
        if isinstance(rows,(list,tuple)):
            for row in rows:
                if isinstance(row,Mapping):
                    text=_canon(row.get("text"))
                else:
                    text=_canon(row)
                if text:
                    out.append(text)
    return _dedupe(out,16)

def _multilingual_queries(original:Mapping[str,Any],provider_name:str)->list[str]:
    query=_canon(original.get("query") or original.get("text"))
    bridges=_bridge_texts(original)
    rows=[query,*bridges]

    # V12 provides script-preserving decomposition without answer-key terms.
    pseudo={"query":query,"provider":provider_name}
    rows.extend(v12.query_variants(pseudo,max_variants=6))

    # GitHub compact forms reduce conjunction pressure while retaining behavior.
    if provider_name=="github":
        rows.extend(v13.github_compact_queries(query,max_queries=4))
        for b in bridges:
            rows.extend(v13.github_compact_queries(b,max_queries=3))
    return _dedupe(rows,16)

def _maven_manifest_bridge(query:str,*,timeout:float,deep:bool)->dict[str,Any]:
    if deep:
        bridge=v14.bridge(query,timeout=timeout,max_repos=20,max_poms=32)
    else:
        bridge=v13.maven_behavior_bridge(query,timeout=timeout)
    coords=[_norm(x) for x in bridge.get("coordinates") or [] if _norm(x)]
    traces=list(bridge.get("search_traces") or [])+list(bridge.get("repository_manifest_traces") or [])
    failures=sum(1 for x in traces if isinstance(x,Mapping) and x.get("status")=="FAILED_RETRYABLE")
    return {
        "candidate_ids":_dedupe(coords),
        "status":"FAILED_RETRYABLE" if traces and failures==len(traces) else "SUCCESS",
        "request_count":len(traces),
        "failed_request_count":failures,
        "traces":traces,
        "bridge":bridge,
    }

def _graph_snowball(
    query:str,
    *,
    source_id:str,
    provider_name:str,
    timeout:float,
)->dict[str,Any]:
    # Repository sources return repository identities. Maven sources additionally
    # verify package coordinates from graph-neighbor manifests.
    if provider_name=="github":
        seeds,traces=v13.github_repo_union(query,limit_per_query=12,timeout=timeout)
        linked,graph=v16.graph_snowball(
            query,seeds,timeout=timeout,max_seed_repos=10,max_links_per_seed=32
        )
        ids=_dedupe([*linked,*seeds])
        return {
            "candidate_ids":[_norm(x) for x in ids],
            "status":"SUCCESS","request_count":len(traces)+len(graph),
            "failed_request_count":sum(
                1 for x in [*traces,*graph]
                if isinstance(x,Mapping) and x.get("status")=="FAILED_RETRYABLE"
            ),
            "traces":[*traces,*graph],
        }

    if provider_name=="maven":
        qs=v14.maven_behavior_queries(query)
        seeds,search_traces=v14.repo_union(qs,limit_per_query=12,timeout=timeout)
        linked,graph_traces=v16.graph_snowball(
            query,seeds,timeout=timeout,max_seed_repos=10,max_links_per_seed=32
        )
        inspection=_dedupe([*linked,*seeds],40)
        coords=[];seen=set();manifest=[]
        for repo in inspection:
            try:
                got,trace=v13.repository_pom_coordinates(repo,timeout=timeout,max_poms=32)
                status="SUCCESS";err=None
            except Exception as exc:
                got=[];trace={"repository":repo,"pom_files":[]}
                status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:400]}"
            trace["status"]=status;trace["error"]=err;manifest.append(trace)
            for coord in got:
                key=_norm(coord)
                if key and key not in seen:
                    seen.add(key);coords.append(key)
        all_traces=[*search_traces,*graph_traces,*manifest]
        failures=sum(1 for x in all_traces if isinstance(x,Mapping) and x.get("status")=="FAILED_RETRYABLE")
        return {
            "candidate_ids":coords,"status":"SUCCESS",
            "request_count":len(all_traces),"failed_request_count":failures,
            "traces":all_traces,
        }

    return {
        "candidate_ids":[],"status":"NOT_APPLICABLE",
        "request_count":0,"failed_request_count":0,"traces":[],
    }

def _version_history_bridge(query:str,*,timeout:float)->dict[str,Any]:
    queries=v14.maven_behavior_queries(query)
    repos,search_traces=v14.repo_union(queries,limit_per_query=12,timeout=timeout)
    coords=[];seen=set();history=[]
    for repo in repos[:16]:
        try:
            row=v18.historical_coordinates(
                repo,timeout=timeout,max_pages=3,max_per_major=2,max_poms=24
            )
            status="SUCCESS";err=None
        except Exception as exc:
            row={"repository":repo,"coordinates":[],"probes":[]}
            status="FAILED_RETRYABLE";err=f"{type(exc).__name__}:{str(exc)[:400]}"
        row["status"]=status;row["error"]=err;history.append(row)
        for coord in row.get("coordinates") or []:
            key=_norm(coord)
            if key and key not in seen:
                seen.add(key);coords.append(key)
    traces=[*search_traces,*history]
    failures=sum(1 for x in traces if isinstance(x,Mapping) and x.get("status")=="FAILED_RETRYABLE")
    return {
        "candidate_ids":coords,"status":"SUCCESS",
        "request_count":len(traces),"failed_request_count":failures,
        "traces":traces,
    }

def _execute_action(
    action:Mapping[str,Any],
    *,
    original:Mapping[str,Any],
    source:Mapping[str,Any],
    timeout:float,
)->dict[str,Any]:
    source_id=_canon(original.get("source_id"))
    provider_name,provider=_provider(source_id,source)
    strategy=_canon(action.get("strategy_id") or original.get("strategy_id") or "RAW_UNSPECIFIED")
    query=_canon(action.get("query") or original.get("query"))
    start=time.perf_counter()

    if action.get("action")!="VERIFIED_RECOVERY_ROUTE":
        limit=200 if provider_name=="huggingface_pipeline" else 40
        out=_run_queries(provider,[query],limit=limit,timeout=timeout)
    elif strategy=="MULTI_QUERY_DECOMPOSITION":
        pseudo={"query":query,"provider":provider_name}
        variants=v12.query_variants(pseudo,max_variants=8)
        limit=200 if provider_name=="huggingface_pipeline" else 40
        out=_run_queries(provider,variants,limit=limit,timeout=timeout)
    elif strategy=="CROSS_LANGUAGE_TECHNICAL_BRIDGE":
        queries=_multilingual_queries(original,provider_name)
        limit=200 if provider_name=="huggingface_pipeline" else 40
        out=_run_queries(provider,queries,limit=limit,timeout=timeout)
    elif strategy=="REPOSITORY_MANIFEST_BRIDGE" and provider_name=="maven":
        out=_maven_manifest_bridge(query,timeout=timeout,deep=False)
    elif strategy=="DEEP_MANIFEST_INSPECTION" and provider_name=="maven":
        out=_maven_manifest_bridge(query,timeout=timeout,deep=True)
    elif strategy=="BEHAVIOR_CONTEXT_CANDIDATE_GRAPH_SNOWBALL":
        out=_graph_snowball(
            query,source_id=source_id,provider_name=provider_name,timeout=timeout
        )
    elif strategy=="VERSION_LINE_HISTORY_IDENTITY_BRIDGE" and provider_name=="maven":
        out=_version_history_bridge(query,timeout=timeout)
    else:
        out={
            "candidate_ids":[],"status":"NOT_APPLICABLE",
            "request_count":0,"failed_request_count":0,"traces":[],
        }

    return {
        "action_id":_canon(action.get("action_id")),
        "action":_canon(action.get("action")),
        "strategy_id":strategy,
        "provider":provider_name,
        "source_id":source_id,
        "query":query,
        "requires_prior_miss_of":list(action.get("requires_prior_miss_of") or []),
        "candidate_ids":_dedupe(out.get("candidate_ids") or []),
        "candidate_count":len(_dedupe(out.get("candidate_ids") or [])),
        "status":out.get("status"),
        "request_count":int(out.get("request_count") or 0),
        "failed_request_count":int(out.get("failed_request_count") or 0),
        "traces":out.get("traces") or [],
        "latency_seconds":max(0.0,time.perf_counter()-start),
        "answer_key_identity_used":False,
    }

def execute_request(
    *,
    root:Path,
    query_action:Mapping[str,Any],
    source:Mapping[str,Any],
    timeout:float=20.0,
)->dict[str,Any]:
    """Execute a frozen V19 plan without any answer-key identity."""
    if "expected_target_answer_key" in query_action or "target" in query_action:
        raise ValueError("ANSWER_KEY_FIELD_FORBIDDEN_IN_EXECUTOR_INPUT")
    plan_wrap=entrypoint.compile_authorized_plan(
        root=root,query_actions=[dict(query_action)],sources=[dict(source)]
    )
    if not str(plan_wrap.get("status") or "").startswith("PASS"):
        return {
            "schema":SCHEMA,"status":"FAIL_CLOSED__PLAN_NOT_AUTHORIZED",
            "plan_wrapper":plan_wrap,"events":[],
            "answer_key_identity_used":False,
        }

    events=[]
    for action in (plan_wrap.get("plan") or {}).get("actions") or []:
        events.append(_execute_action(
            action,original=query_action,source=source,timeout=timeout
        ))

    union=[];seen=set()
    for event in events:
        for cid in event.get("candidate_ids") or []:
            key=_norm(cid)
            if key and key not in seen:
                seen.add(key);union.append(key)

    return {
        "schema":SCHEMA,
        "status":"LIVE_FROZEN_V19_ROUTE_MEASUREMENT_COMPLETE",
        "request_id":_canon(query_action.get("request_id") or query_action.get("action_id")),
        "source_id":_canon(query_action.get("source_id")),
        "plan_status":plan_wrap.get("status"),
        "planned_action_count":len((plan_wrap.get("plan") or {}).get("actions") or []),
        "events":events,
        "candidate_ids":union,
        "candidate_count":len(union),
        "answer_key_identity_used":False,
        "measurement_mode_executes_all_planned_routes_without_answer_key_gating":True,
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "EXECUTOR_ACCEPTS_NO_TARGET_OR_ANSWER_KEY_FIELD",
            "PLAN_IS_COMPILED_BY_FROZEN_CURRENT_ENTRYPOINT_V4",
            "ALL_PLANNED_ROUTES_ARE_MEASURED_WITHOUT_TARGET_DEPENDENT_CONTROL_FLOW",
            "ANSWER_KEY_MAY_ONLY_BE_APPLIED_BY_A_SEPARATE_POST_EXECUTION_SCORER",
            "FAILED_PROVIDER_CALLS_REMAIN_RETRYABLE",
            "LIVE_HOLDOUT_RECALL_IS_NOT_OPEN_WORLD_COMPLETENESS",
        ],
    }

def main()->int:
    # Dry-plan path only. Network holdout execution is performed by the arena.
    print(json.dumps({
        "schema":SCHEMA,
        "status":"READY__ANSWER_KEY_BLIND_V19_EXECUTOR",
        "answer_key_identity_accepted":False,
    },sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
