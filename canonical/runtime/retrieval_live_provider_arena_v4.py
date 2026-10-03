#!/usr/bin/env python3
"""Residual live provider deep-window arena V4.

Tests whether remaining npm/crates misses are ranking-truncation failures rather
than vocabulary failures. Uses the best measured behavior-derived query for each
case and expands the provider result window from 10 to 50.
"""
from __future__ import annotations
import hashlib,json,time
from typing import Any
from canonical.runtime import retrieval_live_provider_arena_v1 as base

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V4"

CASES=(
 {"episode_id":"PACKAGE_TYPED_JS","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","strategy_id":"DEEP_WINDOW_50_V4","provider":"npm","query":"typed superset javascript","target":"typescript"},
 {"episode_id":"PACKAGE_JS_LINT","source_id":"NPM_REGISTRY_SEARCH","upstream_group":"NPM_PUBLIC_REGISTRY","strategy_id":"DEEP_WINDOW_50_V4","provider":"npm","query":"javascript lint","target":"eslint"},
 {"episode_id":"PACKAGE_RUST_SERIALIZE","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","strategy_id":"DEEP_WINDOW_50_V4","provider":"crates","query":"serialize deserialize","target":"serde"},
 {"episode_id":"PACKAGE_RUST_ASYNC","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","strategy_id":"DEEP_WINDOW_50_V4","provider":"crates","query":"async runtime","target":"tokio"},
 {"episode_id":"PACKAGE_RUST_CLI","source_id":"CRATES_IO_SEARCH","upstream_group":"CRATES_IO_PUBLIC_API","strategy_id":"DEEP_WINDOW_50_V4","provider":"crates","query":"command line parser","target":"clap"},
)
PROVIDERS={"npm":base.npm,"crates":base.crates}

def validate_cases()->None:
    seen=set()
    for row in CASES:
        key=(row["episode_id"],row["source_id"],row["strategy_id"])
        if key in seen: raise ValueError("DUPLICATE_CASE:"+repr(key))
        seen.add(key)
        if row["target"].casefold() in row["query"].casefold():
            raise ValueError("TARGET_IDENTITY_LEAKED_IN_QUERY:"+row["episode_id"])

def run(*,limit:int=50,timeout:float=20.0)->dict[str,Any]:
    validate_cases()
    events=[]
    for seq,row in enumerate(CASES,1):
        start=time.perf_counter()
        try:
            ids=PROVIDERS[row["provider"]](row["query"],limit=limit,timeout=timeout)
            status="SUCCESS"; err=None
        except Exception as exc:
            ids=[]; status="FAILED_RETRYABLE"; err=f"{type(exc).__name__}:{str(exc)[:400]}"
        ids=[str(x) for x in ids]
        target=row["target"]
        hit=target in ids
        rank=ids.index(target)+1 if hit else None
        seed=f"{row['episode_id']}\0{row['source_id']}\0{row['strategy_id']}\0{row['query']}\0{limit}"
        events.append({
          "episode_id":row["episode_id"],"source_id":row["source_id"],"upstream_group":row["upstream_group"],
          "strategy_id":row["strategy_id"],"action_id":"LIVEV4:"+hashlib.sha256(seed.encode()).hexdigest()[:24],
          "sequence":seq,"provider":row["provider"],"query":row["query"],"window_size":limit,
          "status":status,"candidate_ids":ids,"candidate_pool_size":len(ids),
          "expected_target_answer_key":target,"target_hit":hit,"target_rank":rank,
          "latency_seconds":max(0.0,time.perf_counter()-start),"request_count":1,"error":err,
        })
    ok=[x for x in events if x["status"]=="SUCCESS"]; hits=[x for x in ok if x["target_hit"]]
    return {
      "schema":SCHEMA,"status":"LIVE_DEEP_WINDOW_PROBE_COMPLETE",
      "case_count":len(events),"successful_case_count":len(ok),"target_hit_count":len(hits),
      "target_recall":len(hits)/len(ok) if ok else None,"events":events,
      "open_world_completeness_claim":False,"incremental_spend_usd":0,
      "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
      "ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,
      "hard_rules":[
        "DEEP_WINDOW_IS_ONLY_FOR_RANKING_TRUNCATION_DIAGNOSIS",
        "ANSWER_KEY_IDENTITY_IS_NOT_A_QUERY_TERM",
        "TARGET_HIT_IS_FINITE_TASK_RECALL_NOT_OPEN_WORLD_COMPLETENESS",
        "FAILED_PROVIDER_CALLS_REMAIN_RETRYABLE",
        "NO_PROVIDER_MISS_TO_NONEXISTENCE_INFERENCE",
      ],
    }

def main()->int:
    out=run(); print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["successful_case_count"]>0 else 1

if __name__=="__main__": raise SystemExit(main())
