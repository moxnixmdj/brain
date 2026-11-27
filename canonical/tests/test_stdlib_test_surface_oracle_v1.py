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

_GUARDED_PKG = '''\
def get_name(x):
    if x is None:
        return None
    return x.strip()
'''

_GUARDED_TEST = '''\
from pkg.names import get_name


def test_none_returns_empty():
    assert get_name(None) == ""
'''

_TWO_SITE_PKG = '''\
def g(x):
    if x is None:
        return None
    return x * 2
'''

_TWO_SITE_TEST = '''\
from pkg.n import g


def test_none_is_zero():
    assert g(None) == 0
'''

_NONLITERAL_PKG = '''\
def h(x):
    return x + 1
'''

_NONLITERAL_TEST = '''\
from pkg.q import h


def test_h():
    assert h(1) == len([1, 2, 3])
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

    def test_failing_baseline_invisible_to_unittest_is_never_called_green(self) -> None:
        """`python -m unittest <file>` prints 'Ran 0 tests ... OK' for this repo.

        The oracle must see the failure. What the search does next is reported
        honestly: either a patch the oracle verifies, or a fail-closed status.
        """
        root = _repo(self.tmp, _PLAIN_FAIL_PKG, _PLAIN_FAIL_TEST, name="pkg/names.py")
        result = solve(
            repo_root=str(root),
            test_targets=["tests/test_target.py"],
            candidate_files=["pkg/names.py"],
            keep_patch_applied=False,
        )
        self.assertNotEqual(result["status"], "PASS__BASELINE_ALREADY_GREEN")
        self.assertEqual(result["model_calls"], 0)
        if result["pass"]:
            self.assertIn("ASSERTION_BACKWARD_OBLIGATION", result["status"])
        else:
            self.assertIn("FAIL_CLOSED", result["status"])

    def test_backward_obligation_repairs_a_none_guard(self) -> None:
        """The failing assertion states the goal: `get_name(None) == ""`.

        Before this route, nothing in the search tried the value the test itself
        published, because `oe_synthesized_exprs` is filled from witnesses and a
        single failing assertion is not a witness. The obligation is read off the
        failure and pushed backward to a return site; the CoW oracle still decides.
        """
        root = _repo(self.tmp, _GUARDED_PKG, _GUARDED_TEST, name="pkg/names.py")
        result = solve(
            repo_root=str(root),
            test_targets=["tests/test_target.py"],
            candidate_files=["pkg/names.py"],
            keep_patch_applied=False,
        )
        self.assertTrue(result["pass"], result.get("status"))
        self.assertIn("ASSERTION_BACKWARD_OBLIGATION", result["status"])
        self.assertEqual(result["backward_obligation_source"], "''")
        self.assertIn("return ''", result["patches"]["pkg/names.py"])
        self.assertEqual(result["model_calls"], 0)

    def test_backward_obligation_touches_only_the_guarded_return(self) -> None:
        """Two return sites; only the one the failure implicates may change."""
        root = _repo(self.tmp, _TWO_SITE_PKG, _TWO_SITE_TEST, name="pkg/n.py")
        result = solve(
            repo_root=str(root),
            test_targets=["tests/test_target.py"],
            candidate_files=["pkg/n.py"],
            keep_patch_applied=False,
        )
        self.assertTrue(result["pass"], result.get("status"))
        patched = result["patches"]["pkg/n.py"]
        self.assertIn("return 0", patched)
        self.assertIn("return x * 2", patched, "the correct site must be left alone")

    def test_constant_duty_is_refused_when_it_stops_reading_the_input(self) -> None:
        """`assert h(1) == len([1,2,3])` is readable as `3`, and `return 3` is refused.

        This is the most important negative control in this file, because the
        refusal is counter-intuitive: the duty IS mined (`literal_source -> '3'`)
        and `return 3` DOES make the suite green. It is refused anyway by
        `repair_input_dependency_gate_v1` as `PATCH_STOPPED_READING_ITS_INPUTS`,
        which is correct -- `def h(x): return 3` is a lookup that discards `x`,
        the exact failure that gate was written for (a billing function
        "repaired" to return 110.0 for every input).

        So `FAIL_CLOSED` here is the right answer, not a bug: no patch can both
        satisfy this test and remain a function of its argument.
        """
        root = _repo(self.tmp, _NONLITERAL_PKG, _NONLITERAL_TEST, name="pkg/q.py")
        result = solve(
            repo_root=str(root),
            test_targets=["tests/test_target.py"],
            candidate_files=["pkg/q.py"],
            keep_patch_applied=False,
        )
        self.assertFalse(result["pass"])
        self.assertIn("FAIL_CLOSED", result["status"])
        self.assertIsNone(result.get("backward_obligation_source"))
        self.assertEqual(result["model_calls"], 0)

    def test_input_dependency_gate_refuses_the_constant_that_would_pass(self) -> None:
        """Pin the gate's verdict directly, so the refusal above cannot silently rot."""
        from canonical.swe_kernel import repair_input_dependency_gate_v1 as dependency_gate

        original = "def h(x):\n    return x + 1\n"
        constant = "def h(x):\n    return 3\n"
        verdict = dependency_gate.gate(original, constant)
        self.assertEqual(verdict["status"], dependency_gate.REFUSED)
        self.assertIn("PATCH_STOPPED_READING_ITS_INPUTS", verdict["reason"])

        # A guard that keeps reading its input on the other path must pass.
        guarded_original = "def g(x):\n    if x is None:\n        return None\n    return x * 2\n"
        guarded_patch = "def g(x):\n    if x is None:\n        return 0\n    return x * 2\n"
        self.assertEqual(dependency_gate.gate(guarded_original, guarded_patch)["status"],
                         dependency_gate.PASS)

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


class StoreKeepsTheValueItLearned(unittest.TestCase):
    """A morphism must remember WHAT it substituted, not only where.

    `literal_witness` is derived from truthiness (`isinstance(v, str) and v`), so it
    silently drops every falsy duty -- `''` and `0` -- which are the commonest duties
    in this defect family. Measured on four morphisms this session learned: only the
    function name differed between them, and `literal_witness` was `{}` on all four.
    `duty_witness` carries the value beside the abstraction instead.
    """

    def setUp(self) -> None:
        self._td = tempfile.mkdtemp(prefix="duty_store_")
        self.path = pathlib.Path(self._td) / "store.json"

    def tearDown(self) -> None:
        shutil.rmtree(self._td, ignore_errors=True)

    def test_falsy_duty_is_recorded_and_survives_a_reload(self) -> None:
        from canonical.swe_kernel import causal_nexus_v1 as causal

        store = causal.SkillStoreV2(self.path)
        before = "def f(x):\n    if x is None:\n        return None\n    return x.upper()\n"
        after = "def f(x):\n    if x is None:\n        return ''\n    return x.upper()\n"
        morph = store.learn(before, after, origin="TEST", duty_witness="''")
        self.assertIsNotNone(morph)
        self.assertEqual(morph.duty_witness, "''")
        self.assertEqual(morph.literal_witness, {},
                         "literal_witness stays truthiness-filtered; duty_witness is the fix")

        reloaded = causal.SkillStoreV2(self.path)
        row = next(m for m in reloaded.morphisms.values() if m.morphism_id == morph.morphism_id)
        self.assertEqual(row.duty_witness, "''")

    def test_zero_duty_is_also_recorded(self) -> None:
        from canonical.swe_kernel import causal_nexus_v1 as causal

        store = causal.SkillStoreV2(self.path)
        before = "def g(x):\n    if x is None:\n        return None\n    return x * 2\n"
        after = "def g(x):\n    if x is None:\n        return 0\n    return x * 2\n"
        morph = store.learn(before, after, origin="TEST", duty_witness="0")
        self.assertEqual(morph.duty_witness, "0")

    def test_morphism_without_a_duty_defaults_to_empty(self) -> None:
        from canonical.swe_kernel import causal_nexus_v1 as causal

        store = causal.SkillStoreV2(self.path)
        before = "def h(x):\n    return x + 1\n"
        after = "def h(x):\n    return x + 2\n"
        morph = store.learn(before, after, origin="TEST")
        if morph is not None:
            self.assertEqual(morph.duty_witness, "")
