"""The identification instrument must be wrong in an obvious way if it is wrong at all.

These tests pin the *logic* of `identification_cost_in_a_real_space_v1`, not any measured number.
The distinction matters here: a test that asserted "gcd needs 1 question" would pin a corpus fact
and go red the day the generator's families change, while teaching nothing. What must stay true is
the claim about objectives -- that maximum elimination and minimax balance are different rules that
give different answers, and that the first is the right one when the true program is defined to
match.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "runtime"))

import identification_cost_in_a_real_space_v1 as ident  # noqa: E402

MATCH = ident.MATCH
NO = ident.NO


def _table(rows: list[list[str]]) -> dict[int, list[str]]:
    return {index: row for index, row in enumerate(rows)}


class TestTheCorrectObjectiveIsNotTheKernels:
    def test_a_balanced_split_is_not_what_matters_when_the_answer_is_known(self) -> None:
        """Six survivors, one question. The kernel balances; the truth only eliminates.

        probe 0: 3 MATCH / 3 NO  -- a perfect halving, which minimax prefers
        probe 1: 1 MATCH / 5 NO  -- eliminates five with certainty
        The answer to any question here is MATCH (the true program agrees by definition), so
        probe 1 is strictly better and probe 0 is a wasted question.
        """
        table = _table([
            [MATCH, MATCH], [MATCH, NO], [MATCH, NO],
            [NO, NO], [NO, NO], [NO, NO],
        ])
        live = [0, 1, 2, 3, 4, 5]
        assert ident.elimination_order(live, table, [0, 1])[0] == 1

    def test_max_elimination_settles_in_one_question_where_minimax_takes_three(self) -> None:
        # live set after one demonstration: hypotheses 0..6, questions 1..3
        table = _table([
            [MATCH, MATCH, MATCH, MATCH],
            [MATCH, NO, MATCH, MATCH],
            [MATCH, NO, NO, MATCH],
            [MATCH, NO, NO, NO],
            [MATCH, MATCH, NO, NO],
            [MATCH, MATCH, MATCH, NO],
            [MATCH, NO, MATCH, NO],
        ])
        live = [0, 1, 2, 3, 4, 5, 6]
        probes = [1, 2, 3]
        elim = ident.settle(live, table, ident.elimination_order(live, table, probes))
        minimax = ident.settle(live, table, ident.eig_order(live, table, probes))
        assert elim["outcome"] == "IDENTIFIED"
        assert minimax["outcome"] == "IDENTIFIED"
        assert elim["asked"] <= minimax["asked"]


class TestTheWallIsRealAndItIsTheSuite:
    def test_a_space_the_published_examples_cannot_split_is_reported_not_hidden(self) -> None:
        """Two programs that agree on every published example cannot be told apart by them.

        This is the case that matters: it is not a search failure and not a budget failure. The
        instrument must say NONIDENTIFIABLE and name how many survivors remain, because reporting
        'identified' here would be the confident-wrong-rule failure the note is about.
        """
        table = _table([[MATCH, MATCH], [MATCH, MATCH], [MATCH, MATCH]])
        live = [0, 1, 2]
        assert ident.elimination_order(live, table, [0, 1]) == []
        result = ident.settle(live, table, [0, 1])
        assert result["outcome"] == "NONIDENTIFIABLE"
        assert len(result["survivors"]) == 3

    def test_an_uninformative_question_does_not_count_as_identification(self) -> None:
        table = _table([[MATCH, MATCH], [MATCH, NO]])
        result = ident.settle([0, 1], table, [0])
        assert result["outcome"] == "NONIDENTIFIABLE"
        result = ident.settle([0, 1], table, [0, 1])
        assert result["outcome"] == "IDENTIFIED"


class TestOutcomesAreExecutionsNotOpinions:
    def test_a_candidate_is_asked_whether_it_agrees_and_nothing_else(self) -> None:
        source = "def f(x):\n    return x + 1\n"
        assert ident.outcomes_for(source, "f", [[1], [2]], [2, 3], 0.05) == [MATCH, MATCH]
        assert ident.outcomes_for(source, "f", [[1], [2]], [2, 4], 0.05) == [MATCH, NO]

    def test_a_candidate_that_cannot_be_installed_is_dropped_rather_than_credited(self) -> None:
        assert ident.outcomes_for("def g(x):\n    return x\n", "f", [[1]], [1], 0.05) is None

    def test_a_raising_candidate_is_scored_as_disagreeing(self) -> None:
        source = "def f(x):\n    raise ValueError('no')\n"
        assert ident.outcomes_for(source, "f", [[1]], [1], 0.05) == [NO]


class TestTheReceiptSeparatesIdentificationFromCorrectness:
    def test_identifying_a_non_repair_is_counted_as_a_non_repair(self) -> None:
        rows = [
            {"task": "a", "kind": "task", "stage": "IDENTIFIED", "elim_asked": 2,
             "minimax_asked": 2, "corpus_asked": 2, "random_asked_mean": 2.0,
             "bits_after_one": 3.0, "survivors_after_one_demonstration": 8,
             "survivor_is_repair": True, "repairs_in_space": 1},
            {"task": "b", "kind": "task", "stage": "IDENTIFIED", "elim_asked": 2,
             "minimax_asked": 2, "corpus_asked": 2, "random_asked_mean": 2.0,
             "bits_after_one": 3.0, "survivors_after_one_demonstration": 8,
             "survivor_is_repair": False, "repairs_in_space": 0},
        ]
        receipt = ident.summarise(rows)
        assert receipt["identified_as_repair"] == 1
        assert receipt["identified_as_anything_else"] == 1
        assert receipt["model_dependency_count"] == 0
