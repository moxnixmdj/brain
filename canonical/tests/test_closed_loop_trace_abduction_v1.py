#!/usr/bin/env python3
"""Mechanism tests for the closed-loop trace-abduction repair engine.

These pin the four causal steps (trace slicing, insufficiency detection,
angelic synthesis, falsification) on tiny programs whose behaviour is known
exactly. They are not benchmark runs: no corpus is read here.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import closed_loop_trace_abduction_repair_v1 as cl  # noqa: E402


def test_trace_records_executed_lines():
    fn = cl.load_function("def f(n):\n    if n == 0:\n        return 0\n    return f(n - 1) + 1\n", "f")
    t = cl.run_with_trace(fn, (3,))
    assert t.status == "value" and t.value == 3
    assert 2 in t.executed_lines and 4 in t.executed_lines


def test_quota_trips_on_non_termination_with_cycle():
    fn = cl.load_function("def f(n):\n    while True:\n        n = n + 1\n    return n\n", "f")
    t = cl.run_with_trace(fn, (0,), step_quota=500)
    assert t.status in ("quota", "quota_cycle")
    diag = cl.loop_cycle_diagnosis(t)
    assert diag["non_terminating"] is True


def test_ochiai_ranks_failing_only_line_first():
    fn = cl.load_function("def f(n):\n    if n < 0:\n        return -1\n    return n * 2\n", "f")
    failing = [cl.run_with_trace(fn, (-5,))]
    passing = [cl.run_with_trace(fn, (3,))]
    ranked = cl.ochiai_rank(failing, passing)
    assert ranked and ranked[0][0] == 3  # the `return -1` line


def test_insufficiency_certificate_detects_collision():
    cert = cl.insufficiency_certificate(["a", "a", "b"], [0.1, 0.9, 0.2], [0, 1, 0])
    assert cert["A_subset_F"] is True
    assert cert["static_separable"] is False
    assert cert["dynamic_vocabulary_admitted"] is True
    assert cert["delta_I_dynamic_given_static"] > 0


def test_insufficiency_certificate_sufficient_static():
    cert = cl.insufficiency_certificate(["a", "b"], [0.1, 0.9], [0, 1])
    assert cert["static_separable"] is True
    assert cert["A_subset_F"] is False


def test_synthesis_finds_doubling_expression():
    exprs = cl.synthesize_expression([({"x": 3}, 6), ({"x": 4}, 8)], names=["x"], constants=[2])
    assert exprs, "synthesis must find an expression"
    for env, want in [({"x": 3}, 6), ({"x": 4}, 8)]:
        assert cl._eval_expr(exprs[0], env) == want


def test_synthesis_rejects_expressions_that_raise():
    # division by a possibly-zero name must not survive on a zero target env
    exprs = cl.synthesize_expression([({"x": 0}, 0), ({"x": 2}, 1)], names=["x"], constants=[1])
    for e in exprs:
        cl._eval_expr(e, {"x": 0})  # must not raise


def test_degeneracy_scan_ignores_preexisting_code():
    buggy = "def f(x):\n    return True\n"
    cand = "def f(x):\n    return True\n"
    assert cl.degeneracy_scan(cand, "assert f(1) == True", buggy)["degenerate"] is False


def test_degeneracy_scan_catches_test_literal_guard():
    buggy = "def f(x):\n    return x + 1\n"
    cand = "def f(x):\n    if x == 3:\n        return 5\n    return x + 1\n"
    scan = cl.degeneracy_scan(cand, "assert f(3) == 5", buggy)
    assert scan["degenerate"] is True


def test_locality_requires_executed_line():
    buggy = "def f(x):\n    return x + 1\n"
    cand = "def f(x):\n    return x + 2\n"
    assert cl.locality_check(buggy, cand, {2})["local"] is True
    assert cl.locality_check(buggy, cand, {99})["local"] is False


def test_crystallize_requires_surviving_falsifier():
    assert cl.crystallize("op", {}, "effect", {"survives": False}) is None
    skill = cl.crystallize("op", {"ochiai": 0.9}, "effect", {"survives": True})
    assert skill is not None and skill["skill_id"].startswith("skill_")
    assert "counterfactual_non_overfitting" in skill["ratchets"]


def test_replace_line_expression_rewrites_return():
    src = "def f(x):\n    return x + 1\n"
    out = cl.replace_line_expression(src, 2, "(x * 2)")
    assert out is not None and "x * 2" in out
    assert cl.replace_line_expression(src, 1, "(x * 2)") is None


def test_extract_assert_cases_splits_pass_fail():
    fn = cl.load_function("def f(x):\n    return x + 1\n", "f")
    test = "def check(candidate):\n    assert candidate(1) == 2\n    assert candidate(2) == 99\n"
    cases = cl.extract_assert_cases(test, "f", fn)
    assert len(cases) == 2
    assert cases[0].passed is True and cases[1].passed is False
    assert cases[1].args == (2,) and cases[1].expected == 99
