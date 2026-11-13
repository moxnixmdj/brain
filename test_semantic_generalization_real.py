#!/usr/bin/env python3
"""Honest replacement for the old "Problem 2 is completely solved" demonstration.

The former version printed a success banner when a retrieved strategy fired; it did not
assert that the answer matched the current file.  This version pins the bounded contract
that actually shipped: a typed, read-only Python AST adapter follows the current request,
works on an unseen file, and refuses negation.  It does not claim weight updates, sentience,
or general computer use.

Authority: NONE.  Temp directories only.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn

PASS_STATUS = "PASS__TIER0A_TYPED_PYTHON_AST_QUERY"
SOURCE = "class C:\n    def method(self):\n        pass\n\ndef free():\n    if True:\n        pass\n"


def _solve(root: pathlib.Path, goal: str):
    return solve_or_learn(
        goal,
        learn=True,
        cwd=root,
        db_path=root / "skills.sqlite",
        r3_state_path=root / "r3.json",
        allow_tier1_composition=False,
        allow_tier2_learning=False,
        allow_jit_network=False,
        record_open_gap=False,
        confinement_admitted=True,
    )


def test_typed_ast_adapter_answers_the_current_question(tmp_path, monkeypatch):
    root = tmp_path / "ws"
    root.mkdir()
    monkeypatch.setenv("BRAIN_COGNITIVE_STATE_DIR", str(tmp_path / "cognitive"))
    (root / "sample.py").write_text(SOURCE, encoding="utf-8")
    unseen = root / "pkg" / "unseen.py"
    unseen.parent.mkdir()
    unseen.write_text(SOURCE, encoding="utf-8")

    methods = _solve(root, "Count methods in sample.py")
    assert methods["pass"] is True, methods
    assert methods["status"] == PASS_STATUS, methods
    assert methods["answer"] == 1, methods

    transferred = _solve(root, "Count if statements in pkg/unseen.py")
    assert transferred["pass"] is True, transferred
    assert transferred["answer"] == 1, transferred
    assert transferred["from_memory"] is False, transferred

    negated = _solve(root, "Do not count functions in sample.py")
    assert negated["pass"] is False, negated
    assert negated["status"].startswith("FAIL_CLOSED__PYTHON_AST"), negated
