#!/usr/bin/env python3
"""An adapter's delegation to its suite runner must be followed, not assumed shallow.

``test_argv`` is optional in every adapter that takes it, because each falls back
to a shared ``suite_argv`` that embeds the collecting suite runner.  The compiler
asks the adapter for that default rather than duplicating the runner, and fails
closed when it cannot find one.

The search looked one module level deep.  But the adapters reach the helper at
different depths:

    python_software_repair_loop_v1.py                   ptg.suite_argv             depth 1  found
    python_repair_measured_acceptance_controller_v1.py  _REPAIR._PATCH.suite_argv  depth 2  MISSED
    python_repair_semantic_acceptance_controller_v1.py  v8._REPAIR._PATCH....      depth 3  MISSED

So two capabilities could never bind ``test_argv``, raised
``GOAL_INPUT_BINDING_REQUIRED:test_argv`` for every sentence, and were
unreachable however well the sentence described the work.  The delegation was
real in all three; only the discovery stopped early.

Measured over the repair / localisation / patch / audit family with the live
harness's own plural phrasing:

    0 of 10 bound   before the plural role-word fix
    7 of 10 bound   after it
    9 of 10 bound   after this

The tenth needs ``pattern``, and a sentence that would use it routes to
``python.source.audit.ast`` instead, which binds -- so that is routing, not a
binding defect, and is deliberately not asserted here.
"""
from __future__ import annotations

import pathlib
import shutil
import sys
import tempfile
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import goal_compiler as gc
from canonical.runtime.live_integrated_brain_v1 import load_verified_registry

# The two that a one-level search could not reach.
DEEP_DELEGATORS = (
    "python.software.repair.measured_acceptance.v1",
    "python.software.repair.semantic_acceptance.v1",
)
# The one that already worked at depth 1 -- widening must not break it.
SHALLOW_DELEGATOR = "python.software.repair.loop.test_guided.ast.v1"

REPAIR_FAMILY = (
    "python.fault.localize.dynamic.dataflow.v1",
    "python.fault.provenance.interprocedural.value.v1",
    "python.patch.search.test_guided.ast.v1",
    "python.software.repair.guided.provenance.coupled.v1",
    "python.software.repair.loop.coupled.ast.v1",
    "python.software.repair.loop.strict_progress.ast.v1",
    "python.software.repair.loop.test_guided.ast.v1",
    "python.software.repair.measured_acceptance.v1",
    "python.software.repair.semantic_acceptance.v1",
)


class SuiteArgvDelegationBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg = gc._platform_admissible_registry(load_verified_registry())

    def setUp(self):
        self.tmp = pathlib.Path(
            tempfile.mkdtemp(prefix="argv_delegation_", dir=str(ROOT / "canonical/astra_runtime/tmp"))
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
    def goal(self):
        phrase = ", ".join(self.rel(t) for t in self.tests)
        return (
            f"Repair the python source root {self.rel(self.src)} using the tests {phrase} "
            f"and save the report to {self.rel(self.out)}."
        )

    def bind(self, cid):
        return gc._bind_inputs(self.goal, ROOT, self.reg[cid])


class TestDeepDelegationIsFollowed(SuiteArgvDelegationBase):
    def test_the_two_deep_delegators_now_bind_test_argv(self):
        for cid in DEEP_DELEGATORS:
            with self.subTest(cid=cid):
                if cid not in self.reg:
                    self.skipTest(f"{cid} not admissible")
                inputs = self.bind(cid)
                argv = inputs.get("test_argv")
                self.assertIsInstance(argv, list)
                self.assertTrue(argv, f"{cid} bound an empty test_argv")

    def test_the_derived_argv_is_the_adapters_own_and_names_the_real_tests(self):
        """Not a fabricated command line: it must be the runner the adapter uses."""
        cid = DEEP_DELEGATORS[0]
        argv = self.bind(cid)["test_argv"]
        self.assertEqual(argv[0], sys.executable)
        joined = " ".join(str(a) for a in argv)
        for t in self.tests:
            self.assertIn(self.rel(t), joined, f"the derived argv omits {self.rel(t)}")

    def test_the_shallow_delegator_still_binds(self):
        """Widening the search must not have broken the case that already bound.

        Note this capability declares no ``test_argv`` input at all -- it takes
        ``source_paths`` and ``test_paths`` and derives its own command line
        internally -- so the honest assertion is that its list inputs still bind,
        not that a key it does not have appeared.
        """
        inputs = self.bind(SHALLOW_DELEGATOR)
        lists = {k: v for k, v in inputs.items() if str(k).endswith("_paths") and v}
        self.assertIn("test_paths", lists)
        self.assertEqual(
            sorted(lists["test_paths"]), sorted(self.rel(t) for t in self.tests),
        )

    def test_nine_of_the_ten_repair_capabilities_bind(self):
        bound = []
        for cid in REPAIR_FAMILY:
            if cid not in self.reg:
                continue
            try:
                inputs = gc._bind_inputs(self.goal, ROOT, self.reg[cid])
            except gc.GoalCompilationFailure:
                continue
            if any(str(k).endswith(("_paths", "_argv")) and v for k, v in inputs.items()):
                bound.append(cid)
        present = [c for c in REPAIR_FAMILY if c in self.reg]
        self.assertEqual(
            len(bound), len(present),
            f"unbound: {sorted(set(present) - set(bound))}",
        )


def _mod(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    return m


class TestTheSearchIsBounded(unittest.TestCase):
    """A recursive walk over an import graph must terminate and still fail closed."""

    def test_an_import_cycle_terminates_and_returns_none(self):
        a = _mod("cycle_a")
        b = _mod("cycle_b", parent=a)
        a.child = b  # a -> b -> a
        self.assertIsNone(gc._find_suite_argv(a))

    def test_a_self_referencing_module_terminates(self):
        a = _mod("self_ref")
        a.me = a
        self.assertIsNone(gc._find_suite_argv(a))

    def test_a_chain_beyond_the_depth_cap_is_not_followed(self):
        """Bounded on purpose: fail closed rather than walk an unbounded graph."""
        runner = _mod("deep_runner", suite_argv=lambda *a: ["python", "-m", "unittest"])
        chain = runner
        for i in range(10):
            chain = _mod(f"hop_{i}", nxt=chain)
        self.assertIsNone(gc._find_suite_argv(chain))

    def test_a_helper_within_the_cap_is_found(self):
        runner = _mod("near_runner", suite_argv=lambda *a: ["python", "-m", "unittest"])
        mid = _mod("mid", inner=runner)
        top = _mod("top", child=mid)
        self.assertIsNotNone(gc._find_suite_argv(top))

    def test_a_module_with_no_runner_anywhere_returns_none(self):
        """The fail-closed behaviour the whole design depends on."""
        leaf = _mod("leaf", helper=lambda: 1)
        top = _mod("top2", child=leaf)
        self.assertIsNone(gc._find_suite_argv(top))

    def test_a_direct_suite_argv_is_preferred_over_a_deeper_one(self):
        near = _mod("near", suite_argv=lambda *a: ["near"])
        far = _mod("far", suite_argv=lambda *a: ["far"])
        top = _mod("top3", suite_argv=near.suite_argv, other=far)
        found = gc._find_suite_argv(top)
        self.assertEqual(found("x"), ["near"])


if __name__ == "__main__":
    unittest.main()
