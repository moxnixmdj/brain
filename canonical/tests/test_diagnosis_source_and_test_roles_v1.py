"""Source and test roles remain distinct when diagnosis consumes both."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from canonical.runtime import declared_input_derivation_v1 as derivation
from canonical.runtime.bound_capabilities._swe_static_soundness_v1 import load_active_bound_registry

ROOT = Path(__file__).resolve().parents[2]
CID = "python.fault.localize.dynamic.dataflow.v1"


def tree(root, tests="tests", initializer=True):
    app = root / "proj/app"
    app.mkdir(parents=True)
    (app / "__init__.py").write_text("")
    (app / "core.py").write_text("def buggy(x):\n    return x - 1\n")
    suite = root / f"proj/{tests}"
    suite.mkdir()
    if initializer:
        (suite / "__init__.py").write_text("")
    (suite / "test_core.py").write_text(
        "import unittest\nfrom app.core import buggy\nclass T(unittest.TestCase):\n"
        "    def test_value(self):\n        self.assertEqual(buggy(2), 3)\n")
    return app, suite


@pytest.mark.parametrize("initializer", [False, True])
@pytest.mark.parametrize("tests", ["tests", "checks"])
def test_stated_application_directory_not_replaced_by_the_test_owner(tmp_path, initializer, tests):
    tree(tmp_path, tests, initializer)
    goal = (f"The test suite in proj/{tests} fails. Which function in proj/app is at fault? "
            "Write its name to proj/answer.json")
    entry = load_active_bound_registry(ROOT)["capabilities"][CID]
    result = derivation.derive(goal, entry, tmp_path)
    assert result["source_root"]["value"] == "proj/app"
    assert result["test_paths"]["value"] == [f"proj/{tests}/test_core.py"]


def test_two_stated_application_roots_are_not_arbitrarily_selected(tmp_path):
    tree(tmp_path)
    (tmp_path / "proj/other").mkdir()
    (tmp_path / "proj/other/core.py").write_text("VALUE = 1\n")
    entry = load_active_bound_registry(ROOT)["capabilities"][CID]
    result = derivation.derive(
        "The test suite in proj/tests fails. Which function in proj/app or proj/other is at fault?",
        entry, tmp_path)
    assert "source_root" not in result


def test_actual_front_door_writes_diagnosis_from_explicit_app_not_test_initializer():
    from canonical.runtime import live_brain_route_admission_v1 as door
    scratch = ROOT / "canonical/astra_runtime/tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="diagnosis-source-roles-", dir=scratch) as temporary:
        root = Path(temporary)
        app, suite = tree(root)
        output = root / "answer.json"
        relative = lambda path: path.relative_to(ROOT).as_posix()
        result = door.solve({"task_id": "DIAGNOSIS_DISTINCT_SOURCE_AND_TESTS",
            "goal": f"The test suite in {relative(suite)} fails. Which function in {relative(app)} "
                    f"is at fault? Write its name to {relative(output)}"})
        assert result["pass"] is True, result
        assert "buggy" in output.read_text()
        report = json.loads(output.read_text())
        assert all(row["path"].startswith(relative(app) + "/") for row in report["ranked_lines"])
