from __future__ import annotations

import unittest

from canonical.runtime.generic_goal_state_verifier_v2 import verify_goal_state


class GenericGoalStateVerifierV2Tests(unittest.TestCase):
    def test_update_is_bound_to_same_target_identity(self):
        out = verify_goal_state(
            goal="Set the Acme shipment status to delivered.",
            context_observations=[
                {"records":[
                    {"id":"shp_1","name":"Acme shipment","status":"pending"},
                    {"id":"shp_2","name":"Other shipment","status":"pending"},
                ]}
            ],
            verification_observations=[
                {"records":[
                    {"id":"shp_1","name":"Acme shipment","status":"pending"},
                    {"id":"shp_2","name":"Other shipment","status":"delivered"},
                ]}
            ],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["intent_results"][0]["reason"],
            "TARGET_POST_ACTION_FIELD_VALUE_NOT_OBSERVED",
        )

    def test_create_checks_additional_exposed_scalar_fields(self):
        out = verify_goal_state(
            goal="Create the task in project proj_blue.",
            context_observations=[
                {"message":{
                    "body":"Create task: Safety Review. Due: 2026-12-01."
                }}
            ],
            verification_observations=[
                {"items":[
                    {"id":"task_1","name":"Safety Review","due_on":"2026-12-02"}
                ]}
            ],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["intent_results"][0]["reason"],
            "CREATED_OBJECT_FIELD_MISMATCH:date",
        )

    def test_delete_requires_strong_absence_evidence(self):
        context = [
            {"records":[{"id":"ord_1","name":"Acme order","status":"open"}]}
        ]
        weak = verify_goal_state(
            goal="Delete the Acme order.",
            context_observations=context,
            verification_observations=[{"records":[]}],
        )
        self.assertFalse(weak["pass"])
        self.assertEqual(
            weak["intent_results"][0]["reason"],
            "DELETE_ABSENCE_NOT_STRONGLY_PROVED",
        )

        strong = verify_goal_state(
            goal="Delete the Acme order.",
            context_observations=context,
            verification_observations=[
                {"error":{"code":404,"message":"Record not found"}}
            ],
        )
        self.assertTrue(strong["pass"], strong)

    def test_association_requires_two_grounded_relation_anchors(self):
        out = verify_goal_state(
            goal="Add the task to the February section.",
            context_observations=[
                {"source":{"body":"Create task: Safety Review."}},
                {"records":[
                    {"gid":"task_7","name":"Safety Review"},
                    {"gid":"sec_feb","name":"February"},
                ]},
            ],
            verification_observations=[
                {"membership":{
                    "task":"task_7",
                    "section":"sec_feb",
                }}
            ],
        )
        self.assertTrue(out["pass"], out)

    def test_notify_requires_grounded_recipient_in_post_state(self):
        out = verify_goal_state(
            goal="Send the notice to ops@example.com.",
            context_observations=[],
            verification_observations=[
                {"messages":[
                    {
                        "id":"m_1",
                        "to":"ops@example.com",
                        "subject":"Notice",
                        "body":"Done",
                    }
                ]}
            ],
        )
        self.assertTrue(out["pass"], out)

    def test_forbidden_delete_is_actively_verified(self):
        goal = "Do not delete the Acme order. Review the Acme order."
        context = [
            {"records":[{"id":"ord_1","name":"Acme order","status":"open"}]}
        ]
        survived = verify_goal_state(
            goal=goal,
            context_observations=context,
            verification_observations=[
                {"records":[{"id":"ord_1","name":"Acme order","status":"open"}]}
            ],
        )
        self.assertTrue(survived["pass"], survived)
        self.assertTrue(survived["constraint_results"][0]["verified"])

        missing = verify_goal_state(
            goal=goal,
            context_observations=context,
            verification_observations=[{"records":[]}],
        )
        self.assertFalse(missing["pass"])
        self.assertEqual(
            missing["constraint_results"][0]["reason"],
            "FORBIDDEN_DELETE_TARGET_NOT_OBSERVED_POST_ACTION",
        )

    def test_unsupported_forbidden_action_fails_closed(self):
        out = verify_goal_state(
            goal="Do not notify the customer.",
            context_observations=[],
            verification_observations=[],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["constraint_results"][0]["reason"],
            "FORBIDDEN_ACTION_VERIFICATION_UNSUPPORTED:notify",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
