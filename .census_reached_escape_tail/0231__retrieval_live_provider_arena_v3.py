#!/usr/bin/env python3
"""Residual live provider multi-query lattice arena V3.

Targets only npm/crates residual misses from V2. Each case uses several
behavior-derived query variants and unions the candidate sets monotonically.
Answer-key identities are evaluation-only and are forbidden from all queries.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Mapping

from canonical.runtime import retrieval_live_provider_arena_v1 as base

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V3"

CASES=(
    {
        "episode_id":"PACKAGE_TYPED_JS",
        "source_id":"NPM_REGISTRY_SEARCH",
        "upstream_group":"NPM_PUBLIC_REGISTRY",
        "strategy_id":"MULTI_QUERY_LATTICE_V3",
        "provider":"npm",
        "queries":[
            "static typing javascript compiler",
            "typed javascript language",
            "javascript type system",
            "superset javascript language",
        ],
        "target":"typescript",
    },
    {
        "episode_id":"PACKAGE_JS_LINT",
        "source_id":"NPM_REGISTRY_SEARCH",
        "upstream_group":"NPM_PUBLIC_REGISTRY",
        "strategy_id":"MULTI_QUERY_LATTICE_V3",
        "provider":"npm",
        "queries":[
            "javascript linter",
            "lint javascript code",
            "static analysis javascript",
            "code quality javascript lint",
        ],
        "target":"eslint",
    },
    {
        "episode_id":"PACKAGE_CODE_FORMAT",
        "source_id":"NPM_REGISTRY_SEARCH",
        "upstream_group":"NPM_PUBLIC_REGISTRY",
        "strategy_id":"MULTI_QUERY_LATTICE_V3",
        "provider":"npm",
        "queries":[
            "code formatter javascript",
            "opinionated formatter javascript",
        ],
        "target":"prettier",
    },
    {
        "episode_id":"PACKAGE_RUST_SERIALIZE",
        "source_id":"CRATES_IO_SEARCH",
        "upstream_group":"CRATES_IO_PUBLIC_API",
        "strategy_id":"MULTI_QUERY_LATTICE_V3",
        "provider":"crates",
        "queries":[
            "serialization rust",
            "serialize deserialize rust",
            "data serialization rust",
            "serialization framework",
        ],
        "target":"serde",
    },
    {
        "episode_id":"PACKAGE_RUST_ASYNC",
        "source_id":"CRATES_IO_SEARCH",
        "upstream_group":"CRATES_IO_PUBLIC_API",
        "strategy_id":"MULTI_QUERY_LATTICE_V3",
        "provider":"crates",
        "queries":[
            "async runtime rust",
            "asynchronous runtime rust",
            "nonblocking io rust",
            "event driven runtime rust",
        ],
        "target":"tokio",
    },
    {
        "episode_id":"PACKAGE_RUST_CLI",
        "source_id":"CRATES_IO_SEARCH",
        "upstream_group":"CRATES_IO_PUBLIC_API",
        "strategy_id":"MULTI_QUERY_LATTICE_V3",
        "provider":"crates",
        "queries":[
            "command line parser rust",
            "cli argument parser rust",
        ],
        "target":"clap",
    },
)

PROVIDERS={"npm":base.npm,"crates":base.crates}

def validate_cases()->None:
    seen=set()
    for row in CASES:
        key=(row["episode_id"],row["source_id"],row["strategy_id"])
        if key in seen:
            raise ValueError("DUPLICATE_CASE:"+repr(key))
        seen.add(key)
        target=str(row["target"]).casefold()
        for q in row["queries"]:
            if target in str(q).casefold():
                raise ValueError("TARGET_IDENTITY_LEAKED_IN_QUERY:"+row["episode_id"])
        if len(row["queries"])<2:
            raise ValueError("MULTI_QUERY_CASE_REQUIRES_AT_LEAST_TWO_VARIANTS")

def run(*,limit_per_query:int=10,timeout:float=20.0)->dict[str,Any]:
    validate_cases()
    events=[]
    for seq,row in enumerate(CASES,1):
        provider=PROVIDERS[row["provider"]]
        union=[]
        seen=set()
        query_rows=[]
        status="SUCCESS"
        errors=[]
        start=time.perf_counter()
        for qi,q in enumerate(row["queries"],1):
            qstart=time.perf_counter()
            try:
                ids=provider(q,limit=limit_per_query,timeout=timeout)
                qstatus="SUCCESS"
                err=None
            except Exception as exc:
                ids=[]
                qstatus="FAILED_RETRYABLE"
                err=f"{type(exc).__name__}:{str(exc)[:400]}"
                status="PARTIAL_RETRYABLE" if union else "FAILED_RETRYABLE"
                errors.append(err)
            before=len(union)
            for cid in ids:
                cid=str(cid)
                if cid not in seen:
                    seen.add(cid)
                    union.append(cid)
            new_count=len(union)-before
            query_rows.append({
                "query_index":qi,
                "query":q,
                "status":qstatus,
                "candidate_count":len(ids),
                "new_union_candidates":new_count,
                "latency_seconds":max(0.0,time.perf_counter()-qstart),
                "error":err,
            })
        latency=max(0.0,time.perf_counter()-start)
        target=str(row["target"])
        hit=target in union
        rank=union.index(target)+1 if hit else None
        seed=f"{row['episode_id']}\0{row['source_id']}\0{row['strategy_id']}\0"+json.dumps(row["queries"],sort_keys=True)
        events.append({
            "episode_id":row["episode_id"],
            "source_id":row["source_id"],
            "upstream_group":row["upstream_group"],
            "strategy_id":row["strategy_id"],
            "action_id":"LIVEV3:"+hashlib.sha256(seed.encode()).hexdigest()[:24],
            "sequence":seq,
            "provider":row["provider"],
            "queries":list(row["queries"]),
            "query_rows":query_rows,
            "status":status,
            "candidate_ids":union,
            "candidate_pool_size":len(union),
            "expected_target_answer_key":target,
            "target_hit":hit,
            "target_rank_in_union":rank,
            "latency_seconds":latency,
            "request_count":len(row["queries"]),
            "errors":errors,
        })
    good=[x for x in events if x["status"] in {"SUCCESS","PARTIAL_RETRYABLE"}]
    hits=[x for x in good if x["target_hit"]]
    source_metrics={}
    for source in sorted({x["source_id"] for x in events}):
        rows=[x for x in events if x["source_id"]==source]
        ok=[x for x in rows if x["status"] in {"SUCCESS","PARTIAL_RETRYABLE"}]
        hh=[x for x in ok if x["target_hit"]]
        source_metrics[source]={
            "case_count":len(rows),
            "usable_case_count":len(ok),
            "target_hit_count":len(hh),
            "target_recall":len(hh)/len(ok) if ok else None,
            "mean_candidate_pool_size":sum(x["candidate_pool_size"] for x in ok)/len(ok) if ok else None,
            "mean_request_count":sum(x["request_count"] for x in ok)/len(ok) if ok else None,
            "mean_latency_seconds":sum(x["latency_seconds"] for x in ok)/len(ok) if ok else None,
        }
    return {
        "schema":SCHEMA,
        "status":"LIVE_MULTI_QUERY_LATTICE_PROBE_COMPLETE",
        "case_count":len(events),
        "usable_case_count":len(good),
        "target_hit_count":len(hits),
        "target_recall":len(hits)/len(good) if good else None,
        "source_metrics":source_metrics,
        "events":events,
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "QUERY_VARIANTS_ARE_BEHAVIOR_DERIVED_AND_TARGET_IDENTITY_FREE",
            "CANDIDATE_UNION_IS_MONOTONIC",
            "FAILED_VARIANTS_REMAIN_RETRYABLE",
            "MULTI_QUERY_TARGET_HIT_IS_FINITE_TASK_RECALL_NOT_OPEN_WORLD_COMPLETENESS",
            "NO_PROVIDER_MISS_TO_NONEXISTENCE_INFERENCE",
        ],
    }

def main()->int:
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["usable_case_count"]>0 else 1

if __name__=="__main__":
    raise SystemExit(main())
