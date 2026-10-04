#!/usr/bin/env python3
"""Live proof that generic V20 route actions execute the two hardest Maven recoveries."""
from __future__ import annotations
import json,time
from canonical.runtime import retrieval_live_provider_arena_v11 as v11
from canonical.runtime import retrieval_verified_route_executor_v1 as executor

SCHEMA="PROJECT_BRAIN_RETRIEVAL_VERIFIED_ROUTE_EXECUTOR_LIVE_PROBE_V1"

CASES=(
    ("MAVEN_COLLECTIONS","BEHAVIOR_CONTEXT_CANDIDATE_GRAPH_SNOWBALL"),
    ("MAVEN_JSON_BIND","VERSION_LINE_HISTORY_IDENTITY_BRIDGE"),
)

def row(episode_id):
    rows=[x for x in v11.TASKS if x["episode_id"]==episode_id]
    if len(rows)!=1:raise ValueError("CASE_MISMATCH:"+episode_id)
    return rows[0]

def run(*,timeout=20.0):
    events=[]
    for episode_id,route in CASES:
        r=row(episode_id)
        action={
            "action":"VERIFIED_RECOVERY_ROUTE",
            "action_id":"V20:"+episode_id,
            "source_id":"MAVEN_CENTRAL_SEARCH",
            "provider_route":"MAVEN_CENTRAL_SEARCH",
            "strategy_id":route,
            "query":str(r["query"]),
            "answer_key_identity_permitted":False,
        }
        start=time.perf_counter()
        try:
            out=executor.execute(action,timeout=timeout)
            status="SUCCESS"
        except Exception as exc:
            out={"candidates":[],"error":f"{type(exc).__name__}:{str(exc)[:500]}"}
            status="FAILED_RETRYABLE"
        target=v11._norm(r["target"])
        ids=[v11._norm(x.get("candidate_id")) for x in out.get("candidates") or []]
        hit=target in set(ids)
        events.append({
            "episode_id":episode_id,
            "route":route,
            "status":status,
            "expected_target_answer_key":target,
            "target_hit":hit,
            "target_rank":ids.index(target)+1 if hit else None,
            "candidate_count":len(ids),
            "answer_key_identity_used_for_route_generation":False,
            "answer_key_identity_used_for_route_execution":False,
            "latency_seconds":max(0.0,time.perf_counter()-start),
            "executor_result":out,
        })
    hits=sum(1 for x in events if x["target_hit"])
    return {
        "schema":SCHEMA,
        "status":"LIVE_GENERIC_VERIFIED_ROUTE_EXECUTOR_PROBE_COMPLETE",
        "case_count":len(events),
        "hit_count":hits,
        "miss_count":len(events)-hits,
        "recall":hits/len(events),
        "events":events,
        "answer_key_identity_used_for_discovery":False,
        "open_world_completeness_claim":False,
        "incremental_spend_usd":0,
        "acceptance_credit_delta":0,
        "family_credit_delta":0,
        "capability_credit_delta":0,
        "ownership_credit_delta":0,
        "execution_authority":False,
        "promotion_authority":False,
        "hard_rules":[
            "THE_SAME_GENERIC_VERIFIED_RECOVERY_ROUTE_ACTION_API_IS_USED_FOR_BOTH_CASES",
            "FROZEN_TARGET_IDENTITIES_SCORE_ONLY_AFTER_ROUTE_EXECUTION",
            "ROUTE_OUTPUT_REMAINS_CANDIDATE_ONLY",
            "TWO_OF_TWO_IS_EXECUTION_INTEGRATION_EVIDENCE_NOT_OPEN_WORLD_COMPLETENESS",
        ],
    }

def main():
    out=run()
    print(json.dumps(out,ensure_ascii=False,sort_keys=True))
    return 0 if out["hit_count"]==out["case_count"] else 2

if __name__=="__main__":
    raise SystemExit(main())
