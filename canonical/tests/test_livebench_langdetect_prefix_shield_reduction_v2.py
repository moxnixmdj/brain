from canonical.runtime import livebench_langdetect_prefix_shield_reduction_v2 as r


def test_plain_prefix_fills_detector_window_and_zeroes_features():
    prefix = r.make_prefix_shield()
    out = r.abstract_detector_projection(prefix)
    assert len(prefix) == 10000
    assert out["cleaning_branch_taken"] is True
    assert out["extracted_ngram_count"] == 0
    assert out["detector_raises_langdetect_exception"] is True
    assert out["suffix_visible_to_detector"] is False


def test_quoted_nth_first_word_survives_raw_first_token_rule():
    word = "administration"
    prefix = r.make_prefix_shield(first_word=word, quote_wrapped=True)
    assert prefix.startswith('"' + word + " ")
    token = prefix.split()[0].strip().lstrip("'").lstrip('"')
    assert token == word
    assert r.abstract_detector_projection(prefix)["extracted_ngram_count"] == 0


def test_frozen_first_word_domain_guard():
    try:
        r.make_prefix_shield(first_word="é")
    except ValueError as exc:
        assert str(exc) == "FROZEN_PREFIX_FIRST_WORD_MUST_BE_ASCII"
    else:
        raise AssertionError("non-ASCII first word admitted")

    try:
        r.make_prefix_shield(first_word="x" * 15)
    except ValueError as exc:
        assert str(exc) == "FROZEN_PREFIX_FIRST_WORD_TOO_LONG"
    else:
        raise AssertionError("out-of-domain first word admitted")


def test_exact_language_compatible_active15_set_and_33_kernel_candidate():
    out = r.verify()
    assert len(out["language_compatible_active15"]) == 9
    assert out["kernel_reduction_candidate"] == {
        "prior_conservative_total": 64,
        "language_sensitive_prior": 31,
        "language_residual_after_failopen": 8,
        "total_after_failopen": 33,
    }
    assert out["acceptance_credit"] is False
    assert out["capability_credit"] is False
    assert out["independent_verification_required"] is True
