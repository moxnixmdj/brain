from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from canonical.runtime.bound_capabilities import python_issue_to_pr_orchestrate as orchestrator
from canonical.runtime.bound_capabilities import python_repo_diff_apply_full_testgate as full_gate


class IssueToPRFullSuiteRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="brain-full-suite-regression-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "src"
        (self.source / "pkg").mkdir(parents=True)
        (self.source / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (self.source / "pkg" / "core.py").write_text(
            "def helper(x):\n    return x + 1\n", encoding="utf-8"
        )
        (self.root / "task.json").write_text(json.dumps({
            "issue_id": "regression-probe",
            "title": "Rename helper to compute",
            "edits": [{"op": "rename_symbol", "module": "pkg/core.py",
                       "name": "helper", "new_name": "compute"}],
        }), encoding="utf-8")

    def add_test(self, name: str, body: str) -> None:
        tests = self.source / "tests"
        tests.mkdir(exist_ok=True)
        (tests / name).write_text(body, encoding="utf-8")

    def pytest_at(self, directory: Path) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        return subprocess.run(
            [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            cwd=directory, env=env, capture_output=True, text=True, timeout=30,
        )

    def run_issue(self, **overrides) -> dict:
        args = {
            "task_path": "task.json",
            "source_root": "src",
            "worktree_path": "worktree",
            "output_path": "out/summary.json",
            "diff_path": "out/change.diff",
            "pr_intent_path": "out/pr_intent.json",
            "python_executable": sys.executable,
            "timeout_s": 30,
        }
        args.update(overrides)
        return orchestrator.run(args, self.root)

    def test_dynamic_dependency_with_zero_selected_is_not_verified(self):
        self.add_test("test_dynamic.py", (
            "import importlib\n"
            "def test_dynamic():\n"
            "    module = importlib.import_module('pkg.core')\n"
            "    assert getattr(module, 'helper')(2) == 3\n"
        ))
        self.assertEqual(self.pytest_at(self.source).returncode, 0)
        result = self.run_issue()
        independent = self.pytest_at(self.root / "worktree")
        self.assertNotEqual(independent.returncode, 0, independent.stdout + independent.stderr)
        self.assertEqual(result["test_selected_count"], 0)
        self.assertTrue(result["edits_verified"])
        self.assertFalse(result["verified"])
        self.assertEqual(result["full_test_gate"], "FAIL")
        self.assertIn("test_dynamic", " ".join(result["full_test_failing_tests"]))
        self.assertIn("def helper", (self.source / "pkg" / "core.py").read_text())

    def test_a_passing_selected_test_does_not_hide_an_omitted_failure(self):
        self.add_test("test_static.py", (
            "from pkg.core import helper\n"
            "def test_static():\n"
            "    assert helper(0) == 1\n"
        ))
        self.add_test("test_dynamic.py", (
            "import importlib\n"
            "def test_dynamic():\n"
            "    module = importlib.import_module('pkg.' + 'co' + 're')\n"
            "    assert getattr(module, 'hel' + 'per')(2) == 3\n"
        ))
        self.assertEqual(self.pytest_at(self.source).returncode, 0)
        result = self.run_issue()
        independent = self.pytest_at(self.root / "worktree")
        self.assertNotEqual(independent.returncode, 0, independent.stdout + independent.stderr)
        self.assertEqual(result["test_selected_count"], 1)
        self.assertEqual(result["test_passed_count"], 1)
        self.assertFalse(result["verified"])
        self.assertEqual(result["full_test_gate"], "FAIL")
        self.assertGreaterEqual(result["full_test_failed_count"], 1)

    def test_configured_full_suite_cannot_skip_a_selected_failing_file(self):
        (self.source / "pytest.ini").write_text(
            "[pytest]\ntestpaths = other\npython_files = check_*.py\n", encoding="utf-8")
        (self.source / "other").mkdir()
        (self.source / "other" / "check_unrelated.py").write_text(
            "def test_unrelated():\n    assert 3 + 4 == 7\n", encoding="utf-8")
        self.add_test("test_visible.py", (
            "import importlib\n"
            "from pkg.core import helper\n"
            "def test_visible():\n"
            "    assert helper(0) == 1\n"
            "    module = importlib.import_module('pkg.core')\n"
            "    assert getattr(module, 'hel' + 'per')(2) == 3\n"
        ))
        result = self.run_issue()
        self.assertEqual(result["test_selected_count"], 1)
        self.assertFalse(result["verified"])
        self.assertIn(result["test_selected_status"], ("FAIL", "UNAVAILABLE"))

    def test_excluded_unselected_indexed_failure_is_not_verified(self):
        (self.source / "pytest.ini").write_text("[pytest]\ntestpaths = other\n", encoding="utf-8")
        (self.source / "other").mkdir()
        (self.source / "other" / "test_unrelated.py").write_text(
            "def test_unrelated():\n    assert True\n", encoding="utf-8")
        self.add_test("test_visible.py", (
            "from pkg.core import helper\n"
            "def test_visible():\n    assert helper(0) == 1\n"
        ))
        self.add_test("test_dynamic.py", (
            "import importlib\n"
            "def test_dynamic():\n"
            "    module = importlib.import_module('pkg.' + 'core')\n"
            "    assert getattr(module, 'hel' + 'per')(2) == 3\n"
        ))
        result = self.run_issue()
        independent = subprocess.run(
            [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_dynamic.py"],
            cwd=self.root / "worktree", capture_output=True, text=True, timeout=30,
        )
        self.assertNotEqual(independent.returncode, 0, independent.stdout + independent.stderr)
        self.assertEqual(result["test_selected_count"], 1)
        self.assertEqual(result["test_selected_status"], "PASS")
        self.assertEqual(result["full_test_gate"], "PASS")  # configured discovery still passes
        self.assertFalse(result["verified"])
        self.assertEqual(result["indexed_test_gate"], "FAIL")
        self.assertGreaterEqual(result["indexed_test_failed_count"], 1)

    def test_unparseable_conventional_file_is_not_lost_by_the_ast_index(self):
        (self.source / "pytest.ini").write_text("[pytest]\ntestpaths = other\n", encoding="utf-8")
        (self.source / "other").mkdir()
        (self.source / "other" / "test_unrelated.py").write_text(
            "def test_unrelated():\n    assert True\n", encoding="utf-8")
        self.add_test("test_visible.py", "from pkg.core import helper\ndef test_visible():\n    assert helper(0) == 1\n")
        self.add_test("test_broken.py", "def test_broken(:\n    pass\n")
        result = self.run_issue()
        self.assertEqual(result["full_test_gate"], "PASS")
        self.assertFalse(result["verified"], result)
        self.assertEqual(result["indexed_test_gate"], "FAIL")
        self.assertIn("tests/test_broken.py", result["indexed_test_omitted_paths"])

    def test_one_passing_omitted_file_cannot_hide_an_uncollected_file(self):
        (self.source / "pytest.ini").write_text("[pytest]\ntestpaths = other\n", encoding="utf-8")
        (self.source / "other").mkdir()
        (self.source / "other" / "test_unrelated.py").write_text(
            "def test_unrelated():\n    assert True\n", encoding="utf-8")
        self.add_test("test_visible.py", "from pkg.core import helper\ndef test_visible():\n    assert helper(0) == 1\n")
        self.add_test("test_dynamic.py", "import importlib\ndef test_dynamic():\n    assert getattr(importlib.import_module('pkg.'+'core'), 'com'+'pute')(2) == 3\n")
        self.add_test("test_uncollected.py", "if __name__ == '__main__':\n    assert False\n")
        result = self.run_issue()
        self.assertEqual(result["full_test_gate"], "PASS")
        self.assertFalse(result["verified"], result)
        self.assertEqual(result["indexed_test_gate"], "UNAVAILABLE")
        self.assertIn("tests/test_uncollected.py", result["indexed_test_unexecuted_paths"])

    def test_excluded_unselected_indexed_pass_is_verified(self):
        (self.source / "pytest.ini").write_text("[pytest]\ntestpaths = other\n", encoding="utf-8")
        (self.source / "other").mkdir()
        (self.source / "other" / "test_unrelated.py").write_text(
            "def test_unrelated():\n    assert True\n", encoding="utf-8")
        self.add_test("test_visible.py", (
            "from pkg.core import helper\n"
            "def test_visible():\n    assert helper(0) == 1\n"
        ))
        self.add_test("test_dynamic.py", (
            "import importlib\n"
            "def test_dynamic():\n"
            "    module = importlib.import_module('pkg.' + 'core')\n"
            "    assert getattr(module, 'com' + 'pute')(2) == 3\n"
        ))
        result = self.run_issue()
        self.assertTrue(result["verified"], result)
        self.assertEqual(result["full_test_gate"], "PASS")
        self.assertEqual(result["indexed_test_gate"], "PASS")
        self.assertGreaterEqual(result["indexed_test_executed_count"], 1)

    def test_no_tests_is_unverified(self):
        result = self.run_issue()
        self.assertEqual(result["test_selected_count"], 0)
        self.assertTrue(result["edits_verified"])
        self.assertFalse(result["verified"])
        self.assertEqual(result["full_test_gate"], "UNAVAILABLE")
        self.assertIn("NO_TESTS_DISCOVERED", result["full_test_reason"])

    def test_interpreter_without_pytest_is_unverified(self):
        self.add_test("test_real.py", "def test_real():\n    assert 1 + 1 == 2\n")
        venv = self.root / "no-pytest-venv"
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)],
                       capture_output=True, text=True, check=True, timeout=30)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        with patch.dict(os.environ, {"PYTHONPATH": ""}):
            result = self.run_issue(python_executable=str(python))
        self.assertTrue(result["edits_verified"])
        self.assertFalse(result["verified"])
        self.assertEqual(result["test_pytest"], "UNAVAILABLE")
        self.assertEqual(result["full_test_gate"], "UNAVAILABLE")
        self.assertEqual(result["full_test_reason"], "PYTEST_UNAVAILABLE")

    def test_environment_selection_flags_cannot_hide_omitted_failures(self):
        self.add_test("test_static.py", (
            "from pkg.core import helper\n"
            "def test_static():\n"
            "    assert helper(0) == 1\n"
        ))
        self.add_test("test_dynamic.py", (
            "import importlib\n"
            "def test_dynamic():\n"
            "    module = importlib.import_module('pkg.' + 'core')\n"
            "    assert getattr(module, 'hel' + 'per')(2) == 3\n"
        ))
        with patch.dict(os.environ, {"PYTEST_ADDOPTS": "-k static"}):
            result = self.run_issue()
        self.assertEqual(result["test_selected_count"], 1)
        self.assertEqual(result["test_passed_count"], 1)
        self.assertFalse(result["verified"])
        self.assertEqual(result["full_test_gate"], "FAIL")
        self.assertIn("test_dynamic", " ".join(result["full_test_failing_tests"]))

    def test_zero_selected_but_passing_full_suite_can_verify(self):
        self.add_test("test_unrelated.py", (
            "def test_arithmetic():\n"
            "    assert 2 + 3 == 5\n"
        ))
        result = self.run_issue()
        self.assertEqual(result["test_selected_count"], 0)
        self.assertTrue(result["verified"])
        self.assertEqual(result["full_test_gate"], "PASS")
        self.assertEqual(result["full_test_passed_count"], 1)
        evidence = result["full_test_gate_evidence"]
        diff_bytes = (self.root / "out" / "change.diff").read_bytes()
        self.assertEqual(evidence["diff_sha256"], hashlib.sha256(diff_bytes).hexdigest())
        evidence_bytes = (json.dumps(evidence, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        self.assertEqual(result["full_test_gate_sha256"], hashlib.sha256(evidence_bytes).hexdigest())
        registry_path = Path(__file__).resolve().parents[2] / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        entry = json.loads(registry_path.read_text())["capabilities"]["python.software.issue_to_pr.orchestrate.v1"]
        self.assertTrue(set(entry["result_fields"]) <= set(result))
        self.assertEqual(self.pytest_at(self.root / "worktree").returncode, 0)

    def test_full_gate_rejects_a_suite_that_only_skips(self):
        self.add_test("test_skipped.py", (
            "import pytest\n"
            "@pytest.mark.skip(reason='not implemented')\n"
            "def test_future_behavior():\n"
            "    raise AssertionError('not implemented')\n"
        ))
        before = (self.source / "pkg" / "core.py").read_text(encoding="utf-8")
        after = before.replace("x + 1", "x + 2")
        diff = "".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile="a/pkg/core.py", tofile="b/pkg/core.py",
        ))
        (self.root / "change.diff").write_text(diff, encoding="utf-8")
        result = full_gate.run({
            "anchor_path": "src", "diff_path": "change.diff",
            "output_path": "out/full-gate.json", "python_executable": sys.executable,
            "timeout_s": 30,
        }, self.root)
        self.assertEqual(result["gate"], "FAIL")
        self.assertFalse(result["verified"])
        self.assertEqual(result["tests_executed"], 0)
        self.assertEqual(result["tests_skipped"], 1)
        self.assertEqual((self.source / "pkg" / "core.py").read_text(), before)

    def test_wholly_xfailed_suite_is_not_verification(self):
        self.add_test("test_xfail.py", (
            "import pytest\n"
            "@pytest.mark.xfail(reason='known defect')\n"
            "def test_known_defect():\n"
            "    raise AssertionError('known defect')\n"
        ))
        result = self.run_issue()
        self.assertFalse(result["verified"])
        self.assertEqual(result["full_test_gate"], "FAIL")
        self.assertEqual(result["full_test_executed_count"], 0)
        self.assertEqual(result["full_test_skipped_count"], 1)

    def test_selected_test_side_effects_do_not_mutate_the_worktree(self):
        self.add_test("test_visible.py", (
            "from pathlib import Path\n"
            "from pkg.core import helper\n"
            "def test_visible():\n"
            "    target = Path(__file__).resolve().parents[1] / 'pkg' / 'core.py'\n"
            "    target.write_text('def helper(x):\\n    return x + 1\\n')\n"
            "    assert helper(0) == 1\n"
        ))
        result = self.run_issue()
        self.assertFalse(result["verified"])
        self.assertIn("def compute", (self.root / "worktree" / "pkg" / "core.py").read_text())
        self.assertIn("def helper", (self.source / "pkg" / "core.py").read_text())

    def test_full_gate_rejects_tests_that_replace_applied_source(self):
        self.add_test("test_rewrite.py", (
            "from pathlib import Path\n"
            "def test_rewrite():\n"
            "    target = Path(__file__).resolve().parents[1] / 'pkg' / 'core.py'\n"
            "    target.write_text('def helper(x):\\n    return x + 1\\n')\n"
            "    assert target.read_text().endswith('return x + 1\\n')\n"
        ))
        before = (self.source / "pkg" / "core.py").read_text(encoding="utf-8")
        after = before.replace("x + 1", "x + 2")
        (self.root / "change.diff").write_text("".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile="a/pkg/core.py", tofile="b/pkg/core.py",
        )), encoding="utf-8")
        result = full_gate.run({
            "anchor_path": "src", "diff_path": "change.diff", "output_path": "out/gate.json",
            "python_executable": sys.executable, "timeout_s": 30,
        }, self.root)
        self.assertEqual(result["gate"], "FAIL")
        self.assertEqual(result["reason"], "APPLIED_FILES_CHANGED_DURING_TESTS")
        self.assertEqual((self.source / "pkg" / "core.py").read_text(), before)

    def test_renamed_source_recreated_by_a_test_fails_the_gate(self):
        self.add_test("test_recreate.py", (
            "from pathlib import Path\n"
            "def test_recreate():\n"
            "    old = Path(__file__).resolve().parents[1] / 'pkg' / 'core.py'\n"
            "    old.write_text('recreated')\n"
            "    assert old.read_text() == 'recreated'\n"
        ))
        (self.root / "rename.diff").write_text(
            "diff --git a/pkg/core.py b/pkg/renamed.py\n"
            "similarity index 100%\n"
            "rename from pkg/core.py\n"
            "rename to pkg/renamed.py\n", encoding="utf-8")
        result = full_gate.run({
            "anchor_path": "src", "diff_path": "rename.diff", "output_path": "out/gate.json",
            "python_executable": sys.executable, "timeout_s": 30,
        }, self.root)
        self.assertEqual(result["gate"], "FAIL")
        self.assertEqual(result["reason"], "APPLIED_FILES_CHANGED_DURING_TESTS")
        self.assertIn("def helper", (self.source / "pkg" / "core.py").read_text())

    def test_diff_changed_by_a_test_is_not_verified(self):
        self.add_test("test_changes_diff.py", (
            "from pathlib import Path\n"
            "def test_change_diff():\n"
            "    for parent in Path(__file__).resolve().parents:\n"
            "        diff = parent / 'out' / 'change.diff'\n"
            "        if diff.is_file():\n"
            "            diff.write_text('changed during pytest', encoding='utf-8')\n"
            "            break\n"
            "    assert diff.read_text(encoding='utf-8') == 'changed during pytest'\n"
        ))
        result = self.run_issue()
        self.assertFalse(result["verified"])
        self.assertFalse(result["diff_intact_after_test_runs"])
        self.assertEqual(result["full_test_gate"], "NOT_RUN")
        self.assertEqual(result["full_test_reason"], "DIFF_CHANGED_BEFORE_FULL_GATE")

    def test_missing_or_malformed_real_pytest_reports_cannot_pass(self):
        self.add_test("test_passing.py", "def test_real():\n    assert 4 + 5 == 9\n")
        before = (self.source / "pkg" / "core.py").read_text(encoding="utf-8")
        after = before.replace("x + 1", "x + 2")
        (self.root / "change.diff").write_text("".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile="a/pkg/core.py", tofile="b/pkg/core.py",
        )), encoding="utf-8")
        for action in (
            "path.unlink()",
            "path.write_text('<broken', encoding='utf-8')",
            "path.write_text('<not-junit><testcase name=\"fake\"/></not-junit>', encoding='utf-8')",
            "path.write_text('<testsuites><testsuite tests=\"1\" errors=\"1\" failures=\"0\" skipped=\"0\">'"
            " + '<testcase name=\"fake\"/></testsuite></testsuites>', encoding='utf-8')",
        ):
            with self.subTest(action=action):
                (self.source / "conftest.py").write_text(
                    "from pathlib import Path\n"
                    "def pytest_unconfigure(config):\n"
                    "    path = Path(config.option.xmlpath)\n"
                    f"    {action}\n", encoding="utf-8")
                result = full_gate.run({
                    "anchor_path": "src", "diff_path": "change.diff",
                    "output_path": "out/full-gate.json", "python_executable": sys.executable,
                    "timeout_s": 30,
                }, self.root)
                self.assertEqual(result["gate"], "FAIL")
                self.assertEqual(result["reason"], "PYTEST_REPORT_UNAVAILABLE_OR_EMPTY")

    def test_inherited_pythonpath_cannot_import_the_unpatched_anchor(self):
        anchor = self.root / "layout"
        (anchor / "src" / "pkg").mkdir(parents=True)
        (anchor / "src" / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        before = "def value():\n    return 1\n"
        after = "def value():\n    return 2\n"
        (anchor / "src" / "pkg" / "core.py").write_text(before, encoding="utf-8")
        (anchor / "tests").mkdir()
        (anchor / "tests" / "test_behavior.py").write_text(
            "from pkg.core import value\ndef test_original_behavior():\n    assert value() == 1\n",
            encoding="utf-8")
        (self.root / "layout.diff").write_text("".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile="a/src/pkg/core.py", tofile="b/src/pkg/core.py",
        )), encoding="utf-8")
        inherited = str(anchor / "src") + os.pathsep + os.environ.get("PYTHONPATH", "")
        with patch.dict(os.environ, {"PYTHONPATH": inherited}):
            result = full_gate.run({
                "anchor_path": "layout", "diff_path": "layout.diff",
                "output_path": "out/layout-gate.json", "python_executable": sys.executable,
                "timeout_s": 30,
            }, self.root)
        patched = self.root / "independent-patched"
        shutil.copytree(anchor, patched)
        (patched / "src" / "pkg" / "core.py").write_text(after, encoding="utf-8")
        env = dict(os.environ, PYTHONPATH=str(patched / "src") + os.pathsep + os.environ.get("PYTHONPATH", ""))
        independent = subprocess.run(
            [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
            cwd=patched, env=env, capture_output=True, text=True, timeout=30,
        )
        self.assertNotEqual(independent.returncode, 0, independent.stdout + independent.stderr)
        self.assertEqual(result["gate"], "FAIL")
        self.assertFalse(result["verified"])

    def test_custom_pytest_discovery_is_used_for_the_full_gate(self):
        (self.source / "pytest.ini").write_text(
            "[pytest]\npython_files = check_*.py\n", encoding="utf-8")
        self.add_test("check_custom.py", (
            "def test_custom_case():\n"
            "    assert 5 * 5 == 25\n"
        ))
        result = self.run_issue()
        self.assertEqual(result["test_selected_count"], 0)
        self.assertTrue(result["verified"])
        self.assertEqual(result["full_test_gate"], "PASS")
        self.assertEqual(result["full_test_passed_count"], 1)
        self.assertEqual(self.pytest_at(self.root / "worktree").returncode, 0)

    def test_artifact_paths_must_not_overwrite_the_verified_diff(self):
        self.add_test("test_real.py", "def test_real():\n    assert 8 - 3 == 5\n")
        with self.assertRaises(SystemExit) as exc:
            self.run_issue(pr_intent_path="out/change.diff")
        self.assertIn("ARTIFACT_PATHS_OVERLAP", str(exc.exception))
        self.assertFalse((self.root / "worktree").exists())

    def test_move_to_a_new_module_can_pass_the_full_gate(self):
        self.add_test("test_real.py", (
            "from pkg.core import helper\n"
            "def test_real():\n"
            "    assert helper(2) == 3\n"
        ))
        (self.root / "task.json").write_text(json.dumps({
            "issue_id": "move-probe", "edits": [{
                "op": "move_symbol", "module": "pkg/core.py",
                "qualname": "helper", "to_module": "pkg/new_module.py",
            }],
        }), encoding="utf-8")
        result = self.run_issue()
        self.assertTrue(result["verified"], result)
        self.assertIn("pkg/new_module.py", result["full_test_gate_evidence"]["applied_files"])
        self.assertIn("def helper", (self.root / "worktree" / "pkg" / "new_module.py").read_text())
        self.assertFalse((self.source / "pkg" / "new_module.py").exists())

    def test_move_target_cannot_escape_the_worktree_before_planning(self):
        (self.root / "task.json").write_text(json.dumps({
            "issue_id": "path-probe", "edits": [{
                "op": "move_symbol", "module": "pkg/core.py",
                "qualname": "helper", "to_module": "../escaped.py",
            }],
        }), encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.run_issue()
        self.assertFalse((self.root / "escaped.py").exists())
        self.assertFalse((self.root / "worktree").exists())
        self.assertIn("def helper", (self.source / "pkg" / "core.py").read_text())

    def test_full_gate_refuses_output_inside_its_anchor(self):
        self.add_test("test_real.py", "def test_real():\n    assert 3 + 4 == 7\n")
        before = (self.source / "pkg" / "core.py").read_text(encoding="utf-8")
        after = before.replace("x + 1", "x + 2")
        (self.root / "change.diff").write_text("".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile="a/pkg/core.py", tofile="b/pkg/core.py",
        )), encoding="utf-8")
        with self.assertRaises(SystemExit) as exc:
            full_gate.run({
                "anchor_path": "src", "diff_path": "change.diff",
                "output_path": "src/out/gate.json", "python_executable": sys.executable,
                "timeout_s": 30,
            }, self.root)
        self.assertIn("OUTPUT_INSIDE_ANCHOR", str(exc.exception))
        self.assertFalse((self.source / "out").exists())
        self.assertEqual((self.source / "pkg" / "core.py").read_text(), before)

    def test_parallel_full_gates_use_independent_scratch_trees(self):
        self.add_test("test_real.py", "def test_real():\n    assert 9 - 2 == 7\n")
        before = (self.source / "pkg" / "core.py").read_text(encoding="utf-8")
        after = before.replace("x + 1", "x + 2")
        (self.root / "change.diff").write_text("".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile="a/pkg/core.py", tofile="b/pkg/core.py",
        )), encoding="utf-8")

        def run_gate(number):
            return full_gate.run({
                "anchor_path": "src", "diff_path": "change.diff",
                "output_path": f"out/gate-{number}.json", "python_executable": sys.executable,
                "timeout_s": 30,
            }, self.root)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run_gate, (1, 2)))
        self.assertTrue(all(result["verified"] for result in results), results)
        self.assertEqual((self.root / "out" / "gate-1.json").read_bytes(),
                         (self.root / "out" / "gate-2.json").read_bytes())
        self.assertFalse(any(path.name.startswith("_gate_tree_")
                             for path in (self.root / "out").iterdir()))

    def test_full_gate_records_passes_and_skips_from_real_pytest(self):
        self.add_test("test_mixed.py", (
            "import pytest\n"
            "def test_executed():\n"
            "    assert 6 * 7 == 42\n"
            "@pytest.mark.skip(reason='not available')\n"
            "def test_skipped():\n"
            "    raise AssertionError('not available')\n"
        ))
        before = (self.source / "pkg" / "core.py").read_text(encoding="utf-8")
        after = before.replace("x + 1", "x + 2")
        (self.root / "change.diff").write_text("".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile="a/pkg/core.py", tofile="b/pkg/core.py",
        )), encoding="utf-8")
        result = full_gate.run({
            "anchor_path": "src", "diff_path": "change.diff",
            "output_path": "out/full-gate.json", "python_executable": sys.executable,
            "timeout_s": 30,
        }, self.root)
        self.assertEqual(result["gate"], "PASS")
        self.assertEqual(result["tests_executed"], 1)
        self.assertEqual(result["tests_passed"], 1)
        self.assertEqual(result["tests_skipped"], 1)
        registry_path = Path(__file__).resolve().parents[2] / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        entry = json.loads(registry_path.read_text())["capabilities"]["python.repo.diff_apply_full_testgate.v1"]
        self.assertEqual(set(entry["result_fields"]), set(result))


if __name__ == "__main__":
    unittest.main()
