from __future__ import annotations

import os
import random
import shutil
from pathlib import Path

import pytest

from canonical.runtime import live_brain_route_admission_v1 as admission
from execution_guard import live_solver_end_to_end_measurement_v1 as h
from execution_guard import live_solver_families_v4 as v4


_STATE = h.ROOT / "canonical/astra_runtime/state"


def _cleanup(task_id: str) -> None:
    for path in _STATE.glob(task_id + "__*"):
        if path.is_file():
            path.unlink()


def _run_case(case):
    assert case.expect_pass is True
    task_id = f"TEST_WAVE4_{case.family}_{os.getpid()}"
    try:
        result = admission.solve({"task_id": task_id, "goal": case.goal})
        assert result.get("pass") is True, result
        passed, reason = case.oracle(result)
        assert passed is True, reason
    finally:
        _cleanup(task_id)


def test_wave_four_families_are_registered():
    assert len(v4.GENERATORS_V4) == 6
    assert "DOCX_CREATE" in v4.GENERATORS_V4
    assert "XLSX_CREATE" in v4.GENERATORS_V4
    assert "XLSX_VERIFY" in v4.GENERATORS_V4
    assert "SOURCE_RANKING_BM25" in v4.GENERATORS_V4
    assert "DECISION_SYNTHESIS" in v4.GENERATORS_V4
    assert "PYTHON_SOURCE_AUDIT" in v4.GENERATORS_V4


def test_wave_four_docx_create(brain_tmp: Path):
    _run_case(v4.gen_docx_create(random.Random(42), brain_tmp, 0))


def test_wave_four_xlsx_create(brain_tmp: Path):
    _run_case(v4.gen_xlsx_create(random.Random(43), brain_tmp, 0))


def test_wave_four_xlsx_verify(brain_tmp: Path):
    _run_case(v4.gen_xlsx_verify(random.Random(44), brain_tmp, 0))


def test_wave_four_bm25_ranking(brain_tmp: Path):
    _run_case(v4.gen_bm25_ranking(random.Random(45), brain_tmp, 0))


def test_wave_four_decision_synthesis(brain_tmp: Path):
    _run_case(v4.gen_decision_synthesis(random.Random(46), brain_tmp, 0))


def test_wave_four_python_source_audit(brain_tmp: Path):
    _run_case(v4.gen_python_source_audit(random.Random(47), brain_tmp, 0))


@pytest.fixture
def brain_tmp(tmp_path: Path):
    work = h.ROOT / "canonical/astra_runtime/tmp" / f"test_f4_{tmp_path.name}"
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    yield work
    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
