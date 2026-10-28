# PROJECT_BRAIN
"""A PR intent must not use a static impact slice as proof of a green suite.

These are real pytest runs against staged copies, not mocked test results.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orch

ROOT = Path(__file__).resolve().parents[2]
CAPABILITY = "python.software.issue_to_pr.orchestrate.v1"

DYNAMIC_TEST = '''import importlib

def test_dynamic_add():
    calc = importlib.import_module("calc")
    add = getattr(calc, "".join(("a", "dd")))
    assert add(2, 3) == 5
'''
STATIC_TEST = '''from calc import add

def test_static_add():
    assert add(2, 3) == 5
'''


def _fixture(root: Path, tests: dict[str, str]) -> None:
    (root / "src" / "tests").mkdir(parents=True)
    (root / "src" / "calc.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8")
    for name, contents in tests.items():
        (root / "src" / "tests" / name).write_text(contents, encoding="utf-8")
    (root / "task.json").write_text(json.dumps({
        "issue_id": "DYNAMIC-1", "title": "Rename add to sum_values",
        "edits": [{"op": "rename_symbol", "module": "calc.py",
                   "name": "add", "new_name": "sum_values"}],
    }), encoding="utf-8")


def _args(prefix: str = "") -> dict:
    def path(name: str) -> str:
        return str(Path(prefix) / name)
    return {
        "task_path": path("task.json"), "source_root": path("src"),
        "worktree_path": path("worktree"), "output_path": path("out/summary.json"),
        "diff_path": path("out/change.diff"), "pr_intent_path": path("out/pr.json"),
        "python_executable": sys.executable, "timeout_s": 30,
    }


def _intent(root: Path) -> dict:
    return json.loads((root / "out" / "pr.json").read_text(encoding="utf-8"))


def _pytest(root: Path, test_file: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", test_file],
        cwd=root, text=True, capture_output=True, timeout=30,
    )


def test_dynamic_import_regression_cannot_be_green_with_empty_impact_slice(tmp_path: Path):
    _fixture(tmp_path, {"test_dynamic.py": DYNAMIC_TEST})
    assert _pytest(tmp_path / "src", "tests/test_dynamic.py").returncode == 0

    result = orch.run(_args(), tmp_path)

    assert result["edits_verified"] is True
    assert result["test_selected_count"] == 0
    assert _pytest(tmp_path / "worktree", "tests/test_dynamic.py").returncode != 0
    assert result["verified"] is False
    assert result["test_failed_count"] == 1
    tests = _intent(tmp_path)["body"]["tests"]
    assert tests["discovered_files"] == 1
    assert tests["pytest_rc"] != 0
    assert tests["scope"] == "conventional_test_files_under_source_root"
    assert (tmp_path / "src" / "calc.py").read_text(encoding="utf-8").startswith("def add(")


def test_unselected_dynamic_failure_is_caught_even_when_selected_tests_pass(tmp_path: Path):
    _fixture(tmp_path, {"test_dynamic.py": DYNAMIC_TEST, "test_static.py": STATIC_TEST})
    assert _pytest(tmp_path / "src", "tests").returncode == 0

    result = orch.run(_args(), tmp_path)

    assert result["test_selected_count"] == 1
    assert result["test_passed_count"] == 1
    assert result["test_failed_count"] == 1
    assert result["verified"] is False
    assert _intent(tmp_path)["body"]["tests"]["discovered_files"] == 2


def test_full_conventional_suite_passes_once_including_unselected_tests(tmp_path: Path):
    _fixture(tmp_path, {
        "test_static.py": STATIC_TEST,
        "test_unrelated.py": "def test_unrelated():\n    assert 'brain'.upper() == 'BRAIN'\n",
    })

    result = orch.run(_args(), tmp_path)

    assert result["verified"] is True
    assert result["test_selected_count"] == 1
    assert result["test_passed_count"] == 2
    assert result["test_failed_count"] == 0
    tests = _intent(tmp_path)["body"]["tests"]
    assert tests["discovered_files"] == 2
    assert tests["reported_cases"] == 2
    assert tests["pytest_rc"] == 0
    assert tests["status"] == "PASSED"
    assert not list((tmp_path / "worktree").glob(".orchestrate_verified_*"))


def test_pytest_testpaths_cannot_hide_another_discovered_directory(tmp_path: Path):
    _fixture(tmp_path, {"test_static.py": STATIC_TEST})
    extra = tmp_path / "src" / "other_tests"
    extra.mkdir()
    (extra / "test_dynamic.py").write_text(DYNAMIC_TEST)
    (tmp_path / "src" / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")

    result = orch.run(_args(), tmp_path)

    assert result["test_selected_count"] == 1
    assert result["verified"] is False
    tests = _intent(tmp_path)["body"]["tests"]
    assert tests["discovered_files"] == 2
    assert tests["failed"] == 1


def test_pytest_ignore_cannot_hide_a_discovered_failure(tmp_path: Path):
    _fixture(tmp_path, {"test_dynamic.py": DYNAMIC_TEST, "test_static.py": STATIC_TEST})
    (tmp_path / "src" / "pytest.ini").write_text(
        "[pytest]\naddopts = --ignore=tests/test_dynamic.py\n")

    result = orch.run(_args(), tmp_path)

    assert result["verified"] is False
    tests = _intent(tmp_path)["body"]["tests"]
    assert tests["pytest_rc"] == 0
    assert tests["uncollected_files"] == 1
    assert tests["status"] == "UNCOLLECTED_TEST_FILES"
    assert tests["uncollected_examples"] == ["tests/test_dynamic.py"]


def test_pytest_deselection_cannot_hide_an_unselected_failure(tmp_path: Path):
    _fixture(tmp_path, {"test_dynamic.py": DYNAMIC_TEST, "test_static.py": STATIC_TEST})
    (tmp_path / "src" / "pytest.ini").write_text("[pytest]\naddopts = -k test_static\n")

    result = orch.run(_args(), tmp_path)

    assert result["test_passed_count"] == 1
    assert result["verified"] is False
    tests = _intent(tmp_path)["body"]["tests"]
    assert tests["pytest_rc"] == 0
    assert tests["deselected"] == 1
    assert tests["status"] == "DESELECTED_TESTS"


def test_plugin_removing_tests_without_deselection_event_cannot_hide_failure(tmp_path: Path):
    _fixture(tmp_path, {"test_dynamic.py": DYNAMIC_TEST, "test_static.py": STATIC_TEST})
    (tmp_path / "src" / "tests" / "conftest.py").write_text('''def pytest_collection_modifyitems(items):
    items[:] = [item for item in items if "test_dynamic" not in item.nodeid]
''')

    result = orch.run(_args(), tmp_path)

    assert result["verified"] is False
    tests = _intent(tmp_path)["body"]["tests"]
    assert tests["pytest_rc"] == 0
    assert tests["deselected"] == 1
    assert tests["status"] == "DESELECTED_TESTS"


def test_collection_error_is_counted_as_a_failed_test(tmp_path: Path):
    _fixture(tmp_path, {"test_collection_error.py": "raise RuntimeError('collection failed')\n"})

    result = orch.run(_args(), tmp_path)

    assert result["verified"] is False
    assert result["test_failed_count"] == 1
    tests = _intent(tmp_path)["body"]["tests"]
    assert tests["status"] == "FAILED"
    assert tests["pytest_rc"] != 0


def test_unavailable_runner_cannot_verify_a_pr(tmp_path: Path):
    _fixture(tmp_path, {"test_static.py": STATIC_TEST})
    args = _args()
    args["python_executable"] = str(tmp_path / "no-such-python")

    result = orch.run(args, tmp_path)

    assert result["edits_verified"] is True
    assert result["verified"] is False
    assert result["test_pytest"] == "UNAVAILABLE"
    assert _intent(tmp_path)["body"]["tests"]["status"] == "PYTEST_UNAVAILABLE"


def test_timeout_cannot_verify_a_pr(tmp_path: Path):
    _fixture(tmp_path, {"test_hang.py": "import time\ntime.sleep(5)\ndef test_it(): assert time.time() > 0\n"})
    args = _args()
    args["timeout_s"] = 2

    result = orch.run(args, tmp_path)

    assert result["verified"] is False
    assert _intent(tmp_path)["body"]["tests"]["status"] == "TIMEOUT"


def test_pr_loop_reuses_a_fresh_index_cache(tmp_path: Path):
    from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer

    _fixture(tmp_path, {"test_static.py": STATIC_TEST})
    indexer.run({"source_root": ".", "output_path": "cache.json"}, tmp_path / "src")
    args = _args()
    args["index_path"] = "src/cache.json"

    result = orch.run(args, tmp_path)

    assert result["verified"] is True
    assert result["test_passed_count"] == 1


def test_pr_loop_refuses_a_cache_missing_new_tests(tmp_path: Path, capsys):
    from canonical.runtime.bound_capabilities import python_source_symbol_index as indexer

    _fixture(tmp_path, {"test_static.py": STATIC_TEST})
    indexer.run({"source_root": ".", "output_path": "cache.json"}, tmp_path / "src")
    (tmp_path / "src" / "tests" / "test_new.py").write_text(DYNAMIC_TEST)
    args = _args()
    args["index_path"] = "src/cache.json"

    with pytest.raises(SystemExit):
        orch.run(args, tmp_path)
    assert "INDEX_CACHE_STALE" in capsys.readouterr().out
    assert (tmp_path / "src" / "calc.py").read_text(encoding="utf-8").startswith("def add(")


def test_no_test_files_cannot_verify_a_pr(tmp_path: Path):
    _fixture(tmp_path, {})

    result = orch.run(_args(), tmp_path)

    assert result["edits_verified"] is True
    assert result["test_selected_count"] == 0
    assert result["verified"] is False
    tests = _intent(tmp_path)["body"]["tests"]
    assert tests["discovered_files"] == 0
    assert tests["pytest_rc"] is None
    assert tests["status"] == "NO_TEST_FILES"


def test_all_skipped_tests_cannot_verify_a_pr(tmp_path: Path):
    _fixture(tmp_path, {"test_skip.py": '''import pytest

@pytest.mark.skip(reason="not executed")
def test_skipped():
    assert False
'''})

    result = orch.run(_args(), tmp_path)

    assert result["verified"] is False
    tests = _intent(tmp_path)["body"]["tests"]
    assert tests["pytest_rc"] == 0
    assert tests["skipped"] == 1
    assert tests["passed"] == 0
    assert tests["status"] == "NO_PASSED_TESTS"


def test_more_than_five_thousand_test_files_are_not_silently_truncated(tmp_path: Path):
    # Real pytest collection: the only failure is beyond the shared helper's
    # default 5,000-file cap. Directory collection must remain practical.
    for number in range(5002):
        text = ""
        if number == 0:
            text = "def test_first(): assert 'ready'.upper() == 'READY'\n"
        elif number == 5001:
            text = "def test_last(): assert 'wrong'.upper() == 'READY'\n"
        (tmp_path / f"test_{number:05}.py").write_text(text)

    evidence = orch._run_worktree_tests(tmp_path, sys.executable, pytest.__version__, 45)

    assert evidence["discovered_files"] == 5002
    assert evidence["uncollected_files"] == 0
    assert evidence["passed"] == 1
    assert evidence["failed"] == 1
    assert evidence["status"] == "FAILED"


def test_live_adapter_dispatch_rejects_broken_dynamic_change():
    # The live dispatcher confines inputs to ROOT. Use a real temporary fixture
    # under it and remove it afterwards, rather than replacing the dispatcher.
    from canonical.runtime import live_brain_route_admission_v1 as admission

    with tempfile.TemporaryDirectory(prefix=".issue_to_pr_fixture_", dir=ROOT) as tmp:
        root = Path(tmp)
        _fixture(root, {"test_dynamic.py": DYNAMIC_TEST})
        relative = str(root.relative_to(ROOT))
        registry = json.loads((ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json")
                              .read_text(encoding="utf-8"))["capabilities"]
        action = {
            "type": "invoke_capability",
            "args": {**_args(relative), "capability_id": CAPABILITY},
            "expect": {"type": "field_equals", "field": "verified", "value": True},
        }
        with pytest.raises(admission.LocalExecutionFailure, match="ACTION_EXPECTATION_FAILED:verified"):
            admission.run_adapter_locally(registry[CAPABILITY], action)
        assert _intent(root)["body"]["tests"]["pytest_rc"] != 0
