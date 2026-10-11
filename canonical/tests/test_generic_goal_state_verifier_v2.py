from __future__ import annotations

import unittest

from canonical.runtime.generic_goal_state_verifier_v2 import verify_goal_state


def receipt(intent: str, action: str, bindings: dict, endpoint: str = "opaque.mutate"):
    return {
        "action_class": action,
        "capability_id": f"act::{intent}::{endpoint}",
        "endpoint_id": endpoint,
        "bindings": bindings,
        "arguments": {},
    }


class GenericGoalStateVerifierV2Tests(unittest.TestCase):
    def test_update_is_bound_to_exact_acted_target(self):
        out = verify_goal_state(
            goal="Find the order, then set the order status to closed.",
            context_observations=[
                {"records":[
                    {"id":"ord_1","name":"Order","status":"open"},
                    {"id":"ord_2","name":"Other Order","status":"open"},
                ]}
            ],
            verification_observations=[
                {"records":[
                    {"id":"ord_1","name":"Order","status":"open"},
                    {"id":"ord_2","name":"Other Order","status":"closed"},
                ]}
            ],
            execution_receipts=[
                receipt(
                    "intent_1",
                    "update",
                    {"parameter.id":{"value":"ord_1","source":"grounded"}},
                )
            ],
        )
        self.assertFalse(out["pass"])
        update = [x for x in out["intent_results"] if x["action_class"] == "update"][0]
        self.assertEqual(
            update["reason"],
            "POST_ACTION_FIELD_VALUE_NOT_OBSERVED_ON_ACTED_TARGET",
        )

    def test_update_exact_target_passes(self):
        out = verify_goal_state(
            goal="Find the order, then set the order status to closed.",
            context_observations=[{"records":[{"id":"ord_1","name":"Order","status":"open"}]}],
            verification_observations=[{"records":[{"id":"ord_1","name":"Order","status":"closed"}]}],
            execution_receipts=[
                receipt(
                    "intent_1",
                    "update",
                    {"parameter.id":{"value":"ord_1","source":"grounded"}},
                )
            ],
        )
        self.assertTrue(out["pass"], out)

    def test_create_requires_observed_delta(self):
        out = verify_goal_state(
            goal="Create the task in project proj_blue.",
            context_observations=[
                {"items":[{"id":"task_old","name":"Safety Review"}]},
                {"message":{"body":"Create task: Safety Review. Due: 2026-12-01."}},
            ],
            verification_observations=[
                {"items":[{"id":"task_old","name":"Safety Review"}]}
            ],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["intent_results"][0]["reason"],
            "CREATED_OBJECT_PREEXISTED_IN_OBSERVED_STATE",
        )

    def test_create_new_exact_name_passes(self):
        out = verify_goal_state(
            goal="Create the task in project proj_blue.",
            context_observations=[
                {"message":{"body":"Create task: Safety Review. Due: 2026-12-01."}}
            ],
            verification_observations=[
                {"items":[{"id":"task_new","name":"Safety Review"}]}
            ],
        )
        self.assertTrue(out["pass"], out)

    def test_association_requires_poststate_cooccurrence_delta(self):
        out = verify_goal_state(
            goal="Add the task to the section.",
            context_observations=[
                {"task":{"id":"task_1","name":"Safety Review"}},
                {"section":{"id":"sec_1","name":"Review"}},
            ],
            verification_observations=[
                {"membership":{"id":"mem_1","task":"task_1","section":"sec_1"}}
            ],
            execution_receipts=[
                receipt(
                    "intent_0",
                    "associate",
                    {
                        "parameter.section_id":{"value":"sec_1","source":"grounded"},
                        "body.task":{"value":"task_1","source":"grounded"},
                    },
                )
            ],
        )
        self.assertTrue(out["pass"], out)

    def test_preexisting_association_is_not_new_success(self):
        relation={"membership":{"id":"mem_1","task":"task_1","section":"sec_1"}}
        out = verify_goal_state(
            goal="Add the task to the section.",
            context_observations=[relation],
            verification_observations=[relation],
            execution_receipts=[
                receipt(
                    "intent_0",
                    "associate",
                    {
                        "parameter.section_id":{"value":"sec_1","source":"grounded"},
                        "body.task":{"value":"task_1","source":"grounded"},
                    },
                )
            ],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["intent_results"][0]["reason"],
            "ASSOCIATION_PREEXISTED_IN_OBSERVED_STATE",
        )

    def test_delete_requires_exact_target_reread_and_not_found(self):
        exec_receipt=receipt(
            "intent_0",
            "delete",
            {"parameter.id":{"value":"inv_1","source":"grounded"}},
        )
        verify_receipt={
            "endpoint_id":"invoice.get",
            "method":"GET",
            "bindings":{"parameter.id":{"value":"inv_1","source":"grounded"}},
            "arguments":{"method":"GET","url":"https://x.invalid/invoices/inv_1"},
        }
        out = verify_goal_state(
            goal="Delete the invoice.",
            context_observations=[{"id":"inv_1","name":"Invoice"}],
            verification_observations=[{"error":{"code":404,"message":"Not found"}}],
            execution_receipts=[exec_receipt],
            verification_receipts=[verify_receipt],
        )
        self.assertTrue(out["pass"], out)

    def test_delete_wrong_reread_target_fails(self):
        out = verify_goal_state(
            goal="Delete the invoice.",
            context_observations=[{"id":"inv_1","name":"Invoice"}],
            verification_observations=[{"error":{"code":404,"message":"Not found"}}],
            execution_receipts=[
                receipt(
                    "intent_0",
                    "delete",
                    {"parameter.id":{"value":"inv_1","source":"grounded"}},
                )
            ],
            verification_receipts=[{
                "endpoint_id":"invoice.get",
                "method":"GET",
                "bindings":{"parameter.id":{"value":"inv_2","source":"grounded"}},
                "arguments":{"method":"GET","url":"https://x.invalid/invoices/inv_2"},
            }],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["intent_results"][0]["reason"],
            "DELETE_TARGET_NOT_INDEPENDENTLY_REREAD",
        )

    def test_notify_requires_fresh_grounded_artifact(self):
        exec_receipt=receipt(
            "intent_0",
            "notify",
            {
                "body.to":{"value":"alice@example.com","source":"grounded"},
                "body.subject":{"value":"Report","source":"grounded"},
                "body.body":{"value":"Report ready","source":"grounded"},
            },
        )
        out = verify_goal_state(
            goal="Send the report to alice@example.com.",
            context_observations=[
                {"messages":[{"id":"msg_old","to":"bob@example.com","subject":"Report","body":"Report ready"}]}
            ],
            verification_observations=[
                {"messages":[{"id":"msg_new","to":"alice@example.com","subject":"Report","body":"Report ready"}]}
            ],
            execution_receipts=[exec_receipt],
        )
        self.assertTrue(out["pass"], out)

    def test_preexisting_equivalent_notification_fails(self):
        artifact={"id":"msg_old","to":"alice@example.com","subject":"Report","body":"Report ready"}
        out = verify_goal_state(
            goal="Send the report to alice@example.com.",
            context_observations=[{"messages":[artifact]}],
            verification_observations=[{"messages":[artifact]}],
            execution_receipts=[
                receipt(
                    "intent_0",
                    "notify",
                    {
                        "body.to":{"value":"alice@example.com","source":"grounded"},
                        "body.subject":{"value":"Report","source":"grounded"},
                        "body.body":{"value":"Report ready","source":"grounded"},
                    },
                )
            ],
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["intent_results"][0]["reason"],
            "EQUIVALENT_NOTIFICATION_PREEXISTED",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
