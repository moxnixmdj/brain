import math
import pytest

from canonical.runtime.gdpval_crowdbt_two_anchor_identification_v1 import (
    TwoAnchorIdentificationError,
    crowd_bt_probability,
    identify,
)


def run(score, eta, r1=1200.0, r2=1700.0):
    return identify({
        "anchor1_rating": r1,
        "anchor2_rating": r2,
        "preference_probability_vs_anchor1": crowd_bt_probability(score, r1, eta),
        "preference_probability_vs_anchor2": crowd_bt_probability(score, r2, eta),
    })


@pytest.mark.parametrize("score", [700.0, 1200.0, 1450.0, 1700.0, 1866.0, 2300.0])
@pytest.mark.parametrize("eta", [0.1, 0.25, 0.49, 0.51, 0.75, 0.95])
def test_recovers_score_and_eta_across_adversarial_and_nonadversarial_judges(score, eta):
    out = run(score, eta)
    assert out["status"].startswith("PASS__")
    assert math.isclose(out["identified_rating"], score, abs_tol=1e-6)
    assert math.isclose(out["identified_eta"], eta, abs_tol=1e-8)


def test_anchor_equality_special_case():
    out = run(1200.0, 0.8)
    assert math.isclose(out["identified_rating"], 1200.0, abs_tol=1e-8)
    assert math.isclose(out["identified_eta"], 0.8, abs_tol=1e-8)


def test_exact_random_judge_is_unidentified():
    out = run(1866.0, 0.5)
    assert out["status"].startswith("UNKNOWN__")
    assert out["identified_rating"] is None


def test_distinct_anchors_required():
    with pytest.raises(TwoAnchorIdentificationError):
        identify({
            "anchor1_rating": 1600.0,
            "anchor2_rating": 1600.0,
            "preference_probability_vs_anchor1": 0.6,
            "preference_probability_vs_anchor2": 0.6,
        })


def test_incompatible_probabilities_fail_closed():
    with pytest.raises(TwoAnchorIdentificationError):
        identify({
            "anchor1_rating": 1200.0,
            "anchor2_rating": 1700.0,
            "preference_probability_vs_anchor1": 0.9,
            "preference_probability_vs_anchor2": 0.9,
        })


def test_no_terminal_credit():
    out = run(1866.0, 0.8)
    assert out["semantic_premise_verified_by_this_runtime"] is False
    assert out["finite_sample_uncertainty_handled"] is False
    assert out["terminal_authority"] is False
    assert out["promotion_authority"] is False
    assert out["terminal_credit_delta"] == 0
