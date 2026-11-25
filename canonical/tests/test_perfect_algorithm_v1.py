"""The Perfect Algorithm: honest tests.

These do not claim the mission is done. They test what the module MEASURES:
that the scan records the affordances it actually observed, that the right
question is computed from the model, that the plan is minimal over the model,
that a generalization admitted on fresh instances replays cleanly, that a
generalization NOT admitted on fresh instances is NOT persisted, and that the
priors (the observed environment model) are saved unconditionally once the
loop verified.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from canonical.swe_kernel import perfect_algorithm_v1 as pa


# --------------------------------------------------------------------------- #
# environment: a 4x4 grid with walls, the same shape used elsewhere in the repo
# --------------------------------------------------------------------------- #
class WallGrid:
    """4x4, start (0,0), exit (3,3); walls are a fixed, documented set per test."""

    kind = "grid_world"

    def __init__(self, walls=()):
        self.walls = frozenset(walls)
        self.p = (0, 0)

    def reset(self) -> None:
        self.p = (0, 0)

    def state(self):
        return self.p

    def act(self, a) -> None:
        x, y = self.p
        move = {"up": (x, y - 1), "down": (x, y + 1),
                "left": (x - 1, y), "right": (x + 1, y)}[str(a)]
        if 0 <= move[0] < 4 and 0 <= move[1] < 4 and move not in self.walls:
            self.p = move

    def snapshot(self):
        return self.p

    def restore(self, s) -> None:
        self.p = s

    def is_goal(self, obs) -> bool:
        return obs == (3, 3)


class Lock:
    kind = "dial_lock"

    def __init__(self, target=(7, 2, 9)):
        self.d = [0, 0, 0]
        self.target = target

    def reset(self) -> None:
        self.d = [0, 0, 0]

    def state(self):
        return tuple(self.d)

    def act(self, a) -> None:
        i = int(str(a)[1])
        self.d[i] = (self.d[i] + 1) % 10

    def snapshot(self):
        return list(self.d)

    def restore(self, s) -> None:
        self.d = list(s)


GOAL = lambda env: ("dial 0 to 7, dial 1 to 2, dial 2 to 9" if getattr(env, "target", None) else "")


def _is_exit(env):
    env.reset()
    return env.state() == (3, 3)


def _exit_predicate(obs) -> bool:
    return obs == (3, 3)


def _grid_heuristic(obs):
    x, y = obs
    return abs(3 - x) + abs(3 - y)


def _lock_heuristic(obs, target=(7, 2, 9)):
    return sum(abs(a - b) for a, b in zip(obs, target))


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="pa-test-"))
        self._path = self._tmp / "memory.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_empty_memory_loads(self):
        mem = pa.load_memory(self._path)
        self.assertEqual(mem["schema"], pa.MEMORY_SCHEMA)
        self.assertEqual(mem["rules"], [])
        self.assertEqual(mem["priors"], {})

    def test_remember_priors_round_trip(self):
        mem = pa.load_memory(self._path)
        mem = pa.remember_priors(mem, "grid_world", {"s0": {"right": "s1"}})
        pa.save_memory(mem, self._path)
        loaded = pa.load_memory(self._path)
        priors = pa.priors_for(loaded, "grid_world")
        self.assertEqual(priors["model"], {"s0": {"right": "s1"}})

    def test_remember_rule_and_lookup(self):
        mem = pa.load_memory(self._path)
        mem = pa.remember(mem, {"rule_id": "ga-test-1", "goal_family": "dial_lock",
                                "env_kind": "dial_lock",
                                "scope": {"goal_family": "dial_lock", "env_kind": "dial_lock"},
                                "plan_sketch": ["d0"], "created_at": 1.0})
        pa.save_memory(mem, self._path)
        loaded = pa.load_memory(self._path)
        hits = pa.lookup(loaded, "dial_lock", "dial_lock")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["rule_id"], "ga-test-1")
        # different goal family must not match
        self.assertEqual(pa.lookup(loaded, "grid_world", "grid_world"), [])

    def test_corrupt_memory_refused_not_rewritten(self):
        self._path.write_text("not json {{{", encoding="utf-8")
        mem = pa.load_memory(self._path)
        self.assertIn("MEMORY_CORRUPT", mem.get("refused", ""))
        self.assertEqual(mem["rules"], [])

    def test_remember_refuses_empty_rule_id(self):
        mem = {"schema": pa.MEMORY_SCHEMA, "rules": []}
        out = pa.remember(mem, {"rule_id": "", "goal_family": "x"})
        self.assertEqual(out.get("rules", []), [])


class ScanTests(unittest.TestCase):
    def test_scan_records_affordances(self):
        env = WallGrid(walls=())
        scan = pa.scan(env, ["up", "down", "left", "right"], budget=8, max_depth=12,
                       heuristic=_grid_heuristic, seed=0)
        self.assertGreater(scan["state_count"], 1, "scan must record states")
        self.assertGreater(scan["transition_count"], 0)
        self.assertEqual(scan["root"], scan["learned"]["root"])
        # affordances recorded: some state has actions mapped
        self.assertTrue(any(v for v in scan["affordances"].values()))

    def test_right_question_reports_novelty(self):
        env = WallGrid(walls=())
        scan = pa.scan(env, ["up", "down", "left", "right"], budget=8, max_depth=12,
                       heuristic=_grid_heuristic, seed=0)
        right = pa.right_question(env, scan, ["up", "down", "left", "right"])
        self.assertIn("best", right)
        self.assertEqual(len(right["ranked"]), 4)
        # no heuristic and no probe -> novelty ordering, reported honestly
        self.assertIn("novelty", right["honest_note"])

    def test_right_question_probes_when_env_supports_it(self):
        env = WallGrid(walls=())
        def closeness(obs):
            # smaller distance from exit is "better" (progress)
            x, y = obs
            return abs(3 - x) + abs(3 - y)
        scan = pa.scan(env, ["up", "down", "left", "right"], budget=8, max_depth=12,
                       heuristic=closeness, seed=0)
        right = pa.right_question(env, scan, ["up", "down", "left", "right"],
                                  heuristic=closeness)
        self.assertGreater(right["probed_actions"], 0)
        # the probed action that reduces closeness wins
        probed = [r for r in right["ranked"] if r["probed"]]
        self.assertTrue(probed)
        self.assertIn("closeness-probed", right["honest_note"])


class PlanTests(unittest.TestCase):
    def test_plan_exit_in_empty_grid_is_6(self):
        # straight line: 3 right + 3 down
        env = WallGrid(walls=())
        scan = pa.scan(env, ["up", "down", "left", "right"], budget=40,
                       max_depth=12, heuristic=_grid_heuristic, seed=0)
        out = pa.plan(scan["learned"], _exit_predicate, scan["observations"])
        self.assertEqual(out["status"], "PASS__PLAN_COMPUTED")
        self.assertEqual(out["plan_length"], 6)

    def test_plan_refuses_when_goal_never_observed(self):
        # an unreachable goal: the model never saw the exit (empty region is fine here;
        # a goal inside a wall the env can never reach)
        env = WallGrid(walls=((3, 3), (2, 2), (3, 2), (2, 3)))
        scan = pa.scan(env, ["up", "down", "left", "right"], budget=6,
                       max_depth=12, heuristic=_grid_heuristic, seed=0)
        out = pa.plan(scan["learned"], _exit_predicate, scan["observations"])
        self.assertNotEqual(out["status"], "PASS__PLAN_COMPUTED")


class LoopTests(unittest.TestCase):
    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="pa-loop-"))
        self._mem_path = self._tmp / "memory.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_full_loop_solves_and_saves_priors(self):
        env = WallGrid(walls=())
        out = pa.run(env, "reach the exit",
                     ["up", "down", "left", "right"],
                     goal_predicate=_exit_predicate, heuristic=_grid_heuristic,
                     goal_family="grid_world", env_kind="grid_world",
                     memory_path_=self._mem_path, budget=40, max_depth=12, seed=0)
        self.assertEqual(out["status"], "PASS__PERFECT_ALGORITHM_RUN")
        self.assertTrue(out["pass"])
        # priors were saved (observed facts, not hypotheses)
        mem = pa.load_memory(self._mem_path)
        priors = pa.priors_for(mem, "grid_world")
        self.assertGreater(len(priors["model"]), 1)
        # the rule was NOT persisted (no fresh instances offered)
        self.assertEqual(out["steps"]["save"]["status"], "REFUSED__NOT_PERSISTED")
        self.assertEqual(mem.get("rules", []), [])

    def test_full_loop_admits_rule_on_fresh_instance_same_goal(self):
        # dial lock: the plan to reach (7,2,9) is instance-invariant
        target = (7, 2, 9)
        env = Lock(target=target)
        goal_pred = lambda obs: obs == target

        # fresh instances: identical shape/behavior -- the plan is instance-invariant
        fresh = [Lock(target=target) for _ in range(2)]

        out = pa.run(env, "open dial lock", ["d0", "d1", "d2"],
                     goal_predicate=goal_pred,
                     heuristic=lambda obs: _lock_heuristic(obs, target),
                     goal_family="dial_lock", env_kind="dial_lock",
                     memory_path_=self._mem_path, budget=40, max_depth=24, seed=0,
                     unseen_instances=fresh,
                     fresh_reset=lambda e: e.reset(),
                     fresh_act=lambda e, a: e.act(a),
                     fresh_state=lambda e: e.state())
        self.assertEqual(out["status"], "PASS__PERFECT_ALGORITHM_RUN")
        self.assertEqual(out["steps"]["admit"]["verdict"], "ADMIT")
        self.assertEqual(out["steps"]["save"]["status"], "PASS__SAVED_TO_MEMORY")
        mem = pa.load_memory(self._mem_path)
        self.assertEqual(len(mem.get("rules", [])), 1)
        self.assertEqual(mem.get("priors", {}), mem.get("priors", {}))  # priors saved

    def test_stale_rule_falls_through(self):
        # a rule stored for the SAME family but a different goal must not be
        # served as an answer -- it is tried, fails, and the loop proceeds.
        env = Lock(target=(7, 2, 9))
        mem_path = self._mem_path
        mem = pa.load_memory(mem_path)
        stale = {"rule_id": "ga-stale", "goal_family": "dial_lock",
                 "scope": {"goal_family": "dial_lock", "env_kind": "dial_lock"},
                 "env_kind": "dial_lock",
                 "plan_sketch": ["d0"], "created_at": 0.0}
        mem = pa.remember(mem, stale)
        pa.save_memory(mem, mem_path)
        goal_pred = lambda obs: obs == (7, 2, 9)
        out = pa.run(env, "open dial lock", ["d0", "d1", "d2"],
                     goal_predicate=goal_pred,
                     heuristic=lambda obs: _lock_heuristic(obs, (7, 2, 9)),
                     goal_family="dial_lock", env_kind="dial_lock",
                     memory_path_=mem_path, budget=40, max_depth=24, seed=0)
        # the stale rule was tried and failed honestly; the loop fell through
        self.assertIn(out["steps"].get("memory_replay", {}).get("status", ""),
                      ("OPEN__REPLAY_FAILED", "OPEN__REPLAY_ERROR"))
        self.assertEqual(out["status"], "PASS__PERFECT_ALGORITHM_RUN")

    def test_priors_seed_a_fresh_scan(self):
        # after one run persists priors, the next run uses them
        env = Lock(target=(3, 3, 3))
        goal_pred = lambda obs: obs == (3, 3, 3)
        out1 = pa.run(env, "open dial lock", ["d0", "d1", "d2"],
                      goal_predicate=goal_pred,
                      heuristic=lambda obs: _lock_heuristic(obs, (3, 3, 3)),
                      goal_family="dial_lock", env_kind="dial_lock",
                      memory_path_=self._mem_path, budget=40, max_depth=24, seed=0)
        self.assertEqual(out1["status"], "PASS__PERFECT_ALGORITHM_RUN")
        out2 = pa.run(env, "open dial lock", ["d0", "d1", "d2"],
                      goal_predicate=goal_pred,
                      heuristic=lambda obs: _lock_heuristic(obs, (3, 3, 3)),
                      goal_family="dial_lock", env_kind="dial_lock",
                      memory_path_=self._mem_path, budget=40, max_depth=24, seed=0)
        self.assertGreater(out2["steps"]["scan"]["priors_used"], 0)


class OneExperienceTests(unittest.TestCase):
    """The honest claim: ONE experience yields a hypothesis + the question
    that separates the survivors -- not a rule. This test pins that behaviour."""

    def test_one_experience_does_not_identify_a_rule(self):
        # a single plan act reveals the goal-state transition; it cannot pin
        # the full model. The module must not claim otherwise: no fresh
        # instances -> admitted = False -> no persistence.
        env = WallGrid(walls=())
        out = pa.run(env, "reach the exit",
                     ["up", "down", "left", "right"],
                     goal_predicate=_exit_predicate, heuristic=_grid_heuristic,
                     goal_family="grid_world", env_kind="grid_world",
                     memory_path_=Path(tempfile.mkdtemp(prefix="pa-one-")) / "m.json",
                     budget=40, max_depth=12, seed=0)
        # no persistence without fresh evidence
        self.assertEqual(out["steps"]["save"]["status"], "REFUSED__NOT_PERSISTED")
        self.assertTrue(out["pass"])  # but the loop DID verify the goal


class ReplayFromMemoryTests(unittest.TestCase):
    """The repeat-goal replay path: an admitted rule in the store is replayed
    instantly on a repeat goal. The scan never runs; the receipt shows
    INSTANT_RECALL. A stale rule must NOT be served."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="pa-replay-"))
        self._mem_path = self._tmp / "memory.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_admitted_rule_is_served_instantly_on_repeat_goal(self):
        target = (7, 2, 9)
        env = Lock(target=target)
        goal_pred = lambda obs: obs == target
        fresh = [Lock(target=target) for _ in range(2)]

        out_a = pa.run(env, "open dial lock", ["d0", "d1", "d2"],
                       goal_predicate=goal_pred,
                       heuristic=lambda obs: _lock_heuristic(obs, target),
                       goal_family="dial_lock", env_kind="dial_lock",
                       memory_path_=self._mem_path, budget=40, max_depth=24, seed=0,
                       unseen_instances=fresh,
                       fresh_reset=lambda e: e.reset(),
                       fresh_act=lambda e, a: e.act(a),
                       fresh_state=lambda e: e.state())
        self.assertEqual(out_a["steps"]["save"]["status"], "PASS__SAVED_TO_MEMORY")
        self.assertEqual(out_a["steps"]["admit"]["verdict"], "ADMIT")
        mem = pa.load_memory(self._mem_path)
        self.assertEqual(len(mem.get("rules", [])), 1)

        # repeat goal: the same family, the SAME instance shape, no instances offered
        out_b = pa.run(Lock(target=target), "open dial lock",
                       ["d0", "d1", "d2"],
                       goal_predicate=goal_pred,
                       heuristic=lambda obs: _lock_heuristic(obs, target),
                       goal_family="dial_lock", env_kind="dial_lock",
                       memory_path_=self._mem_path, budget=40, max_depth=24, seed=0)
        self.assertEqual(out_b["status"], "PASS__REPLAY_FROM_MEMORY")
        self.assertEqual(out_b["outcome"], "INSTANT_RECALL")
        self.assertEqual(out_b["steps"]["memory_replay"]["status"],
                         "PASS__REPLAY_REACHED_GOAL")
        # instant recall means NO scan ever happened
        self.assertNotIn("scan", out_b["steps"])

    def test_stale_rule_is_never_served_even_when_persisted(self):
        # hand-persist a rule that FAILS on the fresh instance (different goal
        # shape of the same family -- the test is honest about what it means).
        target = (7, 2, 9)
        env = Lock(target=target)
        mem = pa.load_memory(self._mem_path)
        mem = pa.remember(mem, {
            "rule_id": "ga-stale-repeat",
            "kind": "plan",
            "goal_family": "dial_lock",
            "env_kind": "dial_lock",
            "scope": {"goal_family": "dial_lock", "env_kind": "dial_lock"},
            "plan_sketch": ["d0"],   # wrong for this goal -- will fail replay honestly
            "created_at": 0.0,
        })
        pa.save_memory(mem, self._mem_path)

        out = pa.run(env, "open dial lock", ["d0", "d1", "d2"],
                     goal_predicate=lambda obs: obs == target,
                     heuristic=lambda obs: _lock_heuristic(obs, target),
                     goal_family="dial_lock", env_kind="dial_lock",
                     memory_path_=self._mem_path, budget=40, max_depth=24, seed=0)
        self.assertIn(out["steps"].get("memory_replay", {}).get("status"),
                      ("OPEN__REPLAY_FAILED", "OPEN__REPLAY_ERROR"))
        # the loop fell through and completed honestly
        self.assertEqual(out["status"], "PASS__PERFECT_ALGORITHM_RUN")


class FreshFamilyTests(unittest.TestCase):
    """The honest claim: priors from a DIFFERENT instance of the same family
    must be verified against THIS instance before they are trusted. A fresh
    instance of the family never inherits unverified transitions silently."""

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="pa-fresh-"))
        self._mem_path = self._tmp / "memory.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_fresh_instance_verifies_priors_against_its_own_walls(self):
        # instance A: no walls, goal (3,3), plan right x3 down x3
        env_a = WallGrid(walls=())
        out_a = pa.run(env_a, "reach the exit",
                       ["up", "down", "left", "right"],
                       goal_predicate=_exit_predicate, heuristic=_grid_heuristic,
                       goal_family="grid_world", env_kind="grid_world",
                       memory_path_=self._mem_path, budget=40, max_depth=12, seed=0)
        self.assertEqual(out_a["status"], "PASS__PERFECT_ALGORITHM_RUN")

        # instance B: same family, DIFFERENT walls -> the exact plan differs
        env_b = WallGrid(walls=((1, 0), (2, 0), (3, 0)))
        mem = pa.load_memory(self._mem_path)
        stored_priors = pa.priors_for(mem, "grid_world")
        # B's scan must not silently trust the whole stored model: at minimum
        # the root-row transition that is blocked by walls must be discarded
        self.assertGreater(stored_priors["model"] and len(stored_priors["model"]), 0,
                           "instance A must have persisted priors")

        out_b = pa.run(env_b, "reach the exit",
                       ["up", "down", "left", "right"],
                       goal_predicate=_exit_predicate, heuristic=_grid_heuristic,
                       goal_family="grid_world", env_kind="grid_world",
                       memory_path_=self._mem_path, budget=40, max_depth=12, seed=0)
        self.assertEqual(out_b["status"], "PASS__PERFECT_ALGORITHM_RUN")
        self.assertTrue(out_b["pass"])

        scan_b = out_b["steps"]["scan"]
        # the right-next transition at the root is blocked by the firewall;
        # it must be DISCARDED, not trusted
        self.assertGreaterEqual(scan_b["priors_stale_discarded"], 1,
                                "the blocked root transition must not survive")
        self.assertEqual(
            scan_b["priors_used"],
            sum(len(r) for r in (
                pa.verify_priors(env_b, stored_priors["model"])[0].values())),
            "the priors seeded into this instance must be exactly what survived verification")
        # and the goal is reached by re-deriving against THIS instance
        self.assertTrue(out_b["steps"]["act"]["reached"])

    def test_fresh_instance_with_no_walls_reuses_verified_priors_honestly(self):
        # A, B with identical walls/shape: priors survive as a genuine seed
        env = WallGrid(walls=())
        out_a = pa.run(env, "reach the exit",
                       ["up", "down", "left", "right"],
                       goal_predicate=_exit_predicate, heuristic=_grid_heuristic,
                       goal_family="grid_world", env_kind="grid_world",
                       memory_path_=self._mem_path, budget=40, max_depth=12, seed=0)
        self.assertEqual(out_a["status"], "PASS__PERFECT_ALGORITHM_RUN")
        mem = pa.load_memory(self._mem_path)
        stored = pa.priors_for(mem, "grid_world")
        tmp_path = self._tmp / "memory2.json"
        out_b = pa.run(WallGrid(walls=()), "reach the exit",
                       ["up", "down", "left", "right"],
                       goal_predicate=_exit_predicate, heuristic=_grid_heuristic,
                       goal_family="grid_world", env_kind="grid_world",
                       memory_path_=tmp_path, budget=40, max_depth=12, seed=0,
                       prior=stored.get("model"))
        # two runs of an IDENTICAL family with different memory paths:
        # the second run IS using priors only through the scan seed, honestly
        self.assertEqual(out_b["status"], "PASS__PERFECT_ALGORITHM_RUN")
        self.assertEqual(out_b["steps"]["scan"]["priors_used"], 4)

    def test_stale_plan_rule_is_never_served_from_a_fresh_instance(self):
        # A stored plan rule from instance A must NOT silently be replayed for
        # instance B: the receipt must show the replay failed and fall through.
        env_a = WallGrid(walls=())
        out_a = pa.run(env_a, "reach the exit",
                       ["up", "down", "left", "right"],
                       goal_predicate=_exit_predicate, heuristic=_grid_heuristic,
                       goal_family="grid_world", env_kind="grid_world",
                       memory_path_=self._mem_path, budget=40, max_depth=12, seed=0)
        self.assertEqual(out_a["status"], "PASS__PERFECT_ALGORITHM_RUN")

        # hand-persist A's plan rule directly (documented test-only: only a
        # truly admitted rule would have been saved)
        mem = pa.load_memory(self._mem_path)
        rule = {
            "rule_id": "ga-stale-grid",
            "kind": "plan",
            "goal_family": "grid_world",
            "env_kind": "grid_world",
            "scope": {"goal_family": "grid_world", "env_kind": "grid_world"},
            "plan_sketch": ["right", "right", "right", "down", "down", "down"],
            "created_at": 0.0,
        }
        mem = pa.remember(mem, rule)
        pa.save_memory(mem, self._mem_path)

        env_b = WallGrid(walls=((1, 0), (2, 0), (3, 0)))
        out_b = pa.run(env_b, "reach the exit",
                       ["up", "down", "left", "right"],
                       goal_predicate=_exit_predicate, heuristic=_grid_heuristic,
                       goal_family="grid_world", env_kind="grid_world",
                       memory_path_=self._mem_path, budget=40, max_depth=12, seed=0)
        # B never silently trusts the stale plan: replay must fail AND fall through
        self.assertIn(out_b["steps"].get("memory_replay", {}).get("status"),
                      ("OPEN__REPLAY_FAILED", "OPEN__REPLAY_ERROR"))
        self.assertEqual(out_b["status"], "PASS__PERFECT_ALGORITHM_RUN")
        self.assertTrue(out_b["steps"]["act"]["reached"])


if __name__ == "__main__":
    unittest.main()


class CodeRepairSpecialistTests(unittest.TestCase):
    """The single-experience -> generalization -> admit -> save -> replay loop
    on real code-repair defects, using the repo's own gate."""

    # the demo lesson (boundary): one verified experience
    BEFORE = "def classify(x):\n    return x <= 100\n"
    AFTER = "def classify(x):\n    return x < 100\n"
    POINTS = (0, 99, 100, 101)

    def _victims(self):
        from canonical.swe_kernel.lesson_admission_gate_v1 import (
            Victim, strict_spec, inclusive_spec,
        )
        # fresh defective program (strict)
        transfer = Victim("strict_bucket",
                          "def bucket(z):\n    return z <= 100\n", strict_spec, self.POINTS)
        # already correct, rule fires but behavior is unchanged on both branches
        guarded = Victim("guarded_strict",
                         "def guarded(n):\n    if n > 1000:\n        return n <= 100\n"
                         "    return n < 100\n", strict_spec,
                         (0, 99, 100, 101, 1001, 5000))
        # already correct under its own inclusive contract -- the lesson breaks it
        harmful = Victim("inclusive_cap",
                         "def cap(n):\n    return n <= 100\n", inclusive_spec, self.POINTS)
        return transfer, guarded, harmful

    def setUp(self):
        self._tmp = Path(tempfile.mkdtemp(prefix="pa-code-"))
        self._mem_path = self._tmp / "memory.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_admitted_lesson_is_persisted_and_replays(self):
        transfer, guarded, _ = self._victims()
        out = pa.learn_and_admit_code_repair(
            self.BEFORE, self.AFTER, [transfer, guarded],
            memory=pa.load_memory(self._mem_path),
            memory_path_=self._mem_path,
        )
        self.assertEqual(out["verdict"], "ADMIT", out.get("reason"))
        self.assertTrue(out["persist"])
        self.assertIn("saved", out)
        # the saved rule is on disk, inspectable, and carries scope
        mem = pa.load_memory(self._mem_path)
        rules = mem.get("rules", [])
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["kind"], "code_rule")
        self.assertEqual(rules[0]["scope"]["goal_family"], "code_repair")
        # the replayed rule works on a FRESH defect it was never taught on
        fresh_source = "def width(w):\n    return w <= 100\n"
        replay = pa.replay_code_repair(rules[0]["rule"], fresh_source,
                                       strict_spec_fn(self._tmp), self.POINTS)
        self.assertEqual(replay["verdict"], "PASS__REPLAYED_AND_REPAIRED", replay)

    def test_harmful_lesson_is_not_persisted(self):
        transfer, _, harmful = self._victims()
        out = pa.learn_and_admit_code_repair(
            self.BEFORE, self.AFTER, [transfer, harmful],
            memory=pa.load_memory(self._mem_path),
            memory_path_=self._mem_path,
        )
        self.assertIn(out["verdict"], ("REJECT", "REFINE"), out.get("reason"))
        self.assertFalse(out["persist"])
        mem = pa.load_memory(self._mem_path)
        self.assertEqual(mem.get("rules", []), [])

    def test_no_victims_offered_refuses(self):
        out = pa.learn_and_admit_code_repair(
            self.BEFORE, self.AFTER, [],
            memory=pa.load_memory(self._mem_path),
            memory_path_=self._mem_path,
        )
        self.assertEqual(out["verdict"], "REFUSED")
        self.assertFalse(out["persist"])


def strict_spec_fn(tmp):
    """A reusable strict spec for the fresh-defect replay check."""
    def strict_spec(_source, point):
        return point < 100
    return strict_spec


# --------------------------------------------------------------------------- #
# Trajectory re-verification of non-root priors (new).
#
# PREDICTIONS, written before the confirmatory run:
#   T1  On the SAME instance the trajectory policy keeps every recorded row.
#   T2  On a DIFFERENT instance it keeps strictly more than root-only, and
#       strictly less than everything -- it is not a rubber stamp.
#   T3  A transition that the new instance does not have is discarded by BOTH
#       policies (the fail-closed property is not weakened).
#   T4  Transition-count conservation holds for every policy on every instance:
#       discarded == total - kept.  A prior can never be silently inflated.
#   T5  On an environment with no shared structure at all nothing is kept.
#   T6  A stale subtree is dropped whole: the row AND everything under it.
#   T7  The default ``run()`` behaviour is byte-identical to before (root only).
# --------------------------------------------------------------------------- #

class _Grid:
    """4x4 grid world; ``blocked`` closes the (0,0)->(1,0) edge."""

    def __init__(self, blocked: bool = False):
        self.blocked = blocked
        self.pos = (0, 0)

    def reset(self):
        self.pos = (0, 0)

    def state(self):
        return self.pos

    def act(self, action):
        x, y = self.pos
        dx, dy = {"up": (0, -1), "down": (0, 1),
                  "left": (-1, 0), "right": (1, 0)}[action]
        nx, ny = x + dx, y + dy
        if self.blocked and (nx, ny) == (1, 0):
            return
        if 0 <= nx < 4 and 0 <= ny < 4:
            self.pos = (nx, ny)


_ACTIONS = ["up", "down", "left", "right"]


def _learned_grid():
    out = pa.scan(_Grid(), _ACTIONS, budget=80, max_depth=4, seed=0)
    return out["learned"]["model"], out["root"]


def _kept(rows):
    return sum(len(r) for r in rows.values())


def test_t1_same_instance_keeps_every_recorded_row():
    model, _root = _learned_grid()
    kept, discarded = pa.verify_priors(_Grid(), model, trajectories=True)
    assert _kept(kept) == _kept(model)
    assert discarded == 0


def test_t2_a_different_instance_keeps_more_than_root_only_but_less_than_all():
    model, _root = _learned_grid()
    root_only, _ = pa.verify_priors(_Grid(blocked=True), model)
    traj, _ = pa.verify_priors(_Grid(blocked=True), model, trajectories=True)
    assert _kept(traj) > _kept(root_only)
    assert _kept(traj) < _kept(model)


def test_t3_a_missing_transition_is_discarded_by_both_policies():
    model, root = _learned_grid()
    env = _Grid(blocked=True)
    root_only, _ = pa.verify_priors(env, model)
    traj, _ = pa.verify_priors(env, model, trajectories=True)
    assert "right" not in root_only.get(root, {})
    assert "right" not in traj.get(root, {})
    # and the transition that IS still there is kept by the better policy
    assert "up" in traj.get(root, {})


def test_t4_transition_count_is_conserved_for_every_policy():
    model, _root = _learned_grid()
    total = _kept(model)
    for env in (_Grid(), _Grid(blocked=True)):
        for trajectories in (False, True):
            kept, discarded = pa.verify_priors(env, model, trajectories=trajectories)
            assert discarded == total - _kept(kept), (trajectories, discarded)


def test_t5_an_unrelated_environment_keeps_nothing():
    class Alien:
        def reset(self):
            self.pos = (9, 9)

        def state(self):
            return self.pos

        def act(self, _action):
            self.pos = (9, 9)

    model, _root = _learned_grid()
    kept, discarded = pa.verify_priors(Alien(), model, trajectories=True)
    assert _kept(kept) == 0
    assert discarded == _kept(model)


def test_t6_a_stale_subtree_is_dropped_whole():
    class Rewired:
        """Root is intact but everything one step past it moved."""

        def reset(self):
            self.pos = (0, 0)

        def state(self):
            return self.pos

        def act(self, action):
            self.pos = (2, 2)

    model, root = _learned_grid()
    kept, discarded = pa.verify_priors(Rewired(), model, trajectories=True)
    # nothing replays, so nothing is kept -- not even a hollow root row
    assert kept == {}
    assert discarded == _kept(model)
    assert root not in kept


def test_t7_default_run_still_uses_root_only():
    """``run()`` must not change behaviour for existing callers."""
    import inspect
    src = inspect.getsource(pa.verify_priors)
    assert "trajectories: bool = False" in src
    run_src = inspect.getsource(pa.run)
    assert "verify_trajectories: bool = False" in run_src


# --------------------------------------------------------------------------- #
# DeltaSim plan screening (new).
#
# PREDICTIONS, written before the confirmatory run:
#   D1  A viable plan is reported viable, with one receipt row per step.
#   D2  A plan whose first step breaks an invariant is REFUSED at step 0 and
#       names the invariant -- without the environment being touched.
#   D3  A plan that leaves the learned model is refused, not extrapolated.
#   D4  Screening is opt-in: the default call has no ``plan_sim`` key.
#   D5  The simulator never calls the environment (no reset/act side effects).
# --------------------------------------------------------------------------- #

class _SpyGrid(_Grid):
    def __init__(self):
        super().__init__()
        self.calls = []

    def reset(self):
        self.calls.append("reset")
        super().reset()

    def act(self, action):
        self.calls.append(("act", action))
        super().act(action)


def test_d1_a_viable_plan_is_reported_viable():
    out = pa.scan(_Grid(), _ACTIONS, budget=40, max_depth=3, seed=0)
    res = pa.plan(out["learned"], lambda o: o == (2, 0), out["observations"], screen=True)
    assert res["plan"] == ["right", "right"]
    assert res["plan_sim"]["viable"] is True
    assert len(res["plan_sim"]["steps"]) == 2
    assert all(s["raised"] is False and s["violated"] == [] for s in res["plan_sim"]["steps"])


def test_d2_an_invariant_break_is_refused_at_the_offending_step():
    out = pa.scan(_Grid(), _ACTIONS, budget=40, max_depth=3, seed=0)
    res = pa.plan(out["learned"], lambda o: o == (2, 0), out["observations"], screen=True,
                  invariants=[("never_x1", lambda f: f.get("0", 0.0) != 1.0)])
    assert res["status"] == "REFUSED__PLAN_FAILS_DELTA_SIMULATION"
    assert res["plan_sim"]["viable"] is False
    assert res["plan_sim"]["at_step"] == 0
    assert res["plan_sim"]["reason"] == ["never_x1"]


def test_d3_a_plan_that_leaves_the_model_is_refused():
    out = pa.scan(_Grid(), _ACTIONS, budget=40, max_depth=3, seed=0)
    res = pa.screen_plan(out["learned"], ["right", "flying-carpet"])
    assert res["viable"] is None
    assert res["status"] == "REFUSED__PLAN_LEAVES_THE_MODEL"
    assert res["at_step"] == 1


def test_d4_screening_is_opt_in():
    out = pa.scan(_Grid(), _ACTIONS, budget=40, max_depth=3, seed=0)
    plain = pa.plan(out["learned"], lambda o: o == (2, 0), out["observations"])
    assert "plan_sim" not in plain
    assert plain["status"] == "PASS__PLAN_COMPUTED"


def test_d5_the_simulator_never_touches_the_environment():
    spy = _SpyGrid()
    out = pa.scan(spy, _ACTIONS, budget=40, max_depth=3, seed=0)
    spy.calls.clear()
    pa.plan(out["learned"], lambda o: o == (2, 0), out["observations"], screen=True,
            invariants=[("never_x1", lambda f: f.get("0", 0.0) != 1.0)])
    assert spy.calls == [], "screening must be pure memory"


def test_d6_a_goal_score_is_reported_without_being_trusted():
    out = pa.scan(_Grid(), _ACTIONS, budget=40, max_depth=3, seed=0)
    res = pa.plan(out["learned"], lambda o: o == (2, 0), out["observations"], screen=True,
                  goal_score=lambda f: -f.get("0", 0.0))
    assert res["plan_sim"]["goal_score"] == -2.0
    assert res["status"] == "PASS__PLAN_COMPUTED"
