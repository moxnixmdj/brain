"""Narrowed evidence, whole-corpus acceptance.

Measured on pluggy 3fc9e561, one injected fault at ``_manager.py:247`` producing 7 failing
tests across two files:

* the aggregate corpus (both files)     OPEN, 542-723 s, 1,162 candidates
* ``test_details.py`` alone             OPEN, 231 s, 1,170 candidates
* ``test_pluginmanager.py`` alone       PASS, 12.6 s, first single candidate

The evidence dilutes across files, so each failing file gets its own sub-run. The first
version of that portfolio narrowed the *acceptance* too and produced a 3-test patch in
12.5 s that left the other 3 failures standing -- fast and wrong. These tests pin the
three properties that keep it fast and right: least-ambiguous file first, a slice that can
actually succeed, and the caller's aggregate command kept as the acceptance.
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
CAP = ROOT / "canonical/runtime/bound_capabilities/python_repair_apply_verified_v1.py"


def _cap():
    spec = importlib.util.spec_from_file_location("_brain_apply_under_test_v1", CAP)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_failure_count_is_read_from_the_run_s_own_summary() -> None:
    cap = _cap()
    assert cap._failure_count("3 failed, 223 passed in 0.53s") == 3
    # progress lines come first and must not be mistaken for the total
    assert cap._failure_count("FAILED a.py::t - x\n1 failed, 9 passed") == 1
    # unittest's shape
    assert cap._failure_count("FAILED (failures=2, errors=1)\n") == 0
    assert cap._failure_count("") == 0


def test_the_file_with_the_fewest_failures_is_tried_first() -> None:
    cap = _cap()
    counts = {pathlib.Path("testing/test_details.py"): 4,
              pathlib.Path("testing/test_pluginmanager.py"): 3}
    assert [p.name for p in cap._ordered_failing_files(counts)] == [
        "test_pluginmanager.py", "test_details.py"]


def test_a_tie_falls_back_to_a_stable_order_not_to_dictionary_order() -> None:
    cap = _cap()
    counts = {pathlib.Path("b.py"): 2, pathlib.Path("a.py"): 2}
    assert [p.name for p in cap._ordered_failing_files(counts)] == ["a.py", "b.py"]


def test_a_slice_is_never_below_the_measured_floor() -> None:
    cap = _cap()
    # 12.6 s is what the winning sub-run needed, floor is 15 s
    assert cap._portfolio_slice(1.0, 4) == cap._MIN_SLICE_S
    assert cap._portfolio_slice(120.0, 2) == 60.0
    # a caller who left almost nothing still gets one honest attempt per file
    assert cap._portfolio_slice(0.0, 1) >= cap._MIN_SLICE_S


def test_the_portfolio_sends_the_aggregate_command_and_one_evidence_file() -> None:
    """The property that failed in the first implementation, pinned as source shape.

    ``_guided_repair`` must pass ``argv`` (the caller's whole-corpus command) as
    ``test_argv`` while narrowing only ``test_paths``. Narrowing both is measurably faster
    and measurably wrong, so the two arguments cannot be allowed to travel together.
    """
    text = CAP.read_text(encoding="utf-8")
    assert '"test_argv":group_argv if group_argv is not None else argv,' in text
    assert "attempt=_guided_repair([p],slice_s,argv)" in text
    # and the portfolio must never build a per-file command to accept against
    assert "per_file_argv" not in text
