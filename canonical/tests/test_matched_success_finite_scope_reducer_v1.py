from canonical.runtime.matched_success_finite_scope_reducer_v1 import (
    INPUT_SCHEMA,
    compile_reducer,
    monotonicity_theorem,
)


def base():
    return {
        "schema": INPUT_SCHEMA,
        "predicate_id": "AGENCY_MATCHED_SUCCESS_NONINFERIOR",
        "scope": {
            "finite": True,
            "complete": True,
            "frozen": True,
            "content_addressed": True,
            "same_case_universe_for_brain_and_opus": True,
            "binary_success_criterion": True,
            "no_population_extrapolation": True,
            "fixed_case_count_before_first_result": True,
            "no_sequential_early_stop": True,
            "case_ids": ["A", "B", "C", "D"],
        },
        "brain_success_case_ids": ["A", "B", "C"],
        "opus_success_case_ids": ["A", "C"],
    }


def test_exact_fraction_and_inclusion_transport():
    out = compile_reducer(base())
    assert out["status"] == "PASS__EXACT_FINITE_SCOPE_REDUCER"
    assert out["brain_bound"]["exact"] == "3/4"
    assert out["opus_bound"]["exact"] == "1/2"
    assert out["brain_noninferior"] is True
    assert out["opus_success_set_subset_of_brain"] is True
    assert out["monotonicity_transport_proved_for_this_input"] is True
    assert out["population_generalization_claimed"] is False


def test_more_successes_without_set_inclusion_still_scores_higher():
    x = base()
    x["brain_success_case_ids"] = ["A", "B", "C"]
    x["opus_success_case_ids"] = ["A", "D"]
    out = compile_reducer(x)
    assert out["brain_noninferior"] is True
    assert out["opus_success_set_subset_of_brain"] is False
    assert out["monotonicity_transport_proved_for_this_input"] is False


def test_brain_fewer_successes_fails_noninferiority():
    x = base()
    x["brain_success_case_ids"] = ["A"]
    x["opus_success_case_ids"] = ["A", "B"]
    out = compile_reducer(x)
    assert out["brain_noninferior"] is False


def test_outside_universe_fails_closed():
    x = base()
    x["brain_success_case_ids"].append("X")
    out = compile_reducer(x)
    assert out["status"] == "FAIL_CLOSED"


def test_incomplete_scope_fails_closed():
    x = base()
    x["scope"]["complete"] = False
    out = compile_reducer(x)
    assert out["status"] == "FAIL_CLOSED"


def test_population_extrapolation_forbidden():
    x = base()
    x["scope"]["no_population_extrapolation"] = False
    out = compile_reducer(x)
    assert out["status"] == "FAIL_CLOSED"


def test_sequential_early_stop_forbidden():
    x = base()
    x["scope"]["no_sequential_early_stop"] = False
    out = compile_reducer(x)
    assert out["status"] == "FAIL_CLOSED"


def test_general_monotonicity_many_sizes():
    for n in range(1, 101):
        assert monotonicity_theorem(n) is True
