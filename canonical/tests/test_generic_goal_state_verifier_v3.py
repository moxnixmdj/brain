from __future__ import annotations

import unittest

from canonical.runtime.generic_goal_state_verifier_v3 import verify_goal_state
from canonical.runtime.generic_goal_tool_effect_planner_v1 import compile_goal_contract


class GenericGoalStateVerifierV3Tests(unittest.TestCase):
    def test_constraint_only_create_passes_from_complete_empty_trace(self):
        out = verify_goal_state(
            goal="Do not create the cobalt widget.",
            context_observations=[],
            verification_observations=[],
            execution_trace=[],
            execution_trace_complete=True,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["constraint_results"][0]["verification_basis"],
            "COMPLETE_EXECUTION_TRACE_NONEXECUTION",
        )

    def test_constraint_only_create_stays_fail_closed_with_incomplete_trace(self):
        out = verify_goal_state(
            goal="Do not create the cobalt widget.",
            context_observations=[],
            verification_observations=[],
            execution_trace=[],
            execution_trace_complete=False,
        )
        self.assertFalse(out["pass"])
        self.assertIn(
            "FORBIDDEN_ACTION_VERIFICATION_UNSUPPORTED",
            out["constraint_results"][0]["reason"],
        )

    def test_conflicting_trace_fails_forbidden_update(self):
        goal = "Update the cobalt widget. Do not update the cobalt widget."
        contract = compile_goal_contract(goal)
        positive = [
            x for x in contract["intents"]
            if not x["forbidden"] and x["action_class"] == "update"
        ][0]
        out = verify_goal_state(
            goal=goal,
            context_observations=[{"records":[{"id":"wid_1","name":"cobalt widget","status":"old"}]}],
            verification_observations=[{"records":[{"id":"wid_1","name":"cobalt widget","status":"old"}]}],
            execution_trace=[{"intent_id":positive["id"],"action_class":"update"}],
            execution_trace_complete=True,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["constraint_results"][0]["reason"],
            "CONFLICTING_MUTATION_EXECUTED",
        )

    def test_forbidden_delete_retains_strong_state_requirement(self):
        out = verify_goal_state(
            goal="Do not delete order ord_100.",
            context_observations=[{"records":[{"id":"ord_100","name":"order ord_100"}]}],
            verification_observations=[{"records":[]}],
            execution_trace=[],
            execution_trace_complete=True,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["constraint_results"][0]["reason"],
            "FORBIDDEN_DELETE_TARGET_NOT_OBSERVED_POST_ACTION",
        )

    def test_no_forbidden_intent_preserves_v2_positive_result(self):
        out = verify_goal_state(
            goal="Review the cobalt widget.",
            context_observations=[],
            verification_observations=[{"records":[{"id":"wid_1","name":"cobalt widget"}]}],
            execution_trace=[],
            execution_trace_complete=True,
        )
        self.assertTrue(out["pass"], out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
