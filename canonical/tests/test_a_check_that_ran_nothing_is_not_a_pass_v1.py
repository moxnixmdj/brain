"""The collector must be REACHABLE, or the vacuity guard silently discards real checks.

Main already refuses to call `Ran 0 tests` a pass, and falls back to pytest for pytest-shaped
modules. That guard is correct and is tested in
`test_the_check_stands_up_what_verification_needs_20261112_V1.py` (with `_pytest_importable`
monkeypatched, so it pins the decision, not the environment).

This file pins the other half: whether the fallback can actually be reached. `_env` used to
build PYTHONPATH from the project copy alone, so a pytest installed anywhere else -- which is
every real run, because the copy holds one pull request's files and no site-packages -- was
invisible. `_pytest_importable()` then returned False and the check was dropped as
CHECK_NO_DISCOVERABLE_TESTS. Safe, but the 943 pytest-shaped files stayed unverifiable for a
reason that has nothing to do with the project under test.

These are real subprocesses on real temporary projects, not mocks: the defect lived in a
process environment, so a mocked runner would have hidden it.

The load-bearing test is `test_a_broken_edit_is_refused_in_a_pytest_style_project`. The controls
run in the other direction, so "refuse everything" cannot score well here.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    return subprocess.run([sys.executable, "-c", "import pytest"],
                          capture_output=True).returncode == 0


def _write_project(files: dict[str, str]) -> pathlib.Path:
    directory = pathlib.Path(tempfile.mkdtemp(prefix="collector-reach-"))
    for path, text in files.items():
        target = directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return directory


class CollectorReachabilityTests(unittest.TestCase):
    @unittest.skipUnless(_pytest_available(), "pytest collector is not installed")
    def test_a_broken_edit_is_refused_in_a_pytest_style_project(self):
        """THE load-bearing test: the fallback is reached, runs, and refuses a broken edit."""
        check = G.Check("tests", PYTEST_STYLE_PROJECT, "pkg/bounds.py")
        try:
            self.assertTrue(check.available, check.reason)
            self.assertTrue(check.accepts("pkg/bounds.py", PYTEST_STYLE_PROJECT["pkg/bounds.py"]))
            self.assertFalse(check.accepts("pkg/bounds.py", BROKEN))
        finally:
            check.close()

    @unittest.skipUnless(_pytest_available(), "pytest collector is not installed")
    def test_the_check_discriminates_rather_than_merely_being_available(self):
        report = G.check_discriminates(PYTEST_STYLE_PROJECT, "pkg/bounds.py")
        self.assertTrue(report["available"], report["reason"])
        self.assertTrue(report["accepts_the_file_as_it_is"])
        self.assertTrue(report["rejects_a_broken_one"])

    def test_a_unittest_project_is_unaffected_and_still_discriminates(self):
        check = G.Check("tests", UNITTEST_STYLE_PROJECT, "pkg/bounds.py")
        try:
            self.assertTrue(check.available, check.reason)
            self.assertTrue(check.accepts("pkg/bounds.py", UNITTEST_STYLE_PROJECT["pkg/bounds.py"]))
            self.assertFalse(check.accepts("pkg/bounds.py", BROKEN))
        finally:
            check.close()

    def test_the_project_copy_stays_first_so_the_suite_tests_the_copy(self):
        """Reachability must never let the repository's own code satisfy the project's suite."""
        check = G.Check("tests", PYTEST_STYLE_PROJECT, "pkg/bounds.py")
        try:
            env = check._env()
            entries = env["PYTHONPATH"].split(os.pathsep)
            self.assertEqual(entries[0], str(check._dir))
            for entry in entries[1:]:
                self.assertTrue(pathlib.Path(entry).is_dir(), entry)
                self.assertNotEqual(entry, str(check._dir))
        finally:
            check.close()

    def test_the_legacy_runner_really_does_accept_the_broken_edit(self):
        """Pins the counterfactual, so the defect cannot be quietly redefined away."""
        directory = _write_project(PYTEST_STYLE_PROJECT)
        try:
            (directory / "pkg/bounds.py").write_text(BROKEN, encoding="utf-8")
            done = subprocess.run(
                [sys.executable, "-m", "unittest", "tests.test_bounds"],
                cwd=str(directory), capture_output=True, timeout=120,
                env={"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(directory),
                     "HOME": str(directory)},
            )
            self.assertEqual(done.returncode, 0, "unittest is expected to pass vacuously")
            self.assertIn(b"Ran 0 tests", done.stderr)
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def test_a_project_with_no_tests_is_unavailable_not_passing(self):
        files = {"pkg/__init__.py": "", "pkg/bounds.py": "def below(n, hi):\n    return n < hi\n"}
        check = G.Check("tests", files, "pkg/bounds.py")
        try:
            self.assertFalse(check.available)
            self.assertFalse(check.accepts("pkg/bounds.py", BROKEN))
        finally:
            check.close()

    def test_a_missing_dependency_is_named_rather_than_counted_as_a_verdict(self):
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
            self.assertNotEqual(check.reason, "")
            self.assertFalse(check.accepts("pkg/bounds.py", BROKEN))
        finally:
            check.close()


if __name__ == "__main__":
    unittest.main()
