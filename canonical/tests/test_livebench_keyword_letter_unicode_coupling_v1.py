from canonical.runtime import livebench_keyword_letter_unicode_coupling_v1 as r


def test_full_unicode_equivalence_reduction():
    out = r.verify()
    assert out["exact_letter_evasions"] == {
        "i": ["U+0131"],
        "s": ["U+017F"],
    }
    assert out["acceptance_credit"] is False


def test_zero_cost_keyword_carriers_for_i_and_s():
    s = r.repeated_keyword_carrier("signal", "s", 3)
    i = r.repeated_keyword_carrier("inside", "i", 3)
    assert r.keyword_count(s, "signal") == 3
    assert r.letter_count(s, "s") == 0
    assert r.keyword_count(i, "inside") == 3
    assert r.letter_count(i, "i") == 0


def test_non_evasion_letter_cost_is_exact():
    value = r.repeated_keyword_carrier("analysis", "a", 3)
    assert r.keyword_count(value, "analysis") == 3
    assert r.letter_count(value, "a") == 6
    assert r.minimal_letter_cost_per_keyword_match("analysis", "a") == 2


def test_digit_boundaries_preserve_exact_nonoverlap_count():
    value = r.repeated_keyword_carrier("a", "a", 3)
    assert value == "9aaa9"
    assert r.keyword_count(value, "a") == 3
    assert r.letter_count(value, "a") == 3
