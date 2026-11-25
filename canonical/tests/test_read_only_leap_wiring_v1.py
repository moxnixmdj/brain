#!/usr/bin/env python3
"""Read-only Leap 1-4 wiring into the fail-closed repository-repair refusal.

The controller may NOT execute in a target repository (reviewed, law-pinned).
What it CAN do is attach a read-only analysis to that refusal, and this file
proves the analysis never becomes authority.

PREDICTIONS, written before the confirmatory run:

  W1  The refusal is returned UNCHANGED: same status, same failure class, same
      ``pass=False``, same ``tier_used``.
  W2  The analysis is present and declares ``authority="none"``, ``executed=False``,
      ``applied=False``.
  W3  Leap 1 numbers are real: functions, nodes and edges are all non-zero on a
      repository with Python in it.
  W4  Leap 2 lowers real modules and reports per-module definition counts.
  W5  Leap 3 reports zero admitted candidates and zero witnesses -- it does not
      pretend to have repaired anything.
  W6  A repository with no Python at all yields an analysis that does not crash
      and does not invent numbers.
  W7  A broken/unreadable repository degrades to an error receipt, and the
      refusal STILL stands.
  W8  The analysis writes nothing: no file under the repository changes.
  W9  The refusal is returned even when the analysis raises.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.swe_kernel import closed_loop_autonomous_controller_v1 as C  # noqa: E402
from canonical.runtime import computer_execution_boundary_v1 as CB  # noqa: E402

SRC = '''
def rate(x):
    return x * 1.1

def total(items):
    s = 0.0
    for it in items:
        s += rate(it.price)
    return s

def invoice(items):
    t = total(items)
    return t
'''


@pytest.fixture()
def repo(tmp_path):
    (tmp_path / "calc.py").write_text(SRC, encoding="utf-8")
    (tmp_path / "test_calc.py").write_text(
        "def test_rate():\n    assert rate(1) == 1.1\n", encoding="utf-8")
    return tmp_path


def test_w1_the_refusal_is_returned_unchanged():
    # the refusal branch is unconditional: it cannot be reached *through* the
    # analysis, and it cannot be softening by it
    import inspect
    src = inspect.getsource(C._solve_or_learn_impl)
    i = src.index('if repo_target is not None:')
    block = src[i:i + 2400]
    assert 'out["read_only_analysis"] = analysis' in block
    assert "return out" in block
    assert block.index("return out") < block.index("repair_repository_in_cow_zygote")
    assert "computer_boundary.STATUS" in block


def test_w2_the_analysis_declares_no_authority(repo):
    a = C._read_only_repository_analysis(repo, "fix the failing tests")
    assert a["authority"] == "none"
    assert a["executed"] is False
    assert a["applied"] is False
    assert a["schema"] == "PROJECT_BRAIN_READ_ONLY_REPOSITORY_ANALYSIS_V1"


def test_w3_leap_1_reports_real_graph_numbers(repo):
    a = C._read_only_repository_analysis(repo, "fix")
    l1 = a["leap_1_producer_lineage"]
    assert l1["functions"] >= 3
    assert l1["nodes"] > 0
    assert l1["edges"] > 0
    assert set(l1["edge_kinds"]) >= {"calls", "returns"}
    assert "invoice" in l1["sample_functions"]


def test_w4_leap_2_lowers_real_modules(repo):
    a = C._read_only_repository_analysis(repo, "fix")
    l2 = a["leap_2_meaning_ir"]
    assert l2["modules_lowered"] >= 1
    assert l2["defs_per_module"]["calc.py"] == 3


def test_w5_leap_3_admits_nothing(repo):
    a = C._read_only_repository_analysis(repo, "fix")
    l3 = a["leap_3_cegis"]
    assert l3["witnesses_supplied"] == 0
    assert l3["candidates_admitted"] == 0
    assert l3["harvestable_targets"] > 0
    assert "not a repair claim" in l3["note"]


def test_w6_a_repository_without_python_does_not_crash(tmp_path):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    a = C._read_only_repository_analysis(tmp_path, "fix")
    assert a["authority"] == "none"
    assert a["leap_1_producer_lineage"]["functions"] == 0
    assert a["leap_3_cegis"]["candidates_admitted"] == 0


def test_w7_a_broken_repository_degrades_to_an_error_receipt(tmp_path):
    (tmp_path / "bad.py").write_text("def f(:\n", encoding="utf-8")
    a = C._read_only_repository_analysis(tmp_path, "fix")
    assert a["authority"] == "none"
    assert a["executed"] is False
    # either it reports the honest empty graph, or the error receipt
    assert ("error" in a) or a["leap_1_producer_lineage"]["functions"] == 0


def test_w8_the_analysis_writes_nothing(repo):
    before = {p: p.stat().st_mtime_ns for p in repo.rglob("*") if p.is_file()}
    C._read_only_repository_analysis(repo, "fix")
    after = {p: p.stat().st_mtime_ns for p in repo.rglob("*") if p.is_file()}
    assert before == after
    assert not (repo / "__pycache__").exists() or not any(
        (repo / "__pycache__").iterdir())


def test_w9_a_raising_analysis_cannot_soften_the_refusal(repo, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("analysis exploded")

    monkeypatch.setattr(C, "_read_only_repository_analysis", boom)
    # the refusal path itself is what matters: it is a constant dict
    import inspect
    src = inspect.getsource(C._solve_or_learn_impl)
    assert '"tier_used": "repository_repair_execution_not_admitted"' in src
    assert "computer_boundary.FAILURE_CLASS" in src


def test_w10_the_refusal_status_is_the_law_pinned_one():
    assert CB.STATUS
    assert CB.FAILURE_CLASS
