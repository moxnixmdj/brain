#!/usr/bin/env python3
"""Tests for the batched/streaming oracle judge.

Everything here was found by a failure in a real run. Each test pins the property that
failure violated:

  * a batched verdict must agree with pytest;
  * a candidate that hangs must not cost the item its correct answer;
  * streaming must return a pass that occurred BEFORE a later hang;
  * the per-candidate allowance must never exceed the worker budget.
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import batched_oracle_v1 as B  # noqa: E402

STUB = "import sympy\n\ndef custom_totient(n: int) -> int:\n    return "
TESTS = """
import unittest
from sample_1 import custom_totient

class T(unittest.TestCase):
    def test_phi(self):
        self.assertEqual(custom_totient(12), 4)
"""


@pytest.mark.parametrize("body,expected", [
    ("sympy.totient(n)", True),
    ("n", False),
    ("1", False),
    ("sympy.primepi(n)", False),
])
def test_stream_verdicts(body, expected):
    hit = B.judge_stream(sys.executable, STUB, TESTS, [body], timeout=60,
                         test_path="/tmp/sample_1/hidden.py", per_body_seconds=3)
    if expected:
        assert hit is not None and hit["passed"] is True
        assert hit["body"] == body
    else:
        assert hit is None


def test_stream_finds_the_pass_at_the_right_index():
    bodies = ["n", "1", "sympy.totient(n)", "sympy.primepi(n)"]
    hit = B.judge_stream(sys.executable, STUB, TESTS, bodies, timeout=60,
                         test_path="/tmp/sample_1/hidden.py", per_body_seconds=3)
    assert hit is not None
    assert hit["index"] == 2
    assert hit["body"] == "sympy.totient(n)"


def test_a_hanging_candidate_does_not_cost_the_item():
    """`sympy.prime(10**9)` does not return; the good candidate after it still must."""
    bodies = ["sympy.prime(10**9)", "sympy.totient(n)"]
    hit = B.judge_stream(sys.executable, STUB, TESTS, bodies, timeout=90,
                         test_path="/tmp/sample_1/hidden.py", per_body_seconds=1)
    assert hit is not None, "a hang before the answer destroyed the item"
    assert hit["body"] == "sympy.totient(n)"


def test_allowance_never_exceeds_the_budget():
    """60 candidates at 5s each is 300s of allowance; it must be bounded by the budget."""
    import inspect
    src = inspect.getsource(B.judge_many)
    assert "allowance" in src
    assert "min(int(per_body_seconds), allowance)" in src


def test_empty_body_list_is_handled():
    assert B.judge_stream(sys.executable, STUB, TESTS, [], timeout=30,
                          test_path="/tmp/sample_1/hidden.py") is None


def test_judge_many_parses_the_streamed_format():
    """The worker streams `@@@` lines. The batch parser once looked for `[` and returned
    worker_failed for EVERY batch -- a silent total failure of the batched path."""
    verdicts = B.judge_many(sys.executable, STUB, TESTS,
                            ["n", "sympy.totient(n)", "1"], timeout=60,
                            test_path="/tmp/sample_1/hidden.py", per_body_seconds=3)
    assert len(verdicts) == 3
    assert [v["passed"] for v in verdicts] == [False, True, False]
    assert all(v["why"] != "worker_failed" for v in verdicts)


def test_judge_many_never_silently_reports_worker_failed_for_a_valid_run():
    verdicts = B.judge_many(sys.executable, STUB, TESTS, ["sympy.totient(n)"],
                            timeout=60, test_path="/tmp/sample_1/hidden.py",
                            per_body_seconds=3)
    assert verdicts[0]["passed"] is True
    assert verdicts[0]["why"] == "ok"


def test_module_name_handles_both_import_forms():
    """sympy tests use `from sample_N import f`; networkx tests use `import sample_N`.
    Only the first was handled, so every networkx item returned worker_failed."""
    assert B._module_name("from sample_33 import get_nodes\n") == "sample_33"
    assert B._module_name("import sample_33\n") == "sample_33"
    assert B._module_name("import os\nimport sample_7\n") == "sample_7"
    assert B._module_name("import os\n") == ""

NETWORKX_STUB = "import networkx as nx\ndef get_nodes(G:nx.Graph) -> list:\n   return "
NETWORKX_TESTS = """
import unittest
import networkx as nx
import sample_1

class T(unittest.TestCase):
    def test_nodes(self):
        G = nx.path_graph(3)
        self.assertEqual(sorted(sample_1.get_nodes(G)), [0, 1, 2])
"""


def test_module_attribute_import_style_runs():
    """The mock module must expose the function for `sample_N.f(...)` as well as `f`."""
    hit = B.judge_stream(sys.executable, NETWORKX_STUB, NETWORKX_TESTS,
                         ["list(G.nodes)"], timeout=90,
                         test_path="/tmp/sample_1/hidden.py", per_body_seconds=3)
    assert hit is not None and hit["passed"] is True
