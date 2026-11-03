"""Refusing to commit when the evidence cannot distinguish.

The defect: the synthesizer returned the first expression whose outputs matched, and deduped its
candidate bank by output signature over the same inputs -- so it could not represent "these two both
fit and are not the same". Measured: twelve distinct admissible bodies for the three teaching
examples of `2x`.

The test that matters most is `test_enumeration_is_not_vacuous`. The first version of the enumeration
swept `max_weight` and called the synthesizer once per weight, and reported exactly one admissible
body every single time -- because a match returns from inside the search. It could not have seen a
second explanation, so it declared every problem DETERMINED. Same class of error as the substitution
counterfactual two rounds earlier.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime.evidence_demand_v1 import (  # noqa: E402
    DETERMINED,
    PROVISIONAL,
    UNRESOLVED,
    cost,
    demand_evidence,
    enumerate_admissible,
    what_would_settle_it,
)
from canonical.runtime.swe_observational_program_synthesizer_v1 import (  # noqa: E402
    last_admissible_bodies,
    synthesize_python_function_body,
)

DOUBLE_X = [((1,), 2.0), ((2,), 4.0), ((3,), 6.0)]


def test_enumeration_is_not_vacuous():
    """The core fix: more than one explanation must be observable at all."""
    bodies = enumerate_admissible(["x"], DOUBLE_X)
    assert len(bodies) > 1, (
        "a single admissible body means the enumeration cannot see multiplicity, which is exactly "
        "the defect this module exists to fix")


def test_default_synthesis_is_unchanged():
    """Adding the collector must not alter what ordinary callers get."""
    default = synthesize_python_function_body(["x"], DOUBLE_X, max_weight=4)
    assert default is not None
    assert default.startswith("return ")

    collecting = synthesize_python_function_body(["x"], DOUBLE_X, max_weight=4,
                                                 collect_admissible=True)
    assert collecting is None, "collecting mode must not also return a single answer"
    assert last_admissible_bodies(), "collecting mode must have collected something"


def test_three_points_leave_the_choice_open():
    report = demand_evidence(["x"], DOUBLE_X)
    assert report["status"] == PROVISIONAL
    assert report["admissible_count"] > 1
    assert report["chosen"] is not None


def test_the_report_says_the_choice_was_a_preference():
    """Simplical choice must never be presented as forced by data."""
    report = demand_evidence(["x"], DOUBLE_X)
    assert "PREFERENCE" in report["why"]
    assert "choice_margin" in report
    assert "cost_preference_is_defeasible" in report


def test_simplicity_does_not_resolve_the_ambiguity():
    """Measured: eleven of twelve admissible bodies tie on cost.

    A tie is the honest outcome and must be reported as one, not hidden by a sort order.
    """
    report = demand_evidence(["x"], DOUBLE_X)
    costs = sorted(report["costs"])
    assert costs[0] == costs[1], "if costs differed, simplicity would be doing work; it is not"
    assert "next cheapest 6" in report["choice_margin"]


def test_asking_shrinks_the_set():
    """The real form of demanding evidence: compute where they disagree and ask."""
    report = demand_evidence(["x"], DOUBLE_X)
    questions = what_would_settle_it(["x"], report["admissible"])
    assert questions["queries"], "there must be an input that separates them"
    probe = questions["queries"][0]["args"]

    extended = DOUBLE_X + [((probe[0],), 2.0 * probe[0])]
    after = demand_evidence(["x"], extended)
    assert after["admissible_count"] < report["admissible_count"]


def test_loop_terminates_and_reports_residual_ambiguity():
    """It must not ask forever, and it must not claim to be done when bodies still differ."""
    examples = list(DOUBLE_X)
    for _ in range(5):
        state = demand_evidence(["x"], examples)
        if state["status"] != PROVISIONAL:
            break
        asked = what_would_settle_it(["x"], state["admissible"])
        if not asked["queries"]:
            assert "residual" in asked, "no question left must be explained, not hidden"
            break
        probe = asked["queries"][0]["args"]
        examples.append(((probe[0],), 2.0 * probe[0]))
    else:
        raise AssertionError("the interrogation loop did not terminate within five questions")


def test_unresolved_when_nothing_fits():
    report = demand_evidence(["x"], [((1,), 999999.0), ((2,), -123456.0)])
    assert report["status"] in (UNRESOLVED, PROVISIONAL)
    if report["status"] == UNRESOLVED:
        assert report["chosen"] is None


def test_trivia_is_not_counted_as_complexity():
    """`(x / 1) + x` and `x + (x / 1)` are the same six graph nodes."""
    assert cost("return ((x / 1) + x)") == cost("return (x + (x / 1))")


def test_no_authority_claimed():
    """Authority stays NONE, and a DETERMINED status must not be reported as truth.

    (An earlier version of this test ended with `or True`, which the repo guard correctly flagged
    as a tautology. A test line that cannot fail is worse than no test line.)
    """
    report = demand_evidence(["x"], DOUBLE_X)
    assert report["authority"] == "NONE"
    if report["status"] == DETERMINED:
        assert "not the same as the body being TRUE" in report["why"]
