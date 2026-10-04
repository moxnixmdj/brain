from canonical.runtime import livebench_union25_extension_kernel_factorization_v1 as f


def test_exact_product_factorization():
    out = f.verify()
    assert out["raw_extra_signatures"] == 156
    assert out["isolated_constrained_response_signatures"] == 1
    assert out["nonconstrained_product_signatures"] == 155
    assert out["semantic_axis_nonempty_state_count"] == 9
    assert out["closed_form_signature_count"]["total"] == 156


def test_axis_state_space_has_no_triples():
    out = f.verify()
    states = out["semantic_axis_states"]
    assert max(map(len, states)) == 2
    assert sum(len(x) == 1 for x in states) == 5
    assert sum(len(x) == 2 for x in states) == 4


def test_numeric_format_carrier_keeps_word_upper_margin():
    budget = f.verify()["numeric_format_carrier_word_budget"]
    assert budget["combined_bound"] == 56
    assert budget["minimum_public_less_than_threshold"] == 100
    assert budget["remaining_margin"] == 44


def test_known_factorizations():
    assert f.factor_signature((f.CONSTRAINED,))["isolated"] == (f.CONSTRAINED,)
    x = f.factor_signature((
        f.KEYWORD_FREQUENCY,
        f.LETTER_FREQUENCY,
        f.PLACEHOLDERS,
        f.NO_COMMA,
    ))
    assert x["semantic_axis"] == (f.KEYWORD_FREQUENCY,)
    assert x["commuting_modifiers"] == (
        f.LETTER_FREQUENCY,
        f.PLACEHOLDERS,
        f.NO_COMMA,
    )
