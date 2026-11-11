"""Real-repository repair, and the mechanism it required.

Two things are tested here.

1. The `dunder_identity` mechanism. Upstream markupsafe 54bb00bfaf fixed a crash where
   `s.__class__ is str` was true for proxy objects that report the proxied type, so
   `escape()` took the "already a str" fast path and then called `.replace` on a proxy.
   `type(s)` cannot be spoofed that way. The engine had no rewrite for this bug class, so
   it failed closed on the real repository. The mechanism was added and the test pins it.

2. The instance itself, end to end, with both controls (fixed version green, buggy
   version red). It is skipped when the network is unavailable rather than allowed to
   report a fake pass -- a skipped network test is honest; a mocked one is not.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from canonical.runtime import real_repo_repair_benchmark_v1 as B  # noqa: E402
from canonical.swe_kernel.multistep_repo_closed_loop_solver_v1 import (  # noqa: E402
    _surgical_span_mutations,
)

SRC = (
    "def escape(s):\n"
    "    if s.__class__ is str:\n"
    "        return s\n"
    "    return helper(s)\n"
)


def test_dunder_identity_rewrites_class_attribute_to_type():
    cands = _surgical_span_mutations(SRC, "escape", [2], {"2": 0.5})
    assert cands, "no candidate produced for a __class__ identity check"
    tags = [t for t, _ in cands]
    assert any("dunder_identity" in t for t in tags), tags
    produced = [c for t, c in cands if "dunder_identity" in t][0]
    assert "type(s) is str" in produced
    assert "s.__class__ is str" not in produced


def test_dunder_identity_also_rewrites_the_inverse():
    src = "def f(x):\n    return type(x) is str\n"
    cands = _surgical_span_mutations(src, "f", [2], {"2": 0.5})
    produced = [c for t, c in cands if "dunder_identity" in t]
    assert produced and any("x.__class__ is str" in c for c in produced)


def test_dunder_identity_output_is_valid_python():
    import ast
    for _tag, code in _surgical_span_mutations(SRC, "escape", [2], {"2": 0.5}):
        ast.parse(code)


def test_the_engine_repairs_the_real_upstream_bug_and_the_controls_hold():
    out = B.evaluate()
    r = out["results"][0]
    if not r.get("valid"):
        pytest.skip(f"network unavailable: {r.get('reason')}")
    assert r["verified"] is True
    assert " 0 failed" in r["after_repair"]
    assert r["buggy_control"].endswith("failed") and "0 failed" not in r["buggy_control"]
    assert r["solved"] is True
    assert r["matched_upstream_fix_exactly"] is True
    assert out["trained_parameters"] == 0
    assert out["external_model_calls"] == 0


def test_no_instance_counts_if_its_controls_fail():
    """An instance whose fixed version is red must not be counted as solved."""
    out = B.evaluate()
    for r in out["results"]:
        if r.get("solved"):
            assert r.get("valid") is True
            assert r.get("fixed_control", "0 passed").split()[0] != "0"
            assert r.get("buggy_control", "0 failed").split()[-2] != "0"
