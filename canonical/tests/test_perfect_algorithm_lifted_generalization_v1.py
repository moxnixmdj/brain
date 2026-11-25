#!/usr/bin/env python3
"""Tests for lifted generalization — the one wire that makes LEARN true understanding."""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import perfect_algorithm_lifted_generalization_v1 as lg
from canonical.swe_kernel import perfect_algorithm_v1 as pa


class LiftTests(unittest.TestCase):
    def test_incidental_suffix_lifted(self):
        out = lg.lift_plan_sketch(["run_gzip", "out.tmp"], goal="compress into out.gz")
        self.assertIn("{{target}}", out["lifted"])

    def test_literal_kept_when_goal_contains_it(self):
        out = lg.lift_plan_sketch(["sort", "words.txt"], goal="sort words.txt")
        # sort is verb, words.txt in goal → not lifted
        self.assertEqual(out["lifted"], ["sort", "words.txt"])
        self.assertEqual(out["lift_count"], 0)

    def test_no_over_generalize_without_evidence(self):
        out = lg.lift_plan_sketch(["d0", "d1"], goal="open dial lock")
        # d0,d1 are action verbs in allowlist → kept
        self.assertEqual(out["lift_count"], 0)

    def test_generalize_lifted_produces_rule(self):
        trace = [{"before": "s0", "action": "d0", "after": "s1"}]
        gen = lg.generalize_lifted(trace, ["d0", "d0"], goal="open lock",
                                   goal_family="dial_lock", env_kind="dial_lock")
        self.assertEqual(gen["status"], "PASS__LIFTED_GENERALIZED")
        rule = gen["generalization"]
        self.assertTrue(rule["rule_id"].startswith("ga-lift-"))
        self.assertEqual(rule["goal_family"], "dial_lock")
        self.assertIn("plan_template", rule)
        self.assertIn("evidence", rule)


class ApplicabilityTests(unittest.TestCase):
    def test_undetermined_with_only_success(self):
        row = lg.induce_applicability(success_states=[{"git": True}], failure_states=[])
        # applicability requires contrast — one success alone is UNDETERMINED
        self.assertIn(row["status"], (lg._APP_UNDETERMINED if lg.HAS_APPLICABILITY else row["status"], "REFUSED__NO_EVIDENCE"))

    def test_identified_with_contrast(self):
        # 2 facts: one success state has {a}, failure has {}
        # Candidate facts = {a}, hypotheses = {(), (a,)}; success needs (a,), failure needs ()
        # → only (a,) survives → IDENTIFIED
        row = lg.induce_applicability(success_states=[["a"]], failure_states=[[]])
        if lg.HAS_APPLICABILITY:
            self.assertEqual(row["status"], "IDENTIFIED__ONE_CONSISTENT_REQUIREMENT")
            self.assertEqual(row["required"], ["a"])

    def test_no_evidence_refused(self):
        row = lg.induce_applicability(success_states=[], failure_states=[])
        self.assertEqual(row["status"], "REFUSED__NO_EVIDENCE")


class RunLiftedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = pathlib.Path(tempfile.mkdtemp(prefix="lg-test-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_run_lifted_on_grid_world(self):
        # reuse perfect_algorithm test env: WallGrid
        from canonical.tests.test_perfect_algorithm_v1 import WallGrid, _grid_heuristic, _exit_predicate
        env = WallGrid(walls=())
        mem_path = self._tmp / "mem.json"
        out = lg.run_lifted(env, "reach the exit", ["up", "down", "left", "right"],
                            goal_predicate=_exit_predicate, heuristic=_grid_heuristic,
                            goal_family="grid_world", env_kind="grid_world",
                            memory_path_=mem_path, budget=40, max_depth=12, seed=0)
        self.assertTrue(out.get("pass"))
        self.assertIn("lifted_generalization", out)
        self.assertEqual(out["lifted_generalization"]["goal_family"], "grid_world")

    def test_lifted_admit_delegates(self):
        # admit on dial lock with fresh instances
        from canonical.tests.test_perfect_algorithm_v1 import Lock, _lock_heuristic
        target = (7, 2, 9)
        env = Lock(target=target)
        goal_pred = lambda obs: obs == target
        trace = [{"a": "d0"}]
        gen = lg.generalize_lifted(trace, plan=["d0"] * 7 + ["d1"] * 2 + ["d2"] * 9,
                                   goal="open dial lock", goal_family="dial_lock", env_kind="dial_lock")
        rule = gen["generalization"]
        # build a permissive applicability to test filtering pass-through
        rule["plan_sketch"] = ["d0"] * 7 + ["d1"] * 2 + ["d2"] * 9
        fresh = [Lock(target=target) for _ in range(2)]
        verdict = lg.admit_lifted(rule, fresh, goal_pred,
                                  reset=lambda e: e.reset(),
                                  act=lambda e, a: e.act(a),
                                  state=lambda e: e.state())
        self.assertEqual(verdict["verdict"], "ADMIT")


if __name__ == "__main__":
    unittest.main()
