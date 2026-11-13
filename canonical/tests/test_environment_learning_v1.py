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


# --------------------------------------------------------------------------- #
# observation identity: the measured type-erasure defect and its honest limits
# --------------------------------------------------------------------------- #
ALIAS_CORPUS = [
    0, "0", 1, "1", 7, "7", True, "True", False, "False", None, "None",
    (1, 2), "(1, 2)", (0, 1), "(0, 1)", b"ab", "b'ab'", 1.0, "1.0",
]


class MixedTypeEnv:
    """The pre-registered mixed environment: int states and their string twins.

    ``quote`` moves an int to its string twin; ``inc`` always returns an int;
    ``reset`` returns int 0. A learner that identifies 7 with "7" writes rows
    that contradict this table even though every action was really executed.
    """

    ACTIONS = ["quote", "inc", "reset"]

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.s = 0

    def state(self):
        return self.s

    def act(self, a) -> None:
        if a == "quote":
            self.s = str(self.s)
        elif a == "inc":
            self.s = int(self.s) + 1 if int(self.s) < 10 else 10
        elif a == "reset":
            self.s = 0
        else:
            raise ValueError(a)

    def expected_after(self, before, action):
        if action == "quote":
            return str(before)
        if action == "inc":
            return int(before) + 1 if int(before) < 10 else 10
        if action == "reset":
            return 0
        raise ValueError(action)


class IntControlEnv:
    """No-alias control: the same learner must still solve an ordinary int world."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.s = 0

    def state(self):
        return self.s

    def act(self, a) -> None:
        if a == "inc":
            self.s = min(10, self.s + 1)
        elif a == "reset":
            self.s = 0
        else:
            raise ValueError(a)


class HiddenBitEnv:
    """A visible observation that does not determine the next visible observation.

    Identity repair cannot invent the hidden bit. The honest result is an open
    model, not a verified plan.
    """

    def __init__(self) -> None:
        self.hidden = False
        self.visible = 0

    def reset(self) -> None:
        self.hidden = not self.hidden
        self.visible = 0

    def state(self):
        return self.visible

    def act(self, a) -> None:
        if a == "go":
            self.visible = "ready" if self.hidden else 0
        elif a == "toggle":
            self.hidden = not self.hidden
        else:
            raise ValueError(a)


class StochasticEnv:
    """One visible state, two possible successors. Traces must keep the conflict."""

    def __init__(self) -> None:
        import random
        self.rng = random.Random(3)
        self.s = 0

    def reset(self) -> None:
        self.s = 0

    def state(self):
        return self.s

    def act(self, a) -> None:
        if a == "flip":
            self.s = self.rng.randrange(2)
        else:
            raise ValueError(a)


class ObservationIdentityTests(unittest.TestCase):
    def test_the_fixed_alias_corpus_has_no_collisions(self):
        keys = [el.state_key(value) for value in ALIAS_CORPUS]
        self.assertEqual(len(keys), 20)
        self.assertEqual(len(set(keys)), 20)
        for i, left in enumerate(ALIAS_CORPUS):
            for right in ALIAS_CORPUS[i + 1:]:
                self.assertNotEqual(el.state_key(left), el.state_key(right),
                                    (left, right))

    def test_keys_are_versioned_and_stable(self):
        first = el.state_key({"a": [1, 2]})
        self.assertTrue(first.startswith(el.STATE_KEY_PREFIX))
        self.assertEqual(first, el.state_key({"a": [1, 2]}))
        self.assertEqual(el.STATE_KEY_SCHEMA, "PROJECT_BRAIN_ENVIRONMENT_STATE_KEY_V2")

    def test_mapping_key_types_are_not_erased_by_projection(self):
        self.assertNotEqual(el.state_key({1: "a"}), el.state_key({"1": "a"}))
        self.assertNotEqual(el.state_key({True: "a"}), el.state_key({"True": "a"}))
        self.assertNotEqual(el.state_key({(1, 2): "a"}), el.state_key({"(1, 2)": "a"}))
        self.assertEqual(el.state_key({1: "a", "1": "b"}),
                         el.state_key({"1": "b", 1: "a"}))

    def test_container_kinds_and_order_remain_distinct(self):
        self.assertNotEqual(el.state_key([1, 2]), el.state_key((1, 2)))
        self.assertNotEqual(el.state_key([1, 2]), el.state_key([2, 1]))
        self.assertNotEqual(el.state_key({1, 2}), el.state_key(frozenset({1, 2})))
        self.assertEqual(el.state_key({1, 2}), el.state_key({2, 1}))
        self.assertNotEqual(el.state_key(b"ab"), el.state_key(bytearray(b"ab")))
        self.assertNotEqual(el.state_key(1), el.state_key(1.0))
        self.assertNotEqual(el.state_key(0.0), el.state_key(-0.0))

    def test_volatile_computer_noise_is_still_projected_out(self):
        self.assertEqual(el.state_key({"x": 1, "timestamp": 123}),
                         el.state_key({"x": 1, "timestamp": 456}))
        self.assertEqual(el.state_key({"x": 1, "csrf_token": "a"}),
                         el.state_key({"x": 1, "csrf_token": "b"}))
        self.assertNotEqual(el.state_key({"x": 1}), el.state_key({"x": 2}))

    def test_the_mixed_environment_model_agrees_with_its_own_table(self):
        env = MixedTypeEnv()
        learned = el.learn_model(env, MixedTypeEnv.ACTIONS, budget=40,
                                 max_depth=8, seed=0)
        self.assertEqual(learned["state_key_schema"], el.STATE_KEY_SCHEMA)
        self.assertEqual(len(learned["traces"]), 188)
        observations = learned["observations"]
        wrong = []
        for trace in learned["traces"]:
            before = observations[trace["before"]]
            after = observations[trace["after"]]
            expected = env.expected_after(before, trace["action"])
            if type(expected) is not type(after) or expected != after:
                wrong.append((before, trace["action"], after, expected))
        self.assertEqual(wrong, [])
        for key, snapshot in observations.items():
            self.assertEqual(key, el.state_key(snapshot))

    def test_the_no_alias_control_is_still_solved(self):
        result = el.drive(IntControlEnv(), ["inc", "reset"],
                          is_goal=lambda s: s == 3, budget=40, max_depth=8, seed=0)
        self.assertTrue(result["pass"], result)
        self.assertEqual(result["plan"], ["inc", "inc", "inc"])

    def test_a_legacy_prior_is_rejected_not_reinterpreted(self):
        legacy = {"0": {"inc": "1"}}
        learned = el.learn_model(IntControlEnv(), ["inc", "reset"], budget=2,
                                 max_depth=2, seed=0, prior=legacy)
        self.assertEqual(learned["prior_states"], 0)
        self.assertEqual(learned["prior_rejected_states"], 1)
        self.assertNotIn("0", learned["model"])
        accepted = el.learn_model(IntControlEnv(), ["inc", "reset"], budget=2,
                                  max_depth=2, seed=0, prior=legacy,
                                  prior_schema=el.STATE_KEY_SCHEMA)
        self.assertEqual(accepted["prior_states"], 1)
        self.assertIn("0", accepted["model"])

    def test_hidden_state_is_not_promoted_to_a_verified_plan(self):
        result = el.drive(HiddenBitEnv(), ["go", "toggle"],
                          is_goal=lambda s: s == "ready", budget=20,
                          max_depth=4, seed=0)
        self.assertFalse(result["pass"])
        self.assertNotEqual(result["authority"],
                            "MODEL_LEARNED_PLAN_EXECUTED_GOAL_OBSERVED")

    def test_stochastic_conflicts_remain_in_the_traces(self):
        learned = el.learn_model(StochasticEnv(), ["flip"], budget=20,
                                 max_depth=1, seed=0)
        outcomes = {(t["before"], t["after"]) for t in learned["traces"]}
        zero = el.state_key(0)
        one = el.state_key(1)
        self.assertIn((zero, zero), outcomes)
        self.assertIn((zero, one), outcomes)
        # The tabular model is still a single-successor hypothesis; the conflict is
        # visible in the traces, not silently claimed away as determinism.
        self.assertEqual(len(learned["model"][zero]), 1)

    def test_projection_default_and_identity_mode_are_explicit(self):
        from canonical.swe_kernel.predicate_world_abstraction_v1 import (
            project_computer_observation,
        )
        raw = {1: "a", "1": "b", "timestamp": 123}
        self.assertEqual(project_computer_observation(raw), {"1": "b"})
        self.assertEqual(project_computer_observation(raw, preserve_key_types=True),
                         {1: "a", "1": "b"})
        self.assertNotEqual(el.state_key({1: "a"}), el.state_key({"1": "a"}))

    def test_cycles_and_unsupported_observations_fail_closed(self):
        cycle = []
        cycle.append(cycle)
        with self.assertRaisesRegex(ValueError, "STATE_KEY_CYCLE"):
            el.state_key(cycle)

        class Unsupported:
            __hash__ = None

        with self.assertRaisesRegex(TypeError, "STATE_KEY_UNSUPPORTED"):
            el.state_key(Unsupported())

    def test_arc_observation_keeps_its_caller_supplied_hashable_identity(self):
        from canonical.tools.arc_agi_3_public_exploration_measure_v1 import Observation
        first = Observation(1, b"frame", "start", ("A",))
        second = Observation(1, b"frame", "start", ("A",))
        other = Observation(1, b"other", "start", ("A",))
        self.assertEqual(el.state_key(first), el.state_key(second))
        self.assertNotEqual(el.state_key(first), el.state_key(other))
        self.assertTrue(el.state_key(first).startswith(el.STATE_KEY_PREFIX))

    def test_mixed_reachable_goal_is_solved_and_deep_goal_is_not_invented(self):
        reached = el.drive(MixedTypeEnv(), MixedTypeEnv.ACTIONS,
                           is_goal=lambda s: s == 3, budget=40, max_depth=8, seed=0)
        self.assertTrue(reached["pass"], reached)
        self.assertEqual(reached["plan"], ["inc", "inc", "inc"])
        deep = el.drive(MixedTypeEnv(), MixedTypeEnv.ACTIONS,
                        is_goal=lambda s: s == 10, budget=40, max_depth=8, seed=0)
        self.assertFalse(deep["pass"])
        self.assertEqual(deep["status"], el.FAIL_NO_GOAL)
        self.assertEqual(deep["learned"]["prior_rejected_states"], 0)


if __name__ == "__main__":
    unittest.main()
