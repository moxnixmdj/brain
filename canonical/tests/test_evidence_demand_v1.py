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
    assert report["explanation_count"] > 1, "several ideas, not just several spellings"
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
    # The margin now compares EXPLANATIONS, so it may be a real gap rather than a tie. Either way
    # the report must state it rather than leave it implied.
    assert "chosen cost" in report["choice_margin"]


def test_asking_removes_every_body_that_predicted_otherwise():
    """The real form of demanding evidence: compute where they disagree and ask.

    The original version of this test asserted `after_count < before_count` on the raw program
    count. MEASURED 2026-11-04, after the merge: that fails at 61 > 12 while the creature had in
    fact eliminated the competitors. The count is not a cardinality -- `admissible` holds one
    representative per behaviour class, and the search harvests constants from the incoming data, so
    a truthful answer can enlarge the enumeration.

    What asking is FOR is narrower and has to be asserted directly: no body that predicted a
    different value at the asked input may survive. A body that survives while contradicting the
    answer would be a lie in the report.
    """
    from canonical.runtime.generalization_check_v1 import _compile_body

    report = demand_evidence(["x"], DOUBLE_X)
    questions = what_would_settle_it(["x"], report["explanations"])
    assert questions["queries"], "there must be an input that separates them"
    probe = questions["queries"][0]["args"]
    answer = 2.0 * probe[0]

    wrong_before = []
    for body in report["explanations"]:
        try:
            got = _compile_body(body, ["x"])(probe[0])
        except Exception:  # noqa: BLE001
            continue          # raising is a different kind of disagreement
        if got != answer:
            wrong_before.append(body)
    assert wrong_before, "the chosen question must separate bodies that really differ"

    after = demand_evidence(["x"], DOUBLE_X + [((probe[0],), answer)])
    survivors = set(after["explanations"])
    for body in wrong_before:
        assert body not in survivors, (
            "a body that predicted %r at x=%r survived an observation of %r"
            % (_compile_body(body, ["x"])(probe[0]), probe[0], answer))


def test_the_loop_never_asks_the_same_question_twice():
    """It must not ask forever, and it must not claim to be done while bodies still differ.

    Measured 2026-11-04: the interrogation asked x = 0 ten times in a row, because the tie-break
    ordered candidates by value and the separating probe was always the same. A repeated question
    cannot carry new information -- it is a stall that looks exactly like learning.
    """
    examples = list(DOUBLE_X)
    asked_at: list[tuple] = []
    for _ in range(6):
        state = demand_evidence(["x"], examples)
        if state["status"] != PROVISIONAL:
            break
        asked = what_would_settle_it(["x"], state["explanations"],
                                     known=[a for a, _ in examples])
        if asked.get("status") == "PLATEAU" or not asked["queries"]:
            assert "residual" in asked, "no question left must be explained, not hidden"
            break
        probe = tuple(asked["queries"][0]["args"])
        assert probe not in asked_at, "asked %r twice" % (probe,)
        asked_at.append(probe)
        examples.append(((probe[0],), 2.0 * probe[0]))
    assert len(asked_at) == len(set(asked_at))


def test_single_explanation_does_not_claim_spelling_or_truth():
    """A forced ANSWER is not a forced SPELLING, and neither is truth."""
    report = demand_evidence(["x"], DOUBLE_X + [((-3.5,), -7.0)])
    if report["status"] == DETERMINED and report.get("spelling_variants"):
        assert "not the spelling" in report["why"] or "spelled differently" in report["why"]
        assert "TRUE" in report["why"]
