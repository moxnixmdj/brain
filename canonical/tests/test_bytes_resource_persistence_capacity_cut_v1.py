from canonical.runtime.bytes_resource_persistence_capacity_cut_v1 import (
    PersistenceCapacityError,
    absolute_candidate_elimination_resolution_capacity,
    candidate_check_persistent_bits,
    capacity_certificate,
    minimum_persistent_index_bits,
    minimum_persistent_index_states,
    verify_finite_cut,
)


def test_universal_policy_requires_zero_persistent_bits():
    assert minimum_persistent_index_states(
        policy_cover_size=1,
        effective_nonpersistent_separator_states=1,
        suffix_resolution_capacity=1,
    ) == 1
    assert minimum_persistent_index_bits(
        policy_cover_size=1,
        effective_nonpersistent_separator_states=1,
        suffix_resolution_capacity=1,
    ) == 0


def test_plain_policy_index_bound_recovered_when_no_other_capacity():
    assert minimum_persistent_index_bits(
        policy_cover_size=2,
        effective_nonpersistent_separator_states=1,
        suffix_resolution_capacity=1,
    ) == 1
    assert minimum_persistent_index_bits(
        policy_cover_size=8,
        effective_nonpersistent_separator_states=1,
        suffix_resolution_capacity=1,
    ) == 3
    assert minimum_persistent_index_bits(
        policy_cover_size=9,
        effective_nonpersistent_separator_states=1,
        suffix_resolution_capacity=1,
    ) == 4


def test_nonpersistent_separator_and_suffix_capacity_reduce_persistent_bits():
    assert minimum_persistent_index_bits(
        policy_cover_size=8,
        effective_nonpersistent_separator_states=2,
        suffix_resolution_capacity=2,
    ) == 1
    assert minimum_persistent_index_bits(
        policy_cover_size=9,
        effective_nonpersistent_separator_states=2,
        suffix_resolution_capacity=2,
    ) == 2


def test_zero_persistence_when_reacquirable_and_suffix_capacity_cover_policy_classes():
    cert = capacity_certificate(
        policy_cover_size=16,
        effective_nonpersistent_separator_states=4,
        suffix_resolution_capacity=4,
    )
    assert cert["zero_persistent_bits_lower_bound"] is True
    assert cert["minimum_persistent_index_states_lower_bound"] == 1


def test_exact_candidate_checks_have_q_plus_one_elimination_capacity():
    assert absolute_candidate_elimination_resolution_capacity(0) == 1
    assert absolute_candidate_elimination_resolution_capacity(1) == 2
    assert absolute_candidate_elimination_resolution_capacity(3) == 4


def test_candidate_check_corollary():
    assert candidate_check_persistent_bits(
        policy_cover_size=17,
        effective_nonpersistent_separator_states=1,
        max_candidate_checks=3,
    ) == 3
    assert candidate_check_persistent_bits(
        policy_cover_size=17,
        effective_nonpersistent_separator_states=2,
        max_candidate_checks=3,
    ) == 2


def test_capacity_certificate_proves_one_fewer_bit_insufficient():
    cert = capacity_certificate(
        policy_cover_size=33,
        effective_nonpersistent_separator_states=2,
        suffix_resolution_capacity=3,
    )
    assert cert["minimum_persistent_index_bits_lower_bound"] == 3
    assert cert["capacity_with_lower_bound_bits"] >= 33
    assert cert["one_fewer_bit_capacity_insufficient_when_bits_positive"] is True


def test_fail_closed_on_invalid_cardinalities():
    for kwargs in (
        dict(policy_cover_size=0, effective_nonpersistent_separator_states=1, suffix_resolution_capacity=1),
        dict(policy_cover_size=1, effective_nonpersistent_separator_states=0, suffix_resolution_capacity=1),
        dict(policy_cover_size=1, effective_nonpersistent_separator_states=1, suffix_resolution_capacity=0),
    ):
        try:
            minimum_persistent_index_bits(**kwargs)
        except PersistenceCapacityError:
            pass
        else:
            raise AssertionError("expected invalid finite capacity input to fail closed")


def test_exhaustive_small_integer_verification():
    out = verify_finite_cut(128)
    assert out["status"] == "PASS"
    assert out["checked_finite_instances"] == 128 * 8 * 8
