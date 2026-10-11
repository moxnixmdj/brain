from __future__ import annotations

import unittest

from canonical.runtime.automation_zero_model_task_ir_v1 import compile_task_ir


class ZeroModelTaskIRTests(unittest.TestCase):
    def test_simple_multiaction_workflow_splits_and_orders(self):
        out = compile_task_ir(
            "Find the customer record, update the phone number, and send a confirmation email."
        )
        self.assertTrue(out["pass"], out)
        self.assertGreaterEqual(out["clause_count"], 3)
        self.assertEqual(out["model_dependency_count"], 0)
        actions = [x["action_tokens"][0] for x in out["clauses"]]
        self.assertIn("find", actions)
        self.assertIn("update", actions)
        self.assertIn("send", actions)

    def test_literal_values_are_extracted_and_removed_from_discovery_query(self):
        out = compile_task_ir(
            "Send an email to finance-team@example.com about invoice INV-44 for $12,500."
        )
        self.assertTrue(out["pass"], out)
        row = out["clauses"][0]
        kinds = {x["kind"] for x in row["literals"]}
        self.assertIn("EMAIL", kinds)
        self.assertIn("MONEY", kinds)
        self.assertNotIn("finance-team@example.com", row["discovery_query"])
        self.assertNotIn("12,500", row["discovery_query"])

    def test_constraints_are_explicit(self):
        out = compile_task_ir(
            "Update only active records and do not change archived records."
        )
        self.assertTrue(out["pass"], out)
        flags = set(out["clauses"][0]["constraint_flags"])
        self.assertIn("ONLY", flags)
        self.assertIn("NEGATION", flags)

    def test_conditional_and_recency_flags(self):
        out = compile_task_ir(
            "If the latest policy requires escalation, send a notice to #ops-alerts."
        )
        self.assertTrue(out["pass"], out)
        flags = set(out["clauses"][0]["constraint_flags"])
        self.assertIn("CONDITIONAL", flags)
        self.assertIn("RECENCY", flags)
        self.assertIn("CHANNEL", {x["kind"] for x in out["clauses"][0]["literals"]})

    def test_create_schedule_and_notify_are_normalized(self):
        out = compile_task_ir(
            "Schedule a review and notify the owner."
        )
        self.assertTrue(out["pass"], out)
        flattened = [x for row in out["clauses"] for x in row["action_tokens"]]
        self.assertIn("create", flattened)
        self.assertIn("send", flattened)

    def test_no_action_fails_closed(self):
        out = compile_task_ir("The account is currently healthy.")
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "ZERO_ACTION_BEARING_CLAUSES")
        self.assertEqual(out["model_dependency_count"], 0)

    def test_empty_prompt_fails_closed(self):
        out = compile_task_ir("   ")
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "PROMPT_REQUIRED")

    def test_deterministic(self):
        prompt = "Find the latest contract and update the renewal date to 2026-12-31."
        a = compile_task_ir(prompt)
        b = compile_task_ir(prompt)
        self.assertEqual(a, b)

    def test_no_benchmark_specific_runtime_claims(self):
        out = compile_task_ir("Create a task for the account owner.")
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["private_benchmark_information_used"])
        self.assertFalse(out["terminal_authority"])
        self.assertFalse(out["acceptance_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
