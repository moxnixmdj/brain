"""Problem 2, pinned: the ladder, the numbers, and the four mistakes this instrument made.

The owner's framing was "exact recall is solved, generalisation is not". These tests pin the
measurement that makes that framing actionable -- `where` it generalises, and `what` turns a wrong
guess into a usable skill -- and they pin the mistakes the measuring tool made while finding out,
because in this repository the instrument has been wrong more often than the learner.

What is asserted here, in order of how load-bearing it is:

1. **A check changes the outcome.** The same one demonstration repairs two sibling modules and
   BREAKS a third whose `<=` was required -- and with the third module's own tests as the gate,
   the edit is refused and the file is left correct. This is the whole answer to "why can't we just
   let it experience it once": where a check exists the wrong generalisation is caught, where it
   does not the wrong generalisation is kept.
2. **Two showings differ from one, in the recorded corpus** -- 0.529 of the developers' work from
   one, 0.891 from two, on the same 132 pairs.
3. **The widest rung is worse than the shipped learner**: 0.455 precision against 1.000. "Widen
   the rule" is not the lever, and the ladder is not a dial you turn up.
4. **The check cannot run on real migrated files here**, and the tool says so by name rather than
   silently reporting zero: 6 tasks with no test module that imports the file, 6 whose tests need
   a dependency that is not installed. A check that cannot be imported is not a check.

Zero model calls, no network (the corpus numbers are read from committed records), $0.
Authority: NONE.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import edit_kind_learning_v1 as ladder  # noqa: E402
from canonical.tools import generalization_rung_gradient_v1 as measure  # noqa: E402


# ---------------------------------------------------------------- 1. the check is the difference


def test_the_check_machinery_discriminates_when_a_check_exists():
    """Four demands. If any fails, every "the check was unavailable" below is worthless."""
    control = measure.positive_control()
    assert control["available"] is True, control
    assert control["accepts_the_project_as_it_is"] is True
    assert control["accepts_the_correct_edit"] is True
    assert control["rejects_a_wrong_edit_that_still_compiles"] is True
    assert control["rejects_a_broken_file"] is True
    assert control["discriminates"] is True


def test_the_lesson_repairs_the_siblings_it_should():
    """Same defect, same shape, another module: repaired with no check needed."""
    arms = measure.oracle_makes_the_difference()["arms"]
    for path in ("pkg/limits.py", "pkg/edges.py"):
        assert arms[path]["without_a_check"]["is_the_correct_edit"] is True, path


def test_the_lesson_breaks_the_file_whose_operator_was_required():
    """THE LIMIT, pinned on purpose. `<=` here is not a defect and the lesson cannot tell."""
    arms = measure.oracle_makes_the_difference()["arms"]
    arm = arms["pkg/inclusive.py"]
    assert arm["without_a_check"]["edited"] is True
    assert arm["without_a_check"]["is_the_correct_edit"] is False, (
        "if this ever passes, a semantic guard has appeared somewhere: name it and rewrite this test"
    )


def test_a_check_turns_that_break_into_a_refusal():
    """THE ANSWER: with the file's own tests as the gate, the wrong edit is not made at all."""
    arms = measure.oracle_makes_the_difference()["arms"]
    arm = arms["pkg/inclusive.py"]
    assert arm["check_available"] is True
    assert arm["with_a_check"]["is_the_correct_edit"] is True
    assert arm["with_a_check"]["edited"] is False, "the file is correct because nothing was changed"


def test_a_weak_check_is_weaker_than_it_looks():
    """A test that pins only one side passes `return x > hi`. The gate is only as strong as it is."""
    arms = measure.oracle_makes_the_difference()["arms"]
    assert arms["pkg/limits.py"]["check_strength"]["passes_a_wrong_edit_that_satisfies_it"] == "return x > hi"
    assert arms["pkg/edges.py"]["check_strength"]["passes_a_wrong_edit_that_satisfies_it"] is None


def test_every_wrong_correction_was_actually_tried():
    """`nothing got through` must not mean `nothing was tried`."""
    arms = measure.oracle_makes_the_difference()["arms"]
    for path, arm in arms.items():
        assert arm["check_strength"]["wrong_edits_tried"] == 3, path


def test_the_demonstration_settles_the_boundary_it_was_tested_on():
    """Why three plausible corrections all fail on THIS file, and none of it is about generality.

    `pkg/window.py` pins both of its own boundaries: the edge is out and zero is in. `x > hi`,
    `x < 0` and `False` each keep the edge-out half and each drop a boundary this file's own test
    states. A correction that carries half a file's behaviour is under-determined on that file,
    and no widening of the rule can recover the half that was never carried.
    """
    import sys

    sys.path.insert(0, str(ROOT / "canonical/tools"))
    import generalization_rung_gradient_v1 as tool

    sys.path.insert(0, str(ROOT / "canonical/runtime"))
    import edit_kind_learning_v1 as ladder

    after = tool.ORACLE_AFTER["pkg/window.py"]
    demos = tool._learned([(tool.ORACLE_PROJECT["pkg/window.py"], after)])
    shown = tool._apply_everywhere(demos, tool.ORACLE_PROJECT["pkg/window.py"])
    assert shown is not None
    # On the file it was shown on, the lesson is exact: it reproduces what was demonstrated ...
    assert ladder.same_program(shown, after)
    # ... and each half-correction is a different program from the one demonstrated.
    for half in ("return x > hi", "return x < 0", "return False"):
        assert not ladder.same_program(after.replace("return x < hi", half), after), half


# ---------------------------------------------------------------- 2. the recorded corpus


@pytest.fixture(scope="module")
def recorded_arms():
    """The arms as the corpus run reported them, from the committed record."""
    path = ROOT / "canonical/verification/GENERALIZATION_RUNG_GRADIENT_20261112_V1.json"
    if not path.is_file():
        pytest.skip("the corpus record is not on this branch")
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def test_one_demonstration_is_right_and_covers_about_half(recorded_arms):
    exact = recorded_arms["summary"]["exact"]
    assert exact["right"] == 384 and exact["wrong"] == 0
    assert exact["precision"] == 1.0
    assert 0.50 <= exact["share_of_the_work"] <= 0.56


def test_a_second_showing_covers_almost_all_of_it(recorded_arms):
    two = recorded_arms["summary"]["two_showings"]
    assert two["right"] == 647 and two["wrong"] == 0
    assert two["share_of_the_work"] > recorded_arms["summary"]["exact"]["share_of_the_work"]


def test_the_widest_rung_is_worse_not_better(recorded_arms):
    """"Widen the rule" loses precision and buys almost nothing. The ladder is not a dial."""
    widest = recorded_arms["summary"]["any_rung"]
    exact = recorded_arms["summary"]["exact"]
    assert widest["precision"] < exact["precision"]
    assert widest["wrong"] > 0, "the wider rungs fire where they should not; that is visible here"


def test_the_check_could_not_run_on_any_real_file_and_that_is_reported(recorded_arms):
    """Zero, by name, with the reason counted -- not silently."""
    assert recorded_arms["summary"]["any_rung_check"]["edited"] == 0
    reasons = recorded_arms["check_reasons"]
    assert reasons.get("CHECK_NO_TEST_MODULE", 0) > 0
    assert reasons.get("CHECK_DEPENDENCY_MISSING", 0) > 0
    assert recorded_arms["positive_control"]["discriminates"] is True


# ---------------------------------------------------------------- 3. the instrument's own bugs


def test_a_candidate_is_accepted_when_the_tests_pass_never_when_they_fail():
    """The inversion this tool had: in repair mode it accepted files whose tests still FAILED.

    The bug was `ok = (returncode == 0) == (expect == "PASS")`, which rewards a failing run when the
    file was found broken. `expect` describes the file as it was found; it must not flip what
    "accepted" means.
    """
    check = measure.Check("tests", measure.ORACLE_PROJECT, "pkg/limits.py", expect="FAIL")
    assert check.available is True
    assert check.accepts("pkg/limits.py", measure.ORACLE_AFTER["pkg/limits.py"]) is True
    assert check.accepts("pkg/limits.py", measure.ORACLE_PROJECT["pkg/limits.py"]) is False, (
        "the unrepaired file fails its own tests and must not be accepted"
    )
    check.close()


def test_the_check_restores_the_original_and_not_the_candidate():
    """After a run the project must be back as it was, or every later candidate is judged against
    an earlier guess. The first draft restored the candidate."""
    check = measure.Check("tests", dict(measure.ORACLE_PROJECT), "pkg/limits.py", expect="FAIL")
    assert check.available is True
    original = measure.ORACLE_PROJECT["pkg/limits.py"]
    check.accepts("pkg/limits.py", measure.ORACLE_AFTER["pkg/limits.py"])
    assert (check._dir / "pkg/limits.py").read_text() == original
    check.close()


def test_a_test_module_that_merely_mentions_the_name_is_not_a_check():
    """"`stem` appears in the text" picked a helper as the check for a test-package file. The
    criterion is an import, not a mention."""
    project = {
        "pkg/__init__.py": "",
        "pkg/thing.py": "def f():\n    return 1\n",
        "tests/__init__.py": "",
        "tests/test_helper.py": "x = 'pkg.thing'  # mentions it, imports nothing\n",
    }
    check = measure.Check("tests", project, "pkg/thing.py")
    assert check._test is None
    assert check.available is False
    assert check.reason == "CHECK_NO_TEST_MODULE"
    check.close()


def test_the_ladder_writes_several_rungs_from_one_demonstration():
    """The premise: one demonstration is not one rule but a ladder of them."""
    operators = ladder.operators_of(
        "def f(x, hi):\n    return x <= hi\n", "def f(x, hi):\n    return x < hi\n")
    rungs = {operator.openness for operator in operators}
    assert len(operators) >= 5
    assert "as_it_was" in rungs
    assert rungs & {"names_open", "both_open", "untouched_open"}
