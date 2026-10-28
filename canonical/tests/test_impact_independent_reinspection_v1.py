# PROJECT_BRAIN
"""Independent impact acceptance must not trust an incomplete producer ledger."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from canonical.runtime import live_brain_route_admission_v1 as admission
from canonical.runtime import raw_goal_trace_acceptance_v1 as acceptance
from canonical.runtime.bound_capabilities import python_change_impact_testselect as impact

ROOT = Path(__file__).resolve().parents[2]
DYNAMIC = '''import importlib

def test_dynamic():
    module = importlib.import_module("calc")
    assert getattr(module, "".join(("a", "dd")))(2, 3) == 5
'''


def _fixture(root: Path, tests: dict[str, str]) -> None:
    (root / "src" / "tests").mkdir(parents=True)
    (root / "src" / "calc.py").write_text("def add(a, b):\n    return a - b\n")
    for name, text in tests.items():
        (root / "src" / "tests" / name).write_text(text)


def _produce(root: Path, changed: str = "src/calc.py") -> tuple[dict, dict]:
    args = {"source_root": "src", "changed_paths": [changed],
            "test_roots": ["src/tests"], "output_path": "report.json"}
    return args, impact.run(args, root)


def test_dynamic_omission_cannot_pass_independent_acceptance(tmp_path: Path):
    _fixture(tmp_path, {"test_dynamic.py": DYNAMIC})
    args, result = _produce(tmp_path)
    assert result["selected_test_count"] == 0
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["selection_guarantee"] == "STATIC_HEURISTIC_NOT_A_COMPLETE_TEST_GATE"

    ok, reason, _ = acceptance._inspect_change_impact_testselect(args, result, tmp_path)

    assert not ok
    assert "DYNAMIC" in reason


def test_dynamic_dependency_through_a_helper_cannot_be_omitted(tmp_path: Path):
    _fixture(tmp_path, {"test_helper.py": "from bridge import call\ndef test_call(): assert call() == 5\n"})
    (tmp_path / "src" / "bridge.py").write_text('''import importlib

def call():
    module = importlib.import_module("calc")
    return getattr(module, "add")(2, 3)
''')
    args, result = _produce(tmp_path)
    assert result["selected_test_count"] == 0

    ok, reason, _ = acceptance._inspect_change_impact_testselect(args, result, tmp_path)

    assert not ok
    assert "DYNAMIC" in reason


def test_dynamic_pytest_conftest_cannot_be_omitted(tmp_path: Path):
    _fixture(tmp_path, {"test_fixture.py": "def test_answer(answer): assert answer == 5\n"})
    (tmp_path / "src" / "tests" / "conftest.py").write_text('''import importlib
import pytest

@pytest.fixture
def answer():
    return getattr(importlib.import_module("calc"), "add")(2, 3)
''')
    args, result = _produce(tmp_path)
    assert result["selected_test_count"] == 0

    ok, reason, _ = acceptance._inspect_change_impact_testselect(args, result, tmp_path)

    assert not ok
    assert "DYNAMIC" in reason


def test_builtins_import_indirection_cannot_be_omitted(tmp_path: Path):
    _fixture(tmp_path, {"test_dynamic.py": '''def test_dynamic():
    module = __builtins__["__import__"]("calc")
    assert module.__dict__["add"](2, 3) == 5
'''})
    args, result = _produce(tmp_path)
    assert result["selected_test_count"] == 0

    ok, reason, _ = acceptance._inspect_change_impact_testselect(args, result, tmp_path)

    assert not ok
    assert "DYNAMIC" in reason


def test_inspector_rechecks_candidate_files_on_disk_not_just_producer_counts(tmp_path: Path):
    _fixture(tmp_path, {})
    args, result = _produce(tmp_path)
    assert result["candidate_test_count"] == 0
    (tmp_path / "src" / "tests" / "test_new.py").write_text(
        "from calc import add\ndef test_add(): assert add(2, 3) == 5\n")

    ok, reason, _ = acceptance._inspect_change_impact_testselect(args, result, tmp_path)

    assert not ok
    assert "CANDIDATE" in reason


def test_ignored_non_python_change_cannot_be_semantically_accepted(tmp_path: Path):
    _fixture(tmp_path, {"test_config.py": '''import json
from pathlib import Path

def test_config():
    value = json.loads((Path(__file__).parents[1] / "config.json").read_text())
    assert value["enabled"] is True
'''})
    (tmp_path / "src" / "config.json").write_text('{"enabled": false}')
    args, result = _produce(tmp_path, "src/config.json")
    assert result["ignored_non_python_count"] == 1
    assert result["selected_test_count"] == 0

    ok, reason, _ = acceptance._inspect_change_impact_testselect(args, result, tmp_path)

    assert not ok
    assert "NON_PYTHON" in reason


def test_a_change_outside_the_indexed_source_root_cannot_be_accepted(tmp_path: Path):
    _fixture(tmp_path, {"test_calc.py": "from calc import add\ndef test_it(): assert add(2,3)==5\n"})
    (tmp_path / "external.py").write_text("def external(): return 1\n")
    args = {"source_root": "src", "changed_paths": ["src/calc.py", "external.py"],
            "test_roots": ["src/tests"], "output_path": "report.json"}
    result = impact.run(args, tmp_path)
    assert result["unknown_symbol_module_count"] == 1
    assert result["selected_test_count"] == 1

    ok, reason, _ = acceptance._inspect_change_impact_testselect(args, result, tmp_path)

    assert not ok
    assert reason == "IMPACT_CHANGED_OUTSIDE_SOURCE_ROOT"


def test_correct_transitive_import_selection_can_be_independently_accepted(tmp_path: Path):
    _fixture(tmp_path, {"test_bridge.py": '''from bridge import compute

def test_compute():
    assert compute(2, 3) == 5
'''})
    (tmp_path / "src" / "bridge.py").write_text(
        "from calc import add\ndef compute(a, b):\n    return add(a, b)\n")
    args, result = _produce(tmp_path)
    assert result["selected_test_count"] == 1

    ok, reason, _ = acceptance._inspect_change_impact_testselect(args, result, tmp_path)

    assert ok, reason


def test_inspector_rejects_a_forged_omitted_transitive_test(tmp_path: Path):
    _fixture(tmp_path, {"test_bridge.py": "from bridge import compute\ndef test_it(): assert compute(2,3)==5\n"})
    (tmp_path / "src" / "bridge.py").write_text(
        "from calc import add\ndef compute(a, b): return add(a, b)\n")
    args, result = _produce(tmp_path)
    assert result["selected_test_count"] == 1
    report = json.loads((tmp_path / "report.json").read_text())
    report["selected_tests"] = []
    report["totals"]["selected_tests"] = 0
    report["tests"][0]["selected"] = False
    (tmp_path / "report.json").write_text(json.dumps(report))
    result["selected_test_count"] = 0

    ok, reason, _ = acceptance._inspect_change_impact_testselect(args, result, tmp_path)

    assert not ok
    assert "OMITTED" in reason


def test_inspector_checks_changed_paths_against_original_request(tmp_path: Path):
    _fixture(tmp_path, {"test_calc.py": "from calc import add\ndef test_it(): assert add(2,3)==5\n"})
    (tmp_path / "src" / "other.py").write_text("def unrelated(): return 1\n")
    args, result = _produce(tmp_path)
    report = json.loads((tmp_path / "report.json").read_text())
    report["changed_files"] = ["src/other.py"]
    report["selected_tests"] = []
    report["totals"]["selected_tests"] = 0
    report["tests"][0]["selected"] = False
    report["tests"][0]["reason"] = "UNAFFECTED"
    (tmp_path / "report.json").write_text(json.dumps(report))
    result["selected_test_count"] = 0

    ok, reason, _ = acceptance._inspect_change_impact_testselect(args, result, tmp_path)

    assert not ok
    assert "CHANGED" in reason


def test_live_impact_goal_does_not_accept_a_dynamic_omission():
    with tempfile.TemporaryDirectory(prefix=".impact_fixture_", dir=ROOT) as tmp:
        root = Path(tmp)
        _fixture(root, {"test_dynamic.py": DYNAMIC})
        goal = ("Show which tests are affected by a change to "
                f"{root / 'src' / 'calc.py'} and write the report to {root / 'report.json'}")
        result = admission.solve({"task_id": "dynamic-impact-regression", "goal": goal}) or {}
        assert result.get("pass") is False, result
        assert result.get("semantic_acceptance_complete") is False, result
        assert result.get("unverified_reason") == "IMPACT_DYNAMIC_DEPENDENCY_OMITTED", result
        assert not (root / "report.json").exists()
