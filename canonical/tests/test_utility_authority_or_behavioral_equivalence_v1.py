from canonical.runtime.utility_authority_or_behavioral_equivalence_v1 import (
    utility_free_dominance_requires_equality,
)


def test_nonidentical_laws_have_an_opus_favoring_bounded_indicator():
    out = utility_free_dominance_requires_equality(
        {"a": 0.6, "b": 0.4},
        {"a": 0.2, "b": 0.8},
    )
    assert out["laws_equal"] is False
    assert out["opus_strictly_better_on_indicator"] is True
    assert out["utility_authority_required_for_nonidentical_dominance"] is True


def test_equal_laws_need_no_utility_restriction_for_parity():
    out = utility_free_dominance_requires_equality(
        {"a": 0.25, "b": 0.75},
        {"a": 0.25, "b": 0.75},
    )
    assert out["laws_equal"] is True
    assert out["separating_event"] is None
    assert out["opus_strictly_better_on_indicator"] is False
    assert out["utility_authority_required_for_nonidentical_dominance"] is False


def test_reliability_gap_is_separated():
    out = utility_free_dominance_requires_equality(
        {"failure": 0.49, "success": 0.51},
        {"failure": 0.01, "success": 0.99},
    )
    assert out["separating_event"] == ("success",)
    assert out["brain_event_mass"] == 0.51
    assert out["opus_event_mass"] == 0.99
