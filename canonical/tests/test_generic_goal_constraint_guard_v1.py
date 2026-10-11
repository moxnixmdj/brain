from __future__ import annotations

import unittest

from canonical.runtime.generic_goal_constraint_guard_v1 import (
    intents_may_conflict,
    mutation_step_guard,
    verify_forbidden_execution_trace,
)
from canonical.runtime.generic_goal_tool_effect_planner_v1 import compile_goal_contract


class GenericGoalConstraintGuardV1Tests(unittest.TestCase):
    def test_same_action_same_resource_without_strong_anchor_blocks(self):
        c = compile_goal_contract(
            "Update the customer record. Do not update the customer record."
        )
        pos = [x for x in c["intents"] if not x["forbidden"]][0]
        neg = [x for x in c["intents"] if x["forbidden"]][0]
        self.assertTrue(intents_may_conflict(pos, neg))

    def test_distinct_email_anchors_disambiguate_notify(self):
        c = compile_goal_contract(
            "Send the notice to alpha@example.test. Do not send the notice to beta@example.test."
        )
        pos = [x for x in c["intents"] if not x["forbidden"]][0]
        neg = [x for x in c["intents"] if x["forbidden"]][0]
        self.assertFalse(intents_may_conflict(pos, neg))

    def test_distinct_literal_ids_disambiguate_delete(self):
        c = compile_goal_contract(
            "Delete order ord_100. Do not delete order ord_200."
        )
        pos = [x for x in c["intents"] if not x["forbidden"]][0]
        neg = [x for x in c["intents"] if x["forbidden"]][0]
        self.assertFalse(intents_may_conflict(pos, neg))

    def test_mutation_guard_blocks_ambiguous_forbidden_overlap(self):
        c = compile_goal_contract(
            "Update the customer status to active. Do not update the customer record."
        )
        pos = [x for x in c["intents"] if not x["forbidden"]][0]
        out = mutation_step_guard(
            step={
                "role":"mutation",
                "intent_id":pos["id"],
                "action_class":"update",
            },
            contract=c,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "POTENTIAL_FORBIDDEN_ACTION_CONFLICT")

    def test_complete_empty_trace_proves_constraint_only_nonexecution(self):
        c = compile_goal_contract("Do not notify beta@example.test.")
        out = verify_forbidden_execution_trace(
            contract=c, execution_trace=[], trace_complete=True
        )
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["constraint_results"][0]["verified"])

    def test_incomplete_trace_fails_closed(self):
        c = compile_goal_contract("Do not delete order ord_200.")
        out = verify_forbidden_execution_trace(
            contract=c, execution_trace=[], trace_complete=False
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EXECUTION_TRACE_NOT_COMPLETE")

    def test_trace_detects_conflicting_executed_mutation(self):
        c = compile_goal_contract(
            "Update the customer record. Do not update the customer record."
        )
        pos = [x for x in c["intents"] if not x["forbidden"]][0]
        out = verify_forbidden_execution_trace(
            contract=c,
            execution_trace=[{"intent_id":pos["id"],"action_class":"update"}],
            trace_complete=True,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["constraint_results"][0]["reason"],
            "CONFLICTING_MUTATION_EXECUTED",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
