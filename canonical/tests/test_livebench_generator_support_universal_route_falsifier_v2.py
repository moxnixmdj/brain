from fractions import Fraction

from canonical.runtime import livebench_generator_support_universal_route_falsifier_v2 as f


def test_counterexample_is_conflict_compatible_and_mutually_exclusive():
    out = f.prove()
    assert out["status"] == "PASS__GENERATOR_SUPPORT_UNIVERSAL_THRESHOLD_ROUTE_FALSIFIED"
    assert out["counterexample"]["conflict_compatible"] is True
    assert out["counterexample"]["joint_satisfiable"] is False
    assert out["counterexample"]["maximum_simultaneously_true"] == 1


def test_exact_score_upper_bound_is_one_quarter_and_below_opus_floor():
    assert f.strict_score(False, 1, 2) == Fraction(1, 4)
    assert Fraction(1, 4) < f.OPUS55_FLOOR


def test_end_phrase_contains_forbidden_as_whole_word():
    assert f.end_phrase_forces_forbidden_word() is True


def test_no_terminal_or_acceptance_credit_claimed():
    out = f.prove()
    assert out["terminal_rows_read"] == 0
    assert out["terminal_case_metadata_read"] == 0
    assert out["deduction"]["actual_frozen_population_contains_counterexample"] == "NOT_CLAIMED"
    assert out["deduction"]["acceptance_credit"] is False
