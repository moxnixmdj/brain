"""A hypothesis has a domain, and thirteen rounds never said so.

Every measurement in this session was a FIT. No module recorded the interval a hypothesis was checked
over, so `DETERMINED` was being read as a property of the hypothesis when it is a property of the
observations plus an unstated assumption about how the world continues.

The tests that matter most:

`test_a_prediction_outside_the_verified_interval_is_flagged` -- `relu` trained on x = 0,1,2 is the
identity there, correctly returns `return x`, and predicts -5 for x = -5 where the truth is 0. A
report that hands that back as a prediction, rather than naming it an extrapolation, is the gap this
module closes.

`test_the_rival_check_is_reported_as_a_negative_result` -- a rival search can only find hypotheses the
ontology can express. On `relu` in 0..2 there is no rival at all, because `relu` IS the identity
there; the truth (`max(x,0)`) is not representable and no comparison inside the ontology can notice.
The test asserts the weakness is reported rather than allowed to read as support.

`test_prequential_finds_what_the_ontology_hides` -- the only test that needs no oracle: build from the
first k observations, check against the k+1-th. `mod 2` and `x*x` die immediately; `2x` and `3x+1`
survive every step.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.domain_of_verification_v1 import (  # noqa: E402
    CASES,
    EXTRAPOLATION,
    INSIDE,
    _affine_body,
    check_prediction,
    observed_domain,
    predict_scalar,
    prequential,
    rivals,
)


# ---------------------------------------------------------------------------------------------
# The domain
# ---------------------------------------------------------------------------------------------

def test_the_domain_is_the_observed_interval():
    dom = observed_domain(CASES["2x on 0..2"])
    assert (dom["lo"], dom["hi"]) == (0, 2)
    assert dom["distinct_inputs"] == 3


def test_a_prediction_outside_the_verified_interval_is_flagged():
    dom = observed_domain(CASES["2x on 0..2"])
    assert check_prediction(dom, 1.0)["status"] == INSIDE
    assert check_prediction(dom, 100.0)["status"] == EXTRAPOLATION
    assert "EXTRAPOLATION" in check_prediction(dom, 100.0)["why"]


def test_a_prediction_inside_the_interval_is_not_flagged():
    dom = observed_domain(CASES["relu on -2..3"])
    for x in (-2, -0.5, 0, 2.9, 3):
        assert check_prediction(dom, x)["status"] == INSIDE


def test_predict_scalar_returns_the_value_and_its_status_together():
    dom = observed_domain(CASES["2x on 0..2"])
    out = predict_scalar("return 2 * x", ["x"], 1.5, dom)
    assert out["value"] == 3.0 and out["status"] == INSIDE


def test_a_two_input_domain_is_refused_loudly():
    """Fifth instance this session of an input-shape disagreement; it must not fail silently."""
    out = observed_domain([((1, 2), 3.0)])
    assert out["lo"] is None
    assert "one input at a time" in out["why"]


# ---------------------------------------------------------------------------------------------
# Prequential: no oracle required
# ---------------------------------------------------------------------------------------------

def test_prequential_finds_what_the_ontology_hides():
    """An affine hypothesis on non-affine data dies on the very next observation."""
    mod2 = prequential([((i,), float(i % 2)) for i in range(6)], _affine_body)
    square = prequential([((i,), float(i * i)) for i in range(1, 7)], _affine_body)
    assert mod2["refutations"] > 0 and not mod2["survived_all"]
    assert square["refutations"] > 0 and not square["survived_all"]


def test_an_affine_truth_survives_every_prequential_step():
    """The test must not falsely refute a hypothesis that is actually right."""
    for name, fn in (("2x", lambda i: 2 * i), ("3x+1", lambda i: 3 * i + 1)):
        out = prequential([((i,), float(fn(i))) for i in range(6)], _affine_body)
        assert out["survived_all"] is True
        assert out["refutations"] == 0


def test_prequential_reports_the_step_where_it_died():
    out = prequential([((i,), float(i % 2)) for i in range(6)], _affine_body)
    died = [s for s in out["steps"] if s["status"] == "REFUTED"]
    assert died and died[0]["trained_on"] >= 1
    assert "predicted" in died[0] and "actual" in died[0]


# ---------------------------------------------------------------------------------------------
# The rival check, and its honest weakness
# ---------------------------------------------------------------------------------------------

def test_the_rival_check_is_reported_as_a_negative_result():
    """D1 predicted a rival for relu-on-{0,1,2}. There is none: relu IS the identity there, and the
    affine class already returns the simplest member. The prediction was wrong and this records it.
    """
    out = rivals(CASES["relu on 0..2"], "return x")
    assert out["rivals"] == []
    assert "not about the world" in out["limitation"]


def test_a_degenerate_rival_is_rejected():
    """Without the degrees-of-freedom rule every hypothesis is under-written by a constant fitted to
    a single point -- which means the check says 'under-written' always and therefore says nothing."""
    out = rivals([((0,), 0.0), ((1,), 2.0), ((2,), 4.0)], "return 2 * x")
    assert not any(r["rival"] == "constant" for r in out["rivals"])


def test_absence_of_a_rival_is_not_reported_as_support():
    out = rivals(CASES["3x+1 on 0..2"], "return 3 * x + 1")
    assert out["rivals"] == []
    # the wording must refuse to call that reassurance
    assert "simplest fitting thing HERE" in out["why"] or "not about the world" in out["limitation"]
