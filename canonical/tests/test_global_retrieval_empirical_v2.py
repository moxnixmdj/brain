from pathlib import Path

from canonical.runtime import retrieval_live_event_ledger_v1 as ledger
from canonical.runtime import global_retrieval_controller_v2 as controller
from canonical.runtime import global_retrieval_entrypoint_v2 as entry

ROOT=Path(__file__).resolve().parents[2]

events=[
    {
        "episode_id":"e1","source_id":"A","upstream_group":"G1","action_id":"a1",
        "sequence":1,"status":"SUCCESS","candidate_ids":["x"],"request_count":1,
        "latency_seconds":2.0,
    },
    {
        "episode_id":"e1","source_id":"B","upstream_group":"G2","action_id":"b1",
        "sequence":2,"status":"SUCCESS","candidate_ids":["x","y"],"request_count":2,
        "latency_seconds":1.0,
    },
    {
        "episode_id":"e2","source_id":"A","upstream_group":"G1","action_id":"a2",
        "sequence":1,"status":"FAILED_RETRYABLE","candidate_ids":[],"request_count":1,
        "latency_seconds":3.0,
    },
]
cal=ledger.aggregate(events)
assert cal["event_count"]==3
assert cal["episode_count"]==2
assert cal["source_stats"]["B"]["novel_candidate_actions"]==1
assert cal["source_stats"]["B"]["conditional_after_upstream_group"]["G1"]["attempts"]==1
pair=cal["pairwise_candidate_overlap"][0]
assert pair["candidate_jaccard"]==0.5

try:
    ledger.aggregate([{
        "episode_id":"x","source_id":"S","action_id":"a","status":"SUCCESS",
        "candidate_ids":["c"],"verified_sufficient_candidate_ids":["c"],
    }])
    raise AssertionError("sufficient event without independent receipt accepted")
except ValueError as exc:
    assert "INDEPENDENT_RECEIPT" in str(exc)

stats={
    "A":{"attempts":10,"failures":0,"novel_candidate_actions":6,"sufficient_witness_actions":2,
         "mean_latency_seconds":2.0,"mean_requests":1.0,
         "conditional_after_upstream_group":{"G0":{"attempts":5,"novel_candidate_actions":1}}},
    "B":{"attempts":10,"failures":1,"novel_candidate_actions":4,"sufficient_witness_actions":2,
         "mean_latency_seconds":1.0,"mean_requests":2.0,
         "conditional_after_upstream_group":{"G0":{"attempts":5,"novel_candidate_actions":4}}},
}
ranked=controller.rank_actions_empirical(
    [
        {"action_id":"A1","source_id":"A","upstream_group":"GA"},
        {"action_id":"B1","source_id":"B","upstream_group":"GB"},
    ],
    source_stats=stats,
    consumed_upstream_groups=["G0"],
)
assert len(ranked)==2
for row in ranked:
    p=row["retrieval_priority_v2"]
    assert 0.0 <= p["p_novel_candidate_action"] <= 1.0
    assert 0.0 <= p["p_sufficient_witness_action"] <= 1.0
    assert p["expected_sufficient_witness_per_second"] >= 0.0

plan=controller.compile_global_plan(
    query_actions=[
        {"action_id":"q1","source_id":"A","upstream_group":"GA"},
        {"action_id":"q2","source_id":"B","upstream_group":"GB"},
    ],
    sources=[
        {"source_id":"A","upstream_group":"GA","bounded_scope":False},
        {"source_id":"B","upstream_group":"GB","bounded_scope":False},
        {"source_id":"REG","upstream_group":"REG","bounded_scope":True,
         "authoritative_enumeration":True,"scope_id":"snapshot-1","enumeration_transport":"DIRECT_API"},
    ],
    live_calibration={"event_count":3,"source_stats":stats},
)
assert plan["fixed_correlation_multiplier_used"] is False
assert plan["fixed_source_independence_multiplier_used"] is False
assert plan["queryless_enumeration_action_count"]==1
assert plan["live_calibration_state"]=="MEASURED"
assert plan["open_world_nonexistence_claim_authorized"] is False

real=entry.compile_authorized_plan(
    root=ROOT,
    query_actions=[{"action_id":"g","source_id":"GITHUB_CODE_SURFACE","upstream_group":"GITHUB_PUBLIC_INDEX_AND_API"}],
    sources=[{"source_id":"GITHUB_CODE_SURFACE","upstream_group":"GITHUB_PUBLIC_INDEX_AND_API","bounded_scope":False}],
)
assert real["status"]=="PASS__AUTHORIZED_EMPIRICAL_GLOBAL_RETRIEVAL_PLAN_COMPILED", real
assert real["authority_gate"]["pass"] is True
assert real["live_calibration"]["event_count"]==1
assert "GITHUB_CODE_SURFACE" in real["live_calibration"]["source_stats"]
assert real["plan"]["fixed_correlation_multiplier_used"] is False

print("test_global_retrieval_empirical_v2: PASS")
