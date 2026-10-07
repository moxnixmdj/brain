from canonical.runtime.matched_agency_missing_atoms_v1 import (
    run_replanning,run_tool_recovery,run_fanin,run_development_suite,
)

def test_replanning_real_receipt_and_semantics():
    x=run_replanning(101,0)
    assert x["pass"] is True,x
    assert x["semantic"]["pass"] is True
    assert x["safety"]["plan_changed_after_load_bearing_receipt"] is True
    assert x["safety"]["completed_work_replayed"] is False

def test_tool_failure_recovery_real_execution():
    x=run_tool_recovery(202,0)
    assert x["pass"] is True,x
    assert x["semantic"]["pass"] is True
    assert x["safety"]["distinct_recovery_tool"] is True
    assert x["safety"]["unrecovered_failure"] is False

def test_fanin_uses_real_delegation_dependencies():
    x=run_fanin(303,0)
    assert x["pass"] is True,x
    assert x["semantic"]["pass"] is True
    assert len(x["fanin_inputs"])>=2
    assert x["safety"]["terminal_evidence_preserves_all_owned_evidence"] is True

def test_development_suite():
    x=run_development_suite(404,3)
    assert x["all_pass"] is True,x
    assert x["passed"]==9
