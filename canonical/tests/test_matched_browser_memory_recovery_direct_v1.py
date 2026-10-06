from canonical.runtime.matched_browser_memory_recovery_direct_v1 import execute_case,causal_ablation,run_batch

def test_browser_memory_recovery_batch_passes_all_classes():
    out=run_batch(20261007,12)
    assert out["all_pass"] is True,out
    assert set(out["case_classes"])=={"ENABLE_FEATURE","OPEN_SETTINGS","SEARCH_QUERY"}

def test_memory_is_causally_load_bearing_for_stage2_recovery():
    ab=causal_ablation(123456,0)
    assert ab["full_pass"] is True,ab
    assert ab["ablated_pass"] is False,ab
    assert ab["memory_is_load_bearing"] is True
    assert ab["full_stage2_goal_source"]=="CAPSULE_ONLY"
    assert ab["ablated_stage2_goal_source"]=="MEMORY_MISSING"

def test_objective_trace_has_browser_memory_failure_read_recovery_chain():
    row=execute_case(987654,1)
    assert row["pass"] is True,row
    events=row["objective_trace"]["events"]
    kinds=[x["type"] for x in events]
    assert kinds==["BROWSER_STATE","MEMORY_WRITE","FAILURE","MEMORY_READ","RECOVERY","TERMINAL"]
    write=events[1];read=events[3]
    assert write["key"]==read["key"]=="browser.goal"
    assert write["value_sha256"]==read["value_sha256"]
    assert events[2]["reason"]=="STALE_RENDER_STATE"
    assert events[-1]["success"] is True
