from __future__ import annotations

import json
import unittest

from canonical.runtime.automationbench_owned_policy_kernel_v1 import (
    classify,
    observation_plan,
    parse_search_payload,
    rank_endpoints,
    rank_source_records,
    search_queries,
)


class AutomationBenchOwnedPolicyKernelV1Tests(unittest.TestCase):
    def test_sales_prompt_extracts_apps_actions_and_native_queries(self):
        prompt = (
            "Mark the Salesforce opportunity as won, confirm the account tier from "
            "the Account Hierarchy spreadsheet, check open support escalations, "
            "and send the win notice by Gmail."
        )
        c = classify(prompt)
        self.assertIn("salesforce", c["apps"])
        self.assertIn("google_sheets", c["apps"])
        self.assertIn("gmail", c["apps"])
        self.assertIn("update", c["actions"])
        self.assertIn("send", c["actions"])
        qs = search_queries(prompt)
        self.assertTrue(any("salesforce" in q for q in qs))
        self.assertTrue(any("messages" in q for q in qs))

    def test_ops_draft_and_superseded_records_are_never_ranked_eligible(self):
        prompt = "Check the latest unread facilities email about a fire drill."
        records = [
            {"id":"old","subject":"Fire drill","body_plain":"Due 2026-02-14","date":"2026-01-26T10:00:00Z","is_read":True},
            {"id":"good","subject":"Fire drill reminder","body_plain":"Monthly Fire Drill Checklist February","date":"2026-01-28T09:15:00Z","is_read":False},
            {"id":"draft","subject":"Fire drill UPDATED","body_plain":"DRAFT - DO NOT ACTION: March preview","date":"2026-01-29T08:00:00Z","is_read":False},
            {"id":"sup","subject":"Fire drill correction","body_plain":"SUPERSEDED: disregard this version","date":"2026-01-29T09:00:00Z","is_read":False},
        ]
        ranked = rank_source_records(prompt, records)
        ids = [x["id"] for x in ranked]
        self.assertEqual(ids[0], "good")
        self.assertNotIn("draft", ids)
        self.assertNotIn("sup", ids)

    def test_requested_sender_beats_newer_wrong_sender(self):
        prompt = "Check the latest unread email from the facilities team about a fire drill."
        records = [
            {
                "id":"correct",
                "from_":"facilities@company.example.com",
                "subject":"Fire drill reminder",
                "body_plain":"Create task: Monthly Fire Drill Checklist - February. Due: 2026-02-18.",
                "date":"2026-01-28T09:15:00Z",
                "is_read":False,
            },
            {
                "id":"wrong",
                "from_":"maintenance@company.example.com",
                "subject":"Fire drill reminder",
                "body_plain":"Create task: Monthly Fire Drill Checklist - Annex. Due: 2026-02-19.",
                "date":"2026-01-28T11:00:00Z",
                "is_read":False,
            },
        ]
        ranked = rank_source_records(prompt, records)
        self.assertEqual(ranked[0]["id"], "correct")

    def test_api_search_payload_parsing_is_fail_closed(self):
        self.assertEqual(parse_search_payload("not-json"), [])
        self.assertEqual(parse_search_payload('{"x": []}'), [])
        self.assertEqual(
            parse_search_payload('{"results":[{"id":"x","method":"GET","url":"https://x"}]}')[0]["id"],
            "x",
        )

    def test_observation_plan_emits_get_only(self):
        prompt = "Find Gmail messages and then send a summary."
        payload = {
            "results": [
                {"id":"gmail.list","method":"GET","url":"https://gmail.googleapis.com/gmail/v1/users/me/messages","description":"List messages","parameters":{}},
                {"id":"gmail.send","method":"POST","url":"https://gmail.googleapis.com/gmail/v1/users/me/messages/send","description":"Send message","parameters":{}},
            ]
        }
        plan = observation_plan(prompt, [payload])
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["arguments"]["method"], "GET")
        self.assertEqual(plan[0]["endpoint_id"], "gmail.list")

    def test_observation_skips_ungrounded_required_ids(self):
        prompt = "Review the spreadsheet before doing anything."
        payload = {
            "results": [
                {
                    "id":"sheets.values.get",
                    "method":"GET",
                    "url":"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values/{range}",
                    "description":"Get values",
                    "parameters":{
                        "spreadsheetId":{"required":True,"type":"string"},
                        "range":{"required":True,"type":"string"},
                    },
                }
            ]
        }
        self.assertEqual(observation_plan(prompt, [payload]), [])

    def test_observation_can_ground_literal_identifier(self):
        prompt = "Review project proj_facilities before creating anything."
        payload = {
            "results": [
                {
                    "id":"asana.project.get",
                    "method":"GET",
                    "url":"https://app.asana.com/api/1.0/projects/proj_facilities",
                    "description":"Get project",
                    "parameters":{"project":{"required":True,"type":"string"}},
                }
            ]
        }
        plan = observation_plan(prompt, [payload])
        self.assertEqual(len(plan), 1)
        self.assertIn("/projects/proj_facilities", plan[0]["arguments"]["url"])
        self.assertNotIn("{", plan[0]["arguments"]["url"])

    def test_required_default_path_parameter_is_substituted(self):
        prompt = "Find Gmail messages."
        payload = {
            "results": [
                {
                    "id":"gmail.users.messages.list",
                    "method":"GET",
                    "url":"https://gmail.googleapis.com/gmail/v1/users/{userId}/messages",
                    "description":"List messages",
                    "parameters":{
                        "userId":{"required":True,"location":"path","default":"me"}
                    },
                }
            ]
        }
        plan = observation_plan(prompt, [payload])
        self.assertEqual(len(plan), 1)
        self.assertIn("/users/me/messages", plan[0]["arguments"]["url"])

    def test_endpoint_ranking_prefers_read_for_observation(self):
        prompt = "Find the invoice messages before updating the tracker."
        eps = [
            {"id":"send","method":"POST","url":"https://gmail/messages/send","description":"send messages"},
            {"id":"list","method":"GET","url":"https://gmail/messages","description":"list search messages invoices"},
        ]
        ranked = rank_endpoints(prompt, eps)
        self.assertEqual(ranked[0]["id"], "list")

    def test_negative_guard_is_case_insensitive(self):
        prompt = "Use the latest policy"
        records = [
            {"id":"x","body":"do NOT action this draft","date":"2026-01-03T00:00:00Z"},
            {"id":"y","body":"Policy effective immediately","date":"2026-01-02T00:00:00Z"},
        ]
        self.assertEqual([x["id"] for x in rank_source_records(prompt, records)], ["y"])

    def test_policy_document_discussing_drafts_is_valid_evidence(self):
        prompt = "Check the email processing policy before creating the task"
        records = [
            {
                "id":"policy",
                "title":"Email Processing Rules",
                "description":"Draft Notification Policy: emails marked DRAFT or DO NOT ACTION must not trigger actions.",
                "updated_at":"2026-01-29T00:00:00Z",
            }
        ]
        ranked = rank_source_records(prompt, records, record_role="evidence")
        self.assertEqual([x["id"] for x in ranked], ["policy"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
