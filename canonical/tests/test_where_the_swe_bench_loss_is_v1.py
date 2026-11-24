"""Where the loss actually is on SWE-bench Verified: not in choosing, and not only in finding.

The mission is arbitrary software engineering. The tree holds one real run scored under the
tasks' own tests: 231 Django tasks of SWE-bench Verified, 5 resolved on one submission (3.9%
of the 128 judged tasks that had a candidate), with a pre-registered expectation that held
([4,10]) and a control -- another task's text -- that resolved 0.

A 3.9% headline is not actionable on its own. What is actionable is WHERE the other 96% went,
and it decomposes cleanly:

    44% of tasks        never got a candidate at all
    0.41% of candidates resolve                      (10 of 2422)
    +2 tasks maximum    from perfect SELECTION, because a resolving candidate exists for
                        only 7 of 128 tasks
    128/128 tasks       had EVERY candidate in ONE file, while the expert's file is rank 1
                        only 40% of the time
    18 of 25 tasks      had a candidate that made the failing test PASS and still did not
                        resolve -- 16 of them never even reached the whole-module run

So the loss is not in ranking. It is upstream, in two distinct places, and they need
different fixes: FINDING (the candidate is in the wrong file or absent) and PRECISION (the
candidate does the asked-for thing and breaks a neighbour).

These tests read recorded receipts and assert the decomposition. They do not run SWE-bench,
and they say so.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

REPO = pathlib.Path(__file__).resolve().parents[2]
RUN = REPO / "canonical/verification/CANDIDATE_UNDER_THE_TASKS_TESTS_SWEBENCH_VERIFIED_DJANGO_20261113_V1.json"
LOC = REPO / "canonical/verification/FILE_FOUND_FROM_TASK_TEXT_SWEBENCH_VERIFIED_20261112_V1.json"
RECEIPT = REPO / "canonical/verification/WHERE_THE_SWE_BENCH_LOSS_IS_20261124_V1.json"


@pytest.fixture(scope="module")
def run():
    if not RUN.exists():
        pytest.skip("the recorded SWE-bench run is not in this tree")
    return json.loads(RUN.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def localisation():
    if not LOC.exists():
        pytest.skip("the recorded localisation measurement is not in this tree")
    return json.loads(LOC.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# the number being decomposed, and its control
# --------------------------------------------------------------------------- #
def test_the_headline_is_five_tasks_and_says_so(run):
    """A rate from 5 successes is not a stable rate. The receipt must not present it as one."""
    summary = run["summary"]
    assert summary["one_submission__tasks_resolved"] == 5
    assert len(summary["one_submission__tasks"]) == 5
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert "5 tasks" in receipt["the_honest_reading_of_the_3_9_percent"]
    assert "wide interval" in receipt["the_honest_reading_of_the_3_9_percent"]


def test_the_control_resolves_nothing(run):
    """Another task's text produces no resolution, so the five are not noise."""
    assert run["summary"]["another_tasks_text__tasks_resolved"] == 0


# --------------------------------------------------------------------------- #
# the decomposition
# --------------------------------------------------------------------------- #
def test_44_percent_of_tasks_never_get_a_candidate(run):
    summary = run["summary"]
    assert summary["tasks"] == 231
    assert summary["with_a_candidate"] == 129
    share = summary["with_a_candidate"] / summary["tasks"]
    assert 0.5 < share < 0.6, share


def test_almost_no_candidate_resolves(run):
    summary = run["summary"]
    assert summary["candidates_resolving"] == 10
    assert summary["candidates_run"] > 2000
    assert summary["candidates_resolving"] / summary["candidates_run"] < 0.01


def test_selection_is_worth_at_most_two_tasks(run):
    """THE LEVER THAT IS NOT THERE.

    Perfect ranking would reach the `within twenty` number, 7, against the 5 a submission
    reaches. So all of ranking, the thing one would naturally build next, is worth +2 tasks
    of 128. This asserts the ceiling so a later round cannot optimise it as though it were
    the bottleneck.
    """
    summary = run["summary"]
    ceiling = summary["within_twenty__tasks_resolved"] - summary["one_submission__tasks_resolved"]
    assert ceiling == 2
    assert ceiling / summary["with_a_candidate_and_judged"] < 0.02


def test_every_candidate_for_every_task_sat_in_one_file(run):
    """128 of 128. The generator never considered a second location."""
    per_task = run["per_task"]
    with_candidates = [row for row in per_task.values() if row.get("candidates")]
    single = [row for row in with_candidates
              if len({c["path"] for c in row["candidates"]}) == 1]
    assert len(with_candidates) == 128
    assert len(single) == 128, f"only {len(single)} of {len(with_candidates)} were single-file"


def test_the_expert_file_is_rank_one_less_than_half_the_time(localisation):
    """So a single-file generator is looking in the wrong place more often than not."""
    shares = localisation["summary"]["expert_file_among_the_first__score_alone__share"]
    assert shares["1"] < 0.5
    assert shares["3"] > shares["1"] and shares["10"] > shares["3"]


# --------------------------------------------------------------------------- #
# the second failure mode, which is not localisation
# --------------------------------------------------------------------------- #
def test_precision_is_a_separate_loss_from_finding(run):
    """THE SHARPEST RESULT. A candidate that makes the failing test pass and still does not
    resolve is not in the wrong file -- it did the asked-for thing and broke a neighbour.
    Sixteen of those never even reached the whole-module run, so the breakage is visible
    cheaply and nobody was reading it."""
    per_task = run["per_task"]
    started = [row for row in per_task.values()
               if any(c.get("start_passing") for c in (row.get("candidates") or []))]
    unresolved = [row for row in started
                  if not any(c.get("resolves") for c in (row.get("candidates") or []))]
    never_whole = [row for row in unresolved
                   if not any(c.get("whole_run") for c in (row.get("candidates") or []))]
    assert len(started) == 25
    assert len(unresolved) == 18
    assert len(never_whole) == 16


def test_the_two_failure_modes_are_named_apart_in_the_receipt():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    text = receipt["the_arithmetic"]["conclusion"]
    assert "SELECTION" in text
    # FINDING and PRECISION must both appear, because they need different fixes
    blob = json.dumps(receipt)
    assert "PRECISION" in blob.upper()
    assert "FINDING" in blob.upper()


# --------------------------------------------------------------------------- #
# what the round refuses to claim
# --------------------------------------------------------------------------- #
def test_it_does_not_claim_to_have_run_the_benchmark():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    not_done = " ".join(receipt["what_this_round_does_NOT_do"])
    assert "does not run SWE-bench" in not_done
    assert receipt["model_calls"] == 0
    assert receipt["parameters"] == 0
    assert receipt["authority"].startswith("NONE")


def test_it_names_the_generator_and_not_the_ranker_as_the_bottleneck():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert "generator IS the bottleneck" in receipt["what_this_round_does_NOT_do"][1]
    assert "COVERAGE" in receipt["the_next_bottleneck"]
