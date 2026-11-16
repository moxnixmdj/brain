"""The four worlds a "no first success" page can be in, and why the difference is load-bearing.

The measurement this pins (`canonical/verification/WHERE_THE_WALL_ACTUALLY_IS_20261116_V1.json`)
exists because one number -- "37 held-out pages never produced a first success" -- is produced by
four different worlds with four different repairs. Two of the tests below are the ones that
matter, because each fails if the classification is allowed to go wrong in a way that would send
the roadmap in the wrong direction:

  * a closed exhaustion must NOT be reported as a budget problem. If it were, the answer would
    be "spend more search", and more search provably cannot help a space that was exhausted.
  * a state-blind stop must outrank a budget stop. The explorer stops early because the same
    look behaved two different ways; searching longer over a look that merges distinct states
    cannot fix that, so calling it a budget page would again prescribe the wrong repair.

The third load-bearing test is `test_a_stale_label_never_decides_the_answer`: rows are stored
with a `world` field, and summaries must recompute it from the recorded statuses. A label
written by an older build of the tool must not be able to decide today's roadmap.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import systematic_exploration_v1 as explorer  # noqa: E402
from canonical.tools import miniwob_where_the_wall_actually_is_v1 as wall  # noqa: E402

RECEIPT = ROOT / "canonical/verification/WHERE_THE_WALL_ACTUALLY_IS_20261116_V1.json"


def test_no_success_because_every_reachable_action_was_tried_is_the_action_world():
    assert wall.world_of("NO_FIRST_SUCCESS_FOUND", [explorer.FAIL_EXHAUSTED]) == wall.ACTION_VOCABULARY


def test_an_exhausted_space_is_never_reported_as_a_budget_problem():
    """The mistake that would buy compute instead of building the missing primitive."""
    world = wall.world_of("NO_FIRST_SUCCESS_FOUND", [explorer.FAIL_EXHAUSTED])
    assert world != wall.SEARCH_BUDGET
    assert wall.REPAIR[world] == "add_the_missing_action_primitive"


def test_a_page_that_behaves_differently_on_the_same_look_outranks_the_budget_verdict():
    """It stopped early, which looks like a small budget. It is not: the look is what is wrong."""
    world = wall.world_of("NO_FIRST_SUCCESS_FOUND",
                          [explorer.OPEN_UNSTABLE, explorer.OPEN_BUDGET])
    assert world == wall.BLIND_TO_STATE
    assert wall.REPAIR[world].startswith("add_the_missing_observable")


def test_a_vocabulary_that_offered_nothing_is_not_the_same_as_one_that_was_exhausted():
    assert wall.world_of("NO_FIRST_SUCCESS_FOUND", [explorer.OPEN_NO_VOCABULARY]) == wall.NO_ACTION_OFFERED


def test_running_out_of_budget_is_its_own_world():
    assert wall.world_of("NO_FIRST_SUCCESS_FOUND", [explorer.OPEN_BUDGET]) == wall.SEARCH_BUDGET


def test_a_page_that_reached_the_goal_is_not_a_wall_page():
    assert wall.world_of("DEMONSTRATED", []) == wall.REACHED


def test_a_stale_label_never_decides_the_answer():
    """The row says it ran out of budget; the statuses say the space was exhausted. Statuses win."""
    stale = {"task": "x", "stage": "NO_FIRST_SUCCESS_FOUND",
             "statuses": [explorer.FAIL_EXHAUSTED],
             "world": wall.SEARCH_BUDGET}
    summary = wall.summarise([stale])
    assert summary["worlds"][wall.ACTION_VOCABULARY]["tasks"] == ["x"]
    assert wall.SEARCH_BUDGET not in summary["worlds"]


def test_the_worlds_partition_the_rows():
    rows = [{"task": "a", "stage": "NO_FIRST_SUCCESS_FOUND", "statuses": [explorer.FAIL_EXHAUSTED]},
            {"task": "b", "stage": "NO_FIRST_SUCCESS_FOUND", "statuses": [explorer.OPEN_UNSTABLE]},
            {"task": "c", "stage": "NO_FIRST_SUCCESS_FOUND", "statuses": [explorer.OPEN_BUDGET]},
            {"task": "d", "stage": "DEMONSTRATED", "statuses": []}]
    summary = wall.summarise(rows)
    assert sum(world["count"] for world in summary["worlds"].values()) == len(rows)
    assert summary["reached"] == 1 and summary["not_reached"] == 3


def test_the_unsolved_set_is_derived_from_the_baseline_receipt_and_is_not_typed_by_hand():
    """37 is not a number in this file; it is whatever the receipt says, and this pins the receipt."""
    unsolved = wall.unsolved_held_out()
    baseline = json.loads(wall.BASELINE_RECEIPT.read_text())
    held_out_not_demonstrated = {row["task"] for row in baseline["tasks"]
                                 if row["split"] == "held_out" and row["stage"] != "DEMONSTRATED"}
    assert {row["task"] for row in unsolved} == held_out_not_demonstrated
    assert len(unsolved) == 37


def test_the_receipt_agrees_with_its_own_rows():
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["summary"] == wall.summarise(receipt["tasks"])
    assert {row["task"] for row in receipt["tasks"]} == {row["task"] for row in wall.unsolved_held_out()}


def test_the_receipt_names_no_capability_and_no_credit():
    receipt = json.loads(RECEIPT.read_text())
    assert receipt["authority"] == wall.AUTHORITY
    assert receipt["producer_cognition_model_dependency_count"] == 0
    assert receipt["incremental_spend_usd"] == 0
