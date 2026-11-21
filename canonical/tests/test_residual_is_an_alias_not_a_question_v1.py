"""Every number in the retraction must come from the executed receipt, not from a note."""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "canonical" / "tools"))


RECEIPT = (ROOT / "canonical" / "verification"
           / "RESIDUAL_IS_AN_ALIAS_NOT_A_QUESTION_20261121_V1.json")
OLD = (ROOT / "canonical" / "verification"
       / "BREADTH_BUYS_WHAT_REPETITION_CANNOT_20261201_V1.json")


def _receipt() -> dict:
    return json.loads(RECEIPT.read_text())


def test_every_declared_criterion_met() -> None:
    verdict = _receipt()["verdict"]
    assert set(verdict) == {
        "C1_alias_removed_without_a_question", "C2_every_alias_observed_identical",
        "C3_fourth_machine_respects_the_premise", "C4_behaviours_are_unchanged", "C5_zero"}
    assert all(row["MET"] is True for row in verdict.values())


def test_the_prior_residual_is_retracted_from_two_statements_to_one() -> None:
    receipt = _receipt()
    old = json.loads(OLD.read_text())
    prior = old["verdict"]["B3_the_residual_survives_every_machine"]["texts"]
    assert receipt["prior_residual"]["texts"] == prior
    assert receipt["prior_residual"]["minimal_statements"] == 2
    assert receipt["residual"]["goal_minimal_before"] == 2
    assert receipt["residual"]["goal_minimal_after"] == 1
    assert receipt["residual"]["goal_texts_after"] == ["created_once[probe_new_content]"]
    assert receipt["verdict"]["C1_alias_removed_without_a_question"]["questions_of_the_user"] == 0


def test_the_alias_was_observed_identical_on_every_executed_run() -> None:
    receipt = _receipt()
    assert receipt["verdict"]["C2_every_alias_observed_identical"]["verified"] == 3
    assert all(row["observed_identical"] for row in receipt["aliases"])
    assert sum(receipt["runs"].values()) == 555
    assert receipt["residual"]["behaviours"] == 622


def test_the_fourth_machine_separates_the_pair_because_its_initial_count_is_one() -> None:
    fourth = _receipt()["fourth_machine"]
    assert fourth["name"] == "PRELOADED"
    assert fourth["initial_counts"]["probe_new_content"] == 1
    masks = fourth["probe_new_masks"]
    assert masks["created_once[probe_new_content]"] != (
        masks["monotone[probe_new_content]"] & masks["final:count[probe_new_content]==1"])
    assert fourth["aliases_proposed"] == fourth["aliases_observed_identical"] == 3


def test_the_quotient_is_measured_not_declared() -> None:
    receipt = _receipt()
    assert receipt["authority"] == "NONE__PRODUCER_RUN_SANDBOX"
    assert receipt["criteria_were_declared_before_the_receipt_run"] is True
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0
    assert receipt["cost"]["seconds"] < 400
    assert receipt["residual"]["behaviours_still_ambiguous_after"] == 265
    assert receipt["residual"]["ambiguous_with_concatenated_reader_literals"] == 175
    assert receipt["residual"]["ambiguous_with_clean_literals"] == 90
    assert any("created_once[probe_seed_content]" in statement
               for statement in receipt["residual"]["example_clean_ambiguous_texts"])
    assert "retracted_claim" in receipt and "question of the user" in receipt["retracted_claim"]
    assert "unit increments" in receipt["limits"][0]
