"""Tests for the refusal round.

They do not trust the receipt: they rebuild the world, drive the real binaries, and pin the three things the round
rests on -- that a success cannot separate the behaviours it is consistent with, that a refusal can (and does so
through a message that is a function of the violated fact), and that the schedule is cheap.

The falsifiable edge: if a refusal stopped naming the fact it dropped, or if a success ever identified the
precondition, these tests fail.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parents[1]))

import the_refusal_is_the_other_half_v1 as R  # noqa: E402

RECEIPT = (pathlib.Path(__file__).resolve().parents[1] / "verification"
           / "THE_REFUSAL_IS_THE_OTHER_HALF_20261119_V1.json")


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    root = tmp_path_factory.mktemp("refusal")
    template = R.build_template(root)
    rows = {action.name: R.measure_action(template, root, action) for action in R.ACTIONS}
    spaces = {name: R.version_space(row) for name, row in rows.items()}
    return {"root": root, "template": template, "rows": rows, "spaces": spaces}


# ----------------------------------------------------------------------------------------------------------
# the world is real
# ----------------------------------------------------------------------------------------------------------

def test_every_action_applies_in_the_state_it_is_supposed_to(world):
    failed = [name for name, row in world["rows"].items() if not row["base"]["applied"]]
    assert failed == []


def test_every_violation_is_refused_and_changes_exactly_the_coordinate_it_dropped(world):
    for name, row in world["rows"].items():
        assert row["every_violation_was_refused"], name
        assert row["each_violation_changed_exactly_one_fact"], name
        assert row["the_changed_fact_is_the_dropped_coordinate"], name


# ----------------------------------------------------------------------------------------------------------
# the two halves
# ----------------------------------------------------------------------------------------------------------

def test_one_success_cannot_separate_the_behaviours_it_is_consistent_with(world):
    for name, space in world["spaces"].items():
        assert space["distinct_behaviours_after_the_one_success"] > 1, name


def test_one_refusal_per_coordinate_identifies_the_precondition(world):
    for name, space in world["spaces"].items():
        assert space["identified"], name
        assert space["the_survivor_is_the_true_precondition"], name
        assert space["distinct_behaviours_after_refusals"] == 1


def test_the_message_is_a_function_of_the_violated_coordinate(world):
    for name, row in world["rows"].items():
        assert row["injective"], name
        assert row["invariant_under_distractor"], name


def test_two_coordinates_of_one_action_are_told_apart_by_the_message_alone(world):
    mkdir = world["rows"]["mkdir_nested"]["messages"]
    assert mkdir["absent"] != mkdir["parent"]
    assert "File exists" in mkdir["absent"]
    assert "No such file" in mkdir["parent"]


def test_normalisation_does_not_erase_the_distinguishing_words(world):
    """The rewrite removes paths; it must not remove the fact's name. A rewrite that erased both would be a fake."""
    rmdir = world["rows"]["rmdir_empty"]["messages"]
    assert "Directory not empty" in rmdir["empty"]
    assert "No such file" in rmdir["exists"]
    assert "<state>" in rmdir["exists"] or "files/dir" in rmdir["exists"]


# ----------------------------------------------------------------------------------------------------------
# the price, and the declared check that is narrower than its fact
# ----------------------------------------------------------------------------------------------------------

def test_the_refusal_is_free_up_to_the_programs_own_bookkeeping(world):
    touched = {name: row["refusals_that_changed_something"] for name, row in world["rows"].items()
               if row["refusals_that_changed_something"]}
    objects = [path for paths in touched.values() for group in paths.values() for path in group
               if path.split("/")[-1] not in {"a.txt.rej", "a.txt.orig", "README.txt.orig"}]
    assert objects == []
    assert 0 < len(touched) < len(world["rows"]), "the exception must exist and must be a minority"


def test_the_declared_check_is_measurably_narrower_than_the_fact_it_serves(world):
    finding = R.check_narrower_than_the_fact(world["root"])
    assert finding["MEASURED"] is True
    assert finding["tar_tzf_exit"] == 0


def test_the_whole_schedule_costs_about_five_executions_per_action(world):
    executions = sum(1 + row["refusals"] for row in world["rows"].values())
    assert executions == 48
    assert len(world["rows"]) == 10


# ----------------------------------------------------------------------------------------------------------
# the committed receipt
# ----------------------------------------------------------------------------------------------------------

def test_the_committed_receipt_meets_every_claim():
    receipt = json.loads(RECEIPT.read_text())
    verdict = receipt["verdict"]
    assert [key for key, value in verdict.items() if not value["MET"]] == []
    k1 = verdict["K1_one_success_is_a_point_not_a_boundary"]
    assert min(k1["per_action_distinct_behaviours_left"].values()) > 1
    k3 = verdict["K3_one_refusal_per_coordinate_identifies"]
    assert len(k3["identified_and_equal_to_the_true_precondition"]) == 10
    k4 = verdict["K4_the_failure_is_free"]
    assert k4["objects_changed_by_any_refusal"] == []
    assert k4["refusals"] == 38 and k4["refusals_confined_to_bookkeeping"] == 2
    k5 = verdict["K5_the_schedule_price"]
    assert k5["actions_identified_here"] == 10 and k5["actions_the_previous_round_identified"] == 0
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0


def test_the_producer_has_no_model_no_parameters_no_network():
    source = pathlib.Path(R.__file__).read_text(encoding="utf-8")
    for forbidden in ("import requests", "import urllib", "import socket", "import torch",
                      "import openai", "from openai", "http://", "https://"):
        assert forbidden not in source, forbidden
