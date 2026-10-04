from pathlib import Path
from canonical.runtime import retrieval_fresh_holdout_arena_v20 as h

ROOT=Path(__file__).resolve().parents[2]

def test_freeze_and_no_target_leak():
    frozen=h.validate_freeze(ROOT)
    assert len(frozen["requests"])==12
    answer=h._load_json(ROOT,h.ANSWER_KEY)
    h._validate_no_target_leak(frozen["requests"],answer["targets"])

def test_score_counts_hits_misses_and_failures():
    events=[
        {
            "episode_id":"A","difficulty":"X","provider":"p",
            "retrieval":{
                "status":"LIVE_FROZEN_V19_ROUTE_MEASUREMENT_COMPLETE",
                "candidate_ids":["target-a","other"],
                "planned_action_count":2,
                "events":[
                    {"status":"SUCCESS","candidate_ids":["other"],"latency_seconds":0.1,"action_id":"r1","strategy_id":"RAW"},
                    {"status":"SUCCESS","candidate_ids":["target-a"],"latency_seconds":0.2,"action_id":"r2","strategy_id":"RECOVERY"},
                ],
            },
        },
        {
            "episode_id":"B","difficulty":"X","provider":"p",
            "retrieval":{
                "status":"LIVE_FROZEN_V19_ROUTE_MEASUREMENT_COMPLETE",
                "candidate_ids":["other"],
                "planned_action_count":1,
                "events":[{"status":"SUCCESS","candidate_ids":["other"],"latency_seconds":0.1,"action_id":"r3","strategy_id":"RAW"}],
            },
        },
        {
            "episode_id":"C","difficulty":"Y","provider":"q",
            "retrieval":{
                "status":"LIVE_FROZEN_V19_ROUTE_MEASUREMENT_COMPLETE",
                "candidate_ids":[],
                "planned_action_count":1,
                "events":[{"status":"FAILED_RETRYABLE","candidate_ids":[],"latency_seconds":0.1,"action_id":"r4","strategy_id":"RAW"}],
            },
        },
    ]
    out=h.score(events,{"A":"target-a","B":"target-b","C":"target-c"})
    assert out["case_count"]==3
    assert out["usable_case_count"]==2
    assert out["hit_count"]==1
    assert out["miss_count"]==1
    assert out["failed_retryable_case_count"]==1
    assert out["portfolio_union_recall_on_usable_cases"]==0.5
    assert out["cases"][0]["first_hit"]["action_index"]==2

def test_target_leak_rejected():
    rows=[{
        "episode_id":"A",
        "query_action":{"query":"secret-package behavior","language_variants":[]},
    }]
    try:
        h._validate_no_target_leak(rows,{"A":"org/secret-package"})
        raise AssertionError("target basename leak accepted")
    except ValueError as e:
        assert "TARGET_BASENAME_LEAKED" in str(e)

if __name__=="__main__":
    test_freeze_and_no_target_leak()
    test_score_counts_hits_misses_and_failures()
    test_target_leak_rejected()
    print("test_retrieval_fresh_holdout_arena_v20: PASS")
