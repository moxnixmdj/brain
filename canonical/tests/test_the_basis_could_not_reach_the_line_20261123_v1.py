#!/usr/bin/env python3
"""Tests for the candidate basis, and for the four ways a verifier lied about it.

Each test pins either a measured defect in the repair loop's scoring, or the one family
that converts a real bug. No browser, no network; the AST work is pure.
"""
from __future__ import annotations

import importlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOOP = importlib.import_module(
    "canonical.runtime.bound_capabilities.python_iterative_software_repair_loop_v1")
W = importlib.import_module("canonical.runtime.the_witness_carries_the_distance_v1")


def _run(stdout: str, returncode: int = 1) -> dict:
    return {"returncode": returncode, "stdout": stdout, "stderr": "", "timed_out": False}


# --- the verifier may not be satisfied by running nothing ------------------ #
def test_a_green_exit_with_no_tests_is_not_a_pass() -> None:
    """MEASURED on pypa/packaging 8efde605: a nonsense candidate rewrote a lazy-import
    string so the module could not be collected; the run reported "0 failed, 0 passed"
    with exit 0, and the old `_score` returned 0 -- perfect. The loop accepted it."""
    assert LOOP._score(_run("0 failed, 0 passed in 0.01s", 0)) is None
    assert LOOP._score(_run("no tests ran in 0.01s", 0)) is None
    assert LOOP._score(_run("348 passed in 1.1s", 0)) == 0


def test_a_collection_error_is_refused_not_counted() -> None:
    """`ERROR collecting <module>` means the program cannot be imported: the worst state.
    Counting it as "1 failure" made wrecking a module score better than the four real
    assertion failures it replaced -- 4 -> 1 was accepted as progress."""
    text = ("ERROR collecting tests/x.py\n"
            "Interrupted: 1 error during collection\n1 error in 0.1s")
    assert LOOP._score(_run(text, 2)) is None


def test_a_wrapped_pytest_exit_is_still_an_exit() -> None:
    """THE ONE THAT ACTUALLY GOT THROUGH. The in-process runner wraps a non-zero pytest
    status in `RuntimeError: PYTEST_EXECUTION_FAILED:4` and still prints a summary, so a
    run whose pytest returned 4 (usage error, module never collected) reached the generic
    counter and scored 1 while the bug scored 4. A broken program looked like a repair."""
    text = "RuntimeError: PYTEST_EXECUTION_FAILED:4\n1 failed in 0.1s"
    assert LOOP._score(_run(text, 1)) is None


def test_real_failures_still_score() -> None:
    assert LOOP._score(_run("4 failed, 2420 passed in 1.0s")) == 4
    assert LOOP._score(_run("1 failed in 0.1s")) == 1


# --- the objective refuses the same thing --------------------------------- #
def test_the_objective_refuses_a_run_that_executed_nothing() -> None:
    s = W.score("0 failed, 0 passed in 0.01s")
    assert s["executed"] is False
    assert s["satisfied"] == 0
    assert s["key"][1] <= -1e8, "an unexecuted run must sort worse than any real one"


def test_an_unexecuted_run_never_beats_a_real_failing_one() -> None:
    empty = W.score("0 failed, 0 passed in 0.01s")
    real = W.score("4 failed, 344 passed in 1.0s")
    assert W.improved(real, empty) is False


# --- the missing family --------------------------------------------------- #
def test_a_name_scope_candidate_is_generated_from_the_module_own_fields() -> None:
    """The shape no swap can express: `a.x` rewritten to the bare `x`. 20 of 381 real
    hunks do exactly this (packaging 8efde605: `item.include_group` -> `include_group`),
    and the basis could only ever produce `a.x` -> `a.y`."""
    import ast
    P = importlib.import_module(
        "canonical.runtime.bound_capabilities.python_test_guided_patch_search_v1")
    source = ("class Holder:\n"
              "    width = 1\n"
              "    def use(self, box):\n"
              "        return box.width\n")
    tree = ast.parse(source)
    got = [d for _k, d, _r in P._candidate_specs(tree, [], [], None, structural=False)
           if d.get("family") == "name_scope"]
    assert got, "the name-scope family produced nothing"
    assert any("width" in str(d.get("detail")) for d in got)


def test_the_name_scope_pool_is_the_file_not_the_test_literals() -> None:
    """The pool must be the module's own declared names: a candidate drawn from the test's
    literals would be copying the answer, which is leakage."""
    import ast
    P = importlib.import_module(
        "canonical.runtime.bound_capabilities.python_test_guided_patch_search_v1")
    source = "class K:\n    alpha = 1\n    def f(self, o):\n        return o.alpha\n"
    tree = ast.parse(source)
    details = [str(d.get("detail")) for _k, d, _r in
               P._candidate_specs(tree, [], ["SECRET_FROM_TEST"], None, structural=False)
               if d.get("family") == "name_scope"]
    assert details and all("SECRET_FROM_TEST" not in d for d in details)
