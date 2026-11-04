"""Two defects, both of which made a precise answer look like a different, blander one.

Measured 2026-11-03 on `3a7722d`. `test_front_door_crossfile_task_v1.py` scored 29 failed /
9 passed. Neither defect below is a missing capability; both are the door losing information it
had already computed.

DEFECT 1 — the frozen template was treated as the whole binding.
------------------------------------------------------------------
A complete staged-workflow grammar binds one input per stated path, request-locally, because it
may not change the shared registry. The compiler's completeness check ran FIRST, against the
frozen `action_template` (which names only the slots every request shares), and refused:

    GOAL_INPUT_BINDING_REQUIRED:software.repair.choreograph.crossfile.v1:
        unserved_stated_files:<scratch>/issue.json

...before anything had a chance to add the slot the sentence had stated. The check now runs
again against the binding the request-local grammar will actually use, and only a binding that
consumes EVERY stated path clears it. Nothing is weakened: a path still dropped is still refused.

DEFECT 2 — an unrecognised refusal was re-served, so its reason was overwritten.
----------------------------------------------------------------------------------
`_is_honest_contract_refusal` treats a failure class it does not know as "serve it by acting", and
`_serve_by_acting` answers with the generic execution-boundary status. So a refusal that said
`CROSSFILE_TASK_UNBOUND` -- "this request names files it does not bind" -- reached the caller as
`COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT`, a statement about the execution boundary that
was never consulted. A test whose entire purpose is that the refusal is PRECISE read the wrong
class, and 4 of its cases failed while reporting a safety property they never touched.

The second one matters beyond this file: an agent triaging the honest suite would have counted
those failures as blocked on the carrier review.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from canonical.runtime import goal_compiler
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.tests.test_front_door_crossfile_task_v1 import request
from canonical.tests.test_task_bound_crossfile_workflow_v1 import repo as fixture_repo

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def task():
    """A FRESH root per test, under the repo (inside it is required: the goal states repo paths,
    and the door refuses a path outside its own workspace)."""
    parent = ROOT / "canonical/astra_runtime/tmp"
    parent.mkdir(parents=True, exist_ok=True)
    raw = tempfile.mkdtemp(prefix="precise-refusal-", dir=parent)
    return fixture_repo.__wrapped__(Path(raw))


def test_a_stated_path_the_frozen_template_drops_does_not_stop_a_complete_grammar(task):
    """DEFECT 1. The grammar states three paths; the shared template names two. The third is
    consumed request-locally, so the request is well-formed and must compile."""
    context = door.live_integrated_brain_v1.compile_against_live_registry(request(task)["goal"], ROOT)
    compiled = context[2]
    inputs = dict(compiled.get("inputs") or {})
    assert compiled["selected_capability"] == "software.repair.choreograph.crossfile.v1"
    rel = task.relative_to(ROOT).as_posix()
    assert inputs.get("source_root") == rel + "/src"
    assert inputs.get("output_path") == rel + "/out/report.json"
    # the one the frozen template did not name:
    assert inputs.get("issue_path") == rel + "/issue.json", (
        "the stated issue path was dropped by the shared template and never re-bound")


def test_the_completeness_check_still_refuses_a_path_nothing_consumes(task):
    """The fix must not become a way to ignore a stated file. A fourth path with no slot is
    still GOAL_INPUT_BINDING_REQUIRED -- the rule is completeness, not leniency."""
    goal = request(task)["goal"] + " and also read %s/out/unrelated.json" % (
        task.relative_to(ROOT).as_posix())
    with pytest.raises(goal_compiler.GoalCompilationFailure) as excinfo:
        door.live_integrated_brain_v1.compile_against_live_registry(goal, ROOT)
    assert "GOAL_INPUT_BINDING_REQUIRED" in str(excinfo.value)


def test_a_request_naming_files_it_cannot_bind_keeps_its_own_reason(task):
    """DEFECT 2, stated at the level that was wrong: the class that comes back must be about
    the REQUEST, not about the execution boundary."""
    req = request(task)
    req["goal"] += " Also include a changelog."
    result = door.solve(req)
    assert result["pass"] is False
    assert result["failure_class"] == "CROSSFILE_TASK_UNBOUND", (
        "a precise refusal was replaced; got %r" % (result.get("failure_class"),))
    assert "ADMITTED_CONFINEMENT" not in str(result.get("status") or "")


def test_the_unknown_refusal_class_never_reaches_the_boundary_answer(task):
    """The mechanism, not just the instance: whatever a request-local grammar refuses with, it
    must be listed as an honest refusal so `_serve_by_acting` cannot overwrite it."""
    from canonical.swe_kernel import closed_loop_autonomous_controller_v1 as clc
    refusal = {"pass": False, "status": "FAIL_CLOSED__CROSSFILE_TASK_UNBOUND",
               "failure_class": "CROSSFILE_TASK_UNBOUND"}
    assert clc._is_honest_contract_refusal(refusal) is True
    # and a failure that says nothing about the request is still not excused:
    assert clc._is_honest_contract_refusal({"pass": False, "status": "?", "failure_class": "?"}) is False
