#!/usr/bin/env python3
"""Frontier routing contract: the goals this session made reachable stay reachable.

Three commits wired frontier capability into the unified model:

  f7f8f370  engine trigger supplements + harvested fallback in `solve()`
  5008b3a3  `VERIFICATION_FIRST_MEMORY_BUS`
  e136f137  `WAKE_SLEEP_CONSOLIDATION`

Nothing pinned any of it. A later trigger edit could silently send
"keep improving without forgetting" back to `python.source.add_function.v1`
and every existing check would still pass, because the verifier only pins
that *some* route is confident, not that *this* goal reaches *that* engine.

This file closes that hole. It asserts three separate things:

1. Every frontier goal routes to the engine that actually implements it
   (not merely "confidently somewhere").
2. The negative controls still fail closed. A naive `predict` trigger broke
   one of these during development, so the check is load-bearing.
3. The engines named here are executable with their declared inputs and
   fail closed with the right reason when inputs are missing -- a route to
   a broken engine is worse than no route.

Deliberately NOT asserted: coverage numbers, scores, or candidate order.
Those move when triggers are tuned, and pinning them would make honest
routing work fail a test for no reason. The contract is "this goal reaches
this engine", not "this goal scores 0.83".
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import brain_unified_model_v1 as model_runtime  # noqa: E402

# goal -> the engine that implements it
FRONTIER_GOALS = {
    "learn a new capability from a single demonstration without training": "engine:INSTANT_ONE_SHOT_LEARNER",
    "infer a program from one example and prove it works": "engine:INSTANT_ONE_SHOT_LEARNER",
    "generalize one episode into a reusable rule": "engine:INSTANT_ONE_SHOT_LEARNER",
    "keep improving on new tasks without forgetting earlier ones": "engine:RULE_EXPIRY_WORLD_FINGERPRINT",
    "expire rules that no longer hold and keep the store current": "engine:RULE_EXPIRY_WORLD_FINGERPRINT",
    "recall the right prior episode as context when the window is nearly full": "engine:PROCEDURE_TRAJECTORY_MEMORY",
    "drive an unfamiliar desktop application through its GUI": "engine:INTERFACE_ACTION_GRAMMAR",
    "predict the next screen state before taking the action": "engine:STATE_CONTRACT_WORLD_MODEL",
    "predict what an action does before doing it": "engine:PREDICTIVE_HOARE_CONTRACT",
    # added by 5008b3a3
    "create a durable memory of prior runs": "engine:VERIFICATION_FIRST_MEMORY_BUS",
    "forget one skill without damaging others": "engine:VERIFICATION_FIRST_MEMORY_BUS",
    "consolidate memory during idle time": "engine:VERIFICATION_FIRST_MEMORY_BUS",
    "resolve conflicting memories": "engine:VERIFICATION_FIRST_MEMORY_BUS",
    # added by e136f137
    "promote repair episode to permanent rule": "engine:WAKE_SLEEP_CONSOLIDATION",
    "check a learned rule is not a constant": "engine:WAKE_SLEEP_CONSOLIDATION",
    "two independent witnesses": "engine:WAKE_SLEEP_CONSOLIDATION",
    "memory hygiene": "engine:WAKE_SLEEP_CONSOLIDATION",
}

# The verifier's own negative set. `predict the winner of next year's
# tournament` is the one that a bare `predict` trigger broke; it is listed
# explicitly rather than inherited so this file can never drift from it.
MUST_FAIL_CLOSED = (
    "launch a weather satellite into low earth orbit",
    "write me a poem about the sea",
    "book a flight to tokyo for next tuesday",
    "translate this sentence into medieval french",
    "compose a symphony in the style of debussy",
    "diagnose why my houseplant is losing leaves",
    "negotiate a lower price on a used bicycle",
    "predict the winner of next year's tournament",
)


class FrontierRoutingContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = model_runtime.open_model()

    def test_frontier_goals_reach_the_engine_that_implements_them(self):
        for goal, expected in FRONTIER_GOALS.items():
            with self.subTest(goal=goal):
                routing = self.model.route(goal)
                self.assertTrue(
                    routing["confident"],
                    f"regressed to fail-closed: {goal}",
                )
                self.assertEqual(
                    routing["best"]["id"],
                    expected,
                    f"{goal} routed to {routing['best']['id']}",
                )

    def test_out_of_domain_goals_still_fail_closed(self):
        for goal in MUST_FAIL_CLOSED:
            with self.subTest(goal=goal):
                routing = self.model.route(goal)
                self.assertFalse(
                    routing["confident"],
                    f"false positive: {goal} -> {routing['best']}",
                )

    def test_memory_os_is_executable_and_fails_closed_without_inputs(self):
        ok = self.model.solve(
            "create a durable memory of prior runs",
            inputs={"operation": "SLEEP_CONSOLIDATE", "payload": {}},
        )
        self.assertTrue(ok.get("pass"), ok.get("status"))
        self.assertEqual(ok.get("status"), "PASS__SLEEP_CONSOLIDATED")

        missing = self.model.solve("create a durable memory of prior runs", inputs={})
        self.assertFalse(missing.get("pass"))
        self.assertIn("ENGINE_INPUTS_MISSING", str(missing.get("status")))

        unknown = self.model.solve(
            "create a durable memory of prior runs",
            inputs={"operation": "NOT_A_REAL_OPERATION"},
        )
        self.assertFalse(unknown.get("pass"))
        self.assertIn("UNKNOWN_MEMORY_OPERATION", str(unknown.get("status")))

    def test_wake_sleep_two_witness_gate_is_load_bearing(self):
        one = self.model.solve(
            "check a learned rule is not a constant",
            inputs={
                "operation": "TWO_WITNESS_CHECK",
                "payload": {
                    "episodes": [{"witness_input_sig": "only", "witness_output_sig": "one"}]
                },
            },
        )
        self.assertFalse(
            one.get("pass"),
            "a single witness must never satisfy the permanence gate",
        )
        self.assertIn("INSUFFICIENT_NONCONSTANT_WITNESSES", str(one.get("status")))

        two = self.model.solve(
            "check a learned rule is not a constant",
            inputs={
                "operation": "TWO_WITNESS_CHECK",
                "payload": {
                    "episodes": [
                        {"witness_input_sig": "a", "witness_output_sig": "b"},
                        {"witness_input_sig": "c", "witness_output_sig": "d"},
                    ]
                },
            },
        )
        self.assertTrue(two.get("pass"), two.get("status"))
        self.assertIn("NON_CONSTANT_2_WITNESS_VERIFIED", str(two.get("status")))

    def test_harvested_fallback_stays_unadmitted(self):
        """Reachability must not become admission. Ever."""
        routing = self.model.route_harvested("enforce goal hierarchy")
        self.assertTrue(routing["confident"])
        self.assertFalse(routing["best"]["admitted"])
        out = self.model.execute_harvested_surface(
            capability_id=routing["best"]["id"], args={}
        )
        self.assertFalse(out.get("admitted"))
        self.assertEqual(out.get("admission"), "NOT_ADMITTED")


if __name__ == "__main__":
    unittest.main()
