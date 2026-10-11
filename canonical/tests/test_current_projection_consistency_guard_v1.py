from canonical.runtime.current_projection_consistency_guard_v1 import check_projection_consistency

def _fixtures():
    wake={"scheduler_reconciliation":{"open_checkpoint_obligation_count":12,"wake_gated_open_checkpoint_count":12,"row_specific_same_information_runnable_count":0,"parked_checkpoint_count":1}}
    scheduler={"post_composition":{"escape_open_checkpoint_count":12,"escape_wake_gated_open_count":12,"escape_row_specific_same_information_runnable_count":0,"escape_active_gap_a_count":0,"escape_active_gap_b_count":0,"escape_parked_unresolved_count":1,"bytes_current_frontier":"V58__OK","professional_parallel_policy":"RUN_BYTES_V58_RESOURCE_PARETO_WORK"},"checkpoint_execution_reconciliation":{"open_checkpoint_obligations":12,"wake_gated_open_checkpoint_count":12,"row_specific_same_information_runnable_count":0,"active_gap_a_acquisition_count":0,"active_gap_b_strict_progress_count":0}}
    live={"status":"CURRENT__12_CHECKPOINT_ROWS_WAKE_GATED","candidates":[{"work_id":"BYTES_EXACT_SYMBOLIC_V58_NEXT_PHYSICAL_CUT"}]}
    bytes_state={"status":"ACTIVE_RESEARCH__V58_FRONTIER"}
    return scheduler,live,wake,bytes_state

def test_current_projection_passes():
    assert check_projection_consistency(*_fixtures())["pass"] is True

def test_stale_bytes_policy_fails_closed():
    scheduler,live,wake,bytes_state=_fixtures()
    scheduler["post_composition"]["professional_parallel_policy"]="RUN_BYTES_V57_RESOURCE_PARETO_WORK"
    result=check_projection_consistency(scheduler,live,wake,bytes_state)
    assert result["pass"] is False
    assert "STALE_BYTES_VERSION_IN_PARALLEL_POLICY" in result["errors"]

def test_stale_gap_a_projection_fails_closed():
    scheduler,live,wake,bytes_state=_fixtures()
    scheduler["post_composition"]["escape_active_gap_a_count"]=12
    result=check_projection_consistency(scheduler,live,wake,bytes_state)
    assert result["pass"] is False
    assert "TOPOLOGY_MISMATCH:post.gap_a_zero" in result["errors"]
