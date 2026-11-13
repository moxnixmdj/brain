"""A check that ran nothing is not a pass.

The defect: `unittest` exits 0 on a module it collected nothing from. The shipped check took
that as "the tests pass", so on pytest-style projects it accepted every candidate -- including
a deliberately broken one. These tests pin the repair with real subprocesses on real temporary
projects, not mocks: the whole defect lived in a process boundary, so a mocked runner would
have hidden it.

The load-bearing test is `test_a_broken_edit_is_refused_in_a_pytest_style_project`: it fails on
the legacy code path and passes on the repaired one. The controls make the gate falsifiable in
the other direction -- a genuinely passing project must still be accepted, so "refuse
everything" cannot score well here.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import check_collection_admission_v1 as A
from canonical.tools import generalization_rung_gradient_v1 as G

PYTEST_STYLE_PROJECT = {
    "pkg/__init__.py": "",
    "pkg/bounds.py": "def below(n, hi):\n    return n < hi\n",
    "tests/__init__.py": "",
    "tests/test_bounds.py": (
        "from pkg.bounds import below\n\n"
        "def test_edge_excluded():\n    assert below(10, 10) is False\n\n"
        "def test_below_included():\n    assert below(9, 10) is True\n"
    ),
}
UNITTEST_STYLE_PROJECT = {
    "pkg/__init__.py": "",
    "pkg/bounds.py": "def below(n, hi):\n    return n < hi\n",
    "tests/__init__.py": "",
    "tests/test_bounds.py": (
        "import unittest\n\nfrom pkg.bounds import below\n\n\n"
        "class Bounds(unittest.TestCase):\n"
        "    def test_edge_is_excluded(self):\n        self.assertFalse(below(10, 10))\n\n"
        "    def test_below_is_included(self):\n        self.assertTrue(below(9, 10))\n"
    ),
}
BROKEN = "def below(n, hi):\n    return None\n"


def _pytest_available() -> bool:
    done = subprocess.run([sys.executable, "-c", "import pytest"], capture_output=True)
    return done.returncode == 0


class ParserTests(unittest.TestCase):
    def test_unittest_summary_is_read_from_stderr(self):
        self.assertEqual(A.parse_unittest("", "Ran 12 tests in 0.1s\n\nOK"), 12)
        self.assertEqual(A.parse_unittest("", "Ran 1 test in 0.1s\n\nOK"), 1)

    def test_zero_and_absent_summaries_are_zero(self):
        self.assertEqual(A.parse_unittest("", "Ran 0 tests in 0.000s\n\nOK"), 0)
        self.assertEqual(A.parse_unittest("", "OK"), 0)

    def test_pytest_counts_only_tests_that_reached_a_verdict(self):
        self.assertEqual(A.parse_pytest("2 passed, 3 skipped in 0.1s", ""), 2)
        self.assertEqual(A.parse_pytest("1 failed, 4 passed in 0.2s", ""), 5)
        self.assertEqual(A.parse_pytest("no tests ran in 0.01s", ""), 0)
        self.assertEqual(A.parse_pytest("5 deselected in 0.01s", ""), 0)


class AdmissionTests(unittest.TestCase):
    def test_unknown_is_never_assent(self):
        for verdict in (
            {"ran": False, "passed": None},
            {"ran": False, "passed": True},   # a lie the old code told
            {"ran": True, "passed": None},
        ):
            self.assertFalse(A.accepts(verdict), verdict)
            self.assertFalse(A.accepts(verdict, expect="FAIL"), verdict)

    def test_a_real_verdict_is_honoured_in_both_modes(self):
        self.assertTrue(A.accepts({"ran": True, "passed": True}, expect="PASS"))
        self.assertFalse(A.accepts({"ran": True, "passed": False}, expect="PASS"))
        self.assertTrue(A.accepts({"ran": True, "passed": False}, expect="FAIL"))

    def test_an_empty_module_name_runs_nothing(self):
        verdict = A.run_check("", cwd=ROOT)
        self.assertFalse(verdict["ran"])
        self.assertIsNone(verdict["passed"])
        self.assertEqual(verdict["reason"], A.RAN_NO_TESTS)


class RealProjectTests(unittest.TestCase):
    """Real subprocesses on real files: the defect lived at a process boundary."""

    def test_a_unittest_project_is_still_accepted_and_still_discriminates(self):
        check = G.Check("tests", UNITTEST_STYLE_PROJECT, "pkg/bounds.py")
        try:
            self.assertTrue(check.available, check.reason)
            self.assertTrue(check.accepts("pkg/bounds.py", UNITTEST_STYLE_PROJECT["pkg/bounds.py"]))
            self.assertFalse(check.accepts("pkg/bounds.py", BROKEN))
        finally:
            check.close()

    @unittest.skipUnless(_pytest_available(), "pytest collector is not installed")
    def test_a_broken_edit_is_refused_in_a_pytest_style_project(self):
        """THE load-bearing test. Legacy accepted BROKEN here; the repair must refuse it."""
        check = G.Check("tests", PYTEST_STYLE_PROJECT, "pkg/bounds.py")
        try:
            self.assertTrue(check.available, check.reason)
            self.assertEqual(check.last_collection["runner"], "pytest")
            self.assertGreaterEqual(check.last_collection["collected"], 2)
            self.assertTrue(check.accepts("pkg/bounds.py", PYTEST_STYLE_PROJECT["pkg/bounds.py"]))
            self.assertFalse(check.accepts("pkg/bounds.py", BROKEN))
        finally:
            check.close()

    @unittest.skipUnless(_pytest_available(), "pytest collector is not installed")
    def test_the_check_is_reported_as_discriminating_not_merely_available(self):
        report = G.check_discriminates(PYTEST_STYLE_PROJECT, "pkg/bounds.py")
        self.assertTrue(report["available"], report["reason"])
        self.assertTrue(report["accepts_the_file_as_it_is"])
        self.assertTrue(report["rejects_a_broken_one"])

    def test_the_legacy_runner_really_does_accept_the_broken_edit(self):
        """Pins the counterfactual, so the defect cannot be quietly redefined away."""
        import os
        import tempfile

        directory = pathlib.Path(tempfile.mkdtemp(prefix="legacy-vacuity-"))
        try:
            for path, text in PYTEST_STYLE_PROJECT.items():
                target = directory / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
            (directory / "pkg/bounds.py").write_text(BROKEN, encoding="utf-8")
            done = subprocess.run(
                [sys.executable, "-m", "unittest", "tests.test_bounds"],
                cwd=str(directory), capture_output=True, timeout=120,
                env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(directory),
                     "HOME": str(directory)},
            )
            self.assertEqual(done.returncode, 0, "unittest is expected to pass vacuously")
            self.assertEqual(A.parse_unittest(done.stdout.decode(), done.stderr.decode()), 0)
        finally:
            import shutil

            shutil.rmtree(directory, ignore_errors=True)

    def test_a_project_with_no_tests_is_unavailable_not_passing(self):
        files = {"pkg/__init__.py": "", "pkg/bounds.py": "def below(n, hi):\n    return n < hi\n"}
        check = G.Check("tests", files, "pkg/bounds.py")
        try:
            self.assertFalse(check.available)
            self.assertEqual(check.reason, "CHECK_NO_TEST_MODULE")
            self.assertFalse(check.accepts("pkg/bounds.py", BROKEN))
        finally:
            check.close()

    def test_a_module_importing_a_missing_dependency_is_not_a_pass(self):
        files = {
            "pkg/__init__.py": "",
            "pkg/bounds.py": "def below(n, hi):\n    return n < hi\n",
            "tests/__init__.py": "",
            "tests/test_bounds.py": (
                "from pkg.bounds import below\n"
                "import a_dependency_that_is_not_installed_anywhere\n\n"
                "def test_it():\n    assert below(1, 2)\n"
            ),
        }
        check = G.Check("tests", files, "pkg/bounds.py")
        try:
            self.assertFalse(check.available)
            self.assertEqual(check.reason, A.DEPENDENCY_MISSING)
        finally:
            check.close()


if __name__ == "__main__":
    unittest.main()
