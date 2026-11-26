"""The failure this project already named, made executable.

The bottleneck document says: "3 pages stop because the same look behaves
differently; that is a missing observable". Here that is a runnable app: a
three-step form where step 1 and step 2 render identically.

Measured, both bounded:

  DOM-keyed scan   12,832 probes, 4,000 expanded nodes, goal NOT reached.
                   It has 2,573 distinct nodes that share a DOM digest -- it is
                   not merely slow, it cannot terminate, because it can never
                   tell "clicked once" from "clicked twice".
  Availability     4 probes, and the resulting machine separates the steps.

The second number is the point. Availability is a *prediction* -- "back raises
here" -- and it is exactly the observable the DOM does not carry.
"""
from __future__ import annotations

import unittest

from canonical.runtime import dom_state_environment_v1 as dom
from canonical.runtime import minimal_experiment_v1 as me

NODE_BUDGET = 4000
PROBE_BUDGET = 20000


def replay(word):
    env = dom.DomStateEnvironment()
    for action in word:
        env.act(action)
    return env


def dom_keyed_search(node_budget=NODE_BUDGET):
    """Search keyed only by what the DOM shows -- the current scan's model."""
    probes = 0
    queue = [()]
    visited = set()
    by_dom: dict[str, list[tuple]] = {}
    while queue and len(visited) < node_budget:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        try:
            env = replay(node)
        except ValueError:
            continue
        if env.state()[dom.SUBMITTED]:
            return {"goal": True, "probes": probes, "nodes": len(visited), "by_dom": by_dom}
        by_dom.setdefault(env.dom_digest(), []).append(node)
        for action in env.actions():
            probes += 1
            if probes > PROBE_BUDGET:
                break
            try:
                env.act(action)
                queue.append(node + (action,))
            except ValueError:
                pass
    return {"goal": False, "probes": probes, "nodes": len(visited), "by_dom": by_dom}


class IdenticalLookTests(unittest.TestCase):
    def test_two_hidden_steps_render_the_same_dom(self):
        """The premise: the DOM cannot separate step 1 from step 2."""
        first = dom.DomStateEnvironment()
        second = dom.DomStateEnvironment()
        self.assertEqual(1, first.state()[dom.STEP])
        second.act("next")
        self.assertEqual(2, second.state()[dom.STEP])
        self.assertEqual(first.dom_digest(), second.dom_digest())
        self.assertEqual(
            dom.snapshot_to_elements(first.snapshot()),
            dom.snapshot_to_elements(second.snapshot()),
        )

    def test_availability_separates_them(self):
        """`back` is unavailable at step 1 and available at step 2.

        Availability, not acceptance: both probes land in a non-accepting state,
        so acceptance would call them identical. An earlier version of this test
        did exactly that and passed for the wrong reason.
        """
        first = dom.DomStateEnvironment()
        second = dom.DomStateEnvironment()
        second.act("next")
        self.assertFalse(first.observation("back")["available"])
        self.assertTrue(second.observation("back")["available"])
        self.assertEqual(
            first.observation("back")["accepting"],
            second.observation("back")["accepting"],
            "acceptance cannot separate these two states; that is the point",
        )


class DomKeyedScanCannotFinishTests(unittest.TestCase):
    def test_dom_keyed_search_does_not_reach_the_goal_in_budget(self):
        out = dom_keyed_search()
        self.assertFalse(out["goal"], "if this now passes, the premise changed")
        # and the reason is structural, not luck: many distinct nodes collide
        collisions = max(len(v) for v in out["by_dom"].values())
        self.assertGreater(
            collisions, 100,
            "the DOM must genuinely collapse many distinct states",
        )


class MachineLearnerSeparatesThemTests(unittest.TestCase):
    def test_root_only_probes_correctly_yield_one_state(self):
        """Four probes from the start describe ONE state, because they are one.

        The earlier version of this test asserted two states, which was an
        artefact of probing without restoring: the second question was asked
        from the state the first one had moved to. With honest probing, one
        state is the true answer -- and the module says so rather than
        inventing structure the evidence does not support.
        """
        observations = [
            dom.DomStateEnvironment().observation(action)
            for action in dom.DomStateEnvironment().actions()
        ]
        self.assertEqual(4, len(observations))
        built = me.minimal_consistent_machine(observations)
        self.assertEqual("PASS__MINIMAL_MACHINE", built["status"])
        self.assertEqual(1, built["state_count"])
        self.assertTrue(me.is_consistent(built["machine"], observations))
        # what it DID learn: two actions are dead ends here
        absent = built["machine"]["unavailable"].get("0", [])
        self.assertIn("back", absent)
        self.assertIn("confirm", absent)

    def test_the_action_alphabet_is_derived_from_the_scan(self):
        """Nobody tells the agent what the environment's actions are called."""
        env = dom.DomStateEnvironment()
        elements = dom.snapshot_to_elements(env.snapshot())
        self.assertEqual(["field", "next"], dom.stable_actions(elements))

    def test_the_bound_snapshot_shape_is_accepted(self):
        """The same adapter consumes the real CDP snapshot shape."""
        cdp_like = {
            "schema": "PROJECT_BRAIN_OSWORLD_V21_BROWSER_CDP_V1",
            "pages": [
                {
                    "page_index": 0,
                    "url": "https://example/",
                    "title": "t",
                    "elements": [{"tag": "button", "name": "submit", "text": "Go"}],
                }
            ],
        }
        elements = dom.snapshot_to_elements(cdp_like)
        self.assertEqual(["submit"], dom.stable_actions(elements))

    def test_a_terminal_app_refuses_rather_than_pretending(self):
        env = dom.DomStateEnvironment()
        env.act("next")
        env.act("next")
        env.act("confirm")
        self.assertTrue(env.state()[dom.SUBMITTED])
        with self.assertRaises(ValueError):
            env.act("next")


class LearnThenActTests(unittest.TestCase):
    """The whole loop, on an app whose steps look identical.

    Nine non-destructive probes (three questions from each of the three reachable
    steps, each asked from a fresh restore) produce a three-state machine, proved
    minimal. The plan the machine yields is then executed on the real app and is
    correct. Nothing here reads the hidden state.
    """

    def _ask(self, prefix, action):
        env = dom.DomStateEnvironment()
        for step in prefix:
            env.act(step)
        return env.observation(action, access=prefix)

    def _learn(self):
        observations = []
        for depth in range(3):
            prefix = ["next"] * depth
            for action in ("next", "back", "confirm"):
                observations.append(self._ask(prefix, action))
        return observations, me.minimal_consistent_machine(observations)

    def test_the_hidden_step_count_is_recovered(self):
        observations, built = self._learn()
        self.assertEqual(9, len(observations))
        self.assertEqual("PASS__MINIMAL_MACHINE", built["status"])
        self.assertEqual(3, built["state_count"])
        self.assertEqual("PROVED_MINIMAL", built["optimality"])
        self.assertTrue(me.is_consistent(built["machine"], observations))

    def test_confirm_is_known_unavailable_before_the_last_step(self):
        """The machine must rule it out, not merely fail to consider it."""
        _obs, built = self._learn()
        machine = built["machine"]
        absent = machine["unavailable"]
        self.assertIn("confirm", absent.get(str(machine["start"]), []))
        # no confirm edge exists anywhere before the terminal state
        for state, row in machine["transitions"].items():
            if "confirm" in row:
                self.assertNotEqual(str(machine["start"]), state)

    def test_the_plan_from_the_machine_works_on_the_real_app(self):
        from collections import deque

        _obs, built = self._learn()
        machine = built["machine"]
        start = machine["start"]
        previous = {start: None}
        queue = deque([start])
        while queue:
            state = queue.popleft()
            for action, target in (machine["transitions"].get(str(state)) or {}).items():
                if target not in previous:
                    previous[target] = (state, action)
                    queue.append(target)
        plan = None
        for state in previous:
            if "confirm" in (machine["transitions"].get(str(state)) or {}):
                path = []
                cursor = state
                while previous[cursor] is not None:
                    prior, action = previous[cursor]
                    path.append(action)
                    cursor = prior
                plan = list(reversed(path)) + ["confirm"]
                break
        self.assertIsNotNone(plan)
        env = dom.DomStateEnvironment()
        for action in plan:
            env.act(action)
        self.assertTrue(env.state()[dom.SUBMITTED])

    def test_a_probe_that_is_not_restored_corrupts_the_answer(self):
        """Why the probe above restores: asking in sequence changes the app."""
        env = dom.DomStateEnvironment()
        env.observation("next")           # leaves the app at step 2
        out = env.observation("back")     # so `back` now looks available at "step 1"
        self.assertTrue(out["available"])
        fresh = dom.DomStateEnvironment()
        self.assertFalse(fresh.observation("back")["available"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
