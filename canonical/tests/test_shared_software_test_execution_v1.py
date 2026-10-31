"""Real-framework and stdlib controls for the shared SWE test runner.

The fixtures are temporary repositories. The independent observable is the
actual exit status and side effects of the tests, with a separate native pytest
invocation as a differential control when pytest is available. These are local
regressions, not capability or independent-verification credit.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from canonical.runtime.bound_capabilities import python_test_guided_patch_search_v1 as runner

PYTEST_AVAILABLE = importlib.util.find_spec("pytest") is not None


class SharedTestExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="brain_test_semantics_")
        self.root = Path(self.tmp.name)
        self.env = dict(os.environ)
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

    def tearDown(self):
        self.tmp.cleanup()

    def file(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def shared(self, *paths, without_site_packages=False, timeout=30):
        command = runner.suite_argv(sys.executable, *paths)
        env = dict(self.env)
        if without_site_packages:
            command.insert(1, "-S")
            env.pop("PYTHONPATH", None)
        return subprocess.run(command, cwd=self.root, env=env, text=True,
                              capture_output=True, timeout=timeout)

    def native(self, *paths):
        command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
        return subprocess.run(command + [str(p) for p in paths], cwd=self.root,
                              env=self.env, text=True, capture_output=True, timeout=30)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_failing_fixture_is_not_silently_skipped(self):
        path = self.file("test_fixture.py", """
def test_plain():
    assert 2 + 3 == 5

def test_fixture(tmp_path):
    assert not tmp_path.exists()
""")
        expected = self.native(path)
        observed = self.shared(path)
        self.assertNotEqual(expected.returncode, 0, expected.stdout)
        self.assertNotEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("Ran 2 tests", observed.stdout + observed.stderr)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_passing_fixture_in_conftest_is_actually_executed(self):
        marker = self.root / "executed.txt"
        self.file("conftest.py", """
import pytest

@pytest.fixture
def provided_value():
    return 73
""")
        path = self.file("test_conftest.py", f"""
from pathlib import Path

def test_uses_fixture(provided_value):
    assert provided_value == 73
    Path({str(marker)!r}).write_text(str(provided_value))
""")
        result = self.shared(path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(marker.read_text(), "73")
        self.assertIn("Ran 1 test", result.stdout + result.stderr)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_all_parameterized_cases_run(self):
        path = self.file("test_params.py", """
import pytest

@pytest.mark.parametrize('value, expected', [(3, 3), (4, 99)])
def test_values(value, expected):
    assert value == expected
""")
        expected = self.native(path)
        observed = self.shared(path)
        self.assertNotEqual(expected.returncode, 0, expected.stdout)
        self.assertNotEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("Ran 2 tests", observed.stdout + observed.stderr)

    def test_mixed_unittest_and_bare_functions_do_not_hide_each_other(self):
        path = self.file("test_mixed.py", """
import unittest

class TestNumbers(unittest.TestCase):
    def test_passing(self):
        self.assertEqual(1 + 1, 2)

def test_failing_bare_function():
    assert 2 + 2 == 5
""")
        observed = self.shared(path, without_site_packages=True)
        self.assertNotEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("Ran 2 tests", observed.stdout + observed.stderr)

    def test_missing_pytest_does_not_turn_a_fixture_suite_green(self):
        path = self.file("test_unavailable.py", """
def test_requires_fixture(tmp_path):
    assert not tmp_path.exists()
""")
        observed = self.shared(path, without_site_packages=True)
        self.assertNotEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("PYTEST_REQUIRED", observed.stdout + observed.stderr)

    def test_missing_pytest_does_not_ignore_a_declared_plugin(self):
        path = self.file("test_plugin.py", "pytest_plugins = ['project_plugin']\ndef test_plain():\n    assert 3 + 4 == 7\n")
        observed = self.shared(path, without_site_packages=True)
        self.assertNotEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("PYTEST_REQUIRED", observed.stdout + observed.stderr)

    def test_pure_unittest_still_works_without_pytest(self):
        path = self.file("test_stdlib.py", """
import unittest

class TestMath(unittest.TestCase):
    def test_product(self):
        self.assertEqual(6 * 7, 42)
""")
        observed = self.shared(path, without_site_packages=True)
        self.assertEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("Ran 1 test", observed.stdout + observed.stderr)

    def test_aliased_and_inherited_unittest_cases_work_without_pytest(self):
        path = self.file("test_alias.py", """
from unittest import TestCase as BaseCase
class Base(BaseCase):
    def helper(self):
        return 42
class TestDerived(Base):
    def test_value(self):
        self.assertEqual(self.helper(), 42)
""")
        observed = self.shared(path, without_site_packages=True)
        self.assertEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("Ran 1 test", observed.stdout + observed.stderr)

    def test_a_custom_testcase_is_not_misclassified_as_unittest(self):
        self.file("helper.py", "class TestCase:\n    pass\n")
        path = self.file("test_custom.py", """
from helper import TestCase
class TestCustom(TestCase):
    def test_missing(self):
        assert 2 + 2 == 5
def test_plain():
    assert 2 + 2 == 4
""")
        observed = self.shared(path, without_site_packages=True)
        self.assertNotEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("PYTEST_REQUIRED", observed.stdout + observed.stderr)

    def test_unittest_async_case_works_without_pytest(self):
        path = self.file("test_async.py", """
import unittest as ut
class TestAsync(ut.IsolatedAsyncioTestCase):
    async def test_value(self):
        self.assertEqual(8 * 5, 40)
""")
        observed = self.shared(path, without_site_packages=True)
        self.assertEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("Ran 1 test", observed.stdout + observed.stderr)

    def test_source_encoding_cookie_is_honored_without_pytest(self):
        path = self.root / "test_latin1.py"
        path.write_bytes(b"# coding: latin-1\ndef test_text():\n    assert len('caf\xe9') == 4\n")
        observed = self.shared(path, without_site_packages=True)
        self.assertEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("Ran 1 test", observed.stdout + observed.stderr)

    def test_pure_bare_functions_still_work_without_pytest(self):
        path = self.file("test_simple.py", """
def test_sum():
    assert 7 + 8 == 15
""")
        observed = self.shared(path, without_site_packages=True)
        self.assertEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("Ran 1 test", observed.stdout + observed.stderr)

    def test_no_targets_do_not_count_as_a_passing_suite(self):
        observed = self.shared(without_site_packages=True)
        self.assertNotEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("NO_TESTS_COLLECTED", observed.stdout + observed.stderr)

    def test_empty_module_does_not_count_as_a_passing_suite(self):
        path = self.file("test_empty.py", '"""No tests in this module."""\n')
        observed = self.shared(path, without_site_packages=True)
        self.assertNotEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("NO_TESTS_COLLECTED", observed.stdout + observed.stderr)

    def test_all_skipped_unittest_is_not_a_passing_verification(self):
        path = self.file("test_skipped.py", """
import unittest
class TestNoOracle(unittest.TestCase):
    @unittest.skip('not implemented')
    def test_skipped(self):
        self.fail('not run')
""")
        observed = self.shared(path, without_site_packages=True)
        output = observed.stdout + observed.stderr
        self.assertNotEqual(observed.returncode, 0, output)
        self.assertIn("NO_PASSING_TESTS_EXECUTED", output)
        self.assertIn("errors=1", output)
        self.assertIn("skipped=1", output)

    def test_expected_unittest_failures_are_not_counted_as_passes(self):
        path = self.file("test_expected_failure.py", """
import unittest
class TestExpectedFailure(unittest.TestCase):
    def test_pass(self):
        self.assertEqual(6 * 7, 42)
    @unittest.expectedFailure
    def test_expected_failure(self):
        self.fail('expected')
""")
        observed = self.shared(path, without_site_packages=True)
        output = observed.stdout + observed.stderr
        self.assertEqual(observed.returncode, 0, output)
        self.assertIn("Ran 2 tests", output)
        self.assertIn("skipped=1", output)

    def test_auditor_reports_the_all_skipped_suite_as_red(self):
        from canonical.runtime.bound_capabilities import python_test_audit

        self.file("test_skipped.py", """
import unittest
class TestNoOracle(unittest.TestCase):
    @unittest.skip('not implemented')
    def test_skipped(self):
        self.fail('not run')
""")
        result = python_test_audit.run({"source_root": ".", "test_paths": ["test_skipped.py"],
                                        "output_path": "audit.json"}, self.root)
        self.assertEqual(result["passed_count"], 0, result)
        self.assertEqual((result["error_count"], result["skipped_count"]), (1, 1), result)
        self.assertFalse(result["output_verified"], result)
        self.assertTrue(result["report_verified"], result)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_all_skipped_pytest_is_not_a_passing_verification(self):
        path = self.file("test_pytest_skipped.py", """
import pytest
@pytest.mark.skip(reason='not implemented')
def test_skipped():
    assert False
""")
        observed = self.shared(path)
        output = observed.stdout + observed.stderr
        self.assertNotEqual(observed.returncode, 0, output)
        self.assertIn("Ran 2 tests", output)  # one skipped case and one suite error
        self.assertIn("errors=1", output)
        self.assertIn("skipped=1", output)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_expected_pytest_failures_are_not_counted_as_passes(self):
        path = self.file("test_pytest_xfail.py", """
import pytest
def test_pass():
    assert len('brain') == 5
@pytest.mark.xfail
def test_expected_failure():
    assert False
""")
        observed = self.shared(path)
        output = observed.stdout + observed.stderr
        self.assertEqual(observed.returncode, 0, output)
        self.assertIn("Ran 2 tests", output)
        self.assertIn("skipped=1", output)

    def test_stdlib_test_raising_zero_system_exit_is_not_a_pass(self):
        path = self.file("test_exit.py", "def test_exit():\n    raise SystemExit(0)\n")
        observed = self.shared(path, without_site_packages=True)
        output = observed.stdout + observed.stderr
        self.assertNotEqual(observed.returncode, 0, output)
        self.assertIn("TEST_RAISED_SYSTEM_EXIT_ZERO", output)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_pytest_test_raising_zero_system_exit_is_not_a_pass(self):
        path = self.file("test_exit.py", "def test_exit(tmp_path):\n    raise SystemExit(0)\n")
        observed = self.shared(path)
        output = observed.stdout + observed.stderr
        self.assertNotEqual(observed.returncode, 0, output)
        self.assertIn("TEST_RAISED_SYSTEM_EXIT_ZERO", output)

    def test_successful_guarded_script_exit_remains_supported(self):
        marker = self.root / "script_executed.txt"
        script = self.file("test_script.py", f"""
from pathlib import Path
import sys
if __name__ == '__main__':
    Path({str(marker)!r}).write_text('executed')
    sys.exit(0)
""")
        observed = self.shared(script, without_site_packages=True)
        self.assertEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertEqual(marker.read_text(), "executed")

    def test_successful_script_exit_cannot_hide_a_later_failure(self):
        script = self.file("test_script.py", "import sys\nif __name__ == '__main__':\n    sys.exit(0)\n")
        failing = self.file("test_bad.py", "def test_bad():\n    assert 2 + 2 == 5\n")
        observed = self.shared(script, failing, without_site_packages=True)
        output = observed.stdout + observed.stderr
        self.assertNotEqual(observed.returncode, 0, output)
        self.assertIn("AssertionError", output)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_multiple_requested_files_are_evaluated_together(self):
        first = self.file("test_first.py", "def test_first():\n    assert 4 > 2\n")
        second = self.file("test_second.py", "def test_second(tmp_path):\n    assert not tmp_path.exists()\n")
        expected = self.native(first, second)
        observed = self.shared(first, second)
        self.assertNotEqual(expected.returncode, 0, expected.stdout)
        self.assertNotEqual(observed.returncode, 0, observed.stdout + observed.stderr)
        self.assertIn("Ran 2 tests", observed.stdout + observed.stderr)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_empty_requested_file_does_not_disappear_next_to_a_passing_file(self):
        fixture = self.file("test_fixture.py", "def test_fixture(tmp_path):\n    assert tmp_path.exists()\n")
        empty = self.file("test_empty.py", '"""No tests here."""\n')
        observed = self.shared(fixture, empty)
        output = observed.stdout + observed.stderr
        self.assertNotEqual(observed.returncode, 0, output)
        self.assertIn("NO_TESTS_COLLECTED_IN_TARGET", output)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_guarded_script_is_not_lost_in_a_mixed_pytest_run(self):
        fixture = self.file("test_fixture.py", "def test_fixture(tmp_path):\n    assert tmp_path.exists()\n")
        script = self.file("test_script.py", "if __name__ == '__main__':\n    assert False, 'script ran'\n")
        observed = self.shared(fixture, script)
        output = observed.stdout + observed.stderr
        self.assertNotEqual(observed.returncode, 0, output)
        self.assertIn("script ran", output)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_native_fixture_trace_keeps_project_lines_and_failure(self):
        from canonical.runtime.bound_capabilities import python_dynamic_fault_localizer_v1 as localizer

        self.file("calc.py", "def twice(x):\n    return x + 1\n")
        test = self.file("test_calc.py", "import calc\ndef test_bad(tmp_path):\n    assert calc.twice(2) == 4\n")
        env = runner._source_env(self.root)
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
        trace = localizer._trace_one(self.root, test, 15, 100000, env)
        self.assertFalse(trace["pass"])
        self.assertTrue(any(row[0] == "calc.py" and row[2] == "twice"
                            for row in trace["events"]), trace)
        self.assertTrue(any(row[0] == "test_calc.py" for row in trace["traceback"]), trace)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_native_fixture_provenance_keeps_project_calls_and_values(self):
        from canonical.runtime.bound_capabilities import python_interprocedural_value_provenance_v1 as provenance

        self.file("calc.py", "def twice(x):\n    return x + 1\n")
        test = self.file("test_calc.py", "import calc\ndef test_bad(tmp_path):\n    assert calc.twice(2) == 4\n")
        env = runner._source_env(self.root)
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
        trace = provenance._trace_one(self.root, test, 15, 100000, 80, env)
        self.assertFalse(trace["pass"])
        calls = [e for e in trace["events"] if e["event"] == "call"
                 and e["callee"]["path"] == "calc.py" and e["callee"]["function"] == "twice"]
        self.assertEqual(len(calls), 1, trace)
        self.assertEqual(calls[0]["args"]["x"]["value"], 2)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_test_guided_search_can_repair_a_real_fixture_suite(self):
        source = self.file("calc.py", "def add(a, b):\n    return a - b\n")
        test = self.file("test_calc.py", """
import calc

def test_add(tmp_path):
    assert tmp_path.exists()
    assert calc.add(2, 3) == 5
    assert calc.add(-1, 2) == 1
""")
        before = source.read_bytes()
        self.assertNotEqual(self.native(test).returncode, 0)
        result = runner.run({"source_path": "calc.py", "test_paths": ["test_calc.py"],
                             "output_path": "result.json", "max_candidates": 12,
                             "timeout_s": 10}, self.root)
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["winning_mutation"]["kind"], "BINOP_SWAP")
        self.assertEqual(source.read_bytes(), before)
        fixed = before.replace(b"a - b", b"a + b")
        self.assertEqual(hashlib.sha256(fixed).hexdigest(), result["candidate_source_sha256"])
        source.write_bytes(fixed)
        replay = self.native(test)
        self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)

    @unittest.skipUnless(PYTEST_AVAILABLE, "native pytest is not installed")
    def test_test_guided_search_will_not_accept_a_fixture_failing_candidate(self):
        source = self.file("calc.py", "def twice(x):\n    return x + 1\n")
        test = self.file("test_calc.py", """
import calc

def test_visible():
    assert calc.twice(2) == 4

def test_fixture(tmp_path):
    assert calc.twice(3) == 6
""")
        before = source.read_bytes()
        result = runner.run({"source_path": "calc.py", "test_paths": ["test_calc.py"],
                             "output_path": "result.json", "max_candidates": 12,
                             "timeout_s": 10}, self.root)
        self.assertFalse(result["pass"], result)
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(self.native(test).returncode, 1)


if __name__ == "__main__":
    unittest.main()
