import json
from canonical.runtime import h100_generic_patch_search_transfer_v1 as patchlib
from canonical.runtime.matched_coding_debug_tool_discovery_v1 import (
    PRE_PATH,
    TASK_IDS,
    _public_rows,
    discover_patch,
    execute_case,
    run_all,
)

def test_all_four_coding_debug_tool_discovery_cases_pass():
    out=run_all()
    assert out["all_pass"] is True,out
    assert out["passed"]==4
    assert {x["task_id"] for x in out["tasks"]}==set(TASK_IDS)

def test_hidden_truth_oracle_is_not_needed_by_repair_selection(monkeypatch):
    pre=json.loads(PRE_PATH.read_text(encoding="utf-8"))
    rows=_public_rows("POWER5",pre)
    def forbidden(*args,**kwargs):
        raise AssertionError("HIDDEN_TRUTH_USED_DURING_PATCH_DISCOVERY")
    monkeypatch.setattr(patchlib,"_truth",forbidden)
    out=discover_patch(rows,pre)
    assert out["status"]=="EXACT_PUBLIC_TEST_PATCH_FOUND"
    assert out["family_id"]=="POWER"

def test_each_case_has_real_failure_tool_discovery_patch_and_fresh_pass():
    for task_id in TASK_IDS:
        row=execute_case(task_id)
        assert row["pass"] is True,row
        assert row["initial_test_failed"] is True
        assert row["tool_discovery"]["selected_tool"]=="generic_patch_search"
        assert row["public_test_after_patch_pass"] is True
        assert row["hidden_holdout"]["pass"] is True
        assert row["git_diff_check_pass"] is True
        assert row["coding_finish_gate"]["pass"] is True

def test_objective_trace_has_required_causal_order():
    row=execute_case("HINGE")
    kinds=[x["type"] for x in row["objective_trace"]["events"]]
    assert kinds==[
        "CODE_REVISION","TEST_RESULT","DEBUG","TOOL_DISCOVERY",
        "CODE_REVISION","TEST_RESULT","TERMINAL",
    ]
    events=row["objective_trace"]["events"]
    assert events[1]["pass"] is False
    assert events[2]["failure_observed"] is True
    assert events[3]["selected_tool"]=="generic_patch_search"
    assert events[5]["pass"] is True
    assert events[5]["hidden_holdout_pass"] is True
    assert events[-1]["success"] is True
