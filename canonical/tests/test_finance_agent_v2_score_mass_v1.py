from canonical.runtime.finance_agent_v2_score_mass_v1 import (
    RUN_SCORE_MASS_THRESHOLD_PERCENT,
    TASK_SCORE_MASS_THRESHOLD,
    aggregate_run_score_certificate,
    aggregate_task_score_certificate,
    minimum_full_score_task_run_executions_if_equal_task_average_bound,
    minimum_uniform_full_score_tasks_across_all_runs_if_equal_task_average_bound,
)


def _full_task_runs(n):
    return [
        {
            "run_id": (k // 450) + 1,
            "task_id": f"q{(k % 450) + 1:03d}",
            "lower_bound": "1",
        }
        for k in range(n)
    ]


def test_exact_threshold_constants():
    assert str(RUN_SCORE_MASS_THRESHOLD_PERCENT) == "175.77"
    assert str(TASK_SCORE_MASS_THRESHOLD) == "790.965"
    assert minimum_full_score_task_run_executions_if_equal_task_average_bound() == 791
    assert minimum_uniform_full_score_tasks_across_all_runs_if_equal_task_average_bound() == 264


def test_run_score_mass_exact_threshold_forces_pass():
    out = aggregate_run_score_certificate([
        {"run_id": 1, "lower_bound_percent": "60"},
        {"run_id": 2, "lower_bound_percent": "60"},
        {"run_id": 3, "lower_bound_percent": "55.77"},
    ])
    assert out["forced_pass"] is True
    assert out["certified_run_score_mass_lower_bound_percent"] == "175.77"
    assert out["reported_score_lower_bound_percent"] == "58.59"


def test_run_score_mass_below_threshold_fails():
    out = aggregate_run_score_certificate([
        {"run_id": 1, "lower_bound_percent": "60"},
        {"run_id": 2, "lower_bound_percent": "60"},
        {"run_id": 3, "lower_bound_percent": "55.76"},
    ])
    assert out["forced_pass"] is False
    assert out["certified_run_score_mass_lower_bound_percent"] == "175.76"


def test_missing_runs_contribute_zero_lower_bound():
    out = aggregate_run_score_certificate([
        {"run_id": 1, "lower_bound_percent": "100"},
    ])
    assert out["forced_pass"] is False
    assert out["reported_score_lower_bound_percent"] == "33.33333333333333333333333333"


def test_task_route_fails_closed_without_aggregation_binding():
    try:
        aggregate_task_score_certificate(
            _full_task_runs(791),
            equal_task_average_authoritatively_bound=False,
        )
    except ValueError as exc:
        assert str(exc) == "EQUAL_TASK_AVERAGE_AGGREGATION_NOT_BOUND"
    else:
        raise AssertionError("task route must fail without equal-task aggregation binding")


def test_790_full_task_runs_do_not_force_pass_when_bound():
    out = aggregate_task_score_certificate(
        _full_task_runs(790),
        equal_task_average_authoritatively_bound=True,
    )
    assert out["forced_pass"] is False
    assert out["certified_task_score_mass_lower_bound"] == "790"


def test_791_full_task_runs_force_pass_when_bound():
    out = aggregate_task_score_certificate(
        _full_task_runs(791),
        equal_task_average_authoritatively_bound=True,
    )
    assert out["forced_pass"] is True
    assert out["certified_task_score_mass_lower_bound"] == "791"


def test_exact_fractional_task_mass_forces_pass_when_bound():
    rows = _full_task_runs(790)
    rows.append({"run_id": 2, "task_id": "fractional-extra", "lower_bound": "0.965"})
    out = aggregate_task_score_certificate(
        rows,
        equal_task_average_authoritatively_bound=True,
    )
    assert out["forced_pass"] is True
    assert out["certified_task_score_mass_lower_bound"] == "790.965"


def test_263_uniform_full_score_tasks_are_insufficient_when_bound():
    rows = [
        {"run_id": r, "task_id": f"q{i:03d}", "lower_bound": "1"}
        for r in range(1, 4)
        for i in range(1, 264)
    ]
    out = aggregate_task_score_certificate(
        rows,
        equal_task_average_authoritatively_bound=True,
    )
    assert out["certified_task_score_mass_lower_bound"] == "789"
    assert out["forced_pass"] is False


def test_264_uniform_full_score_tasks_are_sufficient_when_bound():
    rows = [
        {"run_id": r, "task_id": f"q{i:03d}", "lower_bound": "1"}
        for r in range(1, 4)
        for i in range(1, 265)
    ]
    out = aggregate_task_score_certificate(
        rows,
        equal_task_average_authoritatively_bound=True,
    )
    assert out["certified_task_score_mass_lower_bound"] == "792"
    assert out["forced_pass"] is True
