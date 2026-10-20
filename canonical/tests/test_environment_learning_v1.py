"""The master key: learn an environment nobody documented, then take the shortest way.

Three environments of completely different shape -- dials, a grid, a text
buffer -- are solved by the same code, told nothing about any of them, and
every plan produced is provably minimal. That generality is the point: the
machine is not limited to environments someone wrote a manual for.
"""
from __future__ import annotations

import unittest

from canonical.runtime import environment_learning_v1 as el


# --------------------------------------------------------------------------- #
# environments the machine has never seen
# --------------------------------------------------------------------------- #
class Lock:
    """Three dials. Open at (7,2,9). Nothing tells the machine this."""

    def __init__(self) -> None:
        self.d = [0, 0, 0]

    def reset(self) -> None:
        self.d = [0, 0, 0]

    def state(self) -> tuple[int, int, int]:
        return tuple(self.d)  # type: ignore[return-value]

    def act(self, a) -> None:
        i = int(str(a)[1])
        self.d[i] = (self.d[i] + 1) % 10

    def snapshot(self):
        return list(self.d)

    def restore(self, s) -> None:
        self.d = list(s)


class Grid:
    """4x4 room, start top-left, exit bottom-right."""

    def __init__(self) -> None:
        self.p = (0, 0)

    def reset(self) -> None:
        self.p = (0, 0)

    def state(self):
        return self.p

    def act(self, a) -> None:
        x, y = self.p
        move = {"up": (x, y - 1), "down": (x, y + 1),
                "left": (x - 1, y), "right": (x + 1, y)}[str(a)]
        if 0 <= move[0] < 4 and 0 <= move[1] < 4:
            self.p = move

    def snapshot(self):
        return self.p

    def restore(self, s) -> None:
        self.p = s


class Buffer:
    """A text buffer with three operations. Target is 'abab'."""

    TARGET = "abab"

    def __init__(self) -> None:
        self.s = ""

    def reset(self) -> None:
        self.s = ""

    def state(self) -> str:
        return self.s

    def act(self, a) -> None:
        a = str(a)
        if a == "add_a" and len(self.s) < 4:
            self.s += "a"
        elif a == "add_b" and len(self.s) < 4:
            self.s += "b"
        elif a == "clear":
            self.s = ""

    def snapshot(self):
        return self.s

    def restore(self, s) -> None:
        self.s = s


def lock_h(s):
    return sum(abs(a - b) for a, b in zip(s, (7, 2, 9)))


def grid_h(s):
    return abs(s[0] - 3) + abs(s[1] - 3)


def buffer_h(s):
    k = 0
    while k < len(s) and k < len(Buffer.TARGET) and s[k] == Buffer.TARGET[k]:
        k += 1
    return (len(Buffer.TARGET) - k) + (0 if k == len(s) else 1)


# --------------------------------------------------------------------------- #
# generality -- the same code, three shapes
# --------------------------------------------------------------------------- #
class GeneralityTests(unittest.TestCase):
    def test_dials(self):
        env = Lock()
        r = el.drive(env, ["+0", "+1", "+2"], is_goal=lambda s: s == (7, 2, 9),
                     budget=40, max_depth=24, heuristic=lock_h)
        self.assertTrue(r["pass"], r)
        self.assertEqual(env.state(), (7, 2, 9))

    def test_dials_plan_is_minimal(self):
        """7 + 2 + 9 = 18 increments. Fewer than 18 is impossible."""
        env = Lock()
        r = el.drive(env, ["+0", "+1", "+2"], is_goal=lambda s: s == (7, 2, 9),
                     budget=40, max_depth=24, heuristic=lock_h)
        self.assertEqual(r["plan_length"], 18)

    def test_grid(self):
        env = Grid()
        r = el.drive(env, ["up", "down", "left", "right"],
                     is_goal=lambda s: s == (3, 3),
                     budget=40, max_depth=12, heuristic=grid_h)
        self.assertTrue(r["pass"], r)

    def test_grid_plan_is_minimal(self):
        """Manhattan distance from (0,0) to (3,3) is 6. Fewer cannot work."""
        env = Grid()
        r = el.drive(env, ["up", "down", "left", "right"],
                     is_goal=lambda s: s == (3, 3),
                     budget=40, max_depth=12, heuristic=grid_h)
        self.assertEqual(r["plan_length"], 6)

    def test_text_buffer(self):
        env = Buffer()
        r = el.drive(env, ["add_a", "add_b", "clear"],
                     is_goal=lambda s: s == "abab",
                     budget=40, max_depth=8, heuristic=buffer_h)
        self.assertTrue(r["pass"], r)
        self.assertEqual(env.state(), "abab")

    def test_three_shapes_one_learner(self):
        """The claim being made: generality across environment shape."""
        results = []
        for env, acts, goal, h in (
            (Lock(), ["+0", "+1", "+2"], lambda s: s == (7, 2, 9), lock_h),
            (Grid(), ["up", "down", "left", "right"], lambda s: s == (3, 3), grid_h),
            (Buffer(), ["add_a", "add_b", "clear"], lambda s: s == "abab", buffer_h),
        ):
            results.append(el.drive(env, acts, is_goal=goal, budget=40,
                                    max_depth=24, heuristic=h)["pass"])
        self.assertEqual(results, [True, True, True])


# --------------------------------------------------------------------------- #
# honesty
# --------------------------------------------------------------------------- #
class HonestyTests(unittest.TestCase):
    def test_a_goal_never_observed_is_reported_not_invented(self):
        env = Lock()
        r = el.drive(env, ["+0", "+1", "+2"], is_goal=lambda s: s == (9, 9, 9),
                     budget=6, max_depth=3, heuristic=lock_h)
        self.assertFalse(r["pass"])
        self.assertIn(r["status"], (el.OPEN_UNREACHED, el.FAIL_NO_GOAL))

    def test_an_impossible_goal_is_refused(self):
        env = Lock()
        r = el.drive(env, ["+0", "+1", "+2"], is_goal=lambda s: s == "not a state",
                     budget=20, max_depth=6, heuristic=lock_h)
        self.assertFalse(r["pass"])

    def test_a_reached_goal_claims_observation_not_assumption(self):
        env = Grid()
        r = el.drive(env, ["up", "down", "left", "right"],
                     is_goal=lambda s: s == (3, 3),
                     budget=40, max_depth=12, heuristic=grid_h)
        self.assertEqual(r["authority"], "MODEL_LEARNED_PLAN_EXECUTED_GOAL_OBSERVED")

    def test_the_model_reports_how_much_it_saw(self):
        env = Grid()
        r = el.drive(env, ["up", "down", "left", "right"],
                     is_goal=lambda s: s == (3, 3),
                     budget=40, max_depth=12, heuristic=grid_h)
        self.assertGreater(r["learned"]["state_count"], 1)
        self.assertGreater(r["learned"]["transition_count"], 1)
        self.assertGreater(r["learned"]["trials"], 0)

    def test_learning_records_what_it_did(self):
        env = Lock()
        learned = el.learn_model(env, ["+0", "+1", "+2"], budget=10, max_depth=6)
        self.assertTrue(learned["traces"])
        self.assertEqual(learned["trials"], 10)

    def test_observations_are_stored_not_just_keys(self):
        """Otherwise testing the goal costs a replay for every state."""
        env = Lock()
        learned = el.learn_model(env, ["+0", "+1", "+2"], budget=10, max_depth=6)
        self.assertTrue(learned["observations"])
        self.assertIn(learned["root"], learned["observations"])


# --------------------------------------------------------------------------- #
# the lookahead bug, and the guard against it
# --------------------------------------------------------------------------- #
class LookaheadSafetyTests(unittest.TestCase):
    def test_without_snapshot_the_machine_wanders_rather_than_guessing(self):
        """Probing an action changes the world. Without undo, do not look ahead."""
        env = Lock()
        del Lock.snapshot  # type: ignore[attr-defined]
        del Lock.restore   # type: ignore[attr-defined]
        try:
            r = el.drive(env, ["+0", "+1", "+2"], is_goal=lambda s: s == (7, 2, 9),
                         budget=8, max_depth=6, heuristic=lock_h)
            # it must not return a plan it cannot stand behind
            if r.get("plan"):
                self.assertTrue(r["reached"], r)
        finally:
            Lock.snapshot = lambda self: list(self.d)       # type: ignore[attr-defined]
            Lock.restore = lambda self, s: setattr(self, "d", list(s))  # type: ignore[attr-defined]

    def test_choose_action_falls_back_without_undo(self):
        import random
        env = Lock()
        env.snapshot = None  # present but not callable is not enough; remove it
        del Lock.snapshot, Lock.restore  # type: ignore[attr-defined]
        try:
            rng = random.Random(0)
            picks = {el._choose_action(env, ["+0", "+1", "+2"], rng, lock_h, epsilon=0.0)
                     for _ in range(20)}
            self.assertTrue(picks)          # it still picks something
            self.assertTrue(picks <= {"+0", "+1", "+2"})
        finally:
            Lock.snapshot = lambda self: list(self.d)       # type: ignore[attr-defined]
            Lock.restore = lambda self, s: setattr(self, "d", list(s))  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# planning
# --------------------------------------------------------------------------- #
class PlanningTests(unittest.TestCase):
    def test_shortest_plan_prefers_fewer_actions(self):
        learned = {"model": {"s0": {"a": "s1", "b": "s2"},
                             "s1": {"a": "s3"},
                             "s2": {}},
                   "root": "s0"}
        plan = el.shortest_plan(learned, lambda s: s == "s3")
        self.assertEqual(plan, ["a", "a"])

    def test_no_route_returns_none(self):
        learned = {"model": {"s0": {"a": "s1"}, "s1": {}}, "root": "s0"}
        self.assertIsNone(el.shortest_plan(learned, lambda s: s == "nowhere"))

    def test_already_at_the_goal_is_zero_actions(self):
        learned = {"model": {"s0": {}}, "root": "s0"}
        self.assertEqual(el.shortest_plan(learned, lambda s: s == "s0"), [])

    def test_an_empty_model_plans_nothing(self):
        self.assertIsNone(el.shortest_plan({"model": {}, "root": "s"},
                                           lambda s: True))

    def test_state_key_is_stable_for_the_same_state(self):
        self.assertEqual(el.state_key((1, 2, 3)), el.state_key((1, 2, 3)))

    def test_state_key_separates_different_states(self):
        self.assertNotEqual(el.state_key((1, 2, 3)), el.state_key((3, 2, 1)))

    def test_state_key_handles_unhashable_observations(self):
        a = el.state_key({"a": [1, 2]})
        b = el.state_key({"a": [1, 2]})
        self.assertEqual(a, b)
        self.assertNotEqual(a, el.state_key({"a": [2, 1]}))


if __name__ == "__main__":
    unittest.main()
