"""The long-horizon tasks, run by pytest and judged on final state alone.

This file is a thin runner: it executes `canonical/tests/programs/long_horizon_v1.py` in a fresh
temporary world and asserts that every task ends in the state the task named. The tasks themselves are
kept in `programs/` because they are a benchmark, not a unit test, and running them as a subprocess keeps
their environment isolated from this process's.

Why these tasks exist at all: OSWorld 2.0 (arXiv 2606.29537, June 2026) reports 20.6% strict completion
for the best agent and names the failures as long-horizon state, error repair, implicit-state inference
and *dynamic environment*. The suite here tests exactly those four, and none of the existing suites does.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PROGRAM = _ROOT / "canonical/tests/programs/long_horizon_v1.py"


def test_every_long_horizon_task_ends_in_the_state_it_named() -> None:
    result = subprocess.run([sys.executable, str(_PROGRAM)], capture_output=True, text=True,
                            cwd=str(_PROGRAM.parent), timeout=600)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "5/5 long-horizon tasks pass" in result.stdout, result.stdout
