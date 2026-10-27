"""The heartbeat's verdict must be ALIVE only when every measured thing holds, and must name
exactly what failed otherwise (execution_guard/live_solver_end_to_end_measurement_v1)."""
from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from execution_guard.live_solver_end_to_end_measurement_v1 import alive_errors, summary_markdown  # noqa: E402

ALIVE = {
    # A receipt is only a candidate verdict when the run that produced it finished.
    # `run_complete` is now a field of the contract, not an assumption: a run that
    # stops early measures part of the suite, and `alive_errors` refuses to call that
    # ALIVE (see test_an_unfinished_run_is_never_alive below).
    "run_complete": True,
    "seed": 1, "python": "3.11", "machine": {"platform": "linux"},
    "measurements": {"new": {
        "families": {"A": {"oracle_pass": 5, "instances": 5}, "OUT_OF_SCOPE_MUST_FAIL_CLOSED": {"oracle_pass": 5, "instances": 5}},
        "out_of_scope_fail_closed_rate": 1.0}},
    "reachability_from_one_entry": {"capabilities_total": 2, "counts": {"REACHED_AND_BOUND": 1, "BLOCKED_ZERO_INPUT": 1},
                                    "rows": [{"capability_id": "z", "state": "BLOCKED_ZERO_INPUT", "detail": "no input"}]},
    "tool_liveness": {"capabilities_total": 2, "adapter_import_failed": [], "external_dependency_missing_here": ["x"], "adapter_missing": []},
    "families_not_measured_here": {"F": "why"},
}


def test_alive_when_everything_holds():
    assert alive_errors(ALIVE) == []
    md = summary_markdown(ALIVE)
    assert "**Verdict: ALIVE**" in md
    assert "| A | 5/5 |" in md
    assert "Tools runnable on this machine: 1 of 2" in md


def test_one_failing_fresh_instance_is_not_alive():
    r = copy.deepcopy(ALIVE)
    r["measurements"]["new"]["families"]["A"]["oracle_pass"] = 4
    assert alive_errors(r) == ["FAMILY_NOT_FULLY_PASSING:A:4/5"]
    assert "**Verdict: NOT ALIVE**" in summary_markdown(r)


def test_one_false_pass_on_an_out_of_scope_goal_is_not_alive():
    r = copy.deepcopy(ALIVE)
    r["measurements"]["new"]["out_of_scope_fail_closed_rate"] = 0.99
    assert alive_errors(r) == ["OUT_OF_SCOPE_NOT_FAIL_CLOSED:0.99"]


def test_one_unreachable_capability_is_not_alive():
    r = copy.deepcopy(ALIVE)
    r["reachability_from_one_entry"]["counts"]["NOT_REACHABLE"] = 1
    assert alive_errors(r) == ["CAPABILITY_NOT_REACHABLE:1"]


def test_missing_new_entry_measurement_is_not_alive():
    r = copy.deepcopy(ALIVE)
    r["measurements"] = {"old": r["measurements"]["new"]}
    assert alive_errors(r) == ["NEW_ENTRY_NOT_MEASURED"]


# --------------------------------------------------------------------------- #
# A run that did not finish
# --------------------------------------------------------------------------- #
def _unfinished():
    """The receipt a timed-out heartbeat can honestly produce: what it reached."""
    r = copy.deepcopy(ALIVE)
    r["run_complete"] = False
    r["pending_families"] = ["LATE_FAMILY_ONE", "LATE_FAMILY_TWO"]
    r["tool_liveness"] = {"measured": False}
    r["reachability_from_one_entry"] = {"measured": False}
    return r


def test_an_unfinished_run_is_never_alive():
    """The families that DID run all pass here -- and that still must not be ALIVE."""
    assert alive_errors(_unfinished())[0].startswith("MEASUREMENT_INCOMPLETE")


def test_an_unfinished_run_names_the_families_it_never_reached():
    errors = alive_errors(_unfinished())
    named = " ".join(errors)
    assert "LATE_FAMILY_ONE" in named and "LATE_FAMILY_TWO" in named


def test_an_unfinished_summary_says_so_before_it_shows_any_number():
    md = summary_markdown(_unfinished())
    assert "did NOT finish" in md
    head = md.split("Why not alive")[0]
    assert "did NOT finish" in head, "the warning must precede the table, not follow it"
    assert "`LATE_FAMILY_ONE`" in md


def test_an_unfinished_summary_does_not_invent_a_census():
    """Tool liveness was never reached; the summary must say that, not print zeros."""
    md = summary_markdown(_unfinished())
    assert "were not reached in this run" in md
    assert "Tools runnable on this machine" not in md


def test_a_finished_run_still_reads_exactly_as_before():
    """The control: nothing above changed the verdict for a complete receipt."""
    assert alive_errors(ALIVE) == []
    md = summary_markdown(ALIVE)
    assert "**Verdict: ALIVE**" in md
    assert "did NOT finish" not in md
    assert "Tools runnable on this machine" in md
