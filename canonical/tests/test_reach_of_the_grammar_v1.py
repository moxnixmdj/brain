"""Is the ceiling experience or reach? Pinned: the receipt. Live: the two measurements the claim rests on.

A receipt can say "18.7%". It cannot say that the number is a property of the *grammar* rather than of the
recording, and it cannot say that the classification would follow the code if the code changed. Those are the
two ways this file could be self-congratulation:

  1. the grammar -> shape classification could be a table typed in by the producer, in which case the "law" is
     a restatement of the table. It is parsed from the mutation grammar's own source, and there is a test that
     proves it: remove the family from a copy and the verdict flips.
  2. the reach number could be an artefact of the order the tasks happened to be streamed in. The quartiles
     test it: coverage must be FLAT across experience, because the claim is that experience does not buy reach.

Nothing here proposes or generates a patch, so the 2026 contamination of SWE-bench Verified (frontier models
reproducing gold patches from memory) touches nothing below.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import reach_of_the_grammar_v1 as R  # noqa: E402

RECEIPT = ROOT / "canonical" / "verification" / "REACH_OF_THE_GRAMMAR_20261116_V1.json"


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads(RECEIPT.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# the grammar, which must be read from its own code
# --------------------------------------------------------------------------- #
def test_the_grammar_is_parsed_from_the_mutation_search_and_cannot_insert_delete_or_rename():
    grammar = R.grammar_shapes()
    assert grammar["source"].endswith("python_test_guided_patch_search_v1.py")
    assert "BINOP_SWAP" in grammar["families"] and "COMPARE_SWAP" in grammar["families"]
    assert grammar["can_insert_a_node"] is False, "no family in the search adds a node that is not there"
    assert grammar["can_delete_a_node"] is False
    assert grammar["can_rename_a_name"] is False


def test_the_classification_follows_the_code_not_a_table(tmp_path):
    """The load-bearing test: if the grammar gains a family, the law's verdict must change by itself."""
    source = (ROOT / R.GRAMMAR_SOURCE).read_text(encoding="utf-8")
    assert "CALL_FUNC_SWAP" in source
    stripped = source.replace('"CALL_FUNC_SWAP"', '"X_REMOVED"')
    fake = tmp_path / "grammar.py"
    fake.write_text(stripped, encoding="utf-8")
    shapes_before = R.grammar_shapes()["shapes"]
    shapes_after = R.grammar_shapes(fake)["shapes"]
    assert "CALL_FUNC_SWAP" in shapes_before
    assert "CALL_FUNC_SWAP" not in shapes_after, "the parse must not be able to see a family the code lost"
    solver = R.load("humanevalfix")
    before = {row["bug_type"]: row["in_grammar"]
              for row in R.repair_by_membership(solver, shapes_before)["rows"]}
    after = {row["bug_type"]: row["in_grammar"]
             for row in R.repair_by_membership(solver, shapes_after)["rows"]}
    assert before["function misuse"] is True
    assert after["function misuse"] is False, "a defect type must fall out of grammar when its family goes"


# --------------------------------------------------------------------------- #
# A -- experience does not buy reach
# --------------------------------------------------------------------------- #
def test_reach_is_an_asymptote_reached_from_other_tasks_only(report):
    reach = report["reach"]
    assert reach["tasks"] == 500 and reach["pieces"] == 2178
    assert reach["asymptote_pieces"] == 407
    assert 0.15 < reach["coverage_with_all_other_tasks_seen"] < 0.20
    assert reach["coverage_while_streaming"] <= reach["coverage_with_all_other_tasks_seen"]


def test_the_recomputation_agrees_with_the_recording_that_made_it(report):
    """An independent count of the same thing. If these diverged the asymptote would be an assumption."""
    check = report["grammar_membership_predicts_repair"]["recomputation_vs_recording"]
    assert check["recording_made_by_another_task"] == 437
    assert check["difference"] == -30, "leave-one-out can only lose same-task operators, and it loses 30"
    assert abs(check["difference"]) < 50


def test_coverage_does_not_grow_with_experience(report):
    """The claim, as a property: a quarter of the corpus of experience is worth as much as none."""
    quartiles = [q["coverage"] for q in report["reach"]["by_experience_quartile"]]
    assert len(quartiles) == 4
    assert max(quartiles) - min(quartiles) < 0.05, \
        "coverage must be flat across experience; growth here would refute the law"
    assert quartiles[-1] < 0.20, "and flat at the level the asymptote predicts, not flat and high"


def test_three_quarters_of_real_fix_pieces_are_rebuilt_by_nothing_any_other_task_taught(report):
    kinds = report["real_fixes"]
    assert kinds["pieces"] == 2178
    assert kinds["provenance"] == {"M": 437, "L": 103, "N": 1638}
    assert 0.75 <= kinds["never_seen_share"] < 0.76
    # the largest expressible real edit is a structural removal, which the grammar cannot name
    assert kinds["operator_kinds"]["delete"] == 348
    assert kinds["operator_kinds"]["insert"] == 16


# --------------------------------------------------------------------------- #
# B -- the same wall from the other side, on real bugs with real outcomes
# --------------------------------------------------------------------------- #
def test_grammar_membership_separates_repair_rates_perfectly(report):
    rows = report["grammar_membership_predicts_repair"]
    inside = [r["repair_rate"] for r in rows["rows"] if r["in_grammar"]]
    outside = [r["repair_rate"] for r in rows["rows"] if not r["in_grammar"]]
    assert inside and outside
    assert min(inside) > max(outside), "no in-grammar type may repair worse than an out-of-grammar type"
    assert rows["every_in_grammar_type_beats_every_out_type"] is True
    assert rows["anomalies_of_the_law"] == [], "a law with an unexplained exception would need stating as one"
    assert rows["in_grammar"]["repair_rate"] == pytest.approx(0.74, abs=0.005)
    assert rows["out_of_grammar"]["repair_rate"] == pytest.approx(0.32, abs=0.005)
    assert rows["separation"] == pytest.approx(0.42, abs=0.01)


def test_the_counts_come_from_the_recorded_humanevalfix_run(report):
    source = R.load("humanevalfix")["summary"]["by_bug_type"]
    rows = {r["bug_type"]: r for r in report["grammar_membership_predicts_repair"]["rows"]}
    for bug_type, counts in source.items():
        assert rows[bug_type]["bugs"] == counts["bugs"]
        assert rows[bug_type]["repaired"] == counts["repaired"]
    assert sum(r["bugs"] for r in rows.values()) == 100


# --------------------------------------------------------------------------- #
# the composition
# --------------------------------------------------------------------------- #
def test_a_new_environment_is_a_change_of_currency_not_a_free_lunch(report):
    env = report["per_environment_learning"]
    assert env["machines"] == 4
    assert env["adaptation_trials"] == 29
    assert env["crossover_requests"] == pytest.approx(25.78, abs=0.01)
    assert env["crossover_requests"] > 1, "a first request in a new environment is always worse, by measurement"


def test_the_answer_states_what_is_true_and_what_is_false(report):
    answers = report["answers"]
    assert answers["is_one_experience_per_action_enough_to_solve_computer_use"] == "NO"
    assert answers["the_single_bottleneck"].startswith("REACH")
    assert answers["buyable_capability"]["the_gap_that_must_be_bought"] == pytest.approx(0.42, abs=0.01)
    assert len(answers["measured_why"]) >= 5
    assert any("asymptote" in line for line in answers["measured_why"])
    assert any("experience" in line for line in answers["what_is_false"])


def test_the_receipt_is_reproducible_and_model_free(report):
    assert report["schema"] == R.SCHEMA
    assert report["authority"] == "NONE__PRODUCER_RUN_RECOMPOSITION_OF_PUBLISHED_RECEIPTS"
    assert report["model_calls"] == 0 and report["network_calls"] == 0
    again = R.measure()
    assert again["reach"] == report["reach"]
    assert again["grammar"] == report["grammar"]
    assert again["grammar_membership_predicts_repair"] == report["grammar_membership_predicts_repair"]
    assert again["answers"] == report["answers"]
