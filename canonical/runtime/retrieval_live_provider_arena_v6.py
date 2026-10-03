#!/usr/bin/env python3
"""Single-residual ESLint live discovery arena V6.

Tests multiple behavior-derived GitHub repository queries for the sole remaining
known labeled live miss. Candidate sets are unioned monotonically. The answer-key
repository/package identities are evaluation-only and forbidden from queries.
"""
from __future__ import annotations
import hashlib,json,time
from typing import Any
from canonical.runtime import retrieval_live_provider_arena_v1 as base

SCHEMA="PROJECT_BRAIN_RETRIEVAL_LIVE_PROVIDER_ARENA_V6"
CASE={
 "episode_id":"PACKAGE_JS_LINT",
 "source_id":"GITHUB_REPOSITORY_SEARCH",
 "upstream_group":"GITHUB_PUBLIC_API",
 "strategy_id":"GITHUB_BEHAVIOR_LATTICE_V6",
 "queries":[
   "javascript linter in:name,description,readme",
   "javascript code quality static analysis in:name,description,readme",
   "javascript code problems rules in:name,description,readme",
   "find fix javascript problems in:name,description,readme"
 ],
 "target_repo":"eslint/eslint",
 "target_package":"eslint",
}

def validate()->None:
    q=" ".join(CASE["queries"]).casefold()
    if CASE["target_repo"].casefold() in q or CASE["target_package"].casefold() in q:
        raise ValueError("ANSWER_KEY_IDENTITY_LEAKED_IN_QUERY")
    if len(CASE["queries"])<2:
        raise ValueError("QUERY_LATTICE_TOO_SMALL")

def run(*,limit_per_query:int=10,timeout:float=20.0)->dict[str,Any]:
    validate()
    union=[]; seen=set(); rows=[]; errors=[]
    start=time.perf_counter()
    for qi,q in enumerate(CASE["queries"],1):
        qstart=time.perf_counter()
        try:
            ids=base.github(q,limit=limit_per_query,timeout=timeout)
            status="SUCCESS"; err=None
        except Exception as exc:
            ids=[]; status="FAILED_RETRYABLE"; err=f"{type(exc).__name__}:{str(exc)[:400]}"; errors.append(err)
        before=len(union)
        for cid in ids:
            cid=str(cid)
            if cid not in seen:
                seen.add(cid); union.append(cid)
        rows.append({
          "query_index":qi,"query":q,"status":status,
          "candidate_count":len(ids),"new_union_candidates":len(union)-before,
          "latency_seconds":max(0.0,time.perf_counter()-qstart),"error":err,
        })
    target=CASE["target_repo"]
    hit=target.casefold() in {x.casefold() for x in union}
    rank=next((i+1 for i,x in enumerate(union) if x.casefold()==target.casefold()),None)
    seed=json.dumps(CASE["queries"],sort_keys=True)
    event={
      "episode_id":CASE["episode_id"],"source_id":CASE["source_id"],"upstream_group":CASE["upstream_group"],
      "strategy_id":CASE["strategy_id"],"action_id":"LIVEV6:"+hashlib.sha256(seed.encode()).hexdigest()[:24],
      "queries":list(CASE["queries"]),"query_rows":rows,"status":"SUCCESS" if not errors else "PARTIAL_RETRYABLE",
      "candidate_ids":union,"candidate_pool_size":len(union),
      "expected_target_repo_answer_key":target,"expected_target_package_answer_key":CASE["target_package"],
      "target_repo_hit":hit,"target_repo_rank":rank,"manifest_bridge_required":True,
      "latency_seconds":max(0.0,time.perf_counter()-start),"request_count":len(CASE["queries"]),"errors":errors,
    }
    return {
      "schema":SCHEMA,"status":"LIVE_ESLINT_RESIDUAL_PROBE_COMPLETE",
      "case_count":1,"usable_case_count":1,"target_repo_hit_count":1 if hit else 0,
      "target_repo_recall":1.0 if hit else 0.0,"event":event,
      "manifest_bridge_not_executed_in_this_arena":True,
      "open_world_completeness_claim":False,"incremental_spend_usd":0,
      "acceptance_credit_delta":0,"family_credit_delta":0,"capability_credit_delta":0,
      "ownership_credit_delta":0,"execution_authority":False,"promotion_authority":False,
      "hard_rules":[
        "QUERY_VARIANTS_ARE_BEHAVIOR_DERIVED_AND_ANSWER_KEY_IDENTITY_FREE",
        "CANDIDATE_UNION_IS_MONOTONIC",
        "FAILED_VARIANTS_REMAIN_RETRYABLE",
        "REPOSITORY_HIT_REQUIRES_DOWNSTREAM_MANIFEST_OR_REGISTRY_BRIDGE",
        "NO_PROVIDER_MISS_TO_NONEXISTENCE_INFERENCE",
      ],
    }

def main()->int:
    out=run(); print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__": raise SystemExit(main())
