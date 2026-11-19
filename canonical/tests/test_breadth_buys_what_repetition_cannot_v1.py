"""Breadth buys what repetition cannot: every number that decides the claim, pinned.

The round's substance is five counts and one correction: resolving power per environment, the goal's
minimal class as environments are added, the saturation point, the residual and its price in words, and
the retraction of the previous round's inflated 79. These tests hold all of them.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
sys.path.insert(0, str(TOOLS))

import breadth_buys_what_repetition_cannot_v1 as breadth  # noqa: E402
import the_goal_is_a_discriminator_v1 as demand  # noqa: E402

RECEIPT = (ROOT / "canonical" / "verification"
           / "BREADTH_BUYS_WHAT_REPETITION_CANNOT_20261201_V1.json")


def _receipt() -> dict:
    return json.loads(RECEIPT.read_text())


# --------------------------------------------------------------------------------------------------
# breadth: what it buys, and where it stops
# --------------------------------------------------------------------------------------------------

def test_breadth_increases_the_resolving_power_of_the_world() -> None:
    verdict = _receipt()["verdict"]["B1_breadth_increases_resolving_power"]
    assert verdict["single"] == {"TARBALL": 353, "FILESYSTEM": 129, "SQLITE": 78}
    assert verdict["union"] == 622
    assert verdict["MET"] is True


def test_the_goal_class_falls_from_four_to_two_and_stops() -> None:
    """One machine leaves four minimal statements; a second leaves two; a third removes nothing."""
    marginal = _receipt()["verdict"]["B4_breadth_saturates"]["marginal"]
    assert marginal["first_machine_goal_minimal"] == 4
    assert marginal["after_two_machines_goal_minimal"] == 2
    assert marginal["after_three_machines_goal_minimal"] == 2
    assert marginal["second_machine_removed"] == 2
    assert marginal["third_machine_removed"] == 0
    assert _receipt()["verdict"]["B2_breadth_shrinks_the_goal_class"]["MET"] is True


def test_the_residual_is_two_statements_and_one_question_of_words() -> None:
    """The whole answer to "learn it once, permanently": what is left after 555 runs."""
    verdict = _receipt()["verdict"]["B3_the_residual_survives_every_machine"]
    assert verdict["residual_statements"] == 2
    assert verdict["texts"] == [
        "created_once[probe_new_content]",
        "monotone[probe_new_content] ∧ final:count[probe_new_content]==1",
    ]
    price = _receipt()["verdict"]["B5_the_residual_is_priced_in_words"]
    assert price["questions_of_the_user"] == 1.0
    assert price["runs_that_could_pay_it"] == 0


def test_most_behaviours_are_not_pinned_by_one_statement_even_on_the_union() -> None:
    """57 % of 622 behaviours have a unique minimal statement; the rest carry a residual."""
    union = _receipt()["subsets"]["TARBALL+FILESYSTEM+SQLITE"]
    assert union["runs"] == 555
    assert union["hypotheses"] == 29890
    assert union["behaviours"] == 622
    assert union["behaviours_with_a_unique_statement"] == 354
    assert union["share_unique"] == 0.571
    assert union["mean_class"] == 2.09
    assert union["largest_class"] == 38


def test_the_previous_rounds_seventy_nine_is_retracted_with_the_arithmetic() -> None:
    """79 statements held 75 redundant conjunctions. The correction is in the receipt, not in a note."""
    correction = _receipt()["correction_to_the_previous_round"]
    assert "79 statements" in correction["what_was_reported"]
    assert "75 redundant conjunctions" in correction["what_it_was"]
    assert "minimal class is 4" in correction["what_it_was"]
    assert _receipt()["subsets"]["TARBALL"]["goal_minimal_statements"] == 4
    assert _receipt()["subsets"]["TARBALL"]["goal_statements_with_the_behaviour"] == 79


def test_every_subset_is_measured_so_no_environment_is_taken_on_faith() -> None:
    subsets = _receipt()["subsets"]
    assert len(subsets) == 7
    for key in ("TARBALL", "FILESYSTEM", "SQLITE", "TARBALL+FILESYSTEM",
                "TARBALL+SQLITE", "FILESYSTEM+SQLITE", "TARBALL+FILESYSTEM+SQLITE"):
        assert key in subsets
        assert subsets[key]["hypotheses"] == 29890
    assert _receipt()["terms"] == 244
    assert _receipt()["runs"] == {"TARBALL": 231, "FILESYSTEM": 196, "SQLITE": 128}


def test_nothing_was_answered_by_a_model() -> None:
    assert _receipt()["verdict"]["B6_zero"]["MET"] is True
    assert _receipt()["cost"]["model_calls"] == 0
    assert _receipt()["cost"]["parameters_stored"] == 0


# --------------------------------------------------------------------------------------------------
# minimality, on masks small enough to check by hand
# --------------------------------------------------------------------------------------------------

def test_a_conjunction_is_not_minimal_when_one_conjunct_already_carries_the_behaviour() -> None:
    """The exact rule the residual depends on: redundancy is behavioural, not syntactic."""
    terms = [demand.Term("a", lambda _t: True), demand.Term("b", lambda _t: True),
             demand.Term("c", lambda _t: True)]
    # four runs; a = 0b0011, b = 0b0101, c = 0b0111
    analysis = breadth.Analysis(terms, [[0b0011, 0b0101, 0b0111]], [4])
    assert analysis.by_combo[(0, 1)] == 0b0001
    assert analysis.by_combo[(0, 2)] == 0b0011
    # a pair is kept when neither conjunct alone carries the behaviour
    assert analysis.minimal(0b0001, [(0, 1)]) == [(0, 1)]
    # and dropped when one does, even though the text differs
    assert analysis.minimal(0b0011, [(0,), (0, 2)]) == [(0,)]
    assert analysis.classes()[0b0011] == [(0,), (0, 2)]


def test_the_report_excludes_the_two_trivial_behaviours_and_counts_the_class() -> None:
    terms = [demand.Term("a", lambda _t: True), demand.Term("b", lambda _t: True)]
    analysis = breadth.Analysis(terms, [[0b01, 0b10]], [2])
    report = analysis.report(0b01)
    assert report["behaviours"] == 3, "false-everywhere, a, b and their conjunction collapse to three"
    assert report["trivial_behaviours_excluded"] == 1
    assert report["goal_minimal_statements"] == 1
    assert report["goal_minimal_texts"] == ["a"]


# --------------------------------------------------------------------------------------------------
# the receipt is not stale
# --------------------------------------------------------------------------------------------------

def test_the_receipt_recomputes_to_the_same_verdicts() -> None:
    committed = _receipt()
    with tempfile.TemporaryDirectory() as where:
        fresh_path = pathlib.Path(where) / "receipt.json"
        breadth.main(["--receipt", str(fresh_path)])
        fresh = json.loads(fresh_path.read_text())
    assert fresh["verdict"] == committed["verdict"]
    assert fresh["subsets"] == committed["subsets"]
    assert fresh["correction_to_the_previous_round"] == committed["correction_to_the_previous_round"]
