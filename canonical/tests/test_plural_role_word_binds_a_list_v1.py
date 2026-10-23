#!/usr/bin/env python3
"""A role word must match the plural as well as the singular.

``_paths_named_by_role`` turned the input key ``test_paths`` into the role word
``test`` and searched for ``\\btest\\b``.  That cannot match "tests".  A ``*_paths``
input is a LIST, and a sentence names a list in the plural as naturally as in the
singular -- the live harness itself generates "using the tests A, B, C".  The
fallback branch in ``_bind_inputs`` used the same singular-only regex, so both
routes missed and the input went unbound.

Measured with the harness's own phrasing, over the ten repair / localisation /
patch / audit capabilities:

    before   0 of 10 bound
    after    7 of 10 bound   (each picking up all three tests)

The three that still do not bind fail on other inputs -- ``test_argv`` and
``pattern`` -- not on the role word.

The benchmark is unchanged at 23/23 compiled and 22/23 selected, and the CI
suites are unchanged, so the widening did not cost anything.
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
# The capabilities the live harness drives for its repair families.
REPAIR_FAMILY = (
    "python.fault.localize.dynamic.dataflow.v1",
    "python.fault.provenance.interprocedural.value.v1",
    "python.patch.search.test_guided.ast.v1",
    "python.software.repair.guided.provenance.coupled.v1",
    "python.software.repair.loop.coupled.ast.v1",
    "python.software.repair.loop.strict_progress.ast.v1",
    "python.software.repair.loop.test_guided.ast.v1",
)


class PluralRoleBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = gc._platform_admissible_registry(load_verified_registry())

    def setUp(self):
        self.tmp = pathlib.Path(
            tempfile.mkdtemp(prefix="plural_role_", dir=str(ROOT / "canonical/astra_runtime/tmp"))
        )
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.src = self.tmp / "src"
        self.src.mkdir()
        (self.src / "calc_ab.py").write_text("def f(a, b):\n    return a - b\n", encoding="utf-8")
        self.tests = []
        for name in ("fa", "fb", "fc"):
            t = self.src / f"test_calc_ab_{name}.py"
            t.write_text(
                "import os, sys\n"
                "sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
                "import calc_ab as m\n"
                "assert m.f(1, 2) == 3\n",
                encoding="utf-8",
            )
            self.tests.append(t)
        self.out = self.tmp / "report.json"

    def rel(self, p):
        return str(pathlib.Path(p).relative_to(ROOT)).replace("\\", "/")

    @property
    def tests_phrase(self):
        """Exactly what the harness's tests_phrase() returns: comma-joined paths."""
        return ", ".join(self.rel(t) for t in self.tests)

    def bind(self, goal, cid=LOCALIZER):
        return gc._bind_inputs(goal, ROOT, self.reg[cid])


class TestPluralRoleWord(PluralRoleBase):
    def test_the_plural_names_every_file_in_the_list(self):
        goal = (
            f"Localize fault in python source root {self.rel(self.src)} from dynamic trace "
            f"of the tests {self.tests_phrase} with ochiai spectrum and save output_path "
            f"{self.rel(self.out)}."
        )
        inputs = self.bind(goal)
        self.assertEqual(sorted(inputs["test_paths"]), sorted(self.rel(t) for t in self.tests))

    def test_the_singular_still_works(self):
        """Widening the match must not have broken the phrasing that already worked."""
        goal = (
            f"Localize fault in python source root {self.rel(self.src)} from dynamic trace "
            f"of test {self.rel(self.tests[0])} with ochiai spectrum and save output_path "
            f"{self.rel(self.out)}."
        )
        inputs = self.bind(goal)
        self.assertEqual(inputs["test_paths"], [self.rel(self.tests[0])])

    def test_repeated_singular_still_collects_every_file(self):
        goal = (
            f"Localize fault in python source root {self.rel(self.src)} from dynamic trace "
            f"of test {self.rel(self.tests[0])} and test {self.rel(self.tests[1])} with "
            f"ochiai spectrum and save output_path {self.rel(self.out)}."
        )
        inputs = self.bind(goal)
        self.assertEqual(
            sorted(inputs["test_paths"]),
            sorted([self.rel(self.tests[0]), self.rel(self.tests[1])]),
        )

    def test_role_exclusivity_still_holds_under_the_plural(self):
        """The plural fix must not reintroduce the source root or the output."""
        goal = (
            f"Localize fault in python source root {self.rel(self.src)} from dynamic trace "
            f"of the tests {self.tests_phrase} with ochiai spectrum and save output_path "
            f"{self.rel(self.out)}."
        )
        inputs = self.bind(goal)
        self.assertNotIn(self.rel(self.src), inputs["test_paths"])
        self.assertNotIn(self.rel(self.out), inputs["test_paths"])

    def test_a_word_that_merely_contains_the_role_word_is_not_a_role(self):
        """``s?`` must not turn 'latest' or 'greatest' into the role 'test'.

        This is the over-matching risk the widening introduces, asserted directly.
        """
        for decoy in ("latest", "greatest", "contestant"):
            with self.subTest(decoy=decoy):
                found = gc._paths_named_by_role(
                    f"the {decoy} run produced {self.rel(self.tests[0])}", "test", ROOT
                )
                self.assertEqual(
                    found, [],
                    f"'{decoy}' was treated as the role word 'test' and bound {found}",
                )


class TestTheWholeRepairFamily(PluralRoleBase):
    def test_the_harness_phrasing_binds_the_repair_family(self):
        """The measured effect: 0 of 10 before, 7 of 10 after.

        Asserted on the seven that bind. The three that still do not fail on
        other inputs (test_argv, pattern), which is a different defect and is
        deliberately not asserted here.
        """
        goal = (
            f"Repair the python source root {self.rel(self.src)} using the tests "
            f"{self.tests_phrase} and save the report to {self.rel(self.out)}."
        )
        bound = {}
        for cid in REPAIR_FAMILY:
            if cid not in self.reg:
                continue
            try:
                inputs = gc._bind_inputs(goal, ROOT, self.reg[cid])
            except gc.GoalCompilationFailure:
                bound[cid] = None
                continue
            lists = [v for k, v in inputs.items() if str(k).endswith("_paths") and v]
            bound[cid] = lists
        ok = {c: v for c, v in bound.items() if v}
        self.assertEqual(
            len(ok), len([c for c in REPAIR_FAMILY if c in self.reg]),
            f"expected every repair capability to bind the plural tests phrase; "
            f"unbound: {sorted(c for c, v in bound.items() if not v)}",
        )
        for cid, lists in ok.items():
            self.assertTrue(
                any(len(v) == len(self.tests) for v in lists),
                f"{cid} bound {lists} but the sentence named {len(self.tests)} tests",
            )


if __name__ == "__main__":
    unittest.main()
