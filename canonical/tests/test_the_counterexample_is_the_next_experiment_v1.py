"""The round that retracted last round's headline: collisions are not errors.

These tests pin four things that cannot be re-derived cheaply: the conflation counts and the harmful
fraction in them; the failure of both computable question orderings; the one-question repair; and the
verdict-exact transfer of the three-cell table to a depth it was never measured on. Nothing here
re-checks what an earlier round proved.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "canonical" / "tools"
sys.path.insert(0, str(TOOLS))

import the_counterexample_is_the_next_experiment_v1 as cegar  # noqa: E402

RECEIPT = (ROOT / "canonical" / "verification"
           / "THE_COUNTEREXAMPLE_IS_THE_NEXT_EXPERIMENT_20261129_V1.json")


def _receipt() -> dict:
    return json.loads(RECEIPT.read_text())


# --------------------------------------------------------------------------------------------------
# what the round claims
# --------------------------------------------------------------------------------------------------

def test_a_shallow_statistic_is_confused_by_deeper_runs_and_sometimes_harmfully() -> None:
    """Every machine conflates; only one has a conflation that changes a verdict, and that is the point."""
    conflations = _receipt()["verdict"]["C1_the_statistic_confuses_deeper_runs"][
        "conflated_pairs_at_depth3"]
    assert conflations == {"FILESYSTEM": 675, "TARBALL": 321}
    assert _receipt()["verdict"]["C1_the_statistic_confuses_deeper_runs"]["SQLITE"] == 337
    harmful = _receipt()["verdict"]["C2_some_confusions_are_harmful"]["harmful_pairs_at_depth3"]
    assert harmful["FILESYSTEM"] == 0, "a conflation with no verdict behind it is not an error"
    assert harmful["TARBALL"] == 10
    assert (_receipt()["rows"]["TARBALL"]["table_from_depth2_on_depth3"]["false_accepts"] == 2)


def test_the_repair_was_inside_the_family_and_one_generator_away() -> None:
    """So the loop's failure cannot be blamed on the vocabulary: the fix was on the shelf."""
    repair = _receipt()["rows"]["TARBALL"]["expressibility_at_depth3"]
    assert repair["sufficient_statistics_at_depth"] == 779
    assert repair["coarsest"] == ["holders_ever[probe_new_content]",
                                 "decrements[probe_new_content]"]
    assert repair["extends_the_shallow_winner"] is True
    assert repair["added_generators"] == ["decrements[probe_new_content]"]
    assert repair["cells"] == 3


def test_both_computable_question_orderings_spend_the_budget_on_harmless_pairs() -> None:
    """The declared C3 was met only by the control policy; the free-running loops learned nothing."""
    free = _receipt()["verdict"]["C3_one_question_per_counterexample_is_enough"][
        "free_running_orderings"]
    for policy in ("cheapest_refinement", "no_signal"):
        report = free[policy]["TARBALL"]
        assert report["questions"] == 6
        assert report["counterexamples_found"] == 0
        assert report["exact_at_depth_after"] is None
    diagnostics = _receipt()["rows"]["TARBALL"]["acquisition_diagnostics"]
    assert diagnostics["rank_cheapest_refinement"]["best_harmful_rank"] == 130
    assert diagnostics["rank_no_signal"]["best_harmful_rank"] == 136
    # a random scan of the same pool would meet a harmful pair in about 29 questions, not 130
    assert diagnostics["rank_cheapest_refinement"]["random_first_harmful_expectation"] < 30
    assert diagnostics["committee_is_degenerate"]["pairs_where_every_coarsest_statistic_agrees"] == 311


def test_one_counterexample_is_enough_once_the_question_is_a_cell() -> None:
    """Two questions, one of them harmful, and the refit lands exactly on the three-cell statistic."""
    loop = _receipt()["rows"]["TARBALL"]["cegar_exhaustive"]
    assert loop["questions"] == 2
    assert loop["harmful_answers"] == 1
    assert loop["exact_at_depth_after"] == 2
    assert loop["final_statistic"] == ["holders_ever[probe_new_content]",
                                      "decrements[probe_new_content]"]
    ceiling = _receipt()["verdict"]["C3_one_question_per_counterexample_is_enough"][
        "control_policy_cell_labelling"]
    assert ceiling["TARBALL"]["ceiling_n_minus_cells"] == 30
    assert ceiling["TARBALL"]["questions_used"] == 2
    assert ceiling["FILESYSTEM"]["ceiling_n_minus_cells"] == 63


def test_the_three_cell_table_is_right_on_a_depth_it_was_never_measured_on() -> None:
    """1765 conflations of the depth-3 statistic and not one wrong verdict among 87 deeper runs."""
    depth4 = _receipt()["depth4"]
    assert depth4["runs"] == 87
    assert depth4["cells_at_depth4"] == 3
    assert depth4["conflations_of_the_depth3_statistic"] == 1765
    assert depth4["harmful_conflations"] == 0
    table = depth4["table_learned_at_depth3_on_depth4_runs"]
    assert table == {"runs": 87, "undecided": 0, "false_accepts": 0, "false_rejects": 0}
    coarser = depth4["table_of_the_one_generator_statistic_on_depth4"]
    assert coarser["undecided"] == 31, "the coarser statistic abstains where the learned one decides"


def test_nothing_in_this_round_was_answered_by_a_model() -> None:
    receipt = _receipt()
    assert receipt["verdict"]["C5_zero"]["MET"] is True
    assert receipt["model_calls"] == 0
    assert receipt["parameters_stored"] == 0
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"


# --------------------------------------------------------------------------------------------------
# the machinery, on inputs small enough to check by hand
# --------------------------------------------------------------------------------------------------

def test_differ_and_the_price_of_a_refinement_are_set_differences() -> None:
    sigs = {"a": [0, 0, 1], "b": [0, 1, 1], "c": [0, 0, 0]}
    assert cegar.differ(sigs, 0, 1) == ("b",)
    assert cegar.differ(sigs, 0, 2) == ("a", "b")
    assert cegar.differ(sigs, 0, 0) == ()
    assert cegar.cheapest_refinement(("b",), ["a"]) == 1
    assert cegar.cheapest_refinement(("a", "b"), ["a"]) == 1
    assert cegar.cheapest_refinement(("a", "b"), ["a", "b"]) == 99
    assert cegar.cheapest_refinement(("a", "b"), []) == 2


def test_a_stale_table_is_charged_with_its_false_accepts() -> None:
    projections = ["a"]
    generators = {"a": lambda trace, _: trace[0]}
    known = [(("x",),), (("y",),)]
    known_labels = [True, False]
    deeper = [(("x",), (("y",),))[0], ]
    report = cegar.stale_table(projections, generators, known, known_labels,
                               [(("x",),)], [False])
    assert report["false_accepts"] == 1, "the table says True, the run is rejected"
    assert report["undecided"] == 0
    assert cegar.stale_table(projections, generators, known, known_labels,
                             [(("z",),)], [True])["undecided"] == 1
    assert deeper  # the argument exists so the shape of a run stays visible


def test_the_guaranteed_policy_prefers_the_smallest_unfinished_cell() -> None:
    cell_of = {0: "big", 1: "big", 2: "big", 3: "small", 4: "small"}
    assert cegar.score_exhaustive((0, 1), cell_of, set())[0] == 3
    assert cegar.score_exhaustive((3, 4), cell_of, set())[0] == 2
    assert cegar.score_exhaustive((3, 4), cell_of, {(3, 4)})[0] == 0
    assert cegar.score_exhaustive((0, 1), cell_of, {(0, 1)})[0] == 1


# --------------------------------------------------------------------------------------------------
# the receipt is not stale
# --------------------------------------------------------------------------------------------------

def test_the_receipt_recomputes_to_the_same_verdicts() -> None:
    committed = _receipt()
    with tempfile.TemporaryDirectory() as where:
        fresh_path = pathlib.Path(where) / "receipt.json"
        cegar.main(["--receipt", str(fresh_path)])
        fresh = json.loads(fresh_path.read_text())
    assert fresh["verdict"] == committed["verdict"]
    assert fresh["depth4"] == committed["depth4"]
    for name in ("FILESYSTEM", "TARBALL"):
        assert (fresh["rows"][name]["conflations_at_depth3"]
                == committed["rows"][name]["conflations_at_depth3"])
