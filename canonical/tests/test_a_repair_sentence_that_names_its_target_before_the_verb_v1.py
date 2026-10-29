"""A repair sentence that names its target before the verb still promises that target.

Measured on `e2d7981`, fresh tree, the filesystem and the real test runner as the
independent oracles::

    "the add function in <T>/pkg/calc.py is broken, fix it so its tests pass"

returned PASS while `<T>/pkg/calc.py` was **byte-identical** and its own stated test
was **red** (`-1 != 5`).  Two defects produced that, and both are fixed here:

1. The front door only looked for the repaired file AFTER the repair verb, so a
   sentence that states its target first ("the add function in X is broken, fix it")
   promised nothing and the source-change gate had nothing to check
   (`live_brain_route_admission_v1._promised_source_files`).
2. The derived test command executed the test file as a script.  A file with no
   `__main__` guard then exits 0 having run **nothing**, and the repair loop reads
   that 0 as "the stated test already passes" -- the exact trap
   `python_test_guided_patch_search_v1.suite_argv` documents.  The loader command
   line runs the one test and sees it fail, so the loop actually repairs the file.

Every case below builds its own tree and checks the WORLD, not the machine's report:
file bytes for "did anything change", a real subprocess exit code for "is the suite
green", and the pure promise reader for "what does the sentence promise".
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import declared_input_derivation_v1 as derivation  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402

WORK = ROOT / "canonical/astra_runtime/tmp/test_target_before_verb"
BROKEN = "def add(a, b):\n    return a - b\n"
# No `__main__` guard on purpose: 695 of the 2019 unittest files in this repository
# have none, and a script run of such a file executes zero tests and exits 0.
TEST_SOURCE = ("import calc, unittest\n\n\n"
               "class T(unittest.TestCase):\n"
               "    def test_add(self):\n"
               "        self.assertEqual(calc.add(2, 3), 5)\n")


def _fresh(case: str) -> pathlib.Path:
    base = WORK / case
    if base.exists():
        shutil.rmtree(base)
    (base / "pkg").mkdir(parents=True)
    (base / "pkg/calc.py").write_text(BROKEN, encoding="utf-8")
    (base / "pkg/test_calc.py").write_text(TEST_SOURCE, encoding="utf-8")
    return base


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _suite_green(pkg: pathlib.Path) -> bool:
    """The stated test, run by the real runner.  Exit code is the oracle."""
    proc = subprocess.run(
        [sys.executable, "-m", "unittest", "test_calc"],
        cwd=str(pkg), capture_output=True, text=True, timeout=120,
        env={"PYTHONPATH": str(pkg), "PATH": "/usr/bin:/bin:/usr/local/bin"})
    return proc.returncode == 0


class TheTargetIsReadWhereverItSits(unittest.TestCase):
    """The promise reader, against sentences a human actually writes."""

    def test_a_target_before_the_verb_is_the_target(self):
        base = _fresh("before_verb")
        src = _rel(base / "pkg/calc.py")
        promised = door._promised_source_files(
            "the add function in %s is broken, fix it so its tests pass" % src)
        self.assertEqual(promised, [src])

    def test_a_target_after_the_verb_is_still_the_target(self):
        """The old word order kept its old meaning -- this test pins it."""
        base = _fresh("after_verb")
        src = _rel(base / "pkg/calc.py")
        self.assertEqual(door._promised_source_files("fix %s" % src), [src])

    def test_a_witness_test_is_not_a_promise(self):
        """`Bug: <test> fails, fix it` names what must pass, not what must change."""
        base = _fresh("witness")
        test = _rel(base / "pkg/test_calc.py")
        self.assertEqual(door._promised_source_files("Bug: %s fails. Fix it." % test), [])

    def test_a_sentence_with_no_repair_verb_promises_nothing(self):
        base = _fresh("no_verb")
        src = _rel(base / "pkg/calc.py")
        self.assertEqual(
            door._promised_source_files("Explain why the test beside %s fails" % src), [])


class TheDerivedTestCommandActuallyRunsTheSuite(unittest.TestCase):
    """`[python, -B, file]` exits 0 having run nothing when there is no guard."""

    def _entry(self):
        registry = json.loads(
            (ROOT / "canonical/runtime/BOUND_CAPABILITY_REGISTRY_V1.json").read_text())
        return registry["capabilities"]["python.software.repair.apply.verified.v1"]

    def test_the_derived_argv_goes_through_the_loader_not_the_file(self):
        base = _fresh("argv_shape")
        src = _rel(base / "pkg/calc.py")
        rows = derivation.derive(
            "the add function in %s is broken, fix it so its tests pass" % src,
            self._entry(), ROOT)
        argv = rows["test_argv"]["value"]
        self.assertIn("-c", argv,
                      "the derived command must run the repository's suite runner")
        self.assertNotIn("-B", argv[:1] + argv[-1:],
                         "executing the file as a script is the zero-test trap")
        self.assertTrue(rows["test_argv"]["rule"].endswith("SUITE_RUNNER"))

    def test_that_argv_sees_the_failure_the_script_run_hides(self):
        """Both commands, run for real: the script run is green, the suite is red."""
        base = _fresh("argv_verify")
        pkg = base / "pkg"
        src = _rel(pkg / "calc.py")
        rows = derivation.derive(
            "the add function in %s is broken, fix it so its tests pass" % src,
            self._entry(), ROOT)
        env = {"PYTHONPATH": str(pkg), "PATH": "/usr/bin:/bin:/usr/local/bin"}
        script_run = subprocess.run([sys.executable, "-B", "test_calc.py"],
                                    cwd=str(pkg), capture_output=True, text=True,
                                    timeout=120, env=env)
        suite_run = subprocess.run([str(x) for x in rows["test_argv"]["value"]],
                                   cwd=str(pkg), capture_output=True, text=True,
                                   timeout=120, env=env)
        self.assertEqual(script_run.returncode, 0,
                         "the zero-test script run is exactly what a repair loop misreads")
        self.assertNotEqual(suite_run.returncode, 0,
                            "the loader command must see the failing test")

    def test_the_repair_loop_then_repairs_the_file(self):
        """The consequence, measured on the bytes: the source really is fixed."""
        base = _fresh("loop_repairs")
        pkg = base / "pkg"
        src = _rel(pkg / "calc.py")
        rows = derivation.derive(
            "the add function in %s is broken, fix it so its tests pass" % src,
            self._entry(), ROOT)
        args = dict(self._entry()["action_template"]["args"])
        for slot in ("source_root", "test_paths", "test_argv"):
            args[slot] = rows[slot]["value"]
        args["output_path"] = _rel(base / "report.json")
        args["run_tests"] = True
        from canonical.runtime.bound_capabilities import (
            python_repair_apply_verified_v1 as repair,
        )
        payload = repair.run(args, str(ROOT))
        self.assertTrue(payload["applied"], payload.get("status"))
        self.assertEqual(payload["pre_apply_test_returncode"], 1)
        self.assertEqual(payload["post_apply_test_returncode"], 0)
        self.assertNotEqual(_digest(pkg / "calc.py"), hashlib.sha256(BROKEN.encode()).hexdigest())
        self.assertTrue(_suite_green(pkg))


class TheDoorNoLongerCreditsANoOp(unittest.TestCase):
    """End to end, on a fresh tree, with the real runner as the oracle."""

    def test_the_measured_sentence_repairs_the_source_and_greens_the_test(self):
        base = _fresh("end_to_end")
        pkg = base / "pkg"
        src = _rel(pkg / "calc.py")
        before = _digest(pkg / "calc.py")
        goal = ("the add function in %s is broken, fix it so its tests pass" % src)
        result = door.solve({"task_id": "TARGET_BEFORE_VERB", "goal": goal})
        self.assertIs(result.get("pass"), True, result.get("status"))
        # Independent oracle: the world, not the report.
        self.assertNotEqual(_digest(pkg / "calc.py"), before,
                            "a PASS that reports a repair must have changed the file")
        self.assertTrue(_suite_green(pkg), "the stated test must actually pass")

    def test_an_unchanged_source_is_still_reported_as_an_unkept_promise(self):
        """The gate itself, on real before/after digests -- no mocking, no stub."""
        base = _fresh("gate_unit")
        src = _rel(base / "pkg/calc.py")
        goal = "the add function in %s is broken, fix it so its tests pass" % src
        before = {src: _digest(base / "pkg/calc.py")}
        unchanged = door.promised_source_change_errors(goal, before, [])
        self.assertIn("PROMISED_SOURCE_UNCHANGED:" + src, unchanged)
        (base / "pkg/calc.py").write_text("def add(a, b):\n    return a + b\n",
                                          encoding="utf-8")
        self.assertEqual(door.promised_source_change_errors(goal, before, []), [])


class AStatedDefectAlsoNamesItsTarget(unittest.TestCase):
    """A bug report states the defect and its witness instead of asking for a verb.

    Measured 2026-10-29 on `3671140`::

        "Bug: <T>/pkg/calc.py add() returns the wrong value. Failing test: <T>/pkg/test_calc.py."

    returned PASS with the source byte-identical and the named test red.  There is no
    repair verb in a bug report, so the promise reader returned nothing, no digest was
    taken and the source-change gate had nothing to check.  The promise is in the
    statement: a named source reported as broken is a source promised to change.
    """

    def test_a_bug_report_promises_the_source_it_names(self):
        base = _fresh("bug_report")
        src = _rel(base / "pkg/calc.py")
        test = _rel(base / "pkg/test_calc.py")
        promised = door._promised_source_files(
            "Bug: %s add() returns the wrong value. Failing test: %s." % (src, test))
        self.assertEqual(promised, [src], "the witness test is named, not promised")

    def test_a_bug_report_naming_only_a_test_promises_nothing(self):
        base = _fresh("bug_report_test_only")
        test = _rel(base / "pkg/test_calc.py")
        self.assertEqual(
            door._promised_source_files("Bug: %s fails. Investigate." % test), [])

    def test_an_unchanged_source_is_an_unkept_promise_for_a_bug_report_too(self):
        """The source-change gate, on real digests, for a sentence with no verb."""
        base = _fresh("bug_report_gate")
        src = _rel(base / "pkg/calc.py")
        test = _rel(base / "pkg/test_calc.py")
        goal = ("Bug: %s add() returns the wrong value. Failing test: %s." % (src, test))
        before = {src: _digest(base / "pkg/calc.py")}
        self.assertEqual(door.promised_source_change_errors(goal, before, []),
                         ["PROMISED_SOURCE_UNCHANGED:" + src],
                         "a bug report over an untouched source is an unkept promise")
        (base / "pkg/calc.py").write_text("def add(a, b):\n    return a + b\n",
                                          encoding="utf-8")
        self.assertEqual(door.promised_source_change_errors(goal, before, []), [])


if __name__ == "__main__":
    unittest.main()
