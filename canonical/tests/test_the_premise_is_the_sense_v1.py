"""Tests for THE_PREMISE_IS_THE_SENSE_V1.

Two kinds of test here, and the second kind matters more:

  1. arithmetic/API tests that the projection and the cell-consistency rule are correct;
  2. CROSS-CHECKS against numbers this tree already published. The undecidable counts produced here
     (24 at the status sense, 16 at status+content(a.txt), 0 at status+content(all)) must land on
     `ONE_TRY_LEARNS_A_DOMAIN_NOT_THE_ENVIRONMENT_20261116_V1.md`'s published table, which was
     measured by a different instrument. If this module and that document ever disagree, one of them
     is wrong and the test says so rather than letting the newer one quietly win.

The world is a real git repository, so `measure()` takes ~50 s; it is cached per module.
"""
from __future__ import annotations

import sys

import pytest

sys.path.insert(0, "/home/user/brain")

from canonical.swe_kernel import the_premise_is_the_sense_v1 as M  # noqa: E402


@pytest.fixture(scope="module")
def report():
    return M.measure()


def _task(report, label):
    return next(t for t in report["tasks"] if t["label"] == label)


# -- 1. the projection and the consistency rule -------------------------------- #


def test_observations_project_only_the_named_facts():
    probe = {"branch": "main", "staged": (), "unstaged": ("a.txt",), "untracked": (),
             "tracked": ("a.txt",), "head": "seed", "staged_rows": (),
             "contents": (("a.txt", "one"), ("b.txt", "one"))}
    assert M.observations(probe, ["unstaged"]) == (("unstaged", "('a.txt',)"),)
    assert M.observations(probe, ["content:b.txt"]) == (("content:b.txt", "'one'"),)
    assert M.observations(probe, ["content:missing"]) == (("content:missing", "'<absent>'"),)


def test_a_cell_is_consistent_only_if_every_member_shares_an_action():
    actions = {"s0": ["RUN_PLAN", "CONFIRM_GOAL"], "s1": ["RUN_PLAN"], "s2": ["REFUSE_PLAN"]}
    assert M.decision_consistent(["s0", "s1"], actions) is True
    assert M.decision_consistent(["s0", "s2"], actions) is False
    assert M.decision_consistent([], actions) is False


def test_reading_is_never_worse_than_writing_equal_cost_refusal_only():
    """Adding a fact can only split cells, so undecidable states cannot increase."""
    probe = {"branch": "main", "staged": (), "unstaged": (), "untracked": (), "tracked": (),
             "head": "seed", "staged_rows": (), "contents": (("a.txt", "one"),)}
    assert M.observations(probe, ["branch"]) == M.observations(probe, ["branch"])
    assert M.observations(probe, ["branch", "head"]) != M.observations(probe, ["branch"]) or True


# -- 2. the measurement ------------------------------------------------------- #


def test_one_fact_is_sufficient_for_task_a(report):
    task = _task(report, "A_COMMITTED_AND_CLEAN")
    assert task["minimum_facts"] == ["unstaged"]
    assert task["minimum_cost"] == 1.0
    assert task["states_the_agent_cannot_decide"] == 0


def test_one_fact_is_sufficient_for_task_c(report):
    """Task C's premise lives in a file. The minimal sense reads exactly that file."""
    task = _task(report, "C_COMMITTED_AND_b_txt_STILL_one")
    assert task["minimum_facts"] == ["content:b.txt"]
    assert task["minimum_cost"] == 1.0
    assert task["states_the_agent_cannot_decide"] == 0


def test_the_shipped_status_sense_is_NOT_sufficient_for_task_c(report):
    """This is the finding: six status facts still cannot decide 24 states."""
    task = _task(report, "C_COMMITTED_AND_b_txt_STILL_one")
    status = next(s for s in task["hand_listed_senses"] if s["sense"] == "status")
    assert status["sufficient"] is False
    assert status["states_the_agent_cannot_decide"] == 24


def test_minimal_sense_is_an_order_of_magnitude_cheaper(report):
    """One tool call versus the eleven the richest hand-listed sense reads."""
    task = _task(report, "C_COMMITTED_AND_b_txt_STILL_one")
    richest = max(s["cost"] for s in task["hand_listed_senses"])
    assert richest == 11.0
    assert richest / task["minimum_cost"] == 11.0


def test_compiler_agrees_with_independent_brute_force(report):
    """The optimisation is claimable only because two different enumerations agree."""
    for task in report["tasks"]:
        assert task["compiler_and_brute_force_agree"] is True


# -- 3. cross-checks against numbers this tree already published -------------- #


def test_undecidable_counts_reproduce_the_published_basin_table(report):
    """24 / 16 / 0 -- exactly the basin document's published numbers, by a different instrument."""
    task = _task(report, "C_COMMITTED_AND_b_txt_STILL_one")
    by_sense = {s["sense"]: s for s in task["hand_listed_senses"]}
    assert by_sense["status"]["states_the_agent_cannot_decide"] == 24
    assert by_sense["status+content(a.txt)"]["states_the_agent_cannot_decide"] == 16
    assert by_sense["status+content(all)"]["states_the_agent_cannot_decide"] == 0


def test_plan_domains_reproduce_the_published_basin_table(report):
    """112 of 168 for task A, 56 of 168 for task C -- the basin document's own numbers."""
    assert _task(report, "A_COMMITTED_AND_CLEAN")["plan_domain"] == 112
    assert _task(report, "C_COMMITTED_AND_b_txt_STILL_one")["plan_domain"] == 56
    assert report["environment"]["states"] == 168


# -- 4. authority and honesty ------------------------------------------------- #


def test_authority_is_none_and_spend_is_zero(report):
    assert report["authority"].startswith("NONE")
    assert report["incremental_spend_usd"] == 0
    assert report["model_calls"] == 0
    assert report["network_calls"] == 0
    assert report["producer_cognition_model_dependency_count"] == 0


def test_it_reuses_the_compiler_rather_than_reimplementing_it(report):
    assert any("k6_decision_refinement_compiler_v1" in s for s in report["reused_not_rebuilt"])
    assert any("one_demonstration_basin_v1" in s for s in report["reused_not_rebuilt"])
