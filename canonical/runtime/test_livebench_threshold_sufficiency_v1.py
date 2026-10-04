from fractions import Fraction
import pytest

from canonical.runtime.livebench_threshold_sufficiency_v1 import (
    aggregate_score_lower_bound,
    certificate,
    prompt_score_lower_bound,
)


def test_unaffected_prompt_scores_one():
    assert prompt_score_lower_bound(3, 0) == Fraction(1, 1)


def test_single_unsupported_single_constraint_scores_zero():
    assert prompt_score_lower_bound(1, 1) == Fraction(0, 1)


def test_single_unsupported_of_two_scores_quarter():
    assert prompt_score_lower_bound(2, 1) == Fraction(1, 4)


def test_public_ifbench_overlap_histogram_beats_frozen_bar_conservatively():
    # Public IFBench 0.3.0 test set at allenai/IFBench commit
    # 1c40f0c10d9b5c5c2f10a175a28007ebb64f7f4d:
    # exact histogram by (total constraints, ratio:overlap constraints).
    hist = {(1, 0): 251, (2, 0): 37, (1, 1): 5, (2, 1): 7}
    score = aggregate_score_lower_bound(hist)
    assert score == Fraction(1159, 1200)
    assert score > Fraction(657, 1000)


def test_certificate_reports_exact_margin_without_float_authority():
    hist = {(1, 0): 251, (2, 0): 37, (1, 1): 5, (2, 1): 7}
    out = certificate(hist, threshold=Fraction(657, 1000))
    assert out["status"] == "PASS"
    assert out["score_lower_bound_fraction"] == "1159/1200"
    assert out["threshold_fraction"] == "657/1000"
    assert out["margin_fraction"] == "1853/6000"
    assert out["terminal_authority"] is False
    assert out["acceptance_credit"] is False


def test_invalid_histogram_fails_closed():
    with pytest.raises(ValueError, match="UNSUPPORTED_EXCEEDS_TOTAL"):
        aggregate_score_lower_bound({(1, 2): 1})
