from __future__ import annotations

import unittest

from canonical.runtime.generic_goal_state_verifier_v1 import verify_goal_state


class GenericGoalStateVerifierV1Tests(unittest.TestCase):
    def test_update_verified_from_post_action_state(self):
        out = verify_goal_state(
            goal="Set the Acme shipment status to delivered.",
            context_observations=[
                {"records":[{"id":"shp_123","name":"Acme shipment","status":"pending"}]}
            ],
            verification_observations=[
                {"records":[{"id":"shp_123","name":"Acme shipment","status":"delivered"}]}
            ],
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["status"], "VERIFIED")

    def test_wrong_update_value_is_rejected(self):
        out = verify_goal_state(
            goal="Set the Acme shipment status to delivered.",
            context_observations=[],
            verification_observations=[
                {"records":[{"id":"shp_123","name":"Acme shipment","status":"pending"}]}
            ],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["intent_results"][0]["reason"],
            "POST_ACTION_FIELD_VALUE_NOT_OBSERVED",
        )

    def test_update_substring_does_not_false_pass(self):
        out = verify_goal_state(
            goal="Set the ticket status to reopened.",
            context_observations=[],
            verification_observations=[
                {"records":[{"id":"t_1","name":"Ticket","status":"open"}]}
            ],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["intent_results"][0]["reason"],
            "POST_ACTION_FIELD_VALUE_NOT_OBSERVED",
        )

    def test_create_verified_using_grounded_source_name(self):
        out = verify_goal_state(
            goal="Create the task in project proj_blue.",
            context_observations=[
                {"message":{"body":"Create task: Safety Review. Due: 2026-12-01."}}
            ],
            verification_observations=[
                {"items":[{"id":"task_7","name":"Safety Review","due_on":"2026-12-01"}]}
            ],
        )
        self.assertTrue(out["pass"], out)

    def test_create_missing_from_post_state_is_rejected(self):
        out = verify_goal_state(
            goal="Create the task in project proj_blue.",
            context_observations=[
                {"message":{"body":"Create task: Safety Review. Due: 2026-12-01."}}
            ],
            verification_observations=[
                {"items":[{"id":"task_8","name":"Other Task"}]}
            ],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["intent_results"][0]["reason"],
            "CREATED_OBJECT_NOT_OBSERVED",
        )

    def test_create_partial_name_does_not_false_pass(self):
        out = verify_goal_state(
            goal="Create the task in project proj_blue.",
            context_observations=[
                {"message":{"body":"Create task: Safety Review. Due: 2026-12-01."}}
            ],
            verification_observations=[
                {"items":[{"id":"task_7","name":"Safety"}]}
            ],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["intent_results"][0]["reason"],
            "CREATED_OBJECT_NOT_OBSERVED",
        )

    def test_observe_intent_requires_relevant_record(self):
        out = verify_goal_state(
            goal="Review the invoice.",
            context_observations=[],
            verification_observations=[
                {"records":[{"id":"inv_1","name":"Invoice 1"}]}
            ],
        )
        self.assertTrue(out["pass"], out)

    def test_association_remains_fail_closed(self):
        out = verify_goal_state(
            goal="Add the task to the February section.",
            context_observations=[],
            verification_observations=[
                {"result":{"task":"task_1","section":"sec_feb"}}
            ],
        )
        self.assertFalse(out["pass"])
        self.assertIn(
            "GENERIC_VERIFIER_UNSUPPORTED_ACTION_CLASS",
            out["intent_results"][0]["reason"],
        )

    def test_forbidden_action_is_not_a_positive_verification_target(self):
        out = verify_goal_state(
            goal="Do not delete the invoice. Review the invoice.",
            context_observations=[],
            verification_observations=[
                {"records":[{"id":"inv_1","name":"Invoice 1"}]}
            ],
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(len(out["intent_results"]), 1)
        self.assertEqual(out["intent_results"][0]["action_class"], "observe")


if __name__ == "__main__":
    unittest.main(verbosity=2)
