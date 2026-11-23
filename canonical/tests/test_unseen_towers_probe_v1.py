#!/usr/bin/env python3
"""Pins the honest measurement shape of the 3-peg unseen-environment probe.

The probe in the repo root (`unseen_towers_probe_20261123.py`) is the measurement
record; this file pins its two load-bearing verdicts so a future change that
silently weakens the cold solve, the admission path, or the instant-replay same-
instance path fails visibly.

Authority NONE. Producer-run. $0. Zero model calls.
"""
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import perfect_algorithm_v1 as pa
from unseen_towers_probe_20261123 import TowersEnv, ACTIONS, heuristic_peg


def _fresh_mem(tmp):
    return str(tmp / "memory.json")


class UnseenTowersColdTest(unittest.TestCase):
    """A never-seen environment is cold-solved by the full loop (~1600-3000 trials)."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="towers-test-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_cold_solves_unseen_towers(self):
        env = TowersEnv()
        out = pa.run(env, "park all disks on peg 1", ACTIONS,
                     goal_predicate=env.is_goal, heuristic=heuristic_peg,
                     goal_family="towers_park_peg_1", env_kind="towers_stack_like",
                     memory_path_=_fresh_mem(self._tmp), budget=3000,
                     max_depth=12, seed=0)
        self.assertEqual(out["status"], "PASS__PERFECT_ALGORITHM_RUN",
                          msg=f"status={out['status']} pass={out.get('pass')}")
        self.assertTrue(out.get("pass"), msg=str(out.get("steps")))
        reached_goal = env.state()[("1", "2", "3").index("1")] == (1, 2, 3) and \
            all(env.state()[j] == () for j in range(3) if j != 0)
        self.assertTrue(reached_goal,
                        msg=f"goal not reached: state={env.state()}")
        mem = pa.load_memory(_fresh_mem(self._tmp))
        priors = pa.priors_for(mem, "towers_stack_like")
        self.assertGreater(len(priors.get("model") or {}), 1,
                           msg="observed transitions were persisted as priors")

    def test_cold_priors_do_not_carry_across_instances_silently(self):
        """Priors from a different source instance verify (or are discarded)."""
        env_a = TowersEnv()
        path = _fresh_mem(self._tmp)
        out_a = pa.run(env_a, "park all disks on peg 1", ACTIONS,
                       goal_predicate=env_a.is_goal, heuristic=heuristic_peg,
                       goal_family="towers_park_peg_1", env_kind="towers_stack_like",
                       memory_path_=path, budget=3000, max_depth=12, seed=0)
        self.assertTrue(out_a.get("pass"))
        # A different instance: same goal, different start → priors verify
        # only root rows (or none); the scan must re-derive the rest.
        env_b = TowersEnv(goal_peg="1", initial=((), (1,), (2, 3)))
        out_b = pa.run(env_b, "park all disks on peg 1", ACTIONS,
                       goal_predicate=env_b.is_goal, heuristic=heuristic_peg,
                       goal_family="towers_park_peg_1", env_kind="towers_stack_like",
                       memory_path_=path, budget=3000, max_depth=12, seed=0)
        self.assertTrue(out_b.get("pass"))
        steps = out_b.get("steps", {})
        scan = steps.get("scan") or {}
        warm = steps.get("warm_walk") or {}
        priors_used = (scan.get("priors_used") or 0) + (warm.get("priors_used") or 0)
        stale = scan.get("priors_stale_discarded") or 0
        self.assertTrue(priors_used + stale > 0,
                        msg="priors were either used or discarded, never invented")


class UnseenTowersWarmControlTest(unittest.TestCase):
    """Admission + instant recall on the identical-shape instance (control)."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="towers-test-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_identical_shape_instant_recall(self):
        path = _fresh_mem(self._tmp)
        fresh = [TowersEnv() for _ in range(2)]

        out_a = pa.run(TowersEnv(), "park all disks on peg 1", ACTIONS,
                       goal_predicate=TowersEnv().is_goal, heuristic=heuristic_peg,
                       goal_family="towers_park_peg_1", env_kind="towers_stack_like",
                       memory_path_=path, budget=3000, max_depth=12, seed=0,
                       unseen_instances=fresh,
                       fresh_reset=lambda e: e.reset(),
                       fresh_act=lambda e, a: e.act(a),
                       fresh_state=lambda e: e.state())
        self.assertEqual(out_a["steps"]["admit"]["verdict"], "ADMIT",
                         msg=str(out_a.get("steps")))

        out_b = pa.run(TowersEnv(), "park all disks on peg 1", ACTIONS,
                       goal_predicate=TowersEnv().is_goal, heuristic=heuristic_peg,
                       goal_family="towers_park_peg_1", env_kind="towers_stack_like",
                       memory_path_=path, budget=3000, max_depth=12, seed=0)
        self.assertEqual(out_b["status"], "PASS__REPLAY_FROM_MEMORY")
        self.assertEqual(out_b["outcome"], "INSTANT_RECALL")
        # instant recall means no scan ever happened
        self.assertNotIn("scan", out_b["steps"])


if __name__ == "__main__":
    unittest.main()
