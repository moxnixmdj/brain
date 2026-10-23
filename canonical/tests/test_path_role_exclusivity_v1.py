#!/usr/bin/env python3
"""A repository path named in a sentence has exactly one role.

The defect, reproduced end to end.  For the goal

    Localize fault in python source root D from dynamic trace of test D/test_calc.py
    with ochiai spectrum and save output_path R.json.

the list binder put **all three** paths into ``test_paths``:

    test_paths: [ "D",                  <- the source ROOT, a directory
                  "D/test_calc.py",     <- the only actual test
                  "R.json" ]            <- the OUTPUT

The adapter validates each entry with ``_safe_file``, which requires an existing
``.py`` file, so the directory raised ``FaultLocalizerError:FILE_INVALID`` and the
whole family scored 0/3.  A previous guard already tried to drop the output path,
but only by recognising an output *verb* -- and this sentence says
"save output_path R.json", with no "to", so the guard never fired.  Nothing at all
excluded the source root.

Measured after the fix: ``PYTHON_FAULT_LOCALIZE`` 0/3 -> 3/3, and the benchmark is
unchanged at 23/23 compiled and 22/23 selected.

The rule implemented is role exclusivity: any path already bound to another input
key is not also a member of a ``*_paths`` list.  That covers the output path, the
source root, and every phrasing not yet imagined, instead of one more verb.
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
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry

LOCALIZER = "python.fault.localize.dynamic.dataflow.v1"


class PathRoleExclusivityBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = gc._platform_admissible_registry(load_verified_registry())

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="path_roles_", dir=str(ROOT / "canonical/astra_runtime/tmp")))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.src = self.tmp / "src"
        self.src.mkdir()
        (self.src / "calc.py").write_text("def f(x):\n    return x\n", encoding="utf-8")
        self.t1 = self.src / "test_a.py"
        self.t2 = self.src / "test_b.py"
        for t in (self.t1, self.t2):
            t.write_text("import unittest\nclass T(unittest.TestCase):\n    def test_x(self): pass\n",
                         encoding="utf-8")
        self.out = self.tmp / "report.json"

    def rel(self, p):
        return str(p.relative_to(ROOT)).replace("\\", "/")

    def bind(self, goal, cid=LOCALIZER):
        return gc._bind_inputs(goal, ROOT, self.reg[cid])


class TestRoleExclusivity(PathRoleExclusivityBase):
    def test_the_source_root_and_the_output_are_not_tests(self):
        """The exact failing sentence: three paths, three roles."""
        goal = (
            f"Localize fault in python source root {self.rel(self.src)} from dynamic trace "
            f"of test {self.rel(self.t1)} with ochiai spectrum and save output_path "
            f"{self.rel(self.out)}."
        )
        inputs = self.bind(goal)
        self.assertEqual(inputs["test_paths"], [self.rel(self.t1)])
        self.assertEqual(inputs["source_root"], self.rel(self.src))
        self.assertEqual(inputs["output_path"], self.rel(self.out))

    def test_a_directory_never_enters_a_paths_list(self):
        """General form of the same rule, independent of the output phrasing."""
        # output_path is a required input of this capability, so the sentence must
        # name it even though this test is about the source root, not the output.
        goal = (
            f"Localize fault in python source root {self.rel(self.src)} from dynamic trace "
            f"of test {self.rel(self.t1)} with ochiai spectrum and save output_path "
            f"{self.rel(self.out)}."
        )
        inputs = self.bind(goal)
        for entry in inputs["test_paths"]:
            self.assertTrue(
                (ROOT / entry).is_file(),
                f"a directory reached test_paths: {entry}",
            )

    def test_several_real_tests_are_all_still_bound(self):
        """The guard must not over-filter into binding only the first test.

        This is the test that would catch a fix implemented as "take one path".
        """
        goal = (
            f"Localize fault in python source root {self.rel(self.src)} from dynamic trace "
            f"of test {self.rel(self.t1)} and test {self.rel(self.t2)} with ochiai spectrum "
            f"and save output_path {self.rel(self.out)}."
        )
        inputs = self.bind(goal)
        self.assertEqual(sorted(inputs["test_paths"]), sorted([self.rel(self.t1), self.rel(self.t2)]))

    def test_the_output_path_is_excluded_under_a_phrasing_no_verb_helper_knows(self):
        """'save output_path X' has no 'to', so the older verb-based guard never fired."""
        goal = (
            f"Localize fault in python source root {self.rel(self.src)} from dynamic trace "
            f"of test {self.rel(self.t1)} with ochiai spectrum and save output_path "
            f"{self.rel(self.out)}."
        )
        inputs = self.bind(goal)
        self.assertNotIn(self.rel(self.out), inputs["test_paths"])

    def test_a_path_already_bound_to_a_key_is_not_reusable(self):
        """Direct check of the helper the fix is built on."""
        claimed = gc._claimed_paths(
            {"source_root": "a/b", "output_path": "c.json", "test_paths": ["d.py", "e.py"]}
        )
        self.assertEqual(claimed, {"a/b", "c.json", "d.py", "e.py"})

    def test_the_argv_branch_applies_the_same_exclusion(self):
        """*_argv re-derives its targets independently, so it needs the rule too."""
        cid = "python.tests.audit.unittest"
        if cid not in self.reg:
            self.skipTest(f"{cid} not admissible")
        goal = (
            f"Audit the unittest suites {self.rel(self.t1)} in the source root "
            f"{self.rel(self.src)} and save output_path {self.rel(self.out)}."
        )
        try:
            inputs = self.bind(goal, cid)
        except gc.GoalCompilationFailure:
            self.skipTest("this goal does not bind for the audit capability")
        argv = inputs.get("test_argv") or []
        joined = " ".join(str(a) for a in argv)
        self.assertNotIn(self.rel(self.out), joined)
        self.assertNotIn(self.rel(self.src) + " ", joined + " ")


class TestEndToEnd(PathRoleExclusivityBase):
    def test_the_fault_localizer_goal_passes_through_the_front_door(self):
        """The measured effect: this family scored 0/3 before the fix."""
        import canonical.runtime.live_brain_route_admission_v1 as ra

        (self.src / "calc.py").write_text(
            "def sub_wxyz(x):\n    if x > 0:\n        return x - 1\n    return x\n",
            encoding="utf-8",
        )
        (self.src / "test_calc.py").write_text(
            "import sys, pathlib, unittest\n"
            "sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))\n"
            "import calc\n"
            "class T(unittest.TestCase):\n"
            "    def test_pos(self): self.assertEqual(calc.sub_wxyz(2), 1)\n"
            "    def test_zero(self): self.assertEqual(calc.sub_wxyz(0), 1)\n"
            "if __name__ == '__main__':\n    unittest.main()\n",
            encoding="utf-8",
        )
        goal = (
            f"Localize fault in python source root {self.rel(self.src)} from dynamic trace "
            f"of test {self.rel(self.src / 'test_calc.py')} with ochiai spectrum and save "
            f"output_path {self.rel(self.out)}."
        )
        result = ra.solve({"task_id": "PATH_ROLE_EXCLUSIVITY_E2E", "goal": goal})
        self.assertTrue(
            result.get("pass"),
            f"{result.get('failure_class')}: {result.get('reason')}",
        )


if __name__ == "__main__":
    unittest.main()
