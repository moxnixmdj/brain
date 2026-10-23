#!/usr/bin/env python3
"""A fallback must be held to the same evidence as the path it replaces.

Three defects, each found by measuring rather than by reading.

1. THE FALSE PASS.  "Write the text 'hello patch' to the file X and save the
   report to Y" returned status PASS__COMPOSED_CAPABILITY_CHAIN with pass=True,
   having written those 11 bytes into Y.  X -- the file the goal actually named --
   never existed on disk.  Composition is attempted at exactly the two moments
   where the primary path has already failed, and both call sites returned the
   chain's own verdict untouched.  The gate that would have caught it
   (promised_artifact_errors) had already run; its result was discarded on the
   way out.

2. SELF-CANCELLATION.  Template key order for the repair capabilities is
   output_path, source_root, test_argv, test_paths.  test_argv is derived FROM
   the test paths -- a test runner takes the tests as arguments -- so counting a
   derived argv as a competing claim cancels a role against itself.  Measured:
   exclusivity emptied a correct test_paths=[test_goal_compiler.py], the
   "sentence named the files separately" fallback fired, and test_paths became
   every file in the sentence, source included.

3. THE INTERPRETER AS A TEST FILE.  "with the test T and test command
   '/usr/bin/python3 T'" put "usr/bin/python3" into test_paths, because
   _repo_paths only checks that a path RESOLVES under the root, never that it
   exists.  The adapter rejected it with RepairLoopError:FILE_INVALID.  Defect 2
   had been accidentally masking this one: the argv exclusion removed it.
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
import canonical.runtime.live_brain_route_admission_v1 as ra


class TmpBase(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(
            tempfile.mkdtemp(prefix="fallback_evidence_", dir=str(ROOT / "canonical/astra_runtime/tmp"))
        )
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def rel(self, p):
        return str(pathlib.Path(p).relative_to(ROOT)).replace("\\", "/")


class TestNoFalsePassOnAComposedChain(TmpBase):
    def test_a_write_goal_whose_file_was_never_created_does_not_pass(self):
        """The measured over-claim: pass=True for a file that is not on disk."""
        target = self.tmp / "out.txt"
        goal = (
            f"Write the text {chr(39)}hello patch{chr(39)} to the file {self.rel(target)} "
            f"and save the report to {self.rel(self.tmp / 'out.txt.done.json')}."
        )
        result = ra.solve({"task_id": "FALLBACK_FALSE_PASS", "goal": goal})
        self.assertTrue(
            result.get("pass") is not True or target.is_file(),
            "reported success for a file that does not exist: "
            + str(result.get("status")) + " " + str(result.get("promised_artifact_errors")),
        )

    def test_the_missing_file_is_named_in_the_failure(self):
        target = self.tmp / "out.txt"
        goal = (
            f"Write the text {chr(39)}hello patch{chr(39)} to the file {self.rel(target)} "
            f"and save the report to {self.rel(self.tmp / 'out.txt.done.json')}."
        )
        result = ra.solve({"task_id": "FALLBACK_NAMES_IT", "goal": goal})
        if result.get("pass") is True:
            self.skipTest("the file was produced; nothing to name")
        self.assertIn(
            self.rel(target),
            " ".join(result.get("promised_artifact_errors") or []),
        )

    def test_a_chain_that_did_produce_the_artifact_is_still_allowed_to_pass(self):
        """The guard against over-correcting into 'never trust composition'.

        _composed_holds_up must return the chain untouched when the promised file
        is there.  Asserted at the unit level so it cannot be satisfied by a
        chain that happens to fail for another reason.
        """
        made = self.tmp / "made.txt"
        made.write_text("content\n", encoding="utf-8")
        composed = {"status": "PASS__COMPOSED_CAPABILITY_CHAIN", "pass": True}
        out = ra._composed_holds_up(composed, "write it", [self.rel(made)])
        self.assertTrue(out.get("pass") is True)
        self.assertEqual(out.get("status"), "PASS__COMPOSED_CAPABILITY_CHAIN")
        self.assertNotIn("promised_artifact_errors", out)

    def test_the_gate_flips_a_chain_that_left_the_file_missing(self):
        composed = {"status": "PASS__COMPOSED_CAPABILITY_CHAIN", "pass": True}
        out = ra._composed_holds_up(composed, "write it", [self.rel(self.tmp / "never.txt")])
        self.assertTrue(out.get("pass") is False)
        self.assertEqual(out.get("failure_class"), "PROMISED_ARTIFACT_MISSING")
        self.assertTrue(out.get("composer_ran_but_left_the_artifact_missing"))


class TestADerivedArgvIsNotACompetingClaim(TmpBase):
    def test_a_derived_command_line_does_not_claim_its_own_arguments(self):
        claimed = gc._claimed_paths({
            "output_path": "a/b.json",
            "test_argv": ["/usr/bin/python3", "-m", "unittest", "a/test_b.py"],
        })
        self.assertIn("a/b.json", claimed)
        self.assertNotIn("a/test_b.py", claimed)
        self.assertNotIn("/usr/bin/python3", claimed)

    def test_the_test_list_is_not_emptied_by_its_own_argv(self):
        """The measured self-cancellation, on the route-admission sentence."""
        goal = (
            "Repair the python source file canonical/runtime/goal_compiler.py so that the test "
            "canonical/tests/test_goal_compiler.py passes, and write the report to "
            + self.rel(self.tmp / "rep.json") + "."
        )
        entry = gc._platform_admissible_registry(
            __import__("canonical.runtime.live_integrated_brain_v1",
                       fromlist=["load_verified_registry"]).load_verified_registry()
        )["python.software.repair.loop.coupled.ast.v1"]
        bound = gc._bind_inputs(goal, ROOT, entry)
        self.assertEqual(bound["test_paths"], ["canonical/tests/test_goal_compiler.py"])


class TestAnInterpreterIsNotATestFile(TmpBase):
    def test_the_interpreter_from_a_test_command_is_not_bound_as_a_test(self):
        d = self.tmp / "strict_0_ab"
        d.mkdir()
        src = d / "calc_strict.py"
        src.write_text("def f(a,b):\n    return a-b\n", encoding="utf-8")
        t = d / "test_calc_strict_all.py"
        t.write_text(
            "import os, sys\nsys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
            "import calc_strict as m\nassert m.f(1,2)==3\n", encoding="utf-8")
        out = self.tmp / "strict_0_cd.json"
        goal = (
            f"Run the strict progress repair loop on the python source root {self.rel(d)} "
            f"with the test {self.rel(t)} and test command \"{sys.executable} {self.rel(t)}\", "
            f"and save the repair report to {self.rel(out)}."
        )
        entry = gc._platform_admissible_registry(
            __import__("canonical.runtime.live_integrated_brain_v1",
                       fromlist=["load_verified_registry"]).load_verified_registry()
        )["python.software.repair.loop.strict_progress.ast.v1"]
        bound = gc._bind_inputs(goal, ROOT, entry)
        self.assertEqual(bound["test_paths"], [self.rel(t)])

    def test_a_role_list_names_only_files_that_exist(self):
        real = self.tmp / "real.py"
        real.write_text("x = 1\n", encoding="utf-8")
        goal = f"Localize fault from the tests {self.rel(real)} and usr/bin/python3 with ochiai."
        got = gc._paths_named_by_role(goal, "test", ROOT, ["test", "source", "output"])
        self.assertEqual(got, [self.rel(real)])
        self.assertNotIn("usr/bin/python3", got)


if __name__ == "__main__":
    unittest.main()
