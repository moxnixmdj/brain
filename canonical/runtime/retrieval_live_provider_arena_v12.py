#!/usr/bin/env python3
"""Retrieval V12 multi-query decomposition recovery arena.

Replays only the independently observed V11 live misses. Query generation is
strictly answer-key blind: variants are deterministic functions of the original
behavior query and provider identity. Results from all variants are unioned
monotonically, so a later query cannot erase an earlier candidate.

Purpose: measure whether controlled query decomposition recovers V11 misses
before adding more providers or deeper infrastructure.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Mapping

from canonical.runtime import retrieval_live_provider_arena_v11 as v11

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V12"

V11_MISS_EPISODE_IDS=frozenset({
    "GITHUB_ZH_SEGMENTATION","GITHUB_ZH_PINYIN","GITHUB_RU_NLP","GITHUB_AR_TEXT",
    "GITHUB_PY_LINTER","GITHUB_PY_CLI","NPM_PROCESS_EXEC","CRATE_ERROR",
    "CRATE_PARSER","HF_TEXT2TEXT","MAVEN_COLLECTIONS","MAVEN_JSON_BIND",
    "MAVEN_LOG_FACADE","NUGET_JSON","NUGET_STRUCT_LOG","RUBY_HTTP",
    "PHP_HTTP","PHP_LOGGING",
})

WORD=re.compile(r"[^\W_]+(?:[.+#/-][^\W_]+)*",re.UNICODE)
PLATFORM={
    "python","java","rust","ruby","php","javascript","node","nodejs",
    ".net","dotnet","csharp","c#",
}
LOW_INFO={
    "fast","flexible","application","library","toolkit","utilities","utility",
    "api","data","general","open","source","multiple","multi","language",
}
GITHUB_QUALIFIER="in:name,description,readme"


def _canon(x:Any)->str:
    return " ".join(str(x or "").strip().split())


def _tokens(query:str)->list[str]:
    return [x for x in WORD.findall(_canon(query)) if not x.lower().startswith("in:")]


def _platform_tokens(tokens:list[str])->list[str]:
    return [t for t in tokens if t.casefold() in PLATFORM]


def _content_tokens(tokens:list[str])->list[str]:
    out=[t for t in tokens if t.casefold() not in PLATFORM and t.casefold() not in LOW_INFO]
    return out or [t for t in tokens if t.casefold() not in PLATFORM] or list(tokens)


def _windows(tokens:list[str],n:int)->list[str]:
    if len(tokens)<n:
        return []
    return [" ".join(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


def query_variants(row:Mapping[str,Any],*,max_variants:int=6)->list[str]:
    """Answer-key-blind deterministic query decomposition."""
    provider=str(row.get("provider") or "")
    original=_canon(row.get("query"))
    tokens=_tokens(original)
    platforms=_platform_tokens(tokens)
    content=_content_tokens(tokens)

    raw:list[str]=[]

    # Provider-native enumeration has no lexical query decomposition. Measure
    # deeper bounded enumeration instead.
    if provider=="huggingface_pipeline":
        return [original]

    # Strong compressed representation.
    if content:
        raw.append(" ".join(content[: min(4,len(content))]))

    # Contiguous behavior chunks. These preserve phrases that registry search
    # often handles better than long natural-language descriptions.
    for n in (3,2):
        for w in _windows(content,n):
            raw.append(w)

    # Native-script queries often need less conjunction pressure. Keep one
    # platform anchor where it exists, but never translate or insert answer-key
    # vocabulary.
    nonlatin=[
        t for t in content
        if any(ord(ch)>127 for ch in t)
    ]
    if nonlatin:
        for n in (2,1):
            for w in _windows(nonlatin,n):
                raw.append(" ".join([w]+platforms[:1]))

    # For GitHub, explicitly broaden searchable repository text surfaces.
    if provider=="github":
        qualified=[]
        for q in raw:
            q=_canon(q)
            if q:
                qualified.append(f"{q} {GITHUB_QUALIFIER}")
        raw=qualified

    seen=set()
    out=[]
    for q in raw:
        q=_canon(q)
        if not q or q.casefold()==original.casefold() or q.casefold() in seen:
            continue
        seen.add(q.casefold())
        out.append(q)
        if len(out)>=max_variants:
            break
    return out or [original]


def selected_tasks()->tuple[Mapping[str,Any],...]:
    rows=tuple(x for x in v11.TASKS if x["episode_id"] in V11_MISS_EPISODE_IDS)
    if {x["episode_id"] for x in rows}!=set(V11_MISS_EPISODE_IDS):
        raise ValueError("V11_MISS_TASK_SET_MISMATCH")
    return rows


def validate_tasks()->None:
    for row in selected_tasks():
        target=v11._norm(row["target"])
        basename=target.rsplit("/",1)[-1].rsplit(":",1)[-1]
        for q in query_variants(row):
            nq=v11._norm(q)
            if target and target in nq:
                raise ValueError("TARGET_IDENTITY_LEAKED_IN_QUERY:"+row["episode_id"])
            if len(basename)>=4 and basename in nq:
                raise ValueError("TARGET_BASENAME_LEAKED_IN_QUERY:"+row["episode_id"])


def _run_provider_group(rows:list[tuple[int,Mapping[str,Any]]],*,timeout:float)->list[dict[str,Any]]:
    events=[]
    for seq,row in rows:
        provider=v11.PROVIDERS[row["provider"]]
        variants=query_variants(row)
        per_query_limit=100 if row["provider"]=="huggingface_pipeline" else 30
        start=time.perf_counter()
        union:list[str]=[]
        seen=set()
        traces=[]
        failures=0
        for q in variants:
            q_start=time.perf_counter()
            try:
                ids=provider(q,limit=per_query_limit,timeout=timeout)
                status="SUCCESS"; error=None
            except Exception as exc:
                ids=[]; status="FAILED_RETRYABLE"
                error=f"{type(exc).__name__}:{str(exc)[:500]}"
                failures+=1
            normalized=[v11._norm(x) for x in ids if v11._norm(x)]
            for cid in normalized:
                if cid not in seen:
                    seen.add(cid); union.append(cid)
            traces.append({
                "query":q,"status":status,"candidate_count":len(normalized),
                "latency_seconds":max(0.0,time.perf_counter()-q_start),
                "error":error,
            })

        target=v11._norm(row["target"])
        hit=target in seen
        rank=union.index(target)+1 if hit else None
        overall="SUCCESS" if len(variants)>failures else "FAILED_RETRYABLE"
        seed=f"{row['episode_id']}\0V12\0"+ "\0".join(variants)
        events.append({
            "episode_id":row["episode_id"],
            "difficulty":row["difficulty"],
            "source_id":row["source_id"],
            "upstream_group":row["upstream_group"],
            "strategy_id":"MULTI_QUERY_DECOMPOSITION_UNION_V12",
            "provider":row["provider"],
            "original_query":row["query"],
            "generated_queries":variants,
            "answer_key_used_for_query_generation":False,
            "action_id":"LIVEV12:"+hashlib.sha256(seed.encode()).hexdigest()[:24],
            "sequence":seq,
            "status":overall,
            "candidate_ids":union,
            "candidate_count":len(union),
            "expected_target_answer_key":target,
            "target_hit":hit,
            "target_rank_in_union":rank,
            "request_count":len(variants),
            "failed_request_count":failures,
            "query_traces":traces,
            "latency_seconds":max(0.0,time.perf_counter()-start),
        })
    return events


def run(*,timeout:float=20.0)->dict[str,Any]:
    validate_tasks()
    tasks=selected_tasks()
    grouped=defaultdict(list)
    for seq,row in enumerate(tasks,1):
        grouped[row["provider"]].append((seq,row))

    events=[]
    with ThreadPoolExecutor(max_workers=max(1,min(8,len(grouped)))) as pool:
        futures=[
            pool.submit(_run_provider_group,rows,timeout=timeout)
            for _,rows in sorted(grouped.items())
        ]
        for fut in as_completed(futures):
            events.extend(fut.result())
    events.sort(key=lambda x:x["sequence"])

    successful=[x for x in events if x["status"]=="SUCCESS"]
    recovered=[x for x in successful if x["target_hit"]]
    misses=[x for x in successful if not x["target_hit"]]

    by_provider={}
    for provider in sorted({x["provider"] for x in events}):
        rows=[x for x in events if x["provider"]==provider]
        good=[x for x in rows if x["status"]=="SUCCESS"]
        hits=[x for x in good if x["target_hit"]]
        by_provider[provider]={
            "miss_replay_task_count":len(rows),
            "successful_task_count":len(good),
            "recovered_count":len(hits),
            "recovery_rate_on_successful_tasks":len(hits)/len(good) if good else None,
            "mean_requests":sum(x["request_count"] for x in good)/len(good) if good else None,
            "mean_latency_seconds":sum(x["latency_seconds"] for x in good)/len(good) if good else None,
        }

    # V11 had 12/30 hits. Every recovered V11 miss strictly raises the measured
    # union recall; failures never count as negative evidence.
    prior_hit_count=12
    total_case_count=30
    union_hit_count=prior_hit_count+len(recovered)

    return {
        "schema":SCHEMA,
        "status":"LIVE_V11_MISS_RECOVERY_PROBE_COMPLETE",
        "replayed_v11_miss_count":len(events),
        "successful_replay_count":len(successful),
        "recovered_v11_miss_count":len(recovered),
        "remaining_v11_miss_count":len(misses),
        "recovery_rate_on_successful_replays":len(recovered)/len(successful) if successful else None,
        "prior_v11_hit_count":prior_hit_count,
        "prior_v11_recall":prior_hit_count/total_case_count,
        "v11_plus_v12_union_hit_count":union_hit_count,
        "v11_plus_v12_union_recall":union_hit_count/total_case_count,
        "recovered_episode_ids":[x["episode_id"] for x in recovered],
        "remaining_miss_episode_ids":[x["episode_id"] for x in misses],
        "failed_episode_ids":[x["episode_id"] for x in events if x["status"]!="SUCCESS"],
        "provider_metrics":by_provider,
        "events":events,
        "answer_key_identity_used_for_query_generation":False,
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "ONLY_INDEPENDENTLY_OBSERVED_V11_MISSES_ARE_REPLAYED",
            "QUERY_VARIANTS_ARE_DETERMINISTIC_FUNCTIONS_OF_ORIGINAL_QUERY_AND_PROVIDER_ONLY",
            "ANSWER_KEY_IDENTITIES_ARE_SCORING_ONLY",
            "CANDIDATE_UNION_IS_MONOTONIC",
            "FAILED_REQUESTS_REMAIN_RETRYABLE",
            "LIVE_FINITE_RECALL_IS_NOT_OPEN_WORLD_COMPLETENESS",
            "RECOVERED_MISSES_MUST_FEED_ROUTE_STRATEGY_CALIBRATION_ONLY_AFTER_INDEPENDENT_RECEIPT_BINDING",
        ],
    }


def main()->int:
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["successful_replay_count"]>0 else 1


if __name__=="__main__":
    raise SystemExit(main())
