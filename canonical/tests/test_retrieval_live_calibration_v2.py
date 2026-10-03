from pathlib import Path
from canonical.runtime import retrieval_live_event_ledger_v1 as ledger
from canonical.runtime import global_retrieval_entrypoint_v3 as entry

ROOT=Path(__file__).resolve().parents[2]
events=ledger.load_jsonl(ROOT/"canonical/state/retrieval_live_events_v1.jsonl")
agg=ledger.aggregate(events)

assert agg["event_count"]==7,agg["event_count"]
assert agg["episode_count"]==4,agg["episode_count"]
stats=agg["source_stats"]
assert stats["GITHUB_CODE_SURFACE"]["attempts"]==1
assert stats["GITHUB_GLOBAL_SEARCH"]["attempts"]==3
assert stats["GENERAL_OPEN_WEB"]["attempts"]==3
assert stats["GITHUB_GLOBAL_SEARCH"]["failures"]==0
assert stats["GENERAL_OPEN_WEB"]["failures"]==0
assert stats["GITHUB_GLOBAL_SEARCH"]["sufficient_witness_actions"]==0
assert stats["GENERAL_OPEN_WEB"]["sufficient_witness_actions"]==0
assert stats["GITHUB_GLOBAL_SEARCH"]["novel_candidate_actions"]==3
assert stats["GENERAL_OPEN_WEB"]["novel_candidate_actions"]==3

gcond=stats["GITHUB_GLOBAL_SEARCH"]["conditional_after_upstream_group"]
wcond=stats["GENERAL_OPEN_WEB"]["conditional_after_upstream_group"]
assert gcond["HETEROGENEOUS_PUBLIC_WEB_INDEXES"]["attempts"]==1
assert gcond["HETEROGENEOUS_PUBLIC_WEB_INDEXES"]["novel_candidate_actions"]==1
assert wcond["GITHUB_PUBLIC_INDEX_AND_API"]["attempts"]==2
assert wcond["GITHUB_PUBLIC_INDEX_AND_API"]["novel_candidate_actions"]==2

pair=next(
    x for x in agg["pairwise_candidate_overlap"]
    if {x["source_a"],x["source_b"]}=={"GITHUB_GLOBAL_SEARCH","GENERAL_OPEN_WEB"}
)
assert pair["shared_episode_count"]==3
assert pair["candidate_jaccard"]==0.0
assert pair["intersection_candidate_observations"]==0

out=entry.compile_authorized_plan(
    root=ROOT,
    query_actions=[
        {"action_id":"q-web","source_id":"GENERAL_OPEN_WEB"},
        {"action_id":"q-gh","source_id":"GITHUB_GLOBAL_SEARCH"},
    ],
    source_epoch="CALIBRATION_TEST_EPOCH",
)
assert out["status"]=="PASS__AUTHORIZED_CANONICAL_SOURCE_EMPIRICAL_GLOBAL_RETRIEVAL_PLAN_COMPILED",out
assert out["live_calibration"]["event_count"]==7
assert out["live_calibration"]["episode_count"]==4
assert out["plan"]["fixed_correlation_multiplier_used"] is False
assert out["plan"]["fixed_source_independence_multiplier_used"] is False
assert out["plan"]["open_world_nonexistence_claim_authorized"] is False
assert {x["source_id"] for x in out["plan"]["actions"] if x["action"]=="QUERY_SOURCE"}=={"GENERAL_OPEN_WEB","GITHUB_GLOBAL_SEARCH"}

print("test_retrieval_live_calibration_v2: PASS")
