from canonical.runtime import livebench_langdetect_failopen_reduction_v1 as r


def test_minimal_padding_forces_zero_features():
    samples = [
        "",
        "[]",
        "*-*",
        "[] *-*",
        "aaaaaaaaaa",
        "A A A A A",
        "A A A [] *-* 123",
    ]
    for raw in samples:
        out = r.neutralize_for_language_failopen(raw)
        facts = r.abstract_detector_projection(out)
        assert facts["cleaning_branch_taken"] is True
        assert facts["all_remaining_normalize_to_space"] is True
        assert facts["extracted_ngram_count"] == 0
        assert facts["detector_raises_cant_detect"] is True


def test_padding_is_minimal_for_ascii_safe_inputs():
    raw = "Ab[] *-*"
    n = r.padding_needed(raw)
    assert n > 0
    exact = raw + r.ZERO_WIDTH_SPACE * n
    assert r.abstract_detector_projection(exact)["cleaning_branch_taken"] is True
    if n > 0:
        short = raw + r.ZERO_WIDTH_SPACE * (n - 1)
        assert r.abstract_detector_projection(short)["cleaning_branch_taken"] is False


def test_unsafe_nonascii_is_rejected():
    try:
        r.neutralize_for_language_failopen("hello世界")
    except ValueError as exc:
        assert str(exc) == "OUTSIDE_FAILOPEN_SAFE_ALPHABET"
    else:
        raise AssertionError("unsafe non-ASCII input was accepted")


def test_exact_kernel_collapse():
    out = r.verify()
    red = out["kernel_reduction"]
    assert red["prior_conservative_total"] == 64
    assert red["prior_language_sensitive"] == 31
    assert red["language_residual_hard_kernel_count"] == 8
    assert red["candidate_total_after_failopen"] == 33
    assert red["candidate_reduction_vs_prior"] == 31
    assert out["acceptance_credit"] is False
    assert out["independent_verification_required"] is True
