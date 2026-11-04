"""Hypotheses with slots, and a search that admits when it ran out of bank.

`y = 2x + 1` defeated the whole apparatus. Not because it is hard, but because the search cannot say
`a*x + b` -- it can only spell concrete expressions over a frozen constant list, so slope 3 costs
three operations and is unreachable at any affordable budget. This module adds the missing kind of
object and then hands it back to the search's own verifier.

The three tests that matter most:

`test_a_budget_failure_is_not_reported_as_a_fact_about_the_world` -- the search said "no body in the
grammar reproduces the examples" for data whose body is `((x + 1) + x) / 1`. It was reachable at
weight 4 in a bank of 5000. The sentence was false, and no amount of care in the layers above could
have caught it, because the layers above believe what the search tells them.

`test_further_points_test_rather_than_inform` -- a two-parameter family is pinned by two points. The
third is a consistency check. A creature that cannot make that distinction cannot know when it has
enough evidence, only when it stops finding new matches.

`test_a_non_affine_point_set_is_refused_and_never_rounded` -- the fitted parameters must be absent,
not approximately right. Rounding a quadratic onto a line is how a mechanism reports success on
something it did not understand.
"""
from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.evidence_demand_v1 import (  # noqa: E402
    SEARCH_TRUNCATED,
    demand_evidence,
)
from canonical.runtime.hypothesis_classes_v1 import (  # noqa: E402
    FITS,
    INCONSISTENT,
    UNDERDETERMINED,
    Affine,
    Power,
    compile_body,
    determine,
    question_for,
    reach,
)
from canonical.runtime.swe_observational_program_synthesizer_v1 import (  # noqa: E402
    last_search_coverage,
    synthesize_python_function_body,
)

LINE_3 = [((0,), 1.0), ((1,), 4.0), ((2,), 7.0)]      # 3x + 1


# --------------------------------------------------------------------------------------------
# The class knows how much evidence it needs
# --------------------------------------------------------------------------------------------

def test_two_parameters_need_two_points_and_the_third_is_only_a_test():
    two = Affine.fit([(0, 1.0), (1, 3.0)])
    assert two["status"] == FITS
    assert two["needs"] == 2 and two["surplus"] == 0

    three = Affine.fit([(0, 1.0), (1, 3.0), (2, 5.0)])
    assert three["status"] == FITS
    assert three["surplus"] == 1          # a test, not new information


def test_one_point_leaves_a_two_parameter_family_underdetermined():
    assert Affine.fit([(0, 1.0)])["status"] == UNDERDETERMINED


def test_the_question_is_formed_before_the_answer_arrives():
    """The string search can only ask about survivors it already has. A family can ask in advance."""
    ask = question_for([(0, 1.0)], "affine")
    assert len(ask["queries"]) == 1
    assert ask["queries"][0]["x"] != 0


def test_a_pinned_family_asks_nothing_because_nothing_would_inform_it():
    ask = question_for([(0, 1.0), (1, 3.0), (2, 5.0)], "affine")
    assert ask["queries"] == []
    assert ask["surplus_inputs"] == 1


# --------------------------------------------------------------------------------------------
# Refusal, not rounding
# --------------------------------------------------------------------------------------------

def test_a_non_affine_point_set_is_refused_and_never_rounded():
    quad = Affine.fit([(0, 0.0), (1, 1.0), (2, 4.0)])
    assert quad["status"] == INCONSISTENT
    assert quad["parameters"] is None
    assert len(quad["violations"]) == 1


def test_a_piecewise_world_is_not_explained_by_one_family():
    """The true function changes regime; no single line covers it, and the module says so."""
    points = [((-2,), 99.0), ((1,), 2.0), ((2,), 4.0), ((3,), 6.0)]
    assert reach(points, ["x"])["reached"] is False


# --------------------------------------------------------------------------------------------
# Exactness, and where a float stops being exact
# --------------------------------------------------------------------------------------------

def test_whole_number_fits_are_exact_rather_than_tolerance_close():
    fit = Affine.fit([(0, 1.0), (1, 4.0), (2, 7.0)])
    assert fit["parameters"] == {"a": 3, "b": 1}
    assert fit["reconstructed"] is False


def test_a_decimal_one_third_is_reconstructed_to_one_third():
    """The floats 1/3 and 5/3 are not 1/3 and 5/3 as decimals; the REPORT should still read as
    fractions, and must say that it reconstructed rather than solved them."""
    pts = [(0, 1 / 3), (1, 1.0), (2, 5 / 3)]
    fit = Affine.fit(pts)
    assert fit["status"] == FITS
    assert fit["parameters"] == {"a": "2/3", "b": "1/3"}
    assert fit["reconstructed"] is True


def test_reconstruction_does_not_invent_a_simple_answer_for_an_irrational():
    """sqrt(2) reconstructs to a continued-fraction convergent, and that is correct -- 1607521/1136689
    really is within 10^-12 of it. What must NOT happen is that a convergent gets reported as a
    simple answer. The first version of this test asserted the value came back unchanged, which was
    simply wrong about continued fractions; the honest property is that a genuinely irrational value
    never reconstructs to something small enough to look like a clean result.
    """
    from canonical.runtime.hypothesis_classes_v1 import _reconstruct

    val = Fraction(str(2 ** 0.5))
    got = _reconstruct(val)
    assert abs(got - val) <= Fraction(1, 10 ** 12)      # faithful to the stated precision
    assert got.denominator > 1000                        # and not sold as a tidy fraction
    assert _reconstruct(Fraction(str(1 / 3))) == Fraction(1, 3)   # the case that must work


# --------------------------------------------------------------------------------------------
# Handing the fit back to the search
# --------------------------------------------------------------------------------------------

def test_the_line_the_search_could_not_fit_compiles_and_verifies():
    out = reach(LINE_3, ["x"])
    assert out["reached"] is True
    assert out["body"].strip() == "return 3 * x + 1"
    assert out["errors"] == []


def test_a_compiled_body_is_reported_without_a_redundant_plus_zero():
    fit = determine([(1, 2.0), (2, 4.0), (3, 6.0)])["fits"][0]
    assert compile_body(fit).strip() == "return 2 * x"


def test_a_squared_family_compiles_to_a_power_body():
    fit = determine([(1, 1.0), (2, 4.0), (3, 9.0), (4, 16.0)])["fits"][0]
    assert fit["class"] == "power"
    assert compile_body(fit).strip() == "return x ** 2"


def test_two_inputs_are_refused_rather_than_silently_ignored():
    """Fitting the first parameter and dropping the second would be an invented result."""
    out = reach([((1, 2), 3.0), ((3, 4), 7.0)], ["x", "y"])
    assert out["reached"] is False
    assert "one input at a time" in out["why"]


def test_a_power_with_exponent_one_is_not_counted_as_a_second_explanation():
    """`a*x**1` IS `a*x + 0`. Counting it twice would recreate the defect this arc exists to fix."""
    verdict = determine([(1, 2.0), (2, 4.0), (3, 6.0)])
    assert verdict["explanations"] == 1
    power = Power.fit([(1, 2.0), (2, 4.0), (3, 6.0)])
    assert power["subsumed_by"] == "affine"


# --------------------------------------------------------------------------------------------
# The search's own honesty about its budget
# --------------------------------------------------------------------------------------------

def test_a_budget_failure_is_not_reported_as_a_fact_about_the_world():
    """`2x + 1` is in the grammar; a 900-entry bank cannot reach it, and the first version of this
    code said "no body in the grammar reproduces the examples" -- a false statement produced by a
    constant."""
    line = [((0,), 1.0), ((1,), 3.0), ((2,), 5.0)]
    truncated = demand_evidence(["x"], line)
    assert truncated["status"] == SEARCH_TRUNCATED
    assert "budget" in truncated["why"].lower()

    # and with a bank large enough, the body is genuinely there
    assert reach(line, ["x"])["body"].strip() == "return 2 * x + 1"


def test_completeness_is_decided_from_state_the_search_already_keeps():
    line = [((0,), 1.0), ((1,), 3.0), ((2,), 5.0)]
    synthesize_python_function_body(["x"], line, max_weight=3,
                                    collect_admissible=True, max_bank_size=900)
    assert last_search_coverage()["complete"] is False

    synthesize_python_function_body(["x"], line, max_weight=3,
                                    collect_admissible=True, max_bank_size=50000)
    assert last_search_coverage()["complete"] is True


def test_a_grouping_over_a_truncated_enumeration_says_so():
    """A grouping is a claim about all admissible bodies. Over a truncated sweep it is a claim
    about the ones that fit in the bank, which is a different and weaker statement."""
    state = demand_evidence(["x"], [((1,), 2.0), ((2,), 4.0), ((3,), 6.0)])
    assert "TRUNCATED" in state["grouping_basis"] or state["coverage"]["complete"] is True
