#!/usr/bin/env python3
"""Cross-ecosystem live retrieval bridge arena V5.

Tests package requirements that registry search could not recover by searching
implementation repositories instead. This models the production route:
behavior -> repository candidate -> manifest/package identity bridge.
"""
from __future__ import annotations
import hashlib,json,time
from typing import Any
from canonical.runtime import retrieval_live_provider_arena_v1 as base

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V5"

CASES=(
 {"episode_id":"PACKAGE_TYPED_JS","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"CROSS_ECOSYSTEM_REPO_BRIDGE_V5","query":"typed javascript language in:name,description,readme","target_repo":"microsoft/TypeScript","target_package":"typescript"},
 {"episode_id":"PACKAGE_JS_LINT","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"CROSS_ECOSYSTEM_REPO_BRIDGE_V5","query":"javascript lint static analysis in:name,description,readme","target_repo":"eslint/eslint","target_package":"eslint"},
 {"episode_id":"PACKAGE_RUST_SERIALIZE","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"CROSS_ECOSYSTEM_REPO_BRIDGE_V5","query":"serialization rust library in:name,description,readme","target_repo":"serde-rs/serde","target_package":"serde"},
 {"episode_id":"PACKAGE_RUST_ASYNC","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"CROSS_ECOSYSTEM_REPO_BRIDGE_V5","query":"async runtime rust in:name,description,readme","target_repo":"tokio-rs/tokio","target_package":"tokio"},
 {"episode_id":"PACKAGE_RUST_CLI","source_id":"GITHUB_REPOSITORY_SEARCH","upstream_group":"GITHUB_PUBLIC_API","strategy_id":"CROSS_ECOSYSTEM_REPO_BRIDGE_V5","query":"command line parser rust in:name,description,readme","target_repo":"clap-rs/clap","target_package":"clap"},
)

def validate_cases()->None:
    seen=set()
    for row in CASES:
        key=(row["episode_id"],row["strategy_id"])
        if key in seen: raise ValueError("DUPLICATE_CASE:"+repr(key))
        seen.add(key)
        q=row["query"].casefold()
        if row["target_repo"].casefold() in q or row["target_package"].casefold() in q:
            raise ValueError("ANSWER_KEY_IDENTITY_LEAKED_IN_QUERY:"+row["episode_id"])

def run(*,limit:int=10,timeout:float=20.0)->dict[str,Any]:
    validate_cases()
    events=[]
    for seq,row in enumerate(CASES,1):
        start=time.perf_counter()
        try:
            ids=base.github(row["query"],limit=limit,timeout=timeout)
            status="SUCCESS"; err=None
        except Exception as exc:
            ids=[]; status="FAILED_RETRYABLE"; err=f"{type(exc).__name__}:{str(exc)[:400]}"
        ids=[str(x) for x in ids]
        target=row["target_repo"]
        hit=target.casefold() in {x.casefold() for x in ids}
        rank=next((i+1 for i,x in enumerate(ids) if x.casefold()==target.casefold()),None)
        seed=f"{row['episode_id']}\0{row['strategy_id']}\0{row['query']}"
        events.append({
          "episode_id":row["episode_id"],"source_id":row["source_id"],"upstream_group":row["upstream_group"],
          "strategy_id":row["strategy_id"],"action_id":"LIVEV5:"+hashlib.sha256(seed.encode()).hexdigest()[:24],
          "sequence":seq,"provider":"github","query":row["query"],"status":status,
          "candidate_ids":ids,"expected_target_repo_answer_key":target,
          "expected_target_package_answer_key":row["target_package"],
          "target_repo_hit":hit,"target_repo_rank":rank,
          "manifest_bridge_required":True,
          "latency_seconds":max(0.0,time.perf_counter()-start),"request_count":1,"error":err,
        })
    ok=[x for x in events if x["status"]=="SUCCESS"]; hits=[x for x in ok if x["target_repo_hit"]]
    return {
      "schema":SCHEMA,"status":"LIVE_CROSS_ECOSYSTEM_BRIDGE_PROBE_COMPLETE",
      "case_count":len(events),"successful_case_count":len(ok),"target_repo_hit_count":len(hits),
      "target_repo_recall":len(hits)/len(ok) if ok else None,"events":events,
      "manifest_bridge_not_executed_in_this_arena":True,
      "open_world_completeness_claim":False,"incremental_spend_usd":0,
      "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
      "ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,
      "hard_rules":[
        "SEARCH_IMPLEMENTATION_ECOSYSTEM_WHEN_REGISTRY_TEXT_SEARCH_IS_WEAK",
        "REPOSITORY_HIT_REQUIRES_DOWNSTREAM_MANIFEST_BRIDGE_BEFORE_PACKAGE_IDENTITY_ACCEPTANCE",
        "ANSWER_KEY_IDENTITIES_ARE_NOT_QUERY_TERMS",
        "FAILED_PROVIDER_CALLS_REMAIN_RETRYABLE",
        "TARGET_REPO_HIT_IS_FINITE_TASK_RECALL_NOT_OPEN_WORLD_COMPLETENESS",
        "NO_PROVIDER_MISS_TO_NONEXISTENCE_INFERENCE",
      ],
    }

def main()->int:
    out=run(); print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["successful_case_count"]>0 else 1

if __name__=="__main__": raise SystemExit(main())
