from __future__ import annotations

import random
import shutil
from pathlib import Path
import pytest

from execution_guard import live_solver_end_to_end_measurement_v1 as h
from execution_guard import live_solver_families_v5 as v5
from canonical.runtime.live_brain_route_admission_v1 import solve


@pytest.fixture
def work(tmp_path):
    w = h.ROOT / "canonical" / "astra_runtime" / "tmp" / ("t_v5_" + tmp_path.name)
    w.mkdir(parents=True, exist_ok=True)
    yield w
    shutil.rmtree(w, ignore_errors=True)


def test_wave_five_generators_registered():
    assert "MATH_NUMERIC_SYMPY" in v5.GENERATORS_V5
    assert "JSON_QUERY_JQ" in v5.GENERATORS_V5
    assert "PYTHON_FAULT_LOCALIZE" in v5.GENERATORS_V5
    assert "PYTHON_AST_PATCH_SEARCH" in v5.GENERATORS_V5


def test_wave_five_sympy(work):
    rng = random.Random(42)
    case = v5.gen_math_numeric_sympy(rng, work, 0)
    res = solve({"task_id": "TEST_W5_SYMPY", "goal": case.goal})
    ok, err = case.oracle(res)
    assert ok is True, f"SymPy oracle failed: {err}"


def test_wave_five_jq(work):
    rng = random.Random(43)
    case = v5.gen_json_query_jq(rng, work, 1)
    res = solve({"task_id": "TEST_W5_JQ", "goal": case.goal})
    ok, err = case.oracle(res)
    assert ok is True, f"JQ oracle failed: {err}"


def test_wave_five_python_fault_localize(work):
    rng = random.Random(44)
    case = v5.gen_python_fault_localize(rng, work, 2)
    res = solve({"task_id": "TEST_W5_FL", "goal": case.goal})
    ok, err = case.oracle(res)
    assert ok is True, f"Fault localizer oracle failed: {err}"


def test_wave_five_python_ast_patch_search(work):
    rng = random.Random(45)
    case = v5.gen_python_ast_patch_search(rng, work, 3)
    res = solve({"task_id": "TEST_W5_PS", "goal": case.goal})
    ok, err = case.oracle(res)
    assert ok is True, f"AST patch search oracle failed: {err}"
