"""Reproducible board regression with independent held-out examples.

The cases below are evaluation fixtures, not repair rules or a runtime lookup.
Each temporary workspace supplies one ordinary authored failing assertion. The
held-out values are not supplied to the repair engine until after publication.
"""
from __future__ import annotations

import importlib.util

import pytest

from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.runtime import creature_runtime_v1 as creature


CASES = [
    ("mul", "def f(a, b):\n    return a * b\n", "f(3, 4)", "7", [((10, 2), 12), ((-3, 5), 2)]),
    ("mod", "def f(a, b):\n    return a % b\n", "f(7, 2)", "3.5", [((9, 2), 4.5), ((-5, 2), -2.5)]),
    ("floordiv", "def f(a, b):\n    return a // b\n", "f(9, 2)", "4.5", [((7, 2), 3.5), ((-5, 2), -2.5)]),
    ("augassign", "def f(a, b):\n    t = 0\n    t += a\n    t -= b\n    return t\n", "f(7, 2)", "9", [((8, 3), 11), ((-3, 5), 2)]),
    ("augassign2", "def f(a, b):\n    t = 1\n    t *= a\n    return t - b\n", "f(3, 1)", "4", [((8, 3), 11), ((-3, 5), 2)]),
    ("whileacc", "def f(n):\n    t = 0\n    while n > 0:\n        t = t - n\n        n = n - 1\n    return t\n", "f(2)", "3", [((4,), 10), ((6,), 21)]),
    ("binop", "def f(a, b):\n    return a - b\n", "f(7, 2)", "9", [((10, 3), 13), ((-3, 5), 2)]),
    ("boolop", "def f(a, b):\n    return a or b\n", "f(1, 5)", "5", [((0, 5), 0), ((4, 6), 6)]),
    ("offbyone", "def f(a):\n    return a - 1\n", "f(3)", "4", [((9,), 10), ((-3,), -2)]),
    ("compreh", "def f(xs, ys):\n    return [x - y for x, y in zip(xs, ys)]\n", "f([7], [2])", "[9]", [(([3, 6], [2, 4]), [5, 10]), (([2, 8], [7, 1]), [9, 9])]),
]


@pytest.mark.skipif(not broker.namespace_broker_available(), reason="confined execution unavailable")
@pytest.mark.parametrize("name,source,call,expected,heldout", CASES, ids=[x[0] for x in CASES])
def test_board_repairs_with_independent_holdout(tmp_path, name, source, call, expected, heldout):
    workspace = tmp_path / "workspace"
    (workspace / "pkg").mkdir(parents=True)
    (workspace / "pkg" / "__init__.py").write_text("")
    module = workspace / "pkg" / "m.py"
    module.write_text(source)
    (workspace / "tests").mkdir()
    (workspace / "tests" / "test_m.py").write_text(
        "from pkg.m import f\n\n" + f"def test_owed():\n    assert {call} == {expected}\n"
    )
    root = tmp_path / "creature"
    root.mkdir()
    result = creature.run_sovereign_board(root, cycles=4, identity="p", life=480, slice_size=480, workspace=workspace)
    steps = [s for s in result["run"].get("steps", []) if str(s.get("work", "")).startswith("repair:")]
    assert any(s.get("accepted_into_world") == ["pkg/m.py"] for s in steps), (name, steps)
    spec = importlib.util.spec_from_file_location("board_fixture", module)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    for args, value in heldout:
        assert loaded.f(*args) == value
