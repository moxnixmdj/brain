from canonical.runtime import livebench_langdetect_balanced_decorator_invariance_v1 as r


def test_cleaning_branch_identity_exact_at_boundary():
    for p in range(5):
        for l in range(100):
            for n in range(max(0, 2 * l - 3), 2 * l + 4):
                assert r.cleaning_branch_identity(l, n, p)


def test_balanced_placeholder_and_highlight_raw_checker_deltas():
    for p in range(5):
        for h in range(5):
            if p == 0 and h == 0:
                continue
            facts = r._overlay_source_facts(p, h)
            assert facts["latin_count_delta"] == 2 * p
            assert facts["non_latin_count_delta"] == 4 * p
            assert facts["placeholder_checker_delta"] == p
            assert facts["highlight_checker_delta"] == h
            assert facts["ngram_normalized_symbol_set"] == ["SPACE"]
            assert facts["regexp_word_delta"] == 0
            assert facts["ascii_letter_delta"] == 0
            assert facts["comma_delta"] == 0
            assert facts["sentence_terminator_delta"] == 0
            assert facts["cased_character_delta"] == 0


def test_all_pinned_language_carriers_keep_cleaning_branch():
    out = r.verify()
    assert out["pinned_language_carrier_count"] == 30
    assert out["pinned_decorator_cases_checked"] == 720
    assert out["max_decorated_length"] < out["detector_window"]


def test_japanese_no_internal_space_still_has_duplicate_anchor():
    sample = r.LANGUAGE_SAMPLES["ja"]
    assert " " not in sample
    base = sample + " " + sample
    decorated = r.decorate_losslessly(base, placeholders=4, highlights=4)
    assert r.cleaning_removes_latin(decorated) == r.cleaning_removes_latin(base)
