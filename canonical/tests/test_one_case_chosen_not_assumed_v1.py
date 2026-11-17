"""The screen is an instrument, and which case it asks is a design decision, not an order.

Four ways the choice could be a fiction, each pinned:

1. It could read the expected value it is supposed to be blind to when *choosing* the case. The
   choice must be a function of the space the screen will be asked about, and of nothing else.
2. It could call a case good because it admits few candidates -- admitting few is only a virtue if
   the ones it admits are right, so precision must be counted with the whole suite as truth.
3. It could report a proportion where the honest object is a count over a *complete* finite space.
   These tests use small spaces where every cell is known.
4. It could trust its own verdict. Every screen's pick is put to the corpus's pytest, and a pick that
   passes the space and fails the suite is a false accept, recorded as one.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "canonical" / "tools"))

import one_case_chosen_not_assumed_v1 as chosen  # noqa: E402


def rows(*satisfied_rows):
    return [{"satisfied": list(s), "outputs": [str(v) for v in s], "candidate": {}} for s in satisfied_rows]


class TestTheChoice:
    def test_the_case_that_separates_right_from_wrong_is_chosen(self) -> None:
        # case 0 admits three candidates and only one of them is complete; case 1 admits one, and it
        # is complete. Precision 1/3 vs 1/1 -- the second case is the better question.
        table = rows((True, True), (True, False), (True, False), (False, True))
        complete = {0, 3}
        assert chosen.best_case(table, complete) == 1

    def test_two_equally_precise_cases_break_towards_the_fewest_admissions(self) -> None:
        # both cases are perfectly precise; the one that admits one candidate is the sharper filter.
        table = rows((True, False), (False, True), (False, True), (False, True))
        assert chosen.best_case(table, {0}) == 0

    def test_a_case_that_admits_nothing_is_never_chosen(self) -> None:
        table = rows((True, False), (True, False))
        assert chosen.best_case(table, {0}) == 0  # case 1 admits nobody, so it cannot be the answer

    def test_the_first_accepting_candidate_is_the_corpus_order_not_the_best_one(self) -> None:
        table = rows((False,), (True,), (True,))
        assert chosen.first_accepting(table, 0) == 1
        assert chosen.first_complete(rows((False,), (False,), (True,))) == 2


class TestTheErrorRates:
    def test_precision_counts_what_the_case_admits_and_how_much_of_it_is_right(self) -> None:
        table = rows((True,), (True,), (False,))
        report = chosen.screen_report(table, 0, {0})
        assert report["accepted_by_the_case"] == 2
        assert report["of_them_correct"] == 1
        assert report["precision"] == 0.5
        assert report["first_accepted_is_correct"] is True

    def test_recall_loss_is_the_right_answers_the_case_can_never_see(self) -> None:
        # one of the two complete candidates fails case 0, so asking case 0 loses it forever.
        table = rows((True, False), (False, True))
        report = chosen.screen_report(table, 0, {0, 1})
        assert report["recall_loss"] == 0.5

    def test_a_case_that_admits_nobody_reports_no_precision_rather_than_zero(self) -> None:
        table = rows((False,), (False,))
        report = chosen.screen_report(table, 0, set())
        assert report["precision"] is None and report["first_accepted_is_correct"] is False


class TestTheOutcomeTable:
    def test_a_candidate_that_raises_on_a_case_is_recorded_as_failing_it_not_as_unrunnable(self) -> None:
        source = "def f(x):\n    if x == 0:\n        return 1 / 0\n    return x\n"
        seen = chosen.outcome_of(source, "f", [([0], 0), ([2], 2)], 0.05)
        assert seen is not None
        satisfied, outputs = seen
        assert satisfied == [False, True]
        assert outputs[0] == "<RAISED>"

    def test_a_candidate_that_does_not_compile_is_unrunnable(self) -> None:
        assert chosen.outcome_of("def f(x) return x", "f", [([1], 1)], 0.05) is None

    def test_the_output_of_a_candidate_is_recorded_without_reference_to_any_expected_value(self) -> None:
        seen = chosen.outcome_of("def f(x):\n    return x + 1\n", "f", [([1], 999)], 0.05)
        assert seen is not None
        assert seen[0] == [False] and seen[1] == ["2"]
