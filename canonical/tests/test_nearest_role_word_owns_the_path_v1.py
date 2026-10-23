#!/usr/bin/env python3
"""A path belongs to the role word that most recently precedes it.

The defect, reproduced end to end.  For the live harness's own repair sentence

    Repair the python source S with the test guided repair loop so that the unit
    tests in A, B pass, and save the repair report to R.

``_paths_named_by_role`` collected every path appearing *after* the role word,
with no upper bound, so the first role in the sentence swallowed the rest of it:

    source_paths: [S, A, R, ...]      <- everything
    test_paths:   [S, A, R, ...]      <- identical

The repair loop was handed its own tests and the output report as the files to
repair, and died with ``RepairLoopError:NO_LOCALIZED_SOURCE_FILES``.

Measured after the fix, same sentence:

    source_paths: [S]          exactly the file to repair
    test_paths:   [A, B]       exactly the tests
    output_path:  R

Stated plainly, because it matters: this does NOT raise the end-to-end pass rate.
It is 1 of 6 before and 1 of 6 after.  What moves is the failure cause --
``NO_LOCALIZED_SOURCE_FILES`` becomes ``PROMISED_SOURCE_CHANGE_NOT_APPLIED``, the
deliberate gate that fires because the repair loop finds and verifies a patch and
then restores the source, declaring no write authority.  The loop is now fed
correctly and fails at a boundary that is correct by design rather than at a
binding bug.  Feeding it correctly is a prerequisite, not a payoff.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc

REPAIR_LOOP = "python.software.repair.loop.test_guided.ast.v1"


class NearestRoleBase(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(
            tempfile.mkdtemp(prefix="nearest_role_", dir=str(ROOT / "canonical/astra_runtime/tmp"))
        )
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.dir = self.tmp / "repair_0_abcd"
        self.dir.mkdir()
        # The bug is a flipped operator, exactly as the harness's fresh_bug plants it.
        self.src = self.dir / "calc_wxyz.py"
        self.src.write_text(
            "def f1(a, b):\n    return a - b * 3\n\n"
            "def f2(n):\n    total = 0\n    for v in range(n):\n"
            "        total = total + v\n    return total\n",
            encoding="utf-8",
        )
        self.tests = []
        for name, checks in (
            ("f1", ["assert m.f1(2, 3) == 11", "assert m.f1(0, 1) == 3"]),
            ("f2", ["assert m.f2(4) == 6", "assert m.f2(1) == 0"]),
        ):
            t = self.dir / f"test_calc_wxyz_{name}.py"
            t.write_text(
                "import os, sys\n"
                "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
                "import calc_wxyz as m\n" + "\n".join(checks) + "\n",
                encoding="utf-8",
            )
            self.tests.append(t)
        self.out = self.tmp / "repair_0_qrst.json"

    def rel(self, p):
        return str(pathlib.Path(p).relative_to(ROOT)).replace("\\", "/")

    @property
    def repair_goal(self):
        """The live harness's own phrasing for PYTHON_REPAIR_TEST_GUIDED."""
        phrase = ", ".join(self.rel(t) for t in self.tests)
        return (
            f"Repair the python source {self.rel(self.src)} with the test guided repair "
            f"loop so that the unit tests in {phrase} pass, and save the repair report "
            f"to {self.rel(self.out)}."
        )

    def compile_inputs(self, goal):
        import canonical.runtime.live_integrated_brain_v1 as live

        _r, _a, compiled = live.compile_against_live_registry(goal, ROOT)
        return compiled


class TestNearestRoleAssignment(NearestRoleBase):
    def test_the_source_list_holds_only_the_file_to_repair(self):
        compiled = self.compile_inputs(self.repair_goal)
        self.assertEqual(compiled.get("selected_capability"), REPAIR_LOOP)
        self.assertEqual(compiled["inputs"]["source_paths"], [self.rel(self.src)])

    def test_the_test_list_holds_only_the_tests(self):
        compiled = self.compile_inputs(self.repair_goal)
        self.assertEqual(
            sorted(compiled["inputs"]["test_paths"]),
            sorted(self.rel(t) for t in self.tests),
        )

    def test_the_two_lists_are_disjoint(self):
        """The exact defect: they used to be the same list."""
        inputs = self.compile_inputs(self.repair_goal)["inputs"]
        overlap = set(inputs["source_paths"]) & set(inputs["test_paths"])
        self.assertEqual(overlap, set(), f"source and test lists overlap: {sorted(overlap)}")

    def test_the_output_report_is_in_neither_list(self):
        inputs = self.compile_inputs(self.repair_goal)["inputs"]
        self.assertNotIn(self.rel(self.out), inputs["source_paths"])
        self.assertNotIn(self.rel(self.out), inputs["test_paths"])
        self.assertEqual(inputs["output_path"], self.rel(self.out))

    def test_the_repair_loop_no_longer_reports_no_localized_source_files(self):
        """The measured movement: the failure cause, not the pass rate.

        Asserted as progress rather than as success. If the binding regresses this
        returns to NO_LOCALIZED_SOURCE_FILES, which is what makes it a guard.
        """
        import canonical.runtime.live_brain_route_admission_v1 as ra

        result = ra.solve({"task_id": "NEAREST_ROLE_E2E", "goal": self.repair_goal})
        reason = str(result.get("reason") or "")
        self.assertNotIn(
            "NO_LOCALIZED_SOURCE_FILES", reason,
            f"the repair loop is being fed the wrong files again: {reason[:200]}",
        )

    def test_a_single_role_still_collects_every_path_it_names(self):
        """Nearest-preceding must not break the simple case.

        This is the guard against over-correcting into 'one path per role'.
        """
        goal = (
            f"Localize fault in python source root {self.rel(self.dir)} from dynamic "
            f"trace of the tests {', '.join(self.rel(t) for t in self.tests)} with "
            f"ochiai spectrum and save output_path {self.rel(self.out)}."
        )
        inputs = gc._bind_inputs(
            goal, ROOT,
            gc._platform_admissible_registry(
                __import__("canonical.runtime.live_integrated_brain_v1",
                           fromlist=["load_verified_registry"]).load_verified_registry()
            )["python.fault.localize.dynamic.dataflow.v1"],
        )
        self.assertEqual(
            sorted(inputs["test_paths"]), sorted(self.rel(t) for t in self.tests),
        )


class TestRoleWordDerivation(unittest.TestCase):
    def test_role_words_come_from_every_path_bearing_key(self):
        words = gc._path_role_words(
            ["source_paths", "test_paths", "output_path", "source_root", "work_dir",
             "test_argv", "timeout_s", "text"]
        )
        self.assertEqual(words, {"source", "test", "output", "work"})

    def test_a_bare_suffix_is_not_a_role_word(self):
        """'_paths' alone has no stem and must not produce an empty role word."""
        self.assertEqual(gc._path_role_words(["_paths", "_path"]), set())

    def test_an_empty_key_set_is_handled(self):
        self.assertEqual(gc._path_role_words([]), set())
        self.assertEqual(gc._path_role_words(None), set())


if __name__ == "__main__":
    unittest.main()
