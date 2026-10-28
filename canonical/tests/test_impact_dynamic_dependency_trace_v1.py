# PROJECT_BRAIN
"""Impact selection with a recorded dependency map catches what static import
graphs cannot, and selects (never skips) anything the map does not cover.

Real subprocess traces, real pytest sessions, no mocks.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from canonical.runtime import test_dependency_trace_v1 as trace
from canonical.runtime.bound_capabilities import python_change_impact_testselect as impact

DYNAMIC = '''import sys

def test_dynamic():
    __import__("calc")
    module = sys.modules["".join(("ca", "lc"))]
    assert getattr(module, "".join(("a", "dd")))(2, 3) == 5
'''
UNRELATED = "def test_other():\n    assert 1 + 1 == 2\n"
STATIC = "from calc import add\n\ndef test_static():\n    assert add(2, 3) == 5\n"


def _fixture(root: Path) -> None:
    (root / "src" / "tests").mkdir(parents=True)
    (root / "src" / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (root / "src" / "tests" / "test_dynamic.py").write_text(DYNAMIC)
    (root / "src" / "tests" / "test_other.py").write_text(UNRELATED)
    (root / "src" / "tests" / "test_static.py").write_text(STATIC)


def _select(root: Path, **extra) -> dict:
    args = {"source_root": "src", "changed_paths": ["src/calc.py"], "test_roots": ["src/tests"],
            "output_path": "report.json", **extra}
    impact.run(args, root)
    return json.loads((root / "report.json").read_text())


def test_static_alone_misses_the_dynamic_consumer_and_says_so(tmp_path: Path):
    _fixture(tmp_path)
    report = _select(tmp_path)
    rows = {r["path"]: r for r in report["tests"]}
    assert rows["src/tests/test_static.py"]["selected"] is True
    assert rows["src/tests/test_dynamic.py"]["selected"] is False  # the known static blind spot
    assert report["selection_guarantee"] == "STATIC_HEURISTIC_NOT_A_COMPLETE_TEST_GATE"


def test_traced_map_selects_the_dynamic_consumer_and_not_the_unrelated_test(tmp_path: Path):
    _fixture(tmp_path)
    tests = ["src/tests/test_dynamic.py", "src/tests/test_other.py", "src/tests/test_static.py"]
    t0 = time.monotonic()
    mapping = trace.trace(tmp_path, tests, source_root="src", python_executable=sys.executable)
    seconds = time.monotonic() - t0
    assert all(row["status"] == "TRACED" for row in mapping["tests"].values()), mapping
    assert "src/calc.py" in mapping["tests"]["src/tests/test_dynamic.py"]["files"]
    assert "src/calc.py" not in mapping["tests"]["src/tests/test_other.py"]["files"]
    trace.write_map(tmp_path, "deps.json", mapping)
    report = _select(tmp_path, dependency_map_path="deps.json")
    rows = {r["path"]: r for r in report["tests"]}
    assert rows["src/tests/test_dynamic.py"]["selected"] is True
    assert rows["src/tests/test_dynamic.py"]["reason"].startswith("DYNAMIC_DEPENDENCY_TRACED:src/calc.py")
    assert rows["src/tests/test_static.py"]["selected"] is True
    assert rows["src/tests/test_other.py"]["selected"] is False
    assert rows["src/tests/test_other.py"]["dynamic"] == "NOT_EXECUTED_IN_TRACE"
    assert report["selection_guarantee"].startswith("STATIC_CLOSURE_UNION_TRACED_CALL_SET")
    assert seconds < 30, seconds


def test_untraced_and_stale_entries_fail_closed(tmp_path: Path):
    _fixture(tmp_path)
    mapping = trace.trace(tmp_path, ["src/tests/test_other.py"], source_root="src",
                          python_executable=sys.executable)
    trace.write_map(tmp_path, "deps.json", mapping)
    report = _select(tmp_path, dependency_map_path="deps.json")
    rows = {r["path"]: r for r in report["tests"]}
    assert rows["src/tests/test_dynamic.py"]["reason"] == "NO_DYNAMIC_TRACE_FAIL_CLOSED"
    assert rows["src/tests/test_other.py"]["selected"] is False
    # now the traced test file changes under the map: its entry is stale
    (tmp_path / "src" / "tests" / "test_other.py").write_text(UNRELATED + "\n# edited\n")
    report = _select(tmp_path, dependency_map_path="deps.json")
    rows = {r["path"]: r for r in report["tests"]}
    assert rows["src/tests/test_other.py"]["selected"] is True
    assert rows["src/tests/test_other.py"]["reason"] == "DYNAMIC_TRACE_STALE_FAIL_CLOSED"


def test_a_failing_or_erroring_test_is_still_traced_not_trusted_blindly(tmp_path: Path):
    _fixture(tmp_path)
    (tmp_path / "src" / "tests" / "test_broken.py").write_text("import nonexistent_module_xyz\n")
    mapping = trace.trace(tmp_path, ["src/tests/test_broken.py"], source_root="src",
                          python_executable=sys.executable)
    row = mapping["tests"]["src/tests/test_broken.py"]
    assert row["status"] != "TRACED"  # collection error -> pytest exit 2
    trace.write_map(tmp_path, "deps.json", mapping)
    report = _select(tmp_path, dependency_map_path="deps.json")
    rows = {r["path"]: r for r in report["tests"]}
    assert rows["src/tests/test_broken.py"]["selected"] is True
    assert rows["src/tests/test_broken.py"]["reason"].startswith("DYNAMIC_TRACE_INCOMPLETE_FAIL_CLOSED")
