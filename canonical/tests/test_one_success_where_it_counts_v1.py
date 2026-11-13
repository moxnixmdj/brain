#!/usr/bin/env python3
"""The repository already measured the claim. These tests keep it quotable.

Five passes of this conversation argued about whether one demonstration becomes a skill in an
arbitrary environment, while
`canonical/verification/MINIWOB_ONE_SUCCESS_GENERALISATION_20261111_V5.json` sat on disk
containing the answer, measured on 130 MiniWoB++ pages nobody here wrote. The failure was in
reading, not in the repository.

So the assertions below are deliberately about the *shape* of the evidence rather than only the
numbers: every arm present, the control that separates a skill from re-reading present, the
cache arm present and weak, and the refusal firing on a report that hides its cost.
"""
from __future__ import annotations

import json
import pathlib

import pytest

from canonical.tools import one_success_where_it_counts_v1 as T


# ---------------------------------------------------------------------------
# the recorded run is found and read from disk, not from constants in the tool
# ---------------------------------------------------------------------------
def test_the_ladder_is_read_from_a_recorded_run():
    result = T.report()
    assert result["run"].startswith("MINIWOB_ONE_SUCCESS_GENERALISATION_")
    assert result["authority"] == "NONE"
    assert result["pages_demonstrated"] and result["pages_demonstrated"] > 0


def test_every_rung_of_the_ladder_is_present_in_the_newest_run():
    result = T.report()
    present = {row["arm"] for row in result["ladder"] if row["present"]}
    for arm, *_ in T.LADDER:
        assert arm in present, f"{arm} missing from {result['run']}"


def test_the_newest_run_is_the_one_quoted():
    path, _ = T.newest()
    assert path == T.runs()[-1]
    assert T.report()["run"] == path.name


# ---------------------------------------------------------------------------
# the claim, and the two things that make it more than a cache
# ---------------------------------------------------------------------------
def test_generalising_a_success_beats_replaying_it():
    flat = T.report()["where_replay_is_not_enough"]
    assert flat["one_success"] > flat["replay"], "replay is the cache arm and must be the weak one"
    assert flat["lift_over_replay"] > 0


def test_denying_the_instruction_breaks_the_same_learner():
    """Without this control, 'the skill generalised' is indistinguishable from 'it re-read the
    instruction on every instance'. The run reports both sides, so the separation is measured."""
    reads = T.report()["reads_the_instruction"]
    assert reads["fail_when_denied_it"] and reads["fail_when_denied_it"] > 0
    flat = T.report()["where_replay_is_not_enough"]
    assert flat["denied_the_instruction"] < flat["one_success"]


def test_the_tree_s_own_compiler_is_on_the_same_board():
    """The pre-existing mechanism is a rung, not an omitted comparison."""
    rows = {r["arm"]: r for r in T.report()["ladder"] if r["present"]}
    assert rows["existing_compiler"]["where_replay_is_not_enough"] < \
        rows["version_space"]["where_replay_is_not_enough"]


def test_practice_is_reported_as_a_cost_not_hidden():
    flat = T.report()["where_replay_is_not_enough"]
    assert flat["with_practice"] >= flat["one_success"]
    assert any("practice" in line for line in T.report()["refutes"])


def test_a_run_admits_what_it_never_measured():
    assert T.report()["not_done"], "a run that lists no gaps is asserting more than it did"


# ---------------------------------------------------------------------------
# the refusal: a board that contradicts itself must not print as a result
# ---------------------------------------------------------------------------
def _synthetic(**overrides) -> dict:
    base = {
        "run": "SYNTHETIC.json",
        "pages_demonstrated": 78,
        "tasks_that_need_generalisation": 67,
        "tasks_replay_already_solves": 11,
        "where_replay_is_not_enough": {"one_success": 0.65, "denied_the_instruction": 0.18,
                                       "with_practice": 0.74, "replay": 0.14,
                                       "lift_over_replay": 0.51},
        "reads_the_instruction": {"fail_when_denied_it": 33, "succeed_when_denied_it": 1,
                                  "survive_an_instruction_change": 0},
        "not_done": ["an independent re-run"],
    }
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = {**base[key], **value}
        else:
            base[key] = value
    return base


def test_a_clean_board_has_no_contradictions():
    assert T.contradictions(_synthetic()) == []


def test_a_lift_without_a_replay_baseline_is_refused():
    problems = T.contradictions(_synthetic(where_replay_is_not_enough={"replay": None}))
    assert any("NO_REPLAY_BASELINE" in p for p in problems)


def test_a_board_without_the_denied_instruction_control_is_refused():
    problems = T.contradictions(_synthetic(reads_the_instruction={"fail_when_denied_it": None}))
    assert any("NO_DENIED_INSTRUCTION_CONTROL" in p for p in problems)


def test_a_board_where_nothing_needed_generalising_is_refused():
    problems = T.contradictions(_synthetic(tasks_that_need_generalisation=0))
    assert any("NOTHING_TO_GENERALISE" in p for p in problems)


def test_the_cli_prints_a_board_and_exits_zero_on_the_real_run():
    assert T.main([]) == 0


# ---------------------------------------------------------------------------
# the artifact that answers the question is not allowed to go missing
# ---------------------------------------------------------------------------
def test_the_measurement_files_themselves_are_present():
    paths = T.runs()
    assert len(paths) >= 3
    for path in paths:
        json.loads(path.read_text())        # every one must still parse


# ---------------------------------------------------------------------------
# the replication: same ordering, instances that did not exist when it was learned
# ---------------------------------------------------------------------------
def test_a_replication_run_is_on_file_and_is_not_confused_with_the_headline():
    reps = T.replications()
    assert reps, "the fresh-seed replication must stay on file"
    record = T.report()
    # the headline is still taken from the full-scale run, never from the 50-page replication
    assert record["run"].startswith("MINIWOB_ONE_SUCCESS_GENERALISATION_")
    assert record["run"] != reps[-1].name


def test_the_ladder_ordering_reproduces_on_fresh_seeds():
    check = T.replication_check()
    assert check["available"] is True
    assert check["ordering_reproduces"] is True
    names = {c["ordering"] for c in check["checks"]}
    assert "version_space > verbatim" in names
    assert "version_space > version_space_blind" in names


def test_the_replication_records_the_instances_it_used():
    check = T.replication_check()
    seeds = check["test_seeds"]
    assert seeds and min(seeds) >= 1080, "fresh means unused by runs 3/4/5 (1000-1079)"
    assert check["browser"].startswith("HeadlessChrome/")


def test_a_replication_is_never_quoted_as_the_headline_number():
    """The two runs use different task sets; only the ordering may be compared."""
    check = T.replication_check()
    assert check["pages"] < 130, "a replication is smaller than the full run by construction"
    # and the tool says so in the record it writes
    import json as _json
    rep = _json.loads(T.replications()[-1].read_text())
    assert "ordering" in rep["read_this_first"].lower()
    assert "does not" in rep["read_this_first"].lower()
