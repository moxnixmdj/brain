from canonical.runtime import livebench_union25_interaction_kernel_v1 as k


def test_union25_interaction_kernel_exact_partition():
    out = k.verify()
    assert out["input"] == {
        "compatible_union25_structures": 14559,
        "active15_structures": 928,
        "extra_bearing_structures": 13631,
        "extra_family_signatures": 156,
    }
    assert out["interaction_partition"] == {
        "K0_CONSTRAINED_SINGLETON": 1,
        "K1_DECORATOR_GENERAL": 2053,
        "K2_REPEAT_NO_COMMA": 4,
        "K3_HARD_GENERAL": 11569,
        "K4_TWO_LANGUAGE": 4,
    }


def test_union25_hard_kernel_is_exactly_19_cores():
    out = k.verify()
    hard = out["hard_kernel"]
    assert hard["distinct_compatible_hard_cores"] == 19
    assert len(hard["hard_cores"]) == 19
    assert hard["general_structures"] == 11569
    assert hard["two_response_language_structures"] == 4


def test_union25_decorator_kernel_has_only_repeat_no_comma_exception():
    out = k.verify()
    decorators = out["decorator_kernel"]
    assert decorators["distinct_nonempty_signatures"] == 7
    assert decorators["general_structures"] == 2053
    assert len(decorators["repeat_no_comma_exceptions"]) == 4
    assert all("combination:repeat_prompt" in ids for ids in decorators["repeat_no_comma_exceptions"])
    assert all("punctuation:no_comma" in ids for ids in decorators["repeat_no_comma_exceptions"])


def test_interaction_kernel_is_zero_credit_obligation_reduction_only():
    out = k.verify()
    assert out["terminal_rows_used"] == 0
    assert out["hidden_kwargs_used"] == 0
    assert out["target_scores_used"] == 0
    assert out["acceptance_credit"] is False
    assert out["capability_credit"] is False
