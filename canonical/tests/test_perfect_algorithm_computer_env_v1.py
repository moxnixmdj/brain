"""Real-computer proof for the perfect algorithm.

The perfect algorithm has always been measured on constructed toys
(dials, grids, buffers, towers). This test drives it -- cold, with no
instant knowledge, no model calls -- against the REAL computer environment
adapter: real programs (gzip) found on the PATH, real files, real
subprocess execution, real verified artifact.

Not a capability claim: the measured task is one compression of one file in
a temp sandbox. It does not claim OSWorld/Terminal-Bench/ARC-AGI-3 closure.
"""
from __future__ import annotations

import gzip
import json
import tempfile
import time
import unittest
from pathlib import Path

from canonical.swe_kernel.perfect_algorithm_computer_env_v1 import (
    build_env,
    drive_perfect_algorithm,
)

GOAL = "compress seed.txt into seed.txt.gz"
SEED_BYTES = b"alpha beta gamma\ndelta epsilon\nzeta eta\n"


def _fresh():
    return Path(tempfile.mkdtemp(prefix="pa_computer_env_test_"))


class RealComputerAdapterTests(unittest.TestCase):
    def test_narrowing_recommends_the_program_that_compresses_not_decompresses(self):
        env, meta = build_env(GOAL, seed_contents={"seed.txt": SEED_BYTES}, limit=8)
        self.assertIn("gzip", meta["programs"],
                      "the narrowing must keep the compress-specific program "
                      "even though gunzip is the same binary and wins the "
                      "tie-break by name")
        env.close()

    def test_cold_run_closes_with_a_verified_artifact(self):
        tmp = _fresh()
        receipts, meta, env = drive_perfect_algorithm(
            GOAL, seed_contents={"seed.txt": SEED_BYTES},
            limit=8, budget=60, max_depth=4,
            memory_path_=tmp / "memory.json",
        )
        self.assertTrue(receipts.get("pass"), receipts)
        self.assertEqual(receipts.get("outcome"), "VERIFIED_NOT_PERSISTED")
        plan = (receipts.get("steps") or {}).get("act", {}).get("executed")
        self.assertIn("run_gzip", plan or [])
        tree = env.tree()
        self.assertIn("seed.txt.gz", tree)
        self.assertEqual(gzip.decompress(tree["seed.txt.gz"]), SEED_BYTES)
        env.close()

    def test_unseen_content_warm_replay_is_instant(self):
        """Teach on content A, replay on content B: rule does not name bytes."""
        from canonical.swe_kernel import perfect_algorithm_v1 as pa

        tmp = _fresh()
        teach_seed = b"teach seed bytes\nsecond line\n"
        target_seed = b"different bytes entirely\nsame goal\n"
        env_t, meta_t = build_env(GOAL, seed_contents={"seed.txt": teach_seed}, limit=8)
        fresh = []
        for variant in (b"variant alpha\n", b"variant beta\n"):
            fe, _ = build_env(GOAL, seed_contents={"seed.txt": variant}, limit=8)
            fresh.append(fe)
        mem_path = tmp / "memory.json"
        out_teach = pa.run(
            env_t, GOAL, env_t.action_names(),
            goal_predicate=meta_t["is_goal"], env_kind="computer_file_ops",
            memory_path_=mem_path, budget=200, max_depth=4,
            heuristic=meta_t["heuristic"],
            unseen_instances=fresh,
            fresh_reset=lambda e: e.reset(),
            fresh_act=lambda e, a: e.act(a),
            fresh_state=lambda e: e.state(),
        )
        self.assertEqual(out_teach.get("status"), "PASS__PERFECT_ALGORITHM_RUN")
        admit = (out_teach.get("steps") or {}).get("admit") or {}
        self.assertEqual(admit.get("verdict"), "ADMIT")

        env_b, meta_b = build_env(GOAL, seed_contents={"seed.txt": target_seed}, limit=8)
        out_warm = pa.run(
            env_b, GOAL, env_b.action_names(),
            goal_predicate=meta_b["is_goal"], env_kind="computer_file_ops",
            memory_path_=mem_path, budget=200, max_depth=4,
            heuristic=meta_b["heuristic"],
        )
        self.assertEqual(out_warm.get("outcome"), "INSTANT_RECALL")
        warm_steps = out_warm.get("steps") or {}
        self.assertEqual((warm_steps.get("memory_replay") or {}).get("status"),
                         "PASS__REPLAY_REACHED_GOAL")
        env_t.close()
        env_b.close()

        for e in fresh:
            try:
                e.close()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
