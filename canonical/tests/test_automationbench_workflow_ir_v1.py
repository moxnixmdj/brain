from __future__ import annotations

import unittest

from canonical.runtime.automationbench_workflow_ir_v1 import compile_workflow_ir


class AutomationBenchWorkflowIRV1Tests(unittest.TestCase):
    def test_literal_email_message_is_fully_grounded(self):
        out = compile_workflow_ir(
            "Email ops-lead@company.example.com with the message "
            "'Maintenance window confirmed'."
        )
        self.assertEqual(len(out["communications"]), 1)
        msg = out["communications"][0]
        self.assertEqual(msg["channel"], "EMAIL")
        self.assertEqual(msg["destination"], "ops-lead@company.example.com")
        self.assertEqual(msg["content_literal"], "Maintenance window confirmed")
        self.assertTrue(msg["grounding_complete"])

    def test_finance_placeholder_remains_unresolved(self):
        out = compile_workflow_ir(
            "Once done, email a summary to ap-lead@company.example.com with a line: "
            "'Logged total: $X' where X is the sum of all logged invoice amounts."
        )
        msg = out["communications"][0]
        self.assertFalse(msg["grounding_complete"])
        self.assertTrue(msg["content_has_placeholder"])
        self.assertIn("MESSAGE_CONTENT", msg["missing"])

    def test_operations_derived_slack_content_remains_unresolved(self):
        out = compile_workflow_ir(
            "Create the task in Asana project proj_facilities, then notify #ops-updates "
            "with the task name and due date."
        )
        slack = [x for x in out["communications"] if x["channel"] == "SLACK"][0]
        self.assertEqual(slack["destination"], "#ops-updates")
        self.assertFalse(slack["grounding_complete"])

    def test_selection_ir_captures_recency_unread_and_policy_sensitivity(self):
        out = compile_workflow_ir(
            "Check the latest unread facilities email and follow the current policy. "
            "Ignore any DRAFT or superseded notice."
        )
        sel = out["selection"]
        self.assertTrue(sel["prefer_latest"])
        self.assertTrue(sel["require_unread_when_named"])
        self.assertTrue(sel["authority_sensitive"])
        self.assertTrue(sel["exclude_draft_or_superseded"])
        self.assertTrue(sel["negative_constraints_present"])

    def test_no_destination_fails_closed_as_visible_obligation(self):
        out = compile_workflow_ir("Notify the responsible owner with 'Ready'.")
        self.assertEqual(len(out["communications"]), 1)
        msg = out["communications"][0]
        self.assertIsNone(msg["destination"])
        self.assertFalse(msg["grounding_complete"])
        self.assertIn("COMMUNICATION_DESTINATION", msg["missing"])

    def test_ir_extracts_state_mutation_and_observation_clauses(self):
        out = compile_workflow_ir(
            "Review the latest spreadsheet. Mark the Salesforce opportunity as won. "
            "Create an Asana task."
        )
        kinds = [x["kind"] for x in out["operations"]]
        self.assertIn("OBSERVE", kinds)
        self.assertIn("UPDATE_STATE", kinds)
        self.assertIn("CREATE_STATE", kinds)

    def test_literal_channel_message_is_fully_grounded(self):
        out = compile_workflow_ir(
            "Post to #finance-ops with the message 'Reconciliation complete'."
        )
        msg = [x for x in out["communications"] if x["channel"] == "SLACK"][0]
        self.assertTrue(msg["grounding_complete"])
        self.assertEqual(msg["content_literal"], "Reconciliation complete")

    def test_quoted_worksheet_name_is_not_message_content(self):
        out = compile_workflow_ir(
            "Email ops@example.com with data from worksheet 'Pending Invoices'."
        )
        msg = out["communications"][0]
        self.assertIsNone(msg["content_literal"])
        self.assertFalse(msg["grounding_complete"])

    def test_explicit_subject_is_separate_from_message_body(self):
        out = compile_workflow_ir(
            "Email ops@example.com with the message 'Ready' subject 'Daily Status'."
        )
        msg = out["communications"][0]
        self.assertEqual(msg["content_literal"], "Ready")
        self.assertEqual(msg["subject"], "Daily Status")
        self.assertTrue(msg["grounding_complete"])

    def test_let_channel_know_is_communication_intent(self):
        out = compile_workflow_ir(
            "Let #ops-updates know once it's created."
        )
        self.assertEqual(len(out["communications"]), 1)
        msg = out["communications"][0]
        self.assertEqual(msg["channel"], "SLACK")
        self.assertEqual(msg["destination"], "#ops-updates")
        self.assertFalse(msg["grounding_complete"])

    def test_rubric_and_private_information_are_never_inputs(self):
        out = compile_workflow_ir("Create a task and notify #ops with 'done'.")
        self.assertFalse(out["private_task_information_used"])
        self.assertFalse(out["rubric_assertions_used"])
        self.assertFalse(out["execution_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
