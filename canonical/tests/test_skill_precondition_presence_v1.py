#!/usr/bin/env python3
"""Tests for `canonical/swe_kernel/skill_precondition_presence_v1.py` and its learn/apply wiring."""
from __future__ import annotations

import pathlib

from canonical.swe_kernel import skill_precondition_presence_v1 as P
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore


def test_present_defect_permits_learning():
    out = P.gate(
        "def f(x):\n    return x <= 10\n",
        "def f(x):\n    return x < 10\n",
        field="comparison_operator",
        accessor=P.comparison_operator,
    )
    assert out["verdict"] == P.PRESENT
    assert out["may_learn"] is True
    assert out["before"] == ("<=",)
    assert out["after"] == ("<",)


def test_absent_defect_is_refused():
    out = P.gate(
        "def f(x):\n    return x < 10\n",
        "def f(x):\n    return x < 20\n",
        field="comparison_operator",
        accessor=P.comparison_operator,
    )
    assert out["verdict"] == P.ABSENT
    assert out["may_learn"] is False
    assert out["reason"] == "OBSERVED_VALUE_UNCHANGED"


def test_partial_read_trap_caught_by_full_comparison_sequence():
    """`x < 10 and y <= 20` -> `x < 10 and y < 20` changes the second comparison, not the first."""
    out = P.gate(
        "def f(x, y):\n    return x < 10 and y <= 20\n",
        "def f(x, y):\n    return x < 10 and y < 20\n",
        field="comparison_operator",
        accessor=P.comparison_operator,
    )
    assert out["verdict"] == P.PRESENT
    assert out["before"] == ("<", "<=")
    assert out["after"] == ("<", "<")


def test_unobservable_when_no_accessor_supplied():
    out = P.gate("x <= 1", "x < 1", field="comparison_operator", accessor=None)
    assert out["verdict"] == P.UNOBSERVABLE
    assert out["may_learn"] is False
    assert out["reason"] == "NO_ACCESSOR"


def test_refused_when_accessor_raises_on_before_or_after():
    def bad_before(text: str):
        if "<=" in text:
            raise RuntimeError("boom_before")
        return text

    def bad_after(text: str):
        if "< " in text:
            raise ValueError("boom_after")
        return text

    out_b = P.gate("x <= 1", "x < 1", field="f", accessor=bad_before)
    assert out_b["verdict"] == P.REFUSED
    assert out_b["may_learn"] is False
    assert "ACCESSOR_RAISED_ON_BEFORE:RuntimeError" in out_b["reason"]

    out_a = P.gate("x <= 1", "x < 1", field="f", accessor=bad_after)
    assert out_a["verdict"] == P.REFUSED
    assert out_a["may_learn"] is False
    assert "ACCESSOR_RAISED_ON_AFTER:ValueError" in out_a["reason"]


def test_cli_exit_code_reflects_may_learn():
    assert P.main(["--before", "x <= 10", "--after", "x < 10"]) == 0
    assert P.main(["--before", "x < 10", "--after", "x < 20"]) == 1


def test_crystallize_code_fix_gates_on_precondition_presence(tmp_path: pathlib.Path):
    store = VerifiedSkillStore(db_path=tmp_path / "p.sqlite", seed=False)
    refused = store.crystallize_code_fix(
        before_snippet="def f(x):\n    return x < 10\n",
        after_snippet="def f(x):\n    return x < 20\n",
        language="python",
        error_class="BOUNDARY",
        precondition_field="comparison_operator",
        precondition_accessor=P.comparison_operator,
    )
    assert refused["crystallized"] is False
    assert refused["reason"] == "PRECONDITION_DEFECT_ABSENT"
    assert store.count() == 0

    accepted = store.crystallize_code_fix(
        before_snippet="def f(x):\n    return x <= 10\n",
        after_snippet="def f(x):\n    return x < 10\n",
        language="python",
        error_class="BOUNDARY",
        precondition_field="comparison_operator",
        precondition_accessor=P.comparison_operator,
    )
    assert accepted["crystallized"] is True
    assert store.count() == 1
