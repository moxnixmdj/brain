"""Real-pytest adversarial controls for Brain's shared repair/localization runner."""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

from canonical.runtime.bound_capabilities import python_dynamic_fault_localizer_v1 as localizer
from canonical.runtime.bound_capabilities import python_interprocedural_value_provenance_v1 as provenance
from canonical.runtime.bound_capabilities import python_repair_apply_verified_v1 as repair_apply
from canonical.runtime.bound_capabilities import python_software_repair_loop_v1 as multi_repair
from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as patch


class RepairRunnerPytestRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        (self.root / "m.py").write_text("def f():\n    return 0\n", encoding="utf-8")

    def write_test(self, text: str):
        (self.root / "test_m.py").write_text(text, encoding="utf-8")

    def run_shared(self, isolated=False):
        argv = patch.suite_argv(sys.executable, "test_m.py")
        if isolated:
            argv.insert(1, "-S")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(argv, cwd=self.root, env=env, text=True,
                              capture_output=True, timeout=20)

    def run_pytest(self):
        return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                               "test_m.py"], cwd=self.root, text=True,
                              capture_output=True, timeout=20)

    def test_failing_fixture_is_visible_to_runner_and_localizer(self):
        self.write_test("from m import f\ndef test_value(tmp_path):\n    assert f() == 1\n")
        self.assertNotEqual(self.run_pytest().returncode, 0)
        proc = self.run_shared()
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = localizer.run({"source_root": ".", "test_paths": ["test_m.py"],
                                "output_path": "localization.json", "timeout_s": 15}, self.root)
        self.assertEqual(result["failing_test_count"], 1)
        self.assertTrue(any(row["path"] == "m.py" for row in result["ranked_lines"]))

    def test_fixture_repair_replays_with_real_pytest(self):
        self.write_test("from m import f\ndef test_value(tmp_path):\n    assert f() == 1\n")
        result = patch.run({"source_path": "m.py", "test_paths": ["test_m.py"],
                            "output_path": "patch.json", "timeout_s": 10,
                            "max_candidates": 20}, self.root)
        self.assertTrue(result["pass"], result)
        self.assertEqual((self.root / "m.py").read_text(), "def f():\n    return 0\n")
        applied = subprocess.run(["git", "apply", "-"], cwd=self.root, input=result["unified_diff"],
                                 text=True, capture_output=True, timeout=10)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        oracle = self.run_pytest()
        self.assertEqual(oracle.returncode, 0, oracle.stdout + oracle.stderr)

    def test_patch_output_cannot_overwrite_source_or_test(self):
        self.write_test("from m import f\ndef test_value(): assert f() == 1\n")
        for output in ("m.py", "test_m.py"):
            with self.subTest(output=output):
                original_source = (self.root / "m.py").read_bytes()
                original_test = (self.root / "test_m.py").read_bytes()
                with self.assertRaisesRegex(patch.PatchSearchError, "OUTPUT_OVERLAPS_INPUT"):
                    patch.run({"source_path": "m.py", "test_paths": ["test_m.py"],
                               "output_path": output, "timeout_s": 10}, self.root)
                self.assertEqual((self.root / "m.py").read_bytes(), original_source)
                self.assertEqual((self.root / "test_m.py").read_bytes(), original_test)

    def test_patch_search_rejects_and_restores_test_files_modified_by_a_trial(self):
        script = ("from pathlib import Path\nfrom m import f\ndef test_value():\n"
                  "    if f() == 1: Path(__file__).write_text('def test_value(): assert True\\n')\n"
                  "    assert f() == 1\n")
        self.write_test(script)
        with self.assertRaisesRegex(patch.PatchSearchError, "TEST_OR_SOURCE_MODIFIED"):
            patch.run({"source_path": "m.py", "test_paths": ["test_m.py"],
                       "output_path": "patch.json", "timeout_s": 10}, self.root)
        self.assertEqual((self.root / "test_m.py").read_text(), script)
        self.assertEqual((self.root / "m.py").read_text(), "def f():\n    return 0\n")

    def test_patch_search_stops_at_global_wall_budget_and_restores_source(self):
        self.write_test("import time\nfrom m import f\ndef test_value():\n"
                        "    if f() != 0: time.sleep(3)\n    assert f() == 99\n")
        started = time.monotonic()
        result = patch.run({"source_path": "m.py", "test_paths": ["test_m.py"],
                            "output_path": "patch.json", "timeout_s": 10, "max_candidates": 2,
                            "max_wall_time_s": 1}, self.root)
        self.assertLess(time.monotonic() - started, 2.5)
        self.assertFalse(result["pass"])
        self.assertTrue(result["wall_time_budget_exhausted"])
        self.assertEqual(result["status"], "OPEN__WALL_TIME_BUDGET_EXHAUSTED")
        self.assertEqual((self.root / "m.py").read_text(), "def f():\n    return 0\n")

    def test_provenance_traces_real_pytest_fixture_without_tracing_pytest_itself(self):
        (self.root / "m.py").write_text(
            "def inner(x):\n    return x + 1\ndef outer(x):\n    return inner(x) * 2\n", encoding="utf-8")
        self.write_test("from m import outer\ndef test_value(tmp_path):\n    assert outer(2) == 8\n")
        result = provenance.run({"source_root": ".", "test_paths": ["test_m.py"],
                                 "output_path": "provenance.json", "timeout_s": 15}, self.root)
        self.assertEqual(result["failing_test_count"], 1)
        self.assertTrue(any(row["caller"]["function"] == "outer" and row["callee"]["function"] == "inner"
                            for row in result["ranked_call_edges"]))
        self.assertTrue(result["pass"])
        self.assertTrue(any(row["caller_symbol"] == "outer" and row["callee_symbol"] == "inner"
                            and row["assigned_to"] == ["<return>"]
                            for row in result["interprocedural_hypotheses"]))

    def test_subprocess_failure_without_source_trace_is_not_ranked_success(self):
        self.write_test("import subprocess, sys\ndef test_child():\n"
                        "    subprocess.run([sys.executable, '-c', 'from m import f; assert f() == 1'], check=True)\n")
        self.assertNotEqual(self.run_pytest().returncode, 0)
        result = localizer.run({"source_root": ".", "test_paths": ["test_m.py"],
                                "output_path": "localization.json", "timeout_s": 15}, self.root)
        self.assertEqual(result["failing_test_count"], 1)
        self.assertFalse(result["pass"])
        self.assertTrue(result["status"].startswith("OPEN__"))
        self.assertEqual(result["ranked_symbols"], [])
        prov = provenance.run({"source_root": ".", "test_paths": ["test_m.py"],
                               "output_path": "provenance.json", "timeout_s": 15}, self.root)
        self.assertFalse(prov["pass"])
        self.assertEqual(prov["interprocedural_hypotheses"], [])
        self.assertTrue(prov["status"].startswith("OPEN__"))

    def test_unittest_and_pytest_functions_both_run(self):
        self.write_test("import unittest\nclass Good(unittest.TestCase):\n"
                        "    def test_good(self): self.assertEqual(2 + 2, 4)\n"
                        "def test_bad():\n    assert 2 + 2 == 5\n")
        self.assertNotEqual(self.run_pytest().returncode, 0)
        proc = self.run_shared()
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_passing_parameterized_fixture_and_autouse_context(self):
        (self.root / "conftest.py").write_text(
            "import os, pytest\n@pytest.fixture(autouse=True)\n"
            "def set_marker(monkeypatch):\n    monkeypatch.setenv('BRAIN_RUNNER_FIXTURE', 'present')\n",
            encoding="utf-8")
        self.write_test("import os, pytest\n@pytest.mark.parametrize('n', [1, 2])\n"
                        "def test_value(n, tmp_path):\n"
                        "    assert n in (1, 2) and tmp_path.is_dir()\n"
                        "    assert os.environ['BRAIN_RUNNER_FIXTURE'] == 'present'\n")
        oracle = self.run_pytest()
        self.assertEqual(oracle.returncode, 0, oracle.stdout + oracle.stderr)
        proc = self.run_shared()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_multiple_pytest_files_share_one_real_session(self):
        (self.root / "conftest.py").write_text(
            "import pytest\n@pytest.fixture(scope='session')\ndef bucket(): return []\n", encoding="utf-8")
        self.write_test("def test_first(bucket): bucket.append(1)\n")
        other = self.root / "test_other.py"
        other.write_text("def test_second(bucket): assert bucket == []\n", encoding="utf-8")
        oracle = subprocess.run([sys.executable, "-m", "pytest", "-q", "test_m.py", "test_other.py"],
                                cwd=self.root, text=True, capture_output=True, timeout=15)
        self.assertNotEqual(oracle.returncode, 0)
        proc = subprocess.run(patch.suite_argv(sys.executable, self.root / "test_m.py", other),
                              cwd=self.root, text=True, capture_output=True, timeout=15)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_multi_edit_repair_does_not_accept_individual_files_that_fail_together(self):
        (self.root / "conftest.py").write_text(
            "import pytest\n@pytest.fixture(scope='session')\ndef bucket(): return []\n", encoding="utf-8")
        self.write_test("from m import f\ndef test_first(bucket):\n    bucket.append(1)\n    assert f() == 1\n")
        (self.root / "test_other.py").write_text("def test_second(bucket): assert bucket == []\n", encoding="utf-8")
        result = multi_repair.run({"source_paths": ["m.py"], "test_paths": ["test_m.py", "test_other.py"],
                                   "output_path": "repair.json", "max_edits": 1, "max_candidates": 20,
                                   "timeout_s": 10}, self.root)
        self.assertFalse(result["pass"], result)
        self.assertEqual(result["patches"], [])
        self.assertEqual((self.root / "m.py").read_text(), "def f():\n    return 0\n")

    def test_passing_pytest_file_cannot_hide_an_uncollected_or_skipped_file(self):
        self.write_test("def test_good(tmp_path): assert tmp_path.is_dir()\n")
        other = self.root / "test_other.py"
        for content in ("value = 1\n", "import pytest\n@pytest.mark.skip(reason='later')\n"
                        "def test_skipped(): assert False\n"):
            with self.subTest(content=content):
                other.write_text(content, encoding="utf-8")
                proc = subprocess.run(patch.suite_argv(sys.executable, self.root / "test_m.py", other),
                                      cwd=self.root, text=True, capture_output=True, timeout=15)
                self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_assertion_script_can_run_before_a_pytest_session(self):
        script = self.root / "check.py"
        script.write_text("from m import f\nassert f() == 0\n", encoding="utf-8")
        self.write_test("def test_good(tmp_path): assert tmp_path.is_dir()\n")
        proc = subprocess.run(patch.suite_argv(sys.executable, script, self.root / "test_m.py"),
                              cwd=self.root, text=True, capture_output=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_configured_pytest_options_are_not_silently_ignored(self):
        (self.root / "pytest.ini").write_text("[pytest]\naddopts = --strict-markers\n", encoding="utf-8")
        self.write_test("import pytest\n@pytest.mark.undeclared\ndef test_value():\n    assert True\n")
        self.assertNotEqual(self.run_pytest().returncode, 0)
        proc = self.run_shared()
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_configured_deselection_does_not_claim_full_file_pass(self):
        (self.root / "pytest.ini").write_text("[pytest]\naddopts = -k good\n", encoding="utf-8")
        self.write_test("def test_good(): assert True\ndef test_bad(): assert False\n")
        self.assertEqual(self.run_pytest().returncode, 0)
        proc = self.run_shared()
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_missing_pytest_for_fixture_is_not_a_green_exit(self):
        self.write_test("def test_value(tmp_path):\n    assert tmp_path.is_dir()\n")
        proc = self.run_shared(isolated=True)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PYTEST", (proc.stdout + proc.stderr).upper())

    def test_no_pytest_is_needed_for_plain_unittest_and_mixed_bare_functions(self):
        self.write_test("import unittest\nclass Good(unittest.TestCase):\n"
                        "    def test_good(self): self.assertEqual(2 + 2, 4)\n"
                        "def test_also_good():\n    assert 3 + 3 == 6\n")
        proc = self.run_shared(isolated=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Ran 2 tests", proc.stderr)

    def test_skipped_only_suite_is_not_passing_test_evidence(self):
        self.write_test("import unittest\nclass Skipped(unittest.TestCase):\n"
                        "    @unittest.skip('not run')\n    def test_value(self):\n"
                        "        self.assertEqual(1, 2)\n")
        proc = self.run_shared(isolated=True)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_assertion_script_remains_supported_without_pytest_and_runs_once(self):
        self.write_test("from pathlib import Path\nfrom m import f\n"
                        "p = Path('calls.txt')\n"
                        "p.write_text(p.read_text() + 'x' if p.exists() else 'x')\n"
                        "assert f() == 0\n")
        self.assertEqual(self.run_shared(isolated=True).returncode, 0)
        self.assertEqual((self.root / "calls.txt").read_text(), "x")
        self.write_test("from m import f\nassert f() == 1\n")
        self.assertNotEqual(self.run_shared(isolated=True).returncode, 0)

    def test_dead_or_swallowed_assertion_script_is_not_accepted(self):
        for script in ("if False: assert False\n", "try:\n    assert False\nexcept AssertionError:\n    pass\n"):
            with self.subTest(script=script):
                self.write_test(script)
                result = self.run_shared(isolated=True)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_zero_exit_before_test_discovery_is_not_a_pass(self):
        self.write_test("import sys\nsys.exit(0)\ndef test_failure(): assert False\n")
        result = self.run_shared(isolated=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_system_exit_zero_inside_a_test_is_a_failure(self):
        self.write_test("import sys\ndef test_exit():\n    sys.exit(0)\n")
        oracle = self.run_pytest()
        self.assertNotEqual(oracle.returncode, 0)
        proc = self.run_shared(isolated=True)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_process_exit_before_completion_is_runner_infrastructure_error(self):
        self.write_test("import os\nos._exit(0)\n")
        with self.assertRaisesRegex(patch.PatchSearchError, "TEST_RUNNER_INFRASTRUCTURE"):
            patch.run({"source_path": "m.py", "test_paths": ["test_m.py"],
                       "output_path": "patch.json", "timeout_s": 10}, self.root)

    def test_in_place_repair_rejects_incomplete_shared_runner(self):
        self.write_test("import os\nos._exit(0)\n")
        result = repair_apply.run({"source_root": ".", "test_paths": ["test_m.py"],
                                   "output_path": "report.json", "timeout_s": 10}, self.root)
        self.assertFalse(result["pass"], result)
        self.assertFalse(result["applied"])
        self.assertTrue(result["status"].startswith("FAIL_CLOSED__"))

    def test_generator_style_tests_do_not_silently_pass(self):
        self.write_test("def test_generator():\n    yield lambda: False\n")
        self.assertNotEqual(self.run_shared().returncode, 0)

    def test_python_optimized_assertions_cannot_yield_a_green_runner(self):
        self.write_test("from m import f\nassert f() == 1\n")
        proc = subprocess.run(patch.suite_argv(sys.executable, self.root / "test_m.py"), cwd=self.root,
                              env={**os.environ, "PYTHONOPTIMIZE": "1"},
                              text=True, capture_output=True, timeout=15)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
