from canonical.runtime.multiplex_terminal_route_admissibility_audit_v1 import evaluate

def test_four_terminal_derived_records_fail_current_route_admissibility():
    out=evaluate()
    assert out["pass"] is True, out
    assert len(out["quarantine_record_ids"]) == 4
    assert out["live_v6_claimed_record_count"] == 14
    assert out["fail_closed_sound_record_upper_bound_from_this_audit"] == 10
    assert out["p2"]["boundary_conflict"] is True
    assert out["p3"]["boundary_conflict"] is True
    assert out["p3"]["oct5_required_semantics_counterexample_present"] is True
