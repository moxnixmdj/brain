"""Tests for the coverage round.

The receipt's claim is unusual -- the schedule is allowed to ABSTAIN -- so the tests pin the metric itself: a
survivor set may say "undecided", and undecided must never be scored as correct. If `behaviour` ever counted an
undecided state as a hit, or if a survivor set that disagrees on a state were reported as unanimous, these fail.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS.parents[1]))

import coverage_is_the_bottleneck_not_hypotheses_v1 as C  # noqa: E402

RECEIPT = (pathlib.Path(__file__).resolve().parents[1] / "verification"
           / "COVERAGE_IS_THE_BOTTLENECK_NOT_HYPOTHESES_20261119_V1.json")


@pytest.fixture(scope="module")
def receipt():
    return C.measure()


# ----------------------------------------------------------------------------------------------------------
# the metric itself: undecided is not correct
# ----------------------------------------------------------------------------------------------------------

def test_unanimous_returns_none_when_survivors_disagree():
    one_two = C.mask_of(["a_exists", "dir_exists"])
    one = C.mask_of(["a_exists"])
    state_with_dir = C.mask_of(["a_exists", "dir_exists", "stash_present"])
    state_without_dir = C.mask_of(["a_exists", "stash_present"])
    assert C.unanimous([one], state_with_dir) is True
    assert C.unanimous([one], state_without_dir) is True, "{a_exists} holds without the directory"
    assert C.unanimous([one_two], state_without_dir) is False
    assert C.unanimous([one, one_two], state_with_dir) is True
    assert C.unanimous([one, one_two], state_without_dir) is None      # they disagree: undecided, not right


def test_a_disagreeing_set_scores_undecided_not_correct():
    one = C.mask_of(["a_exists"])
    both = C.mask_of(["a_exists", "dir_exists"])
    held = [{"mask": C.mask_of(["a_exists", "stash_present"]), "observed": {"x": True}},
            {"mask": C.mask_of(["a_exists", "dir_exists", "stash_present"]), "observed": {"x": True}}]
    result = C.behaviour([one, both], held, "x")
    assert result["undecided"] == 1
    assert result["unanimous_and_right"] == 1
    assert result["accuracy_of_the_set"] == 0.5, "an undecided state must not be counted as correct"


# ----------------------------------------------------------------------------------------------------------
# the world, and the two schedules
# ----------------------------------------------------------------------------------------------------------

def test_the_pool_is_measured_and_rich(receipt):
    assert receipt["pool"]["states"] == 36
    assert len(receipt["pool"]["facts"]) == 17
    varying = receipt["verdict"]["K3_a_success_is_the_irrelevance_evidence"]["facts_that_vary_anywhere_in_the_pool"]
    assert varying >= 12, "the pool must actually vary the facts, or the round measures nothing"


def test_one_success_plus_refusals_cannot_decide(receipt):
    k1 = receipt["verdict"]["K1_one_success_plus_refusals_leaves_a_rule_that_cannot_decide_off_sample"]
    assert k1["MET"]
    assert k1["maximum_accuracy_of_the_set"] < 1.0
    assert sum(1 for v in k1["undecided_under_A"].values() if v >= 2) >= 7


def test_every_action_has_thousands_of_survivors_from_one_success(receipt):
    rows = [r for r in receipt["rows"] if "skipped" not in r]
    assert len(rows) == 9
    assert all(r["schedule_A"]["survivors"] >= 1024 for r in rows)


def test_varied_successes_collapse_the_survivor_set(receipt):
    """Seven actions collapse below a hundred survivors; six of them are exact, and the seventh is tar_x,
    which abstains because its column is computed by a check narrower than its claim."""
    rows = [r for r in receipt["rows"] if "skipped" not in r]
    collapsed = [r for r in rows if r["schedule_B"]["survivors"] < 100]
    exact = [r for r in collapsed if r["schedule_B"]["behaviour_on_held_out"]["accuracy_of_the_set"] == 1.0]
    abstaining = [r["action"] for r in collapsed
                  if r["schedule_B"]["behaviour_on_held_out"]["accuracy_of_the_set"] < 1.0]
    assert len(collapsed) == 7
    assert len(exact) == 6
    assert abstaining == ["tar_x"]


def test_the_failure_mode_is_abstention_never_confident_error(receipt):
    k2 = receipt["verdict"]["K2_varied_successes_make_identification_exact_on_held_out"]
    assert k2["MET"]
    assert k2["confidently_wrong_anywhere"] == {}
    assert len(k2["exact_on_held_out"]) == 6
    assert sorted(k2["undecided"]) == ["ln_link", "mkdir_nodir_sub", "tar_x"]


def test_an_unsound_fact_is_named_when_one_exists(receipt):
    """tar_x is undecided even with coverage; the receipt names the fact vector that misdescribes the world."""
    rows = {r["action"]: r for r in receipt["rows"] if "skipped" not in r}
    tar = rows["tar_x"]
    assert tar["coverage"]["facts_true_in_every_seen_success"]
    assert tar["schedule_B"]["behaviour_on_held_out"]["undecided"] >= 1


# ----------------------------------------------------------------------------------------------------------
# the price
# ----------------------------------------------------------------------------------------------------------

def test_the_price_is_coverage_not_hypotheses(receipt):
    k4 = receipt["verdict"]["K4_the_price_is_coverage_not_hypotheses"]
    assert k4["facts"] == 17
    assert k4["candidate_subsets"] == 131072
    assert k4["candidate_conjunctions_with_polarity"] == 129140163
    assert k4["certificates_open_bound_at_23_effective_facts"] == 8388608
    assert k4["most_executions_for_any_action"] < 100
    assert k4["most_executions_for_any_action"] < k4["candidate_subsets"] // 1000


def test_the_committed_receipt_meets_every_claim():
    receipt = json.loads(RECEIPT.read_text())
    assert [k for k, v in receipt["verdict"].items() if not v["MET"]] == []
    assert receipt["cost"]["model_calls"] == 0
    assert receipt["cost"]["parameters_stored"] == 0
    assert receipt["cost"]["network_calls_at_run_time"] == 0
    assert receipt["limits"]


def test_the_producer_has_no_model_no_parameters_no_network():
    source = pathlib.Path(C.__file__).read_text(encoding="utf-8")
    for forbidden in ("import requests", "import urllib", "import socket", "import torch",
                      "import openai", "from openai", "http://", "https://"):
        assert forbidden not in source, forbidden
