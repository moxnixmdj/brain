#!/usr/bin/env python3
"""Pins the carried-model warm path in `perfect_algorithm_v1.run`.

Teach instance A (all disks on peg 3 -> goal peg 1), then run a DIFFERENT
instance B (mixed start) whose root IS a state the source's model already
covers. The warm path must verify the carried model edge-by-edge and skip the
full scan -- not the admitted-rule replay (which is identical-shape only).

Authority NONE. Producer-run. $0.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.swe_kernel import perfect_algorithm_v1 as pa
from unseen_towers_probe_20261123 import TowersEnv, ACTIONS, heuristic_peg


class CarriedModelWalkWarmTest(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="walk-test-"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_shared_root_different_start_skips_scan(self):
        path = self._tmp / "memory.json"
        fresh = [TowersEnv() for _ in range(2)]
        # TEACH: source = classic stack on peg3 -> park on peg1
        out_a = pa.run(TowersEnv(goal_peg="1", initial=((), (), (1, 2, 3))),
                       "park all disks on peg 1", ACTIONS,
                       goal_predicate=TowersEnv().is_goal,
                       heuristic=lambda obs: heuristic_peg(obs, "1"),
                       goal_family="towers_park_peg_1", env_kind="towers_stack_like",
                       memory_path_=path, budget=3000, max_depth=12, seed=0,
                       unseen_instances=fresh,
                       fresh_reset=lambda e: e.reset(),
                       fresh_act=lambda e, a: e.act(a),
                       fresh_state=lambda e: e.state())
        self.assertTrue(out_a.get("pass"), msg=str(out_a.get("steps")))

        # WARM: different start, shared goal. Its root state is one the
        # source's stored model already covers.
        env_b = TowersEnv(goal_peg="1", initial=((), (1,), (2, 3)))
        out_b = pa.run(env_b, "park all disks on peg 1", ACTIONS,
                       goal_predicate=env_b.is_goal,
                       heuristic=lambda obs: heuristic_peg(obs, "1"),
                       goal_family="towers_park_peg_1", env_kind="towers_stack_like",
                       memory_path_=path, budget=3000, max_depth=12, seed=0)
        self.assertTrue(out_b.get("pass"))
        walk = out_b["steps"].get("warm_walk")
        self.assertIsNotNone(walk, msg=f"expected a carried-walk receipt, steps={out_b['steps']}")
        self.assertEqual(walk.get("status"), "PASS__CARRIED_WALK_REACHED_GOAL")
        self.assertTrue(walk.get("reached"))
        self.assertNotIn("scan", out_b["steps"],
                         msg="the walk must skip the full scan when it reaches the goal")

    def test_identical_shape_replay_still_takes_priority(self):
        # the admitted rule replay remains the identical-shape path
        path = self._tmp / "memory2.json"
        fresh = [TowersEnv() for _ in range(2)]
        out_a = pa.run(TowersEnv(), "park all disks on peg 1", ACTIONS,
                       goal_predicate=TowersEnv().is_goal,
                       heuristic=lambda obs: heuristic_peg(obs, "1"),
                       goal_family="towers_park_peg_1", env_kind="towers_stack_like",
                       memory_path_=path, budget=3000, max_depth=12, seed=0,
                       unseen_instances=fresh,
                       fresh_reset=lambda e: e.reset(),
                       fresh_act=lambda e, a: e.act(a),
                       fresh_state=lambda e: e.state())
        self.assertTrue(out_a.get("pass"))
        out_b = pa.run(TowersEnv(), "park all disks on peg 1", ACTIONS,
                       goal_predicate=TowersEnv().is_goal,
                       heuristic=lambda obs: heuristic_peg(obs, "1"),
                       goal_family="towers_park_peg_1", env_kind="towers_stack_like",
                       memory_path_=path, budget=3000, max_depth=12, seed=0)
        self.assertEqual(out_b["status"], "PASS__REPLAY_FROM_MEMORY")
        self.assertNotIn("warm_walk", out_b["steps"],
                         msg="rule replay should come first on identical shape")


if __name__ == "__main__":
    unittest.main()
