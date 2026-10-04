from canonical.runtime import livebench_legacy15_composition_partition_v1 as p


def test_exhaustive_finite_partition():
    out = p.prove_exhaustive_partition()
    assert out["status"] == "PASS__EXHAUSTIVE_32768_SUBSET_PARTITION"
    assert out["all_subsets"] == 32768
    assert out["uncovered_valid_subsets"] == 0
    assert out["maximal_mode_count"] == 9
    assert out["maximum_simultaneous_family_count"] == 9


def test_special_modes_are_projected_exactly():
    json_mode = {
        "detectable_format:json_format",
        "keywords:existence",
        "keywords:forbidden_words",
    }
    assert p.is_valid(json_mode)
    assert p.covering_modes(json_mode) == (0,)

    repeat_mode = {
        "combination:repeat_prompt",
        "detectable_format:title",
        "keywords:existence",
    }
    assert p.is_valid(repeat_mode)
    assert p.covering_modes(repeat_mode) == (1,)

    two_mode = {
        "combination:two_responses",
        "detectable_format:title",
        "keywords:existence",
        "keywords:forbidden_words",
    }
    assert p.is_valid(two_mode)
    assert p.covering_modes(two_mode) == (2,)


def test_conflicting_pairs_fail_closed():
    assert not p.is_valid({
        "detectable_format:json_format",
        "length_constraints:number_words",
    })
    assert not p.is_valid({
        "combination:repeat_prompt",
        "keywords:forbidden_words",
    })
    assert not p.is_valid({
        "detectable_format:title",
        "startend:quotation",
    })


def test_unknown_identity_fails_closed():
    out = p.classify({"not:a_real_checker"})
    assert out["status"] == "FAIL_CLOSED"
    assert out["terminal_data_used"] is False
