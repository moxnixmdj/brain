#!/usr/bin/env python3
"""Honest tests for the scan-level code-repair env (§23).

Covers:
  - the env protocol: act, state, snapshot/restore, refusals by name
  - the real-oracle discipline: state reports the subprocess test verdict
  - the full generic chain (§17) on an unseen broken file: scan -> plan ->
    act -> verify -> admit -> persist -> replay, honestly through the same
    path the archive family already proves.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel.code_repair_scan_env_v1 import (
    CodeRepairEnv,
    build_code_repair_env,
    DEFAULT_CANDIDATES,
)

BROKEN = "def add(a, b):\n    return a - b\n"
TEST = "from broken_module import add\nassert add(2, 3) == 5\nassert add(0, 0) == 0\nprint('PASS')\n"


class CodeRepairEnvTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="code_repair_scan_env_test_")
        self.env, self.meta = build_code_repair_env(BROKEN, TEST,
                                                     workdir=self.tmp)

    def tearDown(self):
        self.env.close()

    def test_state_reports_the_real_test_verdict(self):
        self.assertFalse(self.env.state()["passes"])
        self.env.act("fix_op:-|+")
        self.assertTrue(self.env.state()["passes"])

    def test_act_refuses_an_action_outside_the_envelope(self):
        self.assertFalse(self.env.act("rm -rf"))
        self.assertFalse(self.env.act("fix_op:"))
        self.assertFalse(self.env.act("fix_op:+|+"))  # no-op, honestly refused
        self.assertFalse(self.env.act("fix_op:not_a_token|+"))

    def test_act_rewrites_every_occurrence(self):
        self.env._module_file.write_text("def f(x):\n    return x - 1 - x\n", encoding="utf-8")
        self.env.act("fix_op:-|+")
        text = self.env._module_file.read_text()
        self.assertNotIn("-", text)
        self.assertIn("+", text)

    def test_snapshot_restore_round_trips_the_broken_file(self):
        before = self.env._module_file.read_text()
        saved = self.env.snapshot()
        self.env.act("fix_op:-|+")
        self.assertTrue(self.env.state()["passes"])
        self.env.restore(saved)
        self.assertEqual(self.env._module_file.read_text(), before)

    def test_reset_restores_the_broken_file(self):
        self.env.act("fix_op:-|+")
        self.env.reset()
        self.assertFalse(self.env.state()["passes"])

    def test_build_env_meta_exposes_the_scan_hooks(self):
        self.assertEqual(self.meta["env_kind"], "code_repair")
        self.assertTrue(callable(self.meta["is_goal"]))
        self.assertTrue(callable(self.meta["heuristic"]))
        self.assertEqual(self.meta["heuristic"](self.env.state()), 1.0)
        self.env.act("fix_op:-|+")
        self.assertEqual(self.meta["heuristic"](self.env.state()), 0.0)

    def test_action_space_is_content_invariant(self):
        # every action is the same rule across every instance: no instance
        # coordinates anywhere in the plan sketch
        for action in self.env.action_names():
            self.assertTrue(action.startswith("fix_op:")
                            and "|" in action)


class FullChainTeachTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="code_repair_chain_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_teach_admits_persists_and_replays_warm(self):
        # the teach env and the fresh envs
        teach_env, teach_meta = build_code_repair_env(
            BROKEN, TEST,
            workdir=str(Path(self.tmp) / "teach"))

        fresh_a_env, _ = build_code_repair_env(
            "def diff(x, y):\n    return x - y\n",
            "from broken_module import diff\nassert diff(2, 3) == 5\nprint('PASS')\n",
            workdir=str(Path(self.tmp) / "fresh_a"))
        fresh_b_env, _ = build_code_repair_env(
            "def scale(x, y):\n    return x - y\n",
            "from broken_module import scale\nassert scale(10, 2) == 8\nprint('PASS')\n",
            workdir=str(Path(self.tmp) / "fresh_b"))

        mem = str(Path(self.tmp) / "memory.json")
        try:
            teach_out = pa.run(
                teach_env, "fix module.py so its test passes",
                teach_env.action_names(),
                goal_predicate=teach_meta["is_goal"], env_kind="code_repair",
                memory_path_=mem, budget=2, max_depth=4,
                heuristic=teach_meta["heuristic"],
                unseen_instances=[fresh_a_env, fresh_b_env],
                fresh_reset=lambda e: e.reset(),
                fresh_act=lambda e, a: e.act(a),
                fresh_state=lambda e: e.state(),
            )
        finally:
            teach_env.close()
            fresh_a_env.close()
            fresh_b_env.close()

        self.assertTrue(teach_out.get("pass"), teach_out)
        admit = (teach_out.get("steps") or {}).get("admit") or {}
        self.assertEqual(admit.get("verdict"), "ADMIT", admit)
        # rows: REACHED for the same-shape defect, NOT_REACHED for the
        # correctly-guarded one -- the honest receipt
        rows = {row["verdict"] for row in admit.get("rows") or []}
        self.assertIn("REACHED", rows)
        self.assertIn("NOT_REACHED", rows)
        self.assertTrue(admit.get("persist"), admit)
        self.assertEqual(admit.get("reached"), 1)

        # the persisted rule is on disk and matches the plan sketch
        saved = json.loads(Path(mem).read_text())
        rules = saved.get("rules") or []
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].get("plan_sketch"), ["fix_op:-|+"])

        # replay on a fresh same-shape broken file: INSTANT_RECALL, content-verified
        target_env, target_meta = build_code_repair_env(
            "def calc(x, y):\n    return x - y\n",
            "from broken_module import calc\nassert calc(2, 3) == 5\nprint('PASS')\n",
            workdir=str(Path(self.tmp) / "target"))
        try:
            warm_out = pa.run(
                target_env, "fix module.py so its test passes",
                target_env.action_names(),
                goal_predicate=target_meta["is_goal"], env_kind="code_repair",
                memory_path_=mem, budget=2, max_depth=4,
                heuristic=target_meta["heuristic"],
            )
        finally:
            target_env.close()

        self.assertEqual(warm_out.get("outcome"), "INSTANT_RECALL", warm_out)


if __name__ == "__main__":
    unittest.main()
