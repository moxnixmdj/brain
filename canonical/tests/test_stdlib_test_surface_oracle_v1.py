"""The oracle must run where the spine runs, and must never call an empty run green.

Why this file exists
--------------------
Main's `repo_native_test_surface_v1.test_surface` shells out to
`python -m pytest` unconditionally and reads a JUnit XML report. `pytest` is
not a dependency of this project, and it is absent from the sandbox where the
spine is measured. Measured on the tree at `77fc2b16` with this module's
stdlib path removed:

    bintest (a-b -> a+b, a real repair)  -> pass=False  UNMEASURED__NO_REPORT
    fgtest  (failing plain-def test)     -> pass=False  UNMEASURED__NO_REPORT

Both dead. The repair engine could not verify a repair it can actually make,
so every repo-native result degraded to "unmeasured". That is a regression of
the instrument, not a missing feature.

The fix is not a new dependency. The spine already ships
`stdlib_cow_test_runner_v1.run_targets_cow_fork`, which discovers plain
`def test_*` functions, `Test*` classes and `unittest.TestCase` subclasses in
an `os.fork()` CoW child and fails closed on an empty run. Wiring it in as the
no-pytest branch restores both behaviours:

    bintest -> pass=True   PASS__REPO_NATIVE_ANGELIC_OE_STRUCTURAL
    fgtest  -> pass=False  FAIL_CLOSED__REPO_NATIVE_EXHAUSTED

The second line is the one that matters most. `pytest` reports "Ran 0 tests"
as success on a plain-def failing file, which is how a failing repo can be
certified green. The CoW runner reports `rc=1` with the failing nodeid.

Nothing here is relaxed relative to the pytest path: a run that discovers no
cases is `NO_CASES`, a dead child is `RUNNER_ERROR`, and identities are never
invented -- `restored_surface` compares case *sets*, so a count without
nodeids is refused rather than fabricated.
"""
from __future__ import annotations

import pathlib
import shutil
import tempfile
import unittest

from canonical.swe_kernel import repo_native_test_surface_v1 as surface
from canonical.swe_kernel.canonical_swe_spine_v1 import solve_swe_repo_native_multifile as solve


_BINOP_PKG = '''\
def add(a, b):
    return a - b
'''

_BINOP_TEST = '''\
from pkg.calc import add


def test_add():
    assert add(3, 4) == 7
'''

_PLAIN_FAIL_PKG = '''\
def get_name(x):
    if x is None:
        return None
    return x.strip()
'''

_PLAIN_FAIL_TEST = '''\
from pkg.names import get_name


def test_none_returns_empty():
    assert get_name(None) == ""
'''

_GREEN_PKG = '''\
def add(a, b):
    return a + b
'''

_GREEN_TEST = '''\
from pkg.calc import add


def test_add():
    assert add(3, 4) == 7
'''


def _repo(tmp: pathlib.Path, pkg: str, test: str, *, name: str = "pkg/calc.py") -> pathlib.Path:
    root = tmp / "repo"
    (root / "pkg").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (root / name).write_text(pkg, encoding="utf-8")
    (root / "tests" / "test_target.py").write_text(test, encoding="utf-8")
    return root


class StdlibOracleRunsWithoutPytest(unittest.TestCase):
    """`test_surface` answers RED/GREEN with no third-party test runner installed."""

    def setUp(self) -> None:
        self._td = tempfile.mkdtemp(prefix="std_oracle_")
        self.tmp = pathlib.Path(self._td)

    def tearDown(self) -> None:
        shutil.rmtree(self._td, ignore_errors=True)

    def test_failing_plain_def_test_is_red_not_green(self) -> None:
        root = _repo(self.tmp, _PLAIN_FAIL_PKG, _PLAIN_FAIL_TEST, name="pkg/names.py")
        result = surface.test_surface(root, ["tests/test_target.py"], timeout=20)
        self.assertEqual(result["status"], "RED")
        self.assertEqual(len(result["failed"]), 1)
        self.assertEqual(len(result["passed"]), 0)

    def test_passing_plain_def_test_is_green(self) -> None:
        root = _repo(self.tmp, _GREEN_PKG, _GREEN_TEST)
        result = surface.test_surface(root, ["tests/test_target.py"], timeout=20)
        self.assertEqual(result["status"], "GREEN")
        self.assertEqual(len(result["failed"]), 0)
        self.assertEqual(len(result["passed"]), 1)

    def test_directory_target_finds_nested_cases(self) -> None:
        root = _repo(self.tmp, _PLAIN_FAIL_PKG, _PLAIN_FAIL_TEST, name="pkg/names.py")
        result = surface.test_surface(root, ["."], timeout=20)
        self.assertEqual(result["status"], "RED")

    def test_empty_run_is_never_green(self) -> None:
        """The original lie: pytest calls 'Ran 0 tests' a success."""
        root = self.tmp / "empty"
        (root / "tests").mkdir(parents=True)
        (root / "tests" / "test_nothing.py").write_text(
            "def helper():\n    return 1\n", encoding="utf-8"
        )
        result = surface.test_surface(root, ["tests/test_nothing.py"], timeout=20)
        self.assertNotEqual(result["status"], "GREEN")
        self.assertIn(result["status"], {"NO_CASES", "RUNNER_ERROR"})

    def test_passed_identities_are_real_not_synthesised(self) -> None:
        """`restored_surface` compares case sets; invented keys would always mismatch."""
        root = _repo(self.tmp, _GREEN_PKG, _GREEN_TEST)
        result = surface.test_surface(root, ["tests/test_target.py"], timeout=20)
        self.assertEqual(result["status"], "GREEN")
        for classname, name in result["passed"]:
            self.assertTrue(name.startswith("test_"), (classname, name))
            self.assertNotEqual(classname, "[passed]")


class SpineVerifiesWhatItCanRepair(unittest.TestCase):
    """End-to-end: the repair that works must still verify, and the lie must stay dead."""

    def setUp(self) -> None:
        self._td = tempfile.mkdtemp(prefix="spine_oracle_")
        self.tmp = pathlib.Path(self._td)

    def tearDown(self) -> None:
        shutil.rmtree(self._td, ignore_errors=True)

    def test_binop_repair_is_found_and_verified_with_zero_model_calls(self) -> None:
        root = _repo(self.tmp, _BINOP_PKG, _BINOP_TEST)
        result = solve(
            repo_root=str(root),
            test_targets=["tests/test_target.py"],
            candidate_files=["pkg/calc.py"],
            keep_patch_applied=False,
        )
        self.assertTrue(result["pass"], result.get("status"))
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["patched_files"], ["pkg/calc.py"])
        self.assertIn("a + b", result["patches"]["pkg/calc.py"])

    def test_failing_baseline_invisible_to_unittest_is_not_certified(self) -> None:
        """`python -m unittest <file>` reports 'Ran 0 tests ... OK' for this repo."""
        root = _repo(self.tmp, _PLAIN_FAIL_PKG, _PLAIN_FAIL_TEST, name="pkg/names.py")
        result = solve(
            repo_root=str(root),
            test_targets=["tests/test_target.py"],
            candidate_files=["pkg/names.py"],
            keep_patch_applied=False,
        )
        self.assertFalse(result["pass"])
        self.assertNotIn("PASS", str(result.get("status")))
        self.assertEqual(result["model_calls"], 0)

    def test_already_green_baseline_is_reported_as_such(self) -> None:
        root = _repo(self.tmp, _GREEN_PKG, _GREEN_TEST)
        result = solve(
            repo_root=str(root),
            test_targets=["tests/test_target.py"],
            candidate_files=["pkg/calc.py"],
            keep_patch_applied=False,
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["status"], "PASS__BASELINE_ALREADY_GREEN")


if __name__ == "__main__":
    unittest.main()
