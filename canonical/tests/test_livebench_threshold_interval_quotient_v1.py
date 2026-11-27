import pytest

from canonical.runtime.livebench_threshold_interval_quotient_v1 import (
    SENTENCE_DOMAIN,
    WORD_DOMAIN,
    ThresholdQuotientError,
    checker_result,
    compression_summary,
    pass_intervals,
)

def brute(domain, c, relation):
    return {
        n: (c >= n if relation == "at least" else c < n)
        for n in range(domain.minimum, domain.maximum + 1)
    }

def from_interval(domain, interval):
    if interval is None:
        return {n: False for n in range(domain.minimum, domain.maximum + 1)}
    lo, hi = interval
    return {n: lo <= n <= hi for n in range(domain.minimum, domain.maximum + 1)}

@pytest.mark.parametrize("domain,max_count", [(WORD_DOMAIN, 650), (SENTENCE_DOMAIN, 60)])
def test_interval_certificate_exactly_reconstructs_every_frozen_threshold(domain, max_count):
    # Exhaust every measured count around and beyond the frozen domain boundaries.
    for c in range(max_count + 1):
        cert = pass_intervals(domain, c)
        assert from_interval(domain, cert["at_least_pass_threshold_interval"]) == brute(domain, c, "at least")
        assert from_interval(domain, cert["less_than_pass_threshold_interval"]) == brute(domain, c, "less than")
        for n in range(domain.minimum, domain.maximum + 1):
            assert checker_result(domain, c, "at least", n) == (c >= n)
            assert checker_result(domain, c, "less than", n) == (c < n)

def test_boundary_duality_is_exact():
    for domain in (WORD_DOMAIN, SENTENCE_DOMAIN):
        for c in range(0, domain.maximum + 2):
            cert = pass_intervals(domain, c)
            for n in range(domain.minimum, domain.maximum + 1):
                a = checker_result(domain, c, "at least", n)
                l = checker_result(domain, c, "less than", n)
                assert a != l

def test_exact_state_count_collapse():
    out = compression_summary()
    assert out["word_raw_states"] == 802
    assert out["sentence_raw_states"] == 40
    assert out["combined_raw_states"] == 842
    assert out["certificate_scalars_per_domain"] == 1

def test_fail_closed():
    with pytest.raises(ThresholdQuotientError):
        pass_intervals(WORD_DOMAIN, -1)
    with pytest.raises(ThresholdQuotientError):
        checker_result(WORD_DOMAIN, 100, "equal", 100)
    with pytest.raises(ThresholdQuotientError):
        checker_result(WORD_DOMAIN, 100, "at least", 99)
