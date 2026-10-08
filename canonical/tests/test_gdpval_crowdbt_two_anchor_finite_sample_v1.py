import math
import pytest

from canonical.runtime.gdpval_crowdbt_two_anchor_finite_sample_v1 import (
    TwoAnchorFiniteSampleError,
    certify,
)


def test_pass_for_strong_candidate_with_large_nonadversarial_samples():
    out = certify({
        "anchor1_rating": 1400.0,
        "anchor2_rating": 1600.0,
        "target_rating": 1866.0,
        "alpha": 0.05,
        "anchor1_sample": {"brain_wins": 781608, "ties": 0, "reference_wins": 218392},
        "anchor2_sample": {"brain_wins": 745455, "ties": 0, "reference_wins": 254545},
    })
    assert out["status"] == "PASS__HOEFFDING_ROBUST_TARGET_NONINFERIORITY"
    assert out["ratio_interval"]["lower"] > 1.0
    assert out["ratio_interval"]["upper"] <= out["target_boundary_ratio"]


def test_pass_is_orientation_agnostic_for_adversarial_judge():
    out = certify({
        "anchor1_rating": 1400.0,
        "anchor2_rating": 1600.0,
        "target_rating": 1866.0,
        "alpha": 0.05,
        "anchor1_sample": {"brain_wins": 218392, "ties": 0, "reference_wins": 781608},
        "anchor2_sample": {"brain_wins": 254545, "ties": 0, "reference_wins": 745455},
    })
    assert out["status"] == "PASS__HOEFFDING_ROBUST_TARGET_NONINFERIORITY"


def test_unknown_at_target_boundary_due_sampling_uncertainty():
    out = certify({
        "anchor1_rating": 1400.0,
        "anchor2_rating": 1600.0,
        "target_rating": 1866.0,
        "alpha": 0.05,
        "anchor1_sample": {"brain_wins": 76159, "ties": 0, "reference_wins": 23841},
        "anchor2_sample": {"brain_wins": 69331, "ties": 0, "reference_wins": 30669},
    })
    assert out["status"] == "UNKNOWN__FINITE_SAMPLE_BOUND_INSUFFICIENT"


def test_unknown_when_orientation_interval_crosses_random():
    out = certify({
        "anchor1_rating": 1400.0,
        "anchor2_rating": 1600.0,
        "target_rating": 1866.0,
        "alpha": 0.05,
        "anchor1_sample": {"brain_wins": 51, "ties": 0, "reference_wins": 49},
        "anchor2_sample": {"brain_wins": 52, "ties": 0, "reference_wins": 48},
    })
    assert out["status"] == "UNKNOWN__FINITE_SAMPLE_BOUND_INSUFFICIENT"
    assert "SIMULTANEOUS_Z_INTERVALS_DO_NOT_ESTABLISH_A_COMMON_NONZERO_ORIENTATION" in out["blockers"]


def test_ties_are_half_credit():
    out = certify({
        "anchor1_rating": 1400.0,
        "anchor2_rating": 1600.0,
        "target_rating": 1866.0,
        "alpha": 0.05,
        "anchor1_sample": {"brain_wins": 70, "ties": 20, "reference_wins": 10},
        "anchor2_sample": {"brain_wins": 60, "ties": 20, "reference_wins": 20},
    })
    assert math.isclose(out["anchor1_sample"]["empirical_mean"], 0.8)
    assert math.isclose(out["anchor2_sample"]["empirical_mean"], 0.7)


def test_invalid_geometry_fails_closed():
    with pytest.raises(TwoAnchorFiniteSampleError):
        certify({
            "anchor1_rating": 1600.0,
            "anchor2_rating": 1400.0,
            "target_rating": 1866.0,
            "alpha": 0.05,
            "anchor1_sample": {"brain_wins": 1, "ties": 0, "reference_wins": 0},
            "anchor2_sample": {"brain_wins": 1, "ties": 0, "reference_wins": 0},
        })


def test_no_terminal_authority():
    out = certify({
        "anchor1_rating": 1400.0,
        "anchor2_rating": 1600.0,
        "target_rating": 1866.0,
        "alpha": 0.05,
        "anchor1_sample": {"brain_wins": 781608, "ties": 0, "reference_wins": 218392},
        "anchor2_sample": {"brain_wins": 745455, "ties": 0, "reference_wins": 254545},
    })
    assert out["semantic_premises_verified_by_this_runtime"] is False
    assert out["anchor_coordinate_uncertainty_included"] is False
    assert out["owner_exact_reproduction"] is False
    assert out["terminal_authority"] is False
    assert out["terminal_credit_delta"] == 0
