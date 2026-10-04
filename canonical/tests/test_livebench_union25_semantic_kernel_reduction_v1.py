from canonical.runtime import livebench_union25_semantic_kernel_reduction_v1 as r


def test_union25_semantic_kernel_reduction_is_exact():
    out = r.verify()
    assert out["upstream"]["raw_extra10_signatures"] == 156
    assert out["proven_reduction_without_language_assumption"] == {
        "semantic_kernel_count": 64,
        "nonlanguage_hard_kernel_count": 31,
        "language_sensitive_kernel_count": 31,
        "decorator_only_kernel_count": 1,
        "isolated_constrained_kernel_count": 1,
    }
    assert out["conditional_reduction_after_language_neutrality_gate"][
        "semantic_kernel_count"
    ] == 41
    assert out["conditional_reduction_after_language_neutrality_gate"][
        "hard_kernel_count"
    ] == 39


def test_zero_lexeme_decorator_carriers():
    facts = r.verify()["decorator_invariants"]
    assert facts["placeholder_carrier"] == "[]"
    assert facts["highlight_carrier"] == "*-*"
    assert facts["regexp_word_delta_each"] == 0
    assert facts["ascii_letter_delta_each"] == 0
    assert facts["comma_delta_each"] == 0
    assert facts["sentence_terminator_delta_each"] == 0
    assert facts["cased_character_delta_each"] == 0
    assert facts["special_route_compatible"] is False
    assert facts["language_detector_neutrality_proved_here"] is False
