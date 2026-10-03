from canonical.runtime.tb4_docker_limit_attainability_recompiler_v1 import (
    GPU_BLOCKED,
    NON_GPU_REOPENED,
    recompile,
)


def test_fail_closed_without_probe_pass():
    out = recompile(probe_passed=False)
    assert out["reopened_task_count"] == 0
    assert out["upper_bound_successes"] == 180
    assert out["attainability_state"] == "PRIOR_IMPOSSIBILITY_VERDICT_UNCHANGED"
    assert out["execution_authority"] is False
    assert out["acceptance_credit_delta"] == 0


def test_probe_pass_reopens_nine_non_gpu_rows_only():
    assert len(NON_GPU_REOPENED) == 9
    assert len(GPU_BLOCKED) == 3
    assert set(NON_GPU_REOPENED).isdisjoint(GPU_BLOCKED)
    out = recompile(probe_passed=True)
    assert out["reopened_task_count"] == 9
    assert out["remaining_creditable_task_count"] == 45
    assert out["upper_bound_successes"] == 225
    assert out["required_successes"] == 220
    assert out["headroom_successes"] == 5
    assert out["attainability_state"] == "NOT_FALSIFIED__ROUTE_REOPENED_FOR_MINIMUM_REALITY_SELECTION"
    assert out["execution_authority"] is False
    assert out["acceptance_credit_delta"] == 0


def test_invalid_inputs_fail_closed():
    import pytest
    with pytest.raises(ValueError):
        recompile(probe_passed=True, trials_per_task=0)
