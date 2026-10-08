from fractions import Fraction
import pytest

from canonical.runtime.gdpval_crowd_bt_orientation_mirror_v1 import (
    OrientationMirrorError,
    certify,
    mirror_world,
)


@pytest.mark.parametrize("p,eta", [
    ("3/4", "9/10"),
    ("2/3", "1/4"),
    ("9/20", "7/10"),
    ("1/2", "1"),
    ("1", "0"),
])
def test_exact_mirror_identity(p, eta):
    out = mirror_world(p, eta)
    assert out["observationally_identical"] is True
    assert Fraction(out["original_observed_probability"]) == Fraction(out["mirror_observed_probability"])


def test_reverses_latent_direction_away_from_half():
    out = mirror_world("3/4", "4/5")
    assert out["latent_direction_reversed"] is True
    assert Fraction(out["mirror_true_preference"]) < Fraction(1, 2)


def test_multi_judge_certificate():
    out = certify({"judges": [
        {"true_preference": "7/10", "eta": "4/5"},
        {"true_preference": "7/10", "eta": "3/5"},
        {"true_preference": "7/10", "eta": "1/5"},
    ]})
    assert out["status"] == "PASS__EXACT_MIRROR_IDENTITY"
    assert all(x["observationally_identical"] for x in out["witnesses"])
    assert out["terminal_credit_delta"] == 0


def test_rejects_invalid_probability():
    with pytest.raises(OrientationMirrorError):
        mirror_world("6/5", "1/2")
