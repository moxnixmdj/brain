from fractions import Fraction
import pytest

from canonical.runtime.gdpval_crowdbt_two_world_nonidentifiability_v1 import analyze, TwoWorldError


def test_exact_two_world_outcome_reversal():
    out = analyze()
    assert out["status"] == "PASS__OUTCOME_ONLY_TWO_WORLD_REVERSAL_PROVED"
    assert out["all_quality_slopes_positive"] is True
    assert out["worlds"]["W_BRAIN_WIN"]["mle_ordering_limit"] == "BRAIN_ABOVE_OPUS"
    assert out["worlds"]["W_OPUS_WIN"]["mle_ordering_limit"] == "BRAIN_BELOW_OPUS"
    assert out["only_deliberate_world_difference"] == "PREVIOUSLY_UNOBSERVED_BRAIN_PAIRWISE_JUDGE_OUTCOMES"


def test_exact_slope_values():
    out = analyze({"j1": Fraction(9,10), "j2": Fraction(3,4)})
    assert out["quality_slopes_2eta_minus_1"] == {"j1": "4/5", "j2": "1/2"}


def test_reject_uninformative_or_adversarial_quality():
    with pytest.raises(TwoWorldError):
        analyze({"j": Fraction(1,2)})
    with pytest.raises(TwoWorldError):
        analyze({"j": Fraction(2,5)})


def test_zero_credit():
    out = analyze()
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
