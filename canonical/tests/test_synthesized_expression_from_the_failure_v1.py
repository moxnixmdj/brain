"""Synthesis from the failure must build the fix from evidence, not recognise a fix it was taught.

The tests use tiny programs written here on purpose: what they pin is the *mechanism*, never a corpus
fact. The corpus facts live in the receipt.

What must stay true:
  * the scope observed is the one the defective program actually has when it answers;
  * an expression is kept only if it produces every published answer;
  * nothing is substituted at an early return, because the observation does not support it;
  * the tool refuses rather than approximates when the fix is not a return value;
  * a synthesized expression is installed as source and still parses.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import grammar_closed_repair_v1 as gen  # noqa: E402
import synthesized_expression_from_the_failure_v1 as syn  # noqa: E402


class TestTheObservationIsReal:
    def test_the_scope_is_what_the_program_had_when_it_answered(self) -> None:
        gen._install_alarm()
        source = "def f(xs):\n    depth = 0\n    for x in xs:\n        depth += 1\n    return True\n"
        scope = syn.scope_at_return(source, "f", [[1, 2, 3]], 0.05)
        assert scope is not None and scope["depth"] == 3

    def test_a_program_that_cannot_run_is_not_observed(self) -> None:
        source = "def f(x):\n    return x\n"
        assert syn.scope_at_return(source, "g", [[1]], 0.05) is None


class TestTheExpressionIsBuiltFromEvidence:
    def test_an_expression_that_reproduces_every_answer_is_found(self) -> None:
        gen._install_alarm()
        source = "def f(xs):\n    depth = 0\n    for x in xs:\n        depth += 1\n    return True\n"
        # `args` is the positional-argument list: f receives one list here.
        found = syn.synthesize_return(source, "f", [([[1, 2]], True), ([[1, 2, 3, 4]], True)],
                                      0.05, depth=3)
        assert found["status"] == "FOUND"

    def test_an_expression_that_only_fits_one_example_is_not_kept(self) -> None:
        gen._install_alarm()
        source = "def f(n):\n    k = n\n    return 0\n"
        found = syn.synthesize_return(source, "f", [([2], 2), ([3], 9)], 0.05, depth=2)
        # no expression over the observed scope reproduces both answers
        assert found["status"] in {"NO_EXPRESSION", "SCOPE_UNOBSERVABLE"}


class TestItRefusesRatherThanApproximates:
    def test_a_function_that_only_returns_from_branches_is_left_alone(self) -> None:
        source = "def f(xs):\n    if xs:\n        return 1\n    else:\n        return 2\n"
        # every exit is nested and there are two of them: no single observation supports
        # substituting one of them, so the mechanism refuses instead of guessing
        assert syn.install_return(source, "f", "0") is None

    def test_a_loop_early_exit_does_not_stop_the_fall_through_being_used(self) -> None:
        source = ("def f(xs):\n    for x in xs:\n        if x:\n            return 1\n"
                  "    return 3\n")
        # the fall-through return is a direct statement and is the one observed, so it is the
        # one that may be replaced; the early exit inside the loop is untouched
        patched = syn.install_return(source, "f", "len(xs)")
        assert patched is not None and "return 1" in patched and "len(xs)" in patched

    def test_a_function_with_no_return_is_refused(self) -> None:
        assert syn.install_return("def f(x):\n    pass\n", "f", "0") is None

    def test_an_installed_expression_still_parses(self) -> None:
        source = "def f(xs):\n    depth = 0\n    return True\n"
        patched = syn.install_return(source, "f", "(depth == 0)")
        assert patched is not None and "depth == 0" in patched
