from canonical.runtime.matched_cross_capability_handoff_rollback_direct_v1 import execute_case,run_batch

def test_handoff_rollback_batch_passes():
    out=run_batch(20261007,16)
    assert out["all_pass"] is True,out
    assert out["passed"]==16

def test_two_distinct_capabilities_handoff_and_exact_rollback():
    row=execute_case(123456)
    assert row["pass"] is True,row
    assert row["planner_plan"]==["capability_a","capability_b"]
    assert row["handoff_ok"] is True
    assert row["full_prefix_valid_count"]==2
    assert row["tampered_prefix_valid_count"]==1
    assert row["tamper_detected"] is True
    assert row["restored_to_checkpoint"] is True

def test_objective_trace_matches_handoff_rollback_semantics():
    row=execute_case(789012)
    events=row["objective_trace"]["events"]
    kinds=[x["type"] for x in events]
    assert kinds==["CHECKPOINT","HANDOFF","FAILURE","ROLLBACK","STATE_RESTORED","TERMINAL"]
    checkpoint=events[0]["checkpoint_id"]
    assert events[1]["from_capability"]!=events[1]["to_capability"]
    assert events[3]["checkpoint_id"]==checkpoint
    assert events[4]["checkpoint_id"]==checkpoint
    assert events[-1]["success"] is True
