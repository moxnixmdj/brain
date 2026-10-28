from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from canonical.runtime.bound_capabilities import python_repository_acceptance_measurement_v1 as measurement
from canonical.runtime import python_request_acceptance_union_v1 as union


class NonvacuousRepositoryAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="brain-acceptance-nonvacuous-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.project = self.root / "project"
        self.project.mkdir()
        (self.project / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")

    def write_test(self, body, name="test_m.py"):
        (self.project / name).write_text(body, encoding="utf-8")

    def run_measure(self, **overrides):
        args = {"source_root": "project", "test_paths": ["test_m.py"],
                "output_path": "receipt.json", "timeout_s": 15}
        args.update(overrides)
        return measurement.run(args, self.root)

    def test_manifest_rejects_oversized_files_before_reading_them(self):
        large = self.project / "large.bin"
        with large.open("wb") as stream:
            stream.truncate(1024 * 1024)
        with patch.object(pathlib.Path, "open", side_effect=AssertionError("oversized file read")):
            with self.assertRaisesRegex(measurement.MeasurementError, "MEASURED_TREE_BYTE_LIMIT"):
                measurement._tree_manifest(self.project, max_files=20, max_bytes=4096)

    def test_failing_pytest_fixture_is_not_measured_as_passing(self):
        self.write_test("def test_value(tmp_path):\n    assert False\n")
        out = self.run_measure()
        self.assertTrue(out["pass"])
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertGreaterEqual(out["measurements"]["test_count"], 1)

    def test_passing_pytest_fixture_is_executed_and_counted(self):
        self.write_test("def test_value(tmp_path):\n    assert tmp_path.is_dir()\n")
        out = self.run_measure()
        self.assertTrue(out["measurements"]["tests_pass"], out)
        self.assertEqual(out["measurements"]["test_count"], 1)
        self.assertEqual(out["test_evidence"]["oracle_kind"], "PYTEST_JUNIT")

    def test_one_passing_function_cannot_hide_a_failing_fixture(self):
        self.write_test("def test_easy():\n    assert True\n\ndef test_fixture(tmp_path):\n    assert False\n")
        out = self.run_measure()
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertGreaterEqual(out["measurements"]["test_count"], 2)

    def test_empty_and_fake_success_output_are_not_test_evidence(self):
        self.write_test("pass\n")
        out = self.run_measure(test_argv=[sys.executable, "-c", "print('Ran 9 tests\\nOK')"])
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertEqual(out["measurements"]["test_count"], 0)

    def test_skipped_only_pytest_and_unittest_are_not_passing(self):
        self.write_test("import pytest\n@pytest.mark.skip(reason='not available')\ndef test_skip():\n    assert True\n")
        out = self.run_measure()
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertEqual(out["measurements"]["test_count"], 0)
        self.write_test("import unittest\nclass T(unittest.TestCase):\n    @unittest.skip('later')\n    def test_skip(self):\n        self.fail()\nif __name__ == '__main__': unittest.main()\n")
        out = self.run_measure(test_argv=[sys.executable, "test_m.py"])
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertEqual(out["measurements"]["test_count"], 0)

    def test_real_assertion_script_remains_supported(self):
        self.write_test("from m import f\nassert f() == 1\n")
        out = self.run_measure(test_argv=[sys.executable, "test_m.py"])
        self.assertTrue(out["measurements"]["tests_pass"], out)
        self.assertEqual(out["measurements"]["test_count"], 1)
        self.assertEqual(out["test_evidence"]["oracle_kind"], "ASSERTION_SCRIPT_TRACE")
        self.assertTrue(out["test_evidence"]["oracle_fast_path"])
        self.assertIsNone(out["test_evidence"]["pytest_returncode"])

    def test_fast_script_path_does_not_hide_custom_pytest_functions(self):
        (self.project / "pytest.ini").write_text("[pytest]\npython_functions = check_*\n", encoding="utf-8")
        self.write_test("assert 1 == 1\ndef check_hidden():\n    assert False\n")
        out = self.run_measure(test_argv=[sys.executable, "-c", "pass"])
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertFalse(out["test_evidence"]["oracle_fast_path"])
        self.assertEqual(out["test_evidence"]["pytest_returncode"], 1)

    def test_fast_script_path_cannot_hide_an_imported_unittest_class(self):
        (self.project / "m.py").write_text(
            "import unittest\ndef f(): return 1\nclass Sneaky(unittest.TestCase):\n    def test_bad(self): self.fail()\n",
            encoding="utf-8")
        self.write_test("from m import f, Sneaky\nassert f() == 1\n")
        out = self.run_measure(test_argv=[sys.executable, "test_m.py"])
        self.assertFalse(out["measurements"]["tests_pass"], out)

    def test_unexecuted_assert_is_not_an_assertion_script_witness(self):
        self.write_test("if False: assert 1 == 2\n")
        out = self.run_measure(test_argv=[sys.executable, "test_m.py"])
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertEqual(out["measurements"]["test_count"], 0)

    def test_optimized_away_assertion_cannot_authorize_success(self):
        self.write_test("from m import f\nassert f() == 1\n")
        with patch.dict(os.environ, {"PYTHONOPTIMIZE": "1"}):
            out = self.run_measure(test_argv=[sys.executable, "test_m.py"])
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertEqual(out["measurements"]["test_count"], 0)

    def test_caught_exception_inside_assertion_is_not_a_passing_check(self):
        self.write_test("try:\n    assert 1 / 0\nexcept ZeroDivisionError:\n    pass\n")
        out = self.run_measure(test_argv=[sys.executable, "test_m.py"])
        self.assertFalse(out["measurements"]["tests_pass"], out)

    def test_caught_exception_during_assertion_truth_check_is_not_passing(self):
        self.write_test("class Bad:\n    def __bool__(self): raise TypeError('bad truth')\n"
                        "try:\n    assert Bad()\nexcept TypeError:\n    pass\n")
        out = self.run_measure(test_argv=[sys.executable, "test_m.py"])
        self.assertFalse(out["measurements"]["tests_pass"], out)

    def test_failing_fixture_blocks_union_stop_authorization(self):
        self.write_test("def test_value(tmp_path):\n    assert False\n")
        baseline = self.root / "baseline"
        shutil.copytree(self.project, baseline)
        _, baseline_sha = measurement._tree_manifest(baseline, max_files=20000, max_bytes=500_000_000)
        out = self.run_measure()
        decision = union.evaluate_union(
            "tests_pass must be true.", measurement_receipt_path="receipt.json", receipt_root=self.root,
            baseline_root=baseline, candidate_root=self.project, expected_baseline_snapshot_sha256=baseline_sha,
        )
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertFalse(decision["acceptance_stop_authorized"], decision)
        self.assertFalse(decision["candidate_accepted"], decision)

    def test_command_cannot_rewrite_a_failing_test_before_evidence(self):
        self.write_test("def test_value():\n    assert False\n")
        command = [sys.executable, "-c", "from pathlib import Path; Path('test_m.py').write_text('def test_value():\\n    assert True\\n')"]
        out = self.run_measure(test_argv=command)
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertFalse(out["test_evidence"]["source_intact_after_command"])
        self.assertIn("assert False", (self.project / "test_m.py").read_text())

    def test_evidence_does_not_inherit_files_created_by_the_test_command(self):
        self.write_test("from pathlib import Path\ndef test_marker():\n    assert Path('marker.txt').exists()\n")
        out = self.run_measure(test_argv=[sys.executable, "-c", "from pathlib import Path; Path('marker.txt').touch()"])
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertFalse((self.project / "marker.txt").exists())

    def test_pytest_config_addopts_cannot_deselect_a_declared_failure(self):
        (self.project / "pytest.ini").write_text("[pytest]\naddopts = -k good\n", encoding="utf-8")
        self.write_test("def test_good():\n    assert True\n\ndef test_hidden():\n    assert False\n")
        out = self.run_measure(test_argv=[sys.executable, "-c", "pass"])
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertEqual(out["measurements"]["test_count"], 2)

    def test_uncollected_main_guard_script_is_not_hidden_by_another_test(self):
        self.write_test("def test_good(tmp_path):\n    assert tmp_path.is_dir()\n")
        self.write_test("if __name__ == '__main__':\n    assert 1 == 2\n", name="check_script.py")
        out = self.run_measure(test_paths=["test_m.py", "check_script.py"],
                               test_argv=[sys.executable, "-c", "pass"])
        self.assertFalse(out["measurements"]["tests_pass"], out)
        self.assertEqual(out["test_evidence"]["path_evidence"][1]["kind"], "ASSERTION_SCRIPT_TRACE")

    def test_stale_vacuous_receipt_cannot_authorize_union_stop(self):
        self.write_test("from m import f\nassert f() == 1\n")
        baseline = self.root / "baseline"
        shutil.copytree(self.project, baseline)
        _, baseline_sha = measurement._tree_manifest(baseline, max_files=20000, max_bytes=500_000_000)
        self.run_measure(test_argv=[sys.executable, "test_m.py"])
        receipt_path = self.root / "receipt.json"
        legacy = json.loads(receipt_path.read_text())
        legacy["measurements"]["test_count"] = 0
        legacy["test_evidence"] = {"returncode": 0, "timed_out": False, "test_count": 0}
        legacy.pop("receipt_payload_sha256")
        legacy["receipt_payload_sha256"] = measurement._sha_obj(legacy)
        receipt_path.write_text(json.dumps(legacy), encoding="utf-8")
        decision = union.evaluate_union(
            "tests_pass must be true.", measurement_receipt_path="receipt.json", receipt_root=self.root,
            baseline_root=baseline, candidate_root=self.project, expected_baseline_snapshot_sha256=baseline_sha,
        )
        self.assertFalse(decision["acceptance_stop_authorized"], decision)
        self.assertFalse(decision["candidate_accepted"], decision)

    def test_without_pytest_stdlib_unittest_still_works_but_fixture_is_unverified(self):
        venv = self.root / "no-pytest"
        subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(venv)],
                       capture_output=True, text=True, check=True, timeout=30)
        python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        self.write_test("import unittest\nclass T(unittest.TestCase):\n    def test_value(self): self.assertEqual(1, 1)\nif __name__ == '__main__': unittest.main()\n")
        with patch.dict(os.environ, {"PYTHONPATH": ""}):
            out = self.run_measure(test_argv=[str(python), "test_m.py"])
        self.assertTrue(out["measurements"]["tests_pass"], out)
        self.assertEqual(out["measurements"]["test_count"], 1)
        self.write_test("def test_value(tmp_path):\n    assert False\n")
        with patch.dict(os.environ, {"PYTHONPATH": ""}):
            out = self.run_measure(test_argv=measurement._PATCH.suite_argv(str(python), "test_m.py"))
        self.assertFalse(out["measurements"]["tests_pass"], out)
        (self.project / "pytest.ini").write_text("[pytest]\npython_functions = check_*\n", encoding="utf-8")
        self.write_test("import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n"
                        "def check_bad():\n    assert False\nif __name__ == '__main__': unittest.main()\n")
        with patch.dict(os.environ, {"PYTHONPATH": ""}):
            out = self.run_measure(test_argv=[str(python), "test_m.py"])
        self.assertFalse(out["measurements"]["tests_pass"], out)


if __name__ == "__main__":
    unittest.main()
