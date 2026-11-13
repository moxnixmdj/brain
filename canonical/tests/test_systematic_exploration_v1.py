"""Systematic exploration: what it guarantees, checked against oracles this file computes itself.

Every expected value below comes from the environment's DEFINITION (a transition table the
test owns, searched by the test's own breadth-first search), never from the explorer's own
counters. An explorer that is wrong about what it did must not be able to pass by agreeing
with itself.

What these tests do NOT show: that any of this helps in an environment too large to
tabulate. It does not -- see `canonical/tools/arc_agi_3_public_exploration_measure_v1.py`.
"""
from __future__ import annotations

import os
import random
import shutil
import tempfile
import unittest
from collections import deque

from canonical.runtime import environment_learning_v1 as el
from canonical.runtime import systematic_exploration_v1 as sx
from canonical.runtime import transfer_learning_v1 as tl
from canonical.tools import arc_agi_3_public_exploration_measure_v1 as arc_measure


class TableEnv:
    """A deterministic environment defined by a table: {state: {action: next_state}}.

    It records every (state, action) it is asked to perform, so a test can see what was
    actually done to it rather than what the explorer says it did.
    """

    def __init__(self, table, start, dead=()):
        self.table, self.start, self.dead = table, start, set(dead)
        self.log = []
        self.resets = 0
        self.at = start

    def reset(self):
        self.resets += 1
        self.at = self.start

    def act(self, action):
        if self.at in self.dead:
            raise AssertionError("acted in a dead state: %r" % (self.at,))
        self.log.append((self.at, action))
        self.at = self.table[self.at][action]

    def state(self):
        return self.at


def true_distances(table, start, dead=()):
    """Breadth-first distances over the definition. The oracle for every test below."""
    dist = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        if node in dead:
            continue
        for nxt in table[node].values():
            if nxt not in dist:
                dist[nxt] = dist[node] + 1
                queue.append(nxt)
    return dist


def random_table(rng, states, actions):
    return {s: {a: rng.randrange(states) for a in actions} for s in range(states)}


ACTIONS = ["a", "b", "c"]


class NothingIsPaidForTwiceTests(unittest.TestCase):
    def test_every_pair_is_an_experiment_at_most_once_and_the_rest_is_travel(self):
        for seed in range(40):
            rng = random.Random(seed)
            table = random_table(rng, 30, ACTIONS)
            env = TableEnv(table, 0)
            out = sx.explore_to_goal(env, ACTIONS, is_goal=lambda s: False, action_budget=10**6)
            first_time = len(set(env.log))
            repeats = len(env.log) - first_time
            self.assertEqual(out["experiment_acts"], first_time, seed)
            self.assertEqual(out["travel_acts"], repeats, seed)
            self.assertEqual(out["acts"], len(env.log), seed)
            self.assertEqual(out["surprises"], 0, seed)

    def test_the_learned_table_is_the_real_one(self):
        rng = random.Random(7)
        table = random_table(rng, 25, ACTIONS)
        env = TableEnv(table, 0)
        out = sx.explore_to_goal(env, ACTIONS, is_goal=lambda s: False, action_budget=10**6)
        reachable = true_distances(table, 0)
        learned = out["model"]
        # The shared observation identity is versioned; the oracle is still the
        # environment's own transition table, looked up under that exact identity.
        self.assertEqual(set(learned), {el.state_key(s) for s in reachable})
        for s in reachable:
            self.assertEqual(learned[el.state_key(s)],
                             {a: el.state_key(table[s][a]) for a in ACTIONS})


class ExhaustionTests(unittest.TestCase):
    def test_absence_is_proven_only_when_everything_reachable_was_tried(self):
        rng = random.Random(3)
        table = random_table(rng, 40, ACTIONS)
        reachable = true_distances(table, 0)
        env = TableEnv(table, 0)
        out = sx.explore_to_goal(env, ACTIONS, is_goal=lambda s: s == "nowhere",
                                 action_budget=10**6)
        self.assertEqual(out["status"], sx.FAIL_EXHAUSTED)
        self.assertTrue(out["exhausted"])
        self.assertEqual(out["state_count"], len(reachable))
        self.assertEqual(out["transition_count"], len(reachable) * len(ACTIONS))
        self.assertFalse(out["pass"])

    def test_running_out_of_budget_is_not_called_absence(self):
        rng = random.Random(3)
        table = random_table(rng, 40, ACTIONS)
        env = TableEnv(table, 0)
        out = sx.explore_to_goal(env, ACTIONS, is_goal=lambda s: s == "nowhere",
                                 action_budget=10)
        self.assertEqual(out["status"], sx.OPEN_BUDGET)
        self.assertFalse(out["exhausted"])
        self.assertLessEqual(len(env.log), 10)

    def test_a_place_that_does_not_hold_still_is_never_called_exhausted(self):
        class Flicker:
            """One action whose outcome alternates: a hidden bit the state does not show."""

            def __init__(self):
                self.at, self.bit = 0, 0

            def reset(self):
                self.at = 0

            def act(self, action):
                if action == "a":
                    self.bit ^= 1
                    self.at = 1 if self.bit else 2
                else:
                    self.at = 0

            def state(self):
                return self.at

        out = sx.explore_to_goal(Flicker(), ["a", "b"], is_goal=lambda s: s == 99,
                                 action_budget=400)
        self.assertGreater(out["surprises"], 0)
        self.assertNotEqual(out["status"], sx.FAIL_EXHAUSTED)
        self.assertFalse(out["exhausted"])
        self.assertIn(out["status"], (sx.OPEN_UNSTABLE, sx.OPEN_BUDGET))


class RouteQualityTests(unittest.TestCase):
    def test_shallowest_finds_a_shortest_route_and_nearest_only_a_route(self):
        longer = 0
        reached = 0
        for seed in range(120):
            rng = random.Random(1000 + seed)
            states = rng.randrange(8, 40)
            table = random_table(rng, states, ACTIONS)
            goal = rng.randrange(1, states)
            dist = true_distances(table, 0)
            for order in ("shallowest", "nearest"):
                env = TableEnv(table, 0)
                out = sx.explore_to_goal(env, ACTIONS, is_goal=lambda s: s == goal,
                                         action_budget=10**6, order=order)
                if goal not in dist:
                    self.assertEqual(out["status"], sx.FAIL_EXHAUSTED, (seed, order))
                    continue
                self.assertTrue(out["pass"], (seed, order))
                # the route must really lead there, replayed on a fresh copy of the place
                for plan in (out["plan_shortest"], out["plan_walked"]):
                    fresh = TableEnv(table, 0)
                    for action in plan:
                        fresh.act(action)
                    self.assertEqual(fresh.state(), goal, (seed, order))
                if order == "shallowest":
                    reached += 1
                    self.assertEqual(len(out["plan_shortest"]), dist[goal], seed)
                    self.assertEqual(out["plan_minimality"],
                                     "SHORTEST_GIVEN_REPEATABLE_ENVIRONMENT")
                else:
                    self.assertGreaterEqual(len(out["plan_shortest"]), dist[goal], seed)
                    self.assertEqual(out["plan_minimality"], "NOT_PROVEN_SHORTEST")
                    longer += len(out["plan_shortest"]) > dist[goal]
        self.assertGreater(reached, 60)
        # the price of "nearest" is real; if it vanished the label above would be a lie
        self.assertGreater(longer, 0)

    def test_a_goal_far_beyond_any_short_walk_is_reached(self):
        # forty steps deep, and every wrong move sends you back to the start
        length = 40
        table = {i: {"n": i, "b": 0, "f": min(length, i + 1)} for i in range(length + 1)}
        env = TableEnv(table, 0)
        out = sx.explore_to_goal(env, ["n", "b", "f"], is_goal=lambda s: s == length,
                                 action_budget=10**5)
        self.assertTrue(out["pass"])
        self.assertEqual(out["plan_shortest"], ["f"] * length)
        self.assertLessEqual(out["experiment_acts"], (length + 1) * 3)


def cheapest_prices(table, price, start, dead=()):
    """Lowest total price from `start` to every state, over the definition. The oracle for a priced search."""
    best = {start: 0}
    frontier = [start]
    while frontier:                      # label-correcting; tiny tables, no need for a heap
        node = frontier.pop()
        if node in dead:
            continue
        for action, nxt in table[node].items():
            offer = best[node] + price(node, action)
            if nxt not in best or offer < best[nxt]:
                best[nxt] = offer
                frontier.append(nxt)
    return best


def first_tries(log):
    """The experiments, in the order they were made: the first time each (state, action) was done."""
    seen, out = set(), []
    for pair in log:
        if pair not in seen:
            seen.add(pair)
            out.append(pair)
    return out


class CheapestOrderTests(unittest.TestCase):
    def test_nothing_dearer_than_the_goal_is_tried_before_the_goal_and_the_route_is_a_cheapest_one(self):
        reached = 0
        for seed in range(150):
            rng = random.Random(5000 + seed)
            states = rng.randrange(6, 30)
            table = random_table(rng, states, ACTIONS)
            fee = {(s, a): rng.choice([0, 0, 1, 2]) for s in range(states) for a in ACTIONS}
            price = lambda s, a: fee[(s, a)]
            goal = rng.randrange(1, states)
            best = cheapest_prices(table, price, 0)
            env = TableEnv(table, 0)
            out = sx.explore_to_goal(env, ACTIONS, is_goal=lambda s: s == goal, action_budget=10**6,
                                     order="cheapest", cost_of=price)
            if goal not in best:
                self.assertEqual(out["status"], sx.FAIL_EXHAUSTED, seed)
                continue
            reached += 1
            self.assertTrue(out["pass"], seed)
            for plan in (out["plan_cheapest"], out["plan_walked"]):
                fresh = TableEnv(table, 0)
                for action in plan:
                    fresh.act(action)
                self.assertEqual(fresh.state(), goal, seed)
            fresh = TableEnv(table, 0)
            paid = 0
            for action in out["plan_cheapest"]:
                paid += price(fresh.state(), action)
                fresh.act(action)
            self.assertEqual(paid, best[goal], seed)                       # a cheapest route, by the definition
            tries = first_tries(env.log)
            self.assertEqual(len(tries), out["experiment_acts"], seed)      # no pair is an experiment twice
            for state, action in tries:
                self.assertLessEqual(best[state] + price(state, action), best[goal], (seed, state, action))
        self.assertGreater(reached, 80)

    def test_the_prices_are_an_order_and_never_a_filter(self):
        for seed in range(20):
            rng = random.Random(seed)
            table = random_table(rng, 25, ACTIONS)
            fee = {(s, a): rng.choice([0, 1, 5]) for s in range(25) for a in ACTIONS}
            reachable = true_distances(table, 0)
            env = TableEnv(table, 0)
            out = sx.explore_to_goal(env, ACTIONS, is_goal=lambda s: s == "nowhere", action_budget=10**6,
                                     order="cheapest", cost_of=lambda s, a: fee[(s, a)])
            self.assertEqual(out["status"], sx.FAIL_EXHAUSTED, seed)
            self.assertEqual(set(env.log), {(s, a) for s in reachable for a in ACTIONS}, seed)

    def test_a_free_run_is_followed_to_its_end_and_a_dead_end_backs_up_one_step(self):
        # a binary tree, three deep, everything free: the order of first tries must be depth first
        table, order = {}, []

        def grow(name, depth):
            if depth == 3:
                table[name] = {"l": name, "r": name}
                order.extend([(name, "l"), (name, "r")])
                return
            table[name] = {"l": name + "l", "r": name + "r"}
            order.append((name, "l"))
            grow(name + "l", depth + 1)
            order.append((name, "r"))
            grow(name + "r", depth + 1)
        grow("", 0)
        env = TableEnv(table, "")
        out = sx.explore_to_goal(env, ["l", "r"], is_goal=lambda s: False, action_budget=10**6,
                                 order="cheapest", cost_of=lambda s, a: 0)
        self.assertEqual(out["status"], sx.FAIL_EXHAUSTED)
        self.assertEqual(first_tries(env.log), order)

    def test_what_must_be_paid_for_is_paid_for_in_the_shortest_sequence_first(self):
        # three free steps in a row; at each of the three places one paid step leads off to a side room
        table = {0: {"f": 1, "p": 10}, 1: {"f": 2, "p": 11}, 2: {"f": 2, "p": 12}}
        table.update({room: {"f": room, "p": room} for room in (10, 11, 12)})
        env = TableEnv(table, 0)
        out = sx.explore_to_goal(env, ["p", "f"], is_goal=lambda s: False, action_budget=10**6,
                                 order="cheapest", cost_of=lambda s, a: 1 if a == "p" else 0)
        self.assertEqual(out["status"], sx.FAIL_EXHAUSTED)
        self.assertEqual(first_tries(env.log), [
            (0, "f"), (1, "f"), (2, "f"),                 # everything free, to the end of the run
            (0, "p"), (10, "f"),                          # one unit: the payment nearest the start, and what it opens
            (1, "p"), (11, "f"),
            (2, "p"), (12, "f"),
            (10, "p"), (11, "p"), (12, "p")])             # two units

    def test_everything_free_is_tried_before_anything_is_paid_for(self):
        # twelve free steps lead to the goal; at every one of them a paid step leads away
        length = 12
        table = {i: {"go": min(length, i + 1), "away": 100 + i} for i in range(length + 1)}
        table.update({100 + i: {"go": 100 + i, "away": 100 + i} for i in range(length + 1)})
        env = TableEnv(table, 0)
        out = sx.explore_to_goal(env, ["away", "go"], is_goal=lambda s: s == length, action_budget=10**6,
                                 order="cheapest", cost_of=lambda s, a: 0 if a == "go" else 1)
        self.assertTrue(out["pass"])
        self.assertEqual(env.log, [(i, "go") for i in range(length)])      # exactly the free run, nothing else
        self.assertEqual(out["plan_cheapest"], ["go"] * length)

    def test_turn_orders_equal_prices_in_one_state_and_nothing_else(self):
        table = {0: {"a": 1, "b": 2, "c": 3}, 1: {"a": 1, "b": 1, "c": 1}, 2: {"a": 2, "b": 2, "c": 2},
                 3: {"a": 3, "b": 3, "c": 3}}
        turns = {"a": 2, "b": 0, "c": 1}
        env = TableEnv(table, 0)
        sx.explore_to_goal(env, ACTIONS, is_goal=lambda s: False, action_budget=10**6, order="cheapest",
                           cost_of=lambda s, a: (0, turns[a]))
        at_start = [action for state, action in first_tries(env.log) if state == 0]
        self.assertEqual(at_start, ["b", "c", "a"])
        # a dearer action never jumps the queue because its turn is early
        env = TableEnv(table, 0)
        sx.explore_to_goal(env, ACTIONS, is_goal=lambda s: False, action_budget=10**6, order="cheapest",
                           cost_of=lambda s, a: (3 if a == "b" else 0, turns[a]))
        self.assertEqual([action for state, action in first_tries(env.log) if state == 0], ["c", "a", "b"])

    def test_a_free_step_into_a_dead_end_costs_a_reset_and_hides_nothing(self):
        table = {0: {"a": 1, "b": 2, "c": 0}, 1: {"a": 1, "b": 1, "c": 1}, 2: {"a": 3, "b": 2, "c": 2},
                 3: {"a": 3, "b": 3, "c": 3}}
        env = TableEnv(table, 0, dead={1})                # TableEnv raises if anything is done in a dead state
        out = sx.explore_to_goal(env, ACTIONS, is_goal=lambda s: s == 3, is_dead=lambda s: s == 1,
                                 action_budget=10**6, order="cheapest", cost_of=lambda s, a: 0 if a == "a" else 1)
        self.assertTrue(out["pass"])
        self.assertEqual(out["plan_cheapest"], ["b", "a"])
        self.assertEqual(env.log[0], (0, "a"))            # the free step was taken first, and it was a dead end
        self.assertGreaterEqual(env.resets, 2)

    def test_what_the_order_needs_is_demanded(self):
        table = {0: {"a": 0}}
        with self.assertRaises(ValueError):
            sx.explore_to_goal(TableEnv(table, 0), ["a"], is_goal=lambda s: False, action_budget=5, order="cheapest")
        with self.assertRaises(ValueError):
            sx.explore_to_goal(TableEnv(table, 0), ["a"], is_goal=lambda s: False, action_budget=5,
                               order="cheapest", cost_of=lambda s, a: 0.5)
        with self.assertRaises(ValueError):
            sx.explore_to_goal(TableEnv(table, 0), ["a"], is_goal=lambda s: False, action_budget=5,
                               order="cheapest", cost_of=lambda s, a: -1)
        with self.assertRaises(ValueError):
            sx.explore_to_goal(TableEnv(table, 0), ["a"], is_goal=lambda s: False, action_budget=5,
                               order="cheapest", cost_of=lambda s, a: 0, prior={"0": {"a": "0"}})
        with self.assertRaises(ValueError):
            sx.explore_to_goal(TableEnv(table, 0), ["a"], is_goal=lambda s: False, action_budget=5, order="dearest")

    def test_the_budget_still_ends_the_search(self):
        rng = random.Random(11)
        table = random_table(rng, 40, ACTIONS)
        env = TableEnv(table, 0)
        out = sx.explore_to_goal(env, ACTIONS, is_goal=lambda s: s == "nowhere", action_budget=9,
                                 order="cheapest", cost_of=lambda s, a: 1)
        self.assertEqual(out["status"], sx.OPEN_BUDGET)
        self.assertLessEqual(len(env.log), 9)


class DeathAndResetTests(unittest.TestCase):
    def _pit_world(self):
        # 0 -a-> 1 -a-> 2(goal);  b from anywhere falls into the pit, which only reset leaves
        return {0: {"a": 1, "b": "pit"}, 1: {"a": 2, "b": "pit"}, 2: {"a": 2, "b": "pit"},
                "pit": {"a": "pit", "b": "pit"}}

    def test_a_dead_state_is_left_by_reset_and_never_acted_in(self):
        env = TableEnv(self._pit_world(), 0, dead={"pit"})
        out = sx.explore_to_goal(env, ["b", "a"], is_goal=lambda s: s == 2,
                                 action_budget=100, is_dead=lambda s: s == "pit")
        self.assertTrue(out["pass"])  # TableEnv raises if the explorer acts while dead
        self.assertEqual(out["plan_shortest"], ["a", "a"])
        self.assertGreaterEqual(out["dead_state_count"], 1)

    def test_every_reset_after_the_first_is_charged_at_its_price(self):
        for price in (0, 1, 5):
            env = TableEnv(self._pit_world(), 0, dead={"pit"})
            out = sx.explore_to_goal(env, ["b", "a"], is_goal=lambda s: s == 2,
                                     action_budget=100, is_dead=lambda s: s == "pit",
                                     reset_cost=price)
            self.assertEqual(out["budget_spent"], len(env.log) + price * (env.resets - 1), price)

    def test_a_budget_that_cannot_afford_the_reset_stops_before_it(self):
        env = TableEnv(self._pit_world(), 0, dead={"pit"})
        out = sx.explore_to_goal(env, ["b", "a"], is_goal=lambda s: s == 2,
                                 action_budget=3, is_dead=lambda s: s == "pit", reset_cost=5)
        self.assertEqual(out["status"], sx.OPEN_BUDGET)
        self.assertEqual(env.resets, 1)  # only the opening reset; the paid one was refused
        self.assertLessEqual(out["budget_spent"], 3)

    def test_actions_offered_only_in_some_states_are_only_tried_there(self):
        table = {0: {"a": 1}, 1: {"a": 0, "key": 2}, 2: {"a": 2}}
        env = TableEnv(table, 0)
        out = sx.explore_to_goal(env, [], is_goal=lambda s: s == 2, action_budget=50,
                                 actions_of=lambda s: sorted(table[s]))
        self.assertTrue(out["pass"])
        self.assertEqual(out["plan_shortest"], ["a", "key"])
        self.assertNotIn((0, "key"), env.log)


class EffectPriorTests(unittest.TestCase):
    def test_an_action_that_never_does_anything_is_tried_less(self):
        # a long line; only "go" moves, four other buttons do nothing anywhere
        length = 30
        duds = ["d1", "d2", "d3", "d4"]
        table = {i: dict({d: i for d in duds}, go=min(length, i + 1)) for i in range(length + 1)}
        spent = {}
        for flag in (False, True):
            env = TableEnv(table, 0)
            out = sx.explore_to_goal(env, duds + ["go"], is_goal=lambda s: s == length,
                                     action_budget=10**4, effect_prior=flag)
            self.assertTrue(out["pass"], flag)
            spent[flag] = sum(1 for _, action in env.log if action in duds)
        self.assertEqual(spent[False], length * len(duds))  # declared order tries every dud
        self.assertLess(spent[True], spent[False] // 3)


class SharedMemoryTests(unittest.TestCase):
    def setUp(self):
        self.store = tempfile.mkdtemp(prefix="brain-systematic-")
        self._saved = tl.STATE_PATH
        tl.STATE_PATH = os.path.join(self.store, "episodes.json")

    def tearDown(self):
        tl.STATE_PATH = self._saved
        shutil.rmtree(self.store, ignore_errors=True)

    @staticmethod
    def _lock():
        sizes, target = (4, 5, 3), (3, 2, 1)
        table = {}
        for x in range(sizes[0]):
            for y in range(sizes[1]):
                for z in range(sizes[2]):
                    table[(x, y, z)] = {
                        "d0": ((x + 1) % sizes[0], y, z),
                        "d1": (x, (y + 1) % sizes[1], z),
                        "d2": (x, y, (z + 1) % sizes[2]),
                    }
        return table, target

    def test_what_this_learner_finds_the_existing_one_recalls_in_one_trial(self):
        table, target = self._lock()
        first = sx.drive(TableEnv(table, (0, 0, 0)), ["d0", "d1", "d2"],
                         is_goal=lambda s: tuple(s) == target, action_budget=5000,
                         goal_key="shared-memory-lock")
        self.assertEqual(first["status"], sx.PASS_VERIFIED)
        self.assertTrue(first["episode_persisted"])
        again = tl.drive(TableEnv(table, (0, 0, 0)), ["d0", "d1", "d2"],
                         is_goal=lambda s: tuple(s) == target, goal_key="shared-memory-lock",
                         budget=40)
        self.assertTrue(again["pass"])
        self.assertEqual(again["authority"], tl.AUTHORITY_RECALLED)
        self.assertEqual(again["trials_spent"], 1)

    def test_what_the_existing_learner_finds_this_one_recalls_without_exploring(self):
        table, target = self._lock()
        first = tl.drive(TableEnv(table, (0, 0, 0)), ["d0", "d1", "d2"],
                         is_goal=lambda s: tuple(s) == target, goal_key="shared-memory-lock-2",
                         budget=200, max_depth=12)
        self.assertTrue(first["pass"], first.get("status"))
        env = TableEnv(table, (0, 0, 0))
        again = sx.drive(env, ["d0", "d1", "d2"], is_goal=lambda s: tuple(s) == target,
                         action_budget=5000, goal_key="shared-memory-lock-2")
        self.assertEqual(again["status"], sx.PASS_VERIFIED)
        self.assertTrue(again["transferred"])
        self.assertIsNone(again["explored"])

    def test_a_recalled_plan_is_replayed_before_it_is_believed(self):
        # Same place, same goal NAME, but the goal has moved: the stored plan is now wrong.
        table, target = self._lock()
        actions = ["d0", "d1", "d2"]
        sx.drive(TableEnv(table, (0, 0, 0)), actions, is_goal=lambda s: tuple(s) == target,
                 action_budget=5000, goal_key="the-goal-moved")
        moved = (1, 4, 2)
        out = sx.drive(TableEnv(table, (0, 0, 0)), actions,
                       is_goal=lambda s: tuple(s) == moved, action_budget=5000,
                       goal_key="the-goal-moved")
        self.assertTrue(out["pass"])
        self.assertFalse(out["transferred"])
        fresh = TableEnv(table, (0, 0, 0))
        for action in out["plan"]:
            fresh.act(action)
        self.assertEqual(fresh.state(), moved)

    def test_without_a_goal_name_nothing_is_recalled_or_written(self):
        table, target = self._lock()
        out = sx.drive(TableEnv(table, (0, 0, 0)), ["d0", "d1", "d2"],
                       is_goal=lambda s: tuple(s) == target, action_budget=5000)
        self.assertEqual(out["status"], sx.PASS_VERIFIED)
        self.assertNotIn("episode_persisted", out)
        self.assertFalse(os.path.exists(tl.STATE_PATH))

    def test_a_route_that_does_not_replay_is_not_reported_as_reached(self):
        class OnceOnly:
            """The goal can be reached exactly once; after that the same moves lead nowhere."""

            def __init__(self):
                self.at, self.used = 0, False

            def reset(self):
                self.at = 0

            def act(self, action):
                if self.at == 0 and action == "a" and not self.used:
                    self.used, self.at = True, 1
                else:
                    self.at = 0

            def state(self):
                return self.at

        out = sx.drive(OnceOnly(), ["a"], is_goal=lambda s: s == 1, action_budget=50)
        self.assertEqual(out["status"], sx.FAIL_NOT_REPRODUCIBLE)
        self.assertFalse(out["pass"])
        self.assertIsNone(out["plan"])


class PriorSchemaTests(unittest.TestCase):
    """A carried model is only comparable under the identity that wrote it."""

    @staticmethod
    def _env():
        return TableEnv({0: {"a": 1}, 1: {"a": 1}}, 0)

    def test_a_legacy_prior_is_rejected_under_the_shared_identity(self):
        out = sx.explore_to_goal(self._env(), ["a"], is_goal=lambda s: s == 1,
                                 action_budget=10, prior={"0": {"a": "1"}})
        self.assertTrue(out["pass"])
        self.assertEqual(out["state_key_schema"], el.STATE_KEY_SCHEMA)
        self.assertEqual(out["prior_states"], 0)
        self.assertEqual(out["prior_rejected_states"], 1)
        self.assertNotIn("0", out["model"])

    def test_a_declared_current_prior_is_accepted(self):
        prior = {el.state_key(0): {"a": el.state_key(1)}}
        out = sx.explore_to_goal(self._env(), ["a"], is_goal=lambda s: s == 1,
                                 action_budget=10, prior=prior,
                                 prior_schema=el.STATE_KEY_SCHEMA)
        self.assertTrue(out["pass"])
        self.assertEqual(out["prior_states"], 1)
        self.assertEqual(out["prior_rejected_states"], 0)

    def test_a_custom_key_of_is_the_callers_own_identity(self):
        out = sx.explore_to_goal(self._env(), ["a"], is_goal=lambda s: s == 1,
                                 action_budget=10, prior={"0": {"a": "1"}},
                                 key_of=lambda s: str(s))
        self.assertTrue(out["pass"])
        self.assertIsNone(out["state_key_schema"])
        self.assertEqual(out["prior_states"], 1)
        self.assertEqual(out["prior_rejected_states"], 0)


class ClickTargetTests(unittest.TestCase):
    def test_one_target_per_region_and_always_inside_it(self):
        # a ring of 1s around a 0 hole on a 0 background, plus a separate 2
        grid = [
            [0, 0, 0, 0, 0, 0],
            [0, 1, 1, 1, 0, 0],
            [0, 1, 0, 1, 0, 2],
            [0, 1, 1, 1, 0, 0],
            [0, 0, 0, 0, 0, 0],
        ]
        targets = arc_measure.click_targets(grid)
        self.assertEqual(sorted(c for _, _, c in targets), [0, 0, 1, 2])
        for x, y, colour in targets:
            self.assertEqual(grid[y][x], colour)  # the ring's centroid is the hole: not allowed
        ring = [(x, y) for x, y, c in targets if c == 1]
        self.assertEqual(len(ring), 1)

    def test_clicks_pool_their_effects_by_the_colour_clicked(self):
        self.assertEqual(arc_measure.action_class("C:3:9:7"), "C:7")
        self.assertEqual(arc_measure.action_class("C:60:1:7"), "C:7")
        self.assertNotEqual(arc_measure.action_class("C:3:9:7"), arc_measure.action_class("C:3:9:4"))
        self.assertEqual(arc_measure.action_class("A5"), "A5")


class _StubRaw:
    def __init__(self, grid, offered=(6,)):
        self.frame = [[list(row) for row in grid]]
        self.available_actions = list(offered)
        self.state = type("State", (), {"name": "NOT_FINISHED"})()
        self.levels_completed = 0


class _StubBoard:
    """A 4x4 board. Clicking the one cell of colour 2 recolours it; any other click does nothing."""

    def __init__(self, lists_clicks=True, offered=(6,)):
        self.grid = [[0, 0, 0, 0], [0, 2, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
        self.offered = offered
        if lists_clicks:
            action = type("Action", (), {"data": {"x": 1, "y": 1}})()
            self._game = type("Game", (), {
                "_get_valid_clickable_actions": lambda _self: [action]})()

    @property
    def observation_space(self):
        return _StubRaw(self.grid, self.offered)

    def click(self, x, y):
        if self.grid[y][x] == 2:
            self.grid[y][x] = 3
        return _StubRaw(self.grid, self.offered)


class _StubArcade:
    def __init__(self, **board):
        self.board = board

    def make(self, game_id, seed=0):
        return _StubBoard(**self.board)


class ClickAbstractionCheckTests(unittest.TestCase):
    """The instrument's check of itself must be able to fail."""

    @staticmethod
    def _check(arcade, **kwargs):
        return arc_measure.click_abstraction_check(
            arcade, ["zz00-0000"], click=lambda env, x, y: env.click(x, y), **kwargs)

    def test_a_click_the_engine_lists_is_reached_by_a_region_target(self):
        check = self._check(_StubArcade())
        self.assertTrue(check["status"].startswith("PASS"), check)
        self.assertEqual((check["engine_listed_clicks"], check["engine_listed_clicks_covered"]),
                         (1, 1))
        row = check["per_game"][0]
        self.assertEqual((row["adapter_targets"], row["adapter_distinct_outcomes"]), (2, 2))

    def test_an_abstraction_that_hides_the_listed_click_is_reported_as_a_fault(self):
        check = self._check(_StubArcade(), targets_of=lambda grid: [(2, 2, 0)])
        self.assertTrue(check["status"].startswith("FAULT"), check)
        self.assertEqual((check["engine_listed_clicks"], check["engine_listed_clicks_covered"]),
                         (1, 0))

    def test_no_engine_list_or_no_clicking_is_never_reported_as_a_pass(self):
        unlisted = self._check(_StubArcade(lists_clicks=False))
        self.assertFalse(unlisted["per_game"][0]["engine_list_available"])
        self.assertTrue(unlisted["status"].startswith("NOT_CHECKED"), unlisted)
        keyboard_only = self._check(_StubArcade(offered=(1, 2)))
        self.assertEqual(keyboard_only["games_offering_clicks"], 0)
        self.assertTrue(keyboard_only["status"].startswith("NOT_CHECKED"), keyboard_only)


class DigestTests(unittest.TestCase):
    """The committed evidence is a reduction of the tool's own output; the reduction is tested."""

    @staticmethod
    def _result(tree="t1", toolkit="0.9.9"):
        levels = [{"level": 0, "baseline": 17, "budget": 34, "actions": 21, "completed": True},
                  {"level": 1, "baseline": 30, "budget": 60, "actions": 60, "completed": False,
                   "x_status": sx.OPEN_BUDGET}]
        cell = {"arm": "nearest", "budget_multiplier": 2.0, "seed": 0, "official_score": 0.5,
                "levels_completed": 1, "levels_total": 2, "actions": 81,
                "per_game": [{"game_id": "ab12-0123abcd", "levels": levels}]}
        return {"schema": arc_measure.SCHEMA, "date_utc": "2026-11-11T00:00:00Z",
                "instrument": {"arc_agi_version": toolkit, "arcengine_version": "0.9.3",
                               "python": "3.11.2",
                               "environments": {"files": 2, "tree_sha256": tree,
                                                "sha256": {"a": "b"}}},
                "subject": {"as_is_max_depth": 6, "arms": ["nearest"]},
                "summary": [{"budget_multiplier": 2.0, "arm": "nearest", "runs": 1}],
                "cells": [cell]}

    def test_scores_survive_and_the_completed_levels_are_named(self):
        record = arc_measure.digest([("s1", self._result())])
        self.assertEqual(record["authority"], "NONE")
        self.assertEqual(record["digest_of"][0]["sha256"], "s1")
        run = record["runs"][0]
        self.assertEqual((run["official_score"], run["levels_completed"], run["actions"]),
                         (0.5, 1, 81))
        self.assertEqual(run["completed_levels_as_game_level_actions_over_human"],
                         ["ab12:L0:21/17"])
        self.assertEqual(run["levels_not_completed_by_reason"], {sx.OPEN_BUDGET: 1})
        self.assertNotIn("sha256", record["instrument"]["environments"])

    def test_results_from_different_game_files_or_toolkits_are_not_mixed(self):
        for other in (self._result(tree="t2"), self._result(toolkit="1.0.0")):
            with self.assertRaises(SystemExit):
                arc_measure.digest([("s1", self._result()), ("s2", other)])
        with self.assertRaises(SystemExit):
            arc_measure.digest([])


if __name__ == "__main__":
    unittest.main()
