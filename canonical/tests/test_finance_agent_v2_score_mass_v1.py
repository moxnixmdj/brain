from canonical.runtime.finance_agent_v2_score_mass_v1 import (
    THRESHOLD_SCORE_MASS,
    aggregate_certificate,
    minimum_full_score_executions,
    minimum_uniform_full_score_tasks_across_all_runs,
)


def _full(n):
    out = []
    for k in range(n):
        run_id = (k // 450) + 1
        task_id = f"q{(k % 450) + 1:03d}"
        out.append({"run_id": run_id, "task_id": task_id, "lower_bound": "1"})
    return out


def test_exact_threshold_constants():
    assert str(THRESHOLD_SCORE_MASS) == "790.965"
    assert minimum_full_score_executions() == 791
    assert minimum_uniform_full_score_tasks_across_all_runs() == 264


def test_790_full_score_executions_do_not_force_pass():
    out = aggregate_certificate(_full(790))
    assert out["forced_pass"] is False
    assert out["certified_score_mass_lower_bound"] == "790"


def test_791_full_score_executions_force_pass():
    out = aggregate_certificate(_full(791))
    assert out["forced_pass"] is True
    assert out["certified_score_mass_lower_bound"] == "791"


def test_exact_fractional_mass_can_force_pass():
    rows = _full(790)
    rows.append({"run_id": 2, "task_id": "fractional-extra", "lower_bound": "0.965"})
    out = aggregate_certificate(rows)
    assert out["forced_pass"] is True
    assert out["certified_score_mass_lower_bound"] == "790.965"


def test_263_uniform_full_score_tasks_across_three_runs_are_insufficient():
    rows = [
        {"run_id": r, "task_id": f"q{i:03d}", "lower_bound": "1"}
        for r in range(1, 4)
        for i in range(1, 264)
    ]
    out = aggregate_certificate(rows)
    assert out["certified_score_mass_lower_bound"] == "789"
    assert out["forced_pass"] is False


def test_264_uniform_full_score_tasks_across_three_runs_are_sufficient():
    rows = [
        {"run_id": r, "task_id": f"q{i:03d}", "lower_bound": "1"}
        for r in range(1, 4)
        for i in range(1, 265)
    ]
    out = aggregate_certificate(rows)
    assert out["certified_score_mass_lower_bound"] == "792"
    assert out["forced_pass"] is True


def test_duplicate_task_run_fails_closed():
    rows = [
        {"run_id": 1, "task_id": "q001", "lower_bound": "1"},
        {"run_id": 1, "task_id": "q001", "lower_bound": "1"},
    ]
    try:
        aggregate_certificate(rows)
    except ValueError as exc:
        assert str(exc) == "DUPLICATE_TASK_RUN_BOUND"
    else:
        raise AssertionError("duplicate bound must fail closed")


def test_out_of_range_lower_bound_fails_closed():
    try:
        aggregate_certificate([{"run_id": 1, "task_id": "q001", "lower_bound": "1.0001"}])
    except ValueError as exc:
        assert str(exc) == "LOWER_BOUND_OUT_OF_RANGE"
    else:
        raise AssertionError("invalid lower bound must fail closed")
