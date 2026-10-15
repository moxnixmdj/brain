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
