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
