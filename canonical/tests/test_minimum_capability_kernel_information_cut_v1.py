from canonical.runtime.minimum_capability_kernel_information_cut_v1 import (
    absolute_verifier_success,
    best_worst_case_without_separator,
    delayed_separator_usable,
    indistinguishable_binary_worlds,
    separator_aware_success,
    verify_information_cut,
)


def test_no_policy_beats_half_worst_case_without_separator():
    assert best_worst_case_without_separator() == 0.5
    for q in (0.0, 0.1, 0.5, 0.9, 1.0):
        assert indistinguishable_binary_worlds(q).worst_case_success <= 0.5


def test_separator_aware_target_strictly_exceeds_information_blind_bound():
    assert separator_aware_success() == (1.0, 1.0)
    assert min(separator_aware_success()) > best_worst_case_without_separator()


def test_absolute_verifier_is_a_valid_bypass():
    assert absolute_verifier_success() == (1.0, 1.0)


def test_separator_after_irreversible_deadline_is_not_admissible():
    assert delayed_separator_usable(separator_arrival=1, decision_deadline=0) is False
    assert delayed_separator_usable(separator_arrival=0, decision_deadline=0) is True


def test_information_cut_verifier():
    out = verify_information_cut()
    assert out["no_separator_worst_case_upper_bound"] == 0.5
    assert out["generic_search_without_information_not_universally_sufficient"] is True
