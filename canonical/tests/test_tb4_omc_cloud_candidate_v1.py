from canonical.runtime.tb4_omc_cloud_candidate_v1 import evaluate

def test_tb4_omc_documentary_candidate_is_fail_closed():
    out = evaluate()
    assert out["pass"], out
    assert out["additional_creditable_tasks_needed"] == 8
    assert out["minimum_recovery_task_count"] == 8
    assert out["runtime_preflight_required"] is True
    assert out["usable_memory_must_be_observed_inside_guest"] is True
    assert out["attainability_recompile_required_after_runtime_pass"] is True
    assert out["terminal_cases_consumed"] == 0
    assert out["incremental_spend_usd"] == 0
    assert out["execution_authority"] is False
    assert out["promotion_authority"] is False
    assert out["fresh_reality_authority"] is False
