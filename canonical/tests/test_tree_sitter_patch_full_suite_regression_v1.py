from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from canonical.runtime import tree_sitter_swe_kernel_v1 as kernel
from canonical.runtime.bound_capabilities import code_tree_sitter_impact_v1 as impact
from canonical.runtime.bound_capabilities import code_tree_sitter_incremental_index_v1 as index
from canonical.runtime.bound_capabilities import code_tree_sitter_patch_verify_v1 as patch

TS_AVAILABLE = all(importlib.util.find_spec(name) for name in ("tree_sitter", "tree_sitter_languages"))


@unittest.skipUnless(TS_AVAILABLE, "pinned tree-sitter substrate is not installed")
class TreeSitterFullSuiteRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tree-sitter-full-suite-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.project = self.repo / "project"
        self.project.mkdir(parents=True)
        self.source = self.project / "calc.py"
        self.source.write_text("def compute(x):\n    return x + 1\n", encoding="utf-8")

    def write_test(self, name, text):
        (self.project / name).write_text(text, encoding="utf-8")

    def prepare(self):
        index.run({"source_root": "project", "output_path": "index.json"}, self.repo)
        impact.run({"index_path": "index.json", "changed_paths": ["project/calc.py"],
                    "output_path": "selection.json"}, self.repo)
        return json.loads((self.repo / "selection.json").read_text(encoding="utf-8"))

    def run_patch(self, **extra):
        original = self.source.read_bytes()
        start = original.index(b"x + 1")
        args = {
            "index_path": "index.json", "selection_path": "selection.json",
            "edits": [{"path": "project/calc.py", "start_byte": start, "end_byte": start + 5,
                       "expected": "x + 1", "replacement": "x * 2 + 1"}],
            "test_cwd": "project", "output_path": "patch.json", "timeout_s": 30,
        }
        args.update(extra)
        result = patch.run(args, self.repo)
        self.assertEqual(self.source.read_bytes(), original)
        return result

    def independent_pytest_of_candidate(self):
        candidate = self.repo / "independent"
        shutil.copytree(self.project, candidate)
        (candidate / "calc.py").write_text(
            self.source.read_text().replace("x + 1", "x * 2 + 1"), encoding="utf-8")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        env.pop("PYTEST_ADDOPTS", None)
        return subprocess.run([sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                              cwd=candidate, env=env, capture_output=True, text=True, timeout=30)

    def test_scratch_directory_is_outside_even_when_repo_is_temp_root(self):
        root = Path(tempfile.gettempdir()).resolve()
        with patch._outside_temporary_directory(root) as directory:
            scratch = Path(directory).resolve()
            self.assertNotEqual(scratch, root)
            self.assertNotIn(root, scratch.parents)

    def test_passing_selected_test_does_not_hide_a_dynamic_failure(self):
        self.write_test("test_visible.py", (
            "from calc import compute\n"
            "def test_visible():\n"
            "    assert compute(0) == 1\n"
        ))
        self.write_test("test_dynamic.py", (
            "import importlib\n"
            "def test_dynamic():\n"
            "    module = importlib.import_module('ca' + 'lc')\n"
            "    assert getattr(module, 'com' + 'pute')(2) == 3\n"
        ))
        selection = self.prepare()
        self.assertEqual(selection["selected_tests"], ["project/test_visible.py"])
        self.assertEqual(selection["omitted_tests"], ["project/test_dynamic.py"])
        result = self.run_patch()
        independent = self.independent_pytest_of_candidate()
        self.assertNotEqual(independent.returncode, 0, independent.stdout + independent.stderr)
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "PATCH_REJECTED")

    def test_excluded_unselected_indexed_failure_is_not_verified(self):
        (self.project / "pytest.ini").write_text("[pytest]\ntestpaths = other\n", encoding="utf-8")
        (self.project / "other").mkdir()
        (self.project / "other" / "test_unrelated.py").write_text(
            "def test_unrelated():\n    assert True\n", encoding="utf-8")
        self.write_test("test_visible.py", (
            "from calc import compute\n"
            "def test_visible():\n    assert compute(0) == 1\n"
        ))
        self.write_test("test_dynamic.py", (
            "import importlib\n"
            "def test_dynamic():\n"
            "    module = importlib.import_module('ca' + 'lc')\n"
            "    assert getattr(module, 'com' + 'pute')(2) == 3\n"
        ))
        selection = self.prepare()
        self.assertEqual(selection["selected_tests"], ["project/test_visible.py"])
        self.assertIn("project/test_dynamic.py", selection["omitted_tests"])
        result = self.run_patch()
        artifact = json.loads((self.repo / "patch.json").read_text(encoding="utf-8"))
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "PATCH_REJECTED")
        self.assertTrue(all(run["oracle_ok"] for run in artifact["test_runs"]))
        self.assertTrue(any(not run["oracle_ok"] for run in artifact["indexed_test_runs"]))

    def test_one_passing_omitted_file_cannot_hide_an_uncollected_file(self):
        (self.project / "pytest.ini").write_text("[pytest]\ntestpaths = other\n", encoding="utf-8")
        (self.project / "other").mkdir()
        (self.project / "other" / "test_unrelated.py").write_text(
            "def test_unrelated():\n    assert True\n", encoding="utf-8")
        self.write_test("test_visible.py", "from calc import compute\ndef test_visible():\n    assert compute(0) == 1\n")
        self.write_test("test_dynamic.py", "import importlib\ndef test_dynamic():\n    assert getattr(importlib.import_module('ca'+'lc'), 'com'+'pute')(2) == 5\n")
        self.write_test("test_uncollected.py", "if __name__ == '__main__':\n    assert False\n")
        self.prepare()
        result = self.run_patch()
        artifact = json.loads((self.repo / "patch.json").read_text(encoding="utf-8"))
        self.assertFalse(result["verified"], artifact)
        self.assertEqual(result["status"], "PATCH_ORACLE_UNVERIFIED")
        self.assertTrue(any(path.endswith("test_uncollected.py") for path in artifact["indexed_test_runs"][0]["unexecuted_test_files"]))

    def test_pytest_support_files_are_not_misclassified_as_empty_test_suites(self):
        tests = self.project / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "conftest.py").write_text("import pytest\n@pytest.fixture\ndef sample(): return 0\n", encoding="utf-8")
        (tests / "helpers.py").write_text("def helper(): return 0\n", encoding="utf-8")
        (tests / "test_visible.py").write_text(
            "from calc import compute\ndef test_visible(sample):\n    assert compute(sample) == 1\n", encoding="utf-8")
        self.prepare()
        result = self.run_patch()
        artifact = json.loads((self.repo / "patch.json").read_text(encoding="utf-8"))
        self.assertTrue(result["verified"], artifact)
        self.assertNotIn("project/tests/conftest.py", artifact["indexed_test_candidates"])
        self.assertNotIn("project/tests/helpers.py", artifact["indexed_test_candidates"])

    def test_nonstandard_indexed_test_file_is_not_omitted(self):
        (self.project / "pytest.ini").write_text("[pytest]\ntestpaths = other\n", encoding="utf-8")
        (self.project / "other").mkdir()
        (self.project / "other" / "test_unrelated.py").write_text(
            "def test_unrelated():\n    assert True\n", encoding="utf-8")
        tests = self.project / "tests"
        tests.mkdir()
        (tests / "test_visible.py").write_text(
            "from calc import compute\ndef test_visible():\n    assert compute(0) == 1\n", encoding="utf-8")
        (tests / "check_dynamic.py").write_text(
            "import importlib\ndef test_dynamic():\n    assert getattr(importlib.import_module('ca'+'lc'), 'com'+'pute')(2) == 3\n", encoding="utf-8")
        selection = self.prepare()
        self.assertIn("project/tests/check_dynamic.py", selection["omitted_tests"])
        result = self.run_patch()
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "PATCH_REJECTED")

    def test_test_added_after_indexing_is_refused_as_a_stale_file_set(self):
        self.write_test("test_visible.py", "from calc import compute\ndef test_visible():\n    assert compute(0) == 1\n")
        self.prepare()
        self.write_test("test_late.py", "def test_late():\n    assert False\n")
        with self.assertRaisesRegex(kernel.TreeSitterSWEError, "INDEX_FILE_SET_STALE"):
            self.run_patch()

    def test_selection_candidate_metadata_cannot_hide_an_indexed_file(self):
        (self.project / "pytest.ini").write_text("[pytest]\ntestpaths = other\n", encoding="utf-8")
        (self.project / "other").mkdir()
        (self.project / "other" / "test_unrelated.py").write_text(
            "def test_unrelated():\n    assert True\n", encoding="utf-8")
        self.write_test("test_visible.py", "from calc import compute\ndef test_visible():\n    assert compute(0) == 1\n")
        self.write_test("test_dynamic.py", (
            "import importlib\n"
            "def test_dynamic():\n"
            "    assert getattr(importlib.import_module('ca' + 'lc'), 'com' + 'pute')(2) == 3\n"
        ))
        selection = self.prepare()
        selection["candidate_tests"] = selection["selected_tests"]
        selection["omitted_tests"] = []
        (self.repo / "selection.json").write_text(json.dumps(selection), encoding="utf-8")
        result = self.run_patch()
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "PATCH_REJECTED")

    def test_excluded_unselected_indexed_pass_is_verified(self):
        (self.project / "pytest.ini").write_text("[pytest]\ntestpaths = other\n", encoding="utf-8")
        (self.project / "other").mkdir()
        (self.project / "other" / "test_unrelated.py").write_text(
            "def test_unrelated():\n    assert True\n", encoding="utf-8")
        self.write_test("test_visible.py", (
            "from calc import compute\n"
            "def test_visible():\n    assert compute(0) == 1\n"
        ))
        self.write_test("test_dynamic.py", (
            "import importlib\n"
            "def test_dynamic():\n"
            "    module = importlib.import_module('ca' + 'lc')\n"
            "    assert getattr(module, 'com' + 'pute')(2) == 5\n"
        ))
        self.prepare()
        result = self.run_patch()
        artifact = json.loads((self.repo / "patch.json").read_text(encoding="utf-8"))
        self.assertTrue(result["verified"], artifact)
        self.assertTrue(any(run["oracle_ok"] for run in artifact["indexed_test_runs"]))

    def test_pytest_fixture_test_cannot_be_silently_skipped(self):
        self.write_test("test_fixture.py", (
            "import pytest\n"
            "from calc import compute\n"
            "@pytest.fixture\n"
            "def value():\n"
            "    return 2\n"
            "def test_requires_fixture(value):\n"
            "    assert compute(value) == 3\n"
        ))
        self.prepare()
        result = self.run_patch()
        independent = self.independent_pytest_of_candidate()
        self.assertNotEqual(independent.returncode, 0, independent.stdout + independent.stderr)
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "PATCH_REJECTED")

    def test_arbitrary_successful_command_is_not_a_python_test_oracle(self):
        self.write_test("test_behavior.py", (
            "from calc import compute\n"
            "def test_behavior():\n"
            "    assert compute(2) == 3\n"
        ))
        self.prepare()
        result = self.run_patch(test_argv=[sys.executable, "-c", "print('not a test suite')"])
        self.assertNotEqual(self.independent_pytest_of_candidate().returncode, 0)
        self.assertFalse(result["verified"])

    def test_output_cannot_overwrite_indexed_source_or_input_artifacts(self):
        self.write_test("test_visible.py", (
            "from calc import compute\n"
            "def test_visible():\n"
            "    assert compute(0) == 1\n"
        ))
        self.prepare()
        source = self.source.read_bytes()
        original_index = (self.repo / "index.json").read_bytes()
        original_selection = (self.repo / "selection.json").read_bytes()
        for output in ("project/calc.py", "project/test_visible.py", "index.json", "selection.json"):
            with self.subTest(output=output), self.assertRaises(kernel.TreeSitterSWEError):
                self.run_patch(output_path=output)
        self.assertEqual(self.source.read_bytes(), source)
        self.assertEqual((self.repo / "index.json").read_bytes(), original_index)
        self.assertEqual((self.repo / "selection.json").read_bytes(), original_selection)

    def test_configured_suite_cannot_exclude_the_selected_impacted_test(self):
        (self.project / "pytest.ini").write_text("[pytest]\ntestpaths = other\n", encoding="utf-8")
        (self.project / "other").mkdir()
        (self.project / "other" / "test_unrelated.py").write_text(
            "def test_unrelated():\n    assert 3 + 4 == 7\n", encoding="utf-8")
        self.write_test("test_visible.py", (
            "from calc import compute\n"
            "def test_visible():\n"
            "    assert compute(2) == 3\n"
        ))
        selection = self.prepare()
        self.assertEqual(selection["selected_tests"], ["project/test_visible.py"])
        result = self.run_patch()
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "PATCH_REJECTED")

    def test_wholly_skipped_python_suite_is_unverified(self):
        self.write_test("test_skipped.py", (
            "import pytest\n"
            "from calc import compute\n"
            "@pytest.mark.skip(reason='not implemented')\n"
            "def test_skipped():\n"
            "    assert compute(0) == 1\n"
        ))
        self.prepare()
        result = self.run_patch()
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "PATCH_ORACLE_UNVERIFIED")
        self.assertEqual(result["test_pass_count"], 0)
        artifact = json.loads((self.repo / "patch.json").read_text(encoding="utf-8"))
        self.assertEqual(artifact["test_runs"][0]["tests_skipped"], 1)

    def test_passing_fixture_suite_replays_with_real_pytest(self):
        self.write_test("test_fixture.py", (
            "import pytest\n"
            "from calc import compute\n"
            "@pytest.fixture\n"
            "def value():\n"
            "    return 0\n"
            "def test_fixture(value):\n"
            "    assert compute(value) == 1\n"
        ))
        self.prepare()
        result = self.run_patch()
        self.assertTrue(result["verified"])
        self.assertEqual(result["test_pass_count"], 2)
        artifact = json.loads((self.repo / "patch.json").read_text(encoding="utf-8"))
        self.assertEqual([run["tests_passed"] for run in artifact["test_runs"]], [1, 1])
        registry_path = Path(__file__).resolve().parents[2] / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json"
        entry = json.loads(registry_path.read_text())["capabilities"]["code.patch.tree_sitter.verify.v1"]
        self.assertEqual(set(entry["result_fields"]), set(result))
        self.assertEqual(entry["provides"], patch.PROVIDES)

    def test_trial_never_overwrites_original_source_while_tests_run(self):
        original = self.source.read_text(encoding="utf-8")
        self.write_test("test_visible.py", (
            "from pathlib import Path\n"
            "from calc import compute\n"
            "def test_visible():\n"
            f"    assert Path({str(self.source)!r}).read_text() == {original!r}\n"
            "    assert compute(0) == 1\n"
        ))
        self.prepare()
        result = self.run_patch()
        self.assertTrue(result["verified"])
        self.assertEqual(self.source.read_text(encoding="utf-8"), original)

    def test_pytest_side_effects_do_not_change_the_source_workspace(self):
        marker = self.project / "marker.txt"
        marker.write_text("before", encoding="utf-8")
        self.write_test("test_visible.py", (
            "from pathlib import Path\n"
            "from calc import compute\n"
            "def test_visible():\n"
            "    Path('marker.txt').write_text('after')\n"
            "    assert compute(0) == 1\n"
        ))
        self.prepare()
        result = self.run_patch()
        self.assertTrue(result["verified"])
        self.assertEqual(marker.read_text(encoding="utf-8"), "before")

    def test_requested_command_cannot_replace_the_candidate_before_verification(self):
        self.write_test("test_behavior.py", (
            "from calc import compute\n"
            "def test_behavior():\n"
            "    assert compute(2) == 3\n"
        ))
        self.prepare()
        command = [sys.executable, "-c", (
            "from pathlib import Path; "
            "Path('calc.py').write_text('def compute(x):\\n    return x + 1\\n')"
        )]
        result = self.run_patch(test_argv=command)
        self.assertNotEqual(self.independent_pytest_of_candidate().returncode, 0)
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "PATCH_REJECTED")

    def test_pytest_cannot_replace_the_candidate_and_report_success(self):
        self.write_test("test_behavior.py", (
            "from pathlib import Path\n"
            "def test_behavior():\n"
            "    Path(__file__).with_name('calc.py').write_text("
            "'def compute(x):\\n    return x + 1\\n')\n"
            "    from calc import compute\n"
            "    assert compute(2) == 3\n"
        ))
        self.prepare()
        result = self.run_patch()
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "PATCH_REJECTED")

    def test_non_python_successful_command_is_reported_as_unverified(self):
        self.source.unlink()
        js = self.project / "math.js"
        js.write_text("function compute(x) { return x + 1; }\n", encoding="utf-8")
        tests = self.project / "tests"
        tests.mkdir()
        (tests / "math.test.js").write_text("const target = require('../math.js');\n", encoding="utf-8")
        index.run({"source_root": "project", "output_path": "index.json"}, self.repo)
        impact.run({"index_path": "index.json", "changed_paths": ["project/math.js"],
                    "output_path": "selection.json"}, self.repo)
        original = js.read_bytes()
        start = original.index(b"x + 1")
        result = patch.run({
            "index_path": "index.json", "selection_path": "selection.json",
            "edits": [{"path": "project/math.js", "start_byte": start, "end_byte": start + 5,
                       "expected": "x + 1", "replacement": "x + 2"}],
            "test_cwd": "project", "test_argv": [sys.executable, "-c", "print('not a test suite')"],
            "output_path": "patch.json", "timeout_s": 30,
        }, self.repo)
        self.assertEqual(js.read_bytes(), original)
        self.assertFalse(result["verified"])
        self.assertEqual(result["status"], "PATCH_ORACLE_UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
