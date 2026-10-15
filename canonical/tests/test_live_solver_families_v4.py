from __future__ import annotations

import random
import shutil
from pathlib import Path
import pytest

from execution_guard import live_solver_end_to_end_measurement_v1 as h
from execution_guard import live_solver_families_v4 as v4
from canonical.runtime.live_brain_route_admission_v1 import solve


@pytest.fixture
def work(tmp_path):
    w = h.ROOT / "canonical" / "astra_runtime" / "tmp" / ("t_v4_" + tmp_path.name)
    w.mkdir(parents=True, exist_ok=True)
    yield w
    shutil.rmtree(w, ignore_errors=True)


def test_wave_four_families_are_registered():
    gens = h.all_generators()
    for fam in v4.GENERATORS_V4:
        assert fam in gens
    assert len(v4.GENERATORS_V4) == 6


def test_wave_four_docx_create(work: Path):
    rng = random.Random(42)
    case = v4.gen_docx_create(rng, work, 0)
    res = solve({"task_id": "TEST_DOCX_V4", "goal": case.goal})
    assert res.get("pass") is True
    ok, msg = case.oracle(res)
    assert ok, msg


def test_wave_four_xlsx_create(work: Path):
    rng = random.Random(42)
    case = v4.gen_xlsx_create(rng, work, 0)
    res = solve({"task_id": "TEST_XLSX_CREATE_V4", "goal": case.goal})
    assert res.get("pass") is True
    ok, msg = case.oracle(res)
    assert ok, msg


def test_wave_four_xlsx_verify(work: Path):
    rng = random.Random(42)
    # matching
    case = v4.gen_xlsx_verify(rng, work, 0)
    res = solve({"task_id": "TEST_XLSX_VERIFY_MATCH_V4", "goal": case.goal})
    assert res.get("pass") is True
    ok, msg = case.oracle(res)
    assert ok, msg

    # tampered
    case_t = v4.gen_xlsx_verify(rng, work, 2)
    res_t = solve({"task_id": "TEST_XLSX_VERIFY_TAMPER_V4", "goal": case_t.goal})
    assert res_t.get("pass") is False
    ok_t, msg_t = case_t.oracle(res_t)
    assert ok_t, msg_t


def test_wave_four_source_ranking_bm25(work: Path):
    rng = random.Random(42)
    case = v4.gen_source_ranking_bm25(rng, work, 0)
    res = solve({"task_id": "TEST_BM25_V4", "goal": case.goal})
    assert res.get("pass") is True
    ok, msg = case.oracle(res)
    assert ok, msg


def test_wave_four_decision_synthesis(work: Path):
    rng = random.Random(42)
    case = v4.gen_decision_synthesis(rng, work, 0)
    res = solve({"task_id": "TEST_DECISION_V4", "goal": case.goal})
    assert res.get("pass") is True
    ok, msg = case.oracle(res)
    assert ok, msg


def test_wave_four_python_source_audit(work: Path):
    rng = random.Random(42)
    case = v4.gen_python_source_audit(rng, work, 0)
    res = solve({"task_id": "TEST_PY_AUDIT_V4", "goal": case.goal})
    assert res.get("pass") is True
    ok, msg = case.oracle(res)
    assert ok, msg
