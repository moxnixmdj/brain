"""Multi-file SWE repair, with controls.

The controls are the point. A repair benchmark without a clean control measures nothing:
a case whose "clean" version also fails is not a bug, it is a broken test. And a repair
that only edits the test file is a false success, which is a failure mode this tree has
already recorded against itself.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import swe_repair_benchmark_v1 as B  # noqa: E402


def test_every_case_has_a_clean_control():
    for case in B.CASES:
        assert case.get("clean"), f"{case['id']} has no clean version to prove it is a bug"
        assert case.get("tests"), f"{case['id']} has no failing test"


def test_the_clean_control_passes_and_the_bug_fails():
    import tempfile
    import shutil
    from pathlib import Path as P
    for case in B.CASES:
        base = P(tempfile.mkdtemp())
        try:
            d = base / "c"
            d.mkdir()
            B._materialise(case, d)
            for rel, src in case["clean"].items():
                (d / rel).write_text(src)
            cp, cf = B._run_tests(d)
            assert cf == 0 and cp > 0, f"{case['id']} clean control fails"
            b = base / "b"
            b.mkdir()
            B._materialise(case, b)
            bp, bf = B._run_tests(b)
            assert bf > 0, f"{case['id']} bug does not fail"
        finally:
            shutil.rmtree(base, ignore_errors=True)


def test_the_engine_repairs_every_case_and_verifies_it():
    out = B.evaluate()
    assert out["valid_cases"] == out["cases"], "a case was invalid; the control rejected it"
    assert out["solved"] >= 1, "the engine repaired nothing"
    for r in out["results"]:
        assert r["verified"] is True
        assert " 0 failed" in r["after_repair"]


def test_repair_costs_no_model_call_and_no_money():
    out = B.evaluate()
    assert out["trained_parameters"] == 0
    assert out["external_model_calls"] == 0
    assert out["incremental_spend_usd"] == 0
