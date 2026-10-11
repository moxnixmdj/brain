from __future__ import annotations

import json
import unittest

from canonical.runtime.automationbench_multihop_observation_v1 import (
    call_fingerprint,
    discovery_search_queries,
    observation_expansion_plan,
)


PROMPT = (
    "We just closed the Meridian Corp Platform Deal! Mark it as won and route "
    "the win notice per our routing policy. Confirm the account tier from the "
    "'Account Hierarchy' spreadsheet, convert currencies using the 'FX Rates' "
    "spreadsheet, and check open support escalations. Send all emails from Gmail."
)


class AutomationBenchMultiHopObservationV1Tests(unittest.TestCase):
    def test_discovery_queries_include_dependency_apps(self):
        qs = discovery_search_queries(PROMPT)
        self.assertTrue(any(q.startswith("salesforce query") for q in qs))
        self.assertTrue(any(q.startswith("google drive files") for q in qs))
        self.assertTrue(any(q.startswith("google sheets") for q in qs))
        self.assertTrue(any(q.startswith("gmail messages") for q in qs))

    def test_first_wave_uses_bounded_salesforce_collection_reads(self):
        payload = {
            "results": [
                {
                    "id": "salesforce.query",
                    "method": "GET",
                    "url": "https://yourinstance.salesforce.com/services/data/v61.0/query",
                    "description": "Run a SOQL query to search Salesforce records.",
                    "parameters": {
                        "q": {"required": True, "location": "query", "type": "string"}
                    },
                },
                {
                    "id": "google_drive.files.list",
                    "method": "GET",
                    "url": "https://www.googleapis.com/drive/v3/files",
                    "description": "List and search files.",
                    "parameters": {},
                },
                {
                    "id": "gmail.users.messages.list",
                    "method": "GET",
                    "url": "https://gmail.googleapis.com/gmail/v1/users/{userId}/messages",
                    "description": "List mailbox messages.",
                    "parameters": {
                        "userId": {
                            "required": True,
                            "location": "path",
                            "default": "me",
                        }
                    },
                },
            ]
        }
        plan = observation_expansion_plan(PROMPT, [payload], max_calls=6)
        params = [
            json.loads(x["arguments"].get("params", "{}"))
            for x in plan
            if x["endpoint_id"] == "salesforce.query"
        ]
        queries = {x["q"] for x in params}
        self.assertEqual(
            queries,
            {
                "SELECT * FROM Opportunity",
                "SELECT * FROM Account",
                "SELECT * FROM Case",
            },
        )
        self.assertTrue(
            any(x["endpoint_id"] == "google_drive.files.list" for x in plan)
        )
        self.assertTrue(
            any(
                x["endpoint_id"] == "gmail.users.messages.list"
                and "/users/me/messages" in x["arguments"]["url"]
                for x in plan
            )
        )

    def test_second_wave_grounds_sheet_and_gmail_ids_by_service(self):
        payload = {
            "results": [
                {
                    "id": "google_drive.files.list",
                    "method": "GET",
                    "url": "https://www.googleapis.com/drive/v3/files",
                    "description": "List files.",
                    "parameters": {},
                },
                {
                    "id": "sheets.spreadsheets.get",
                    "method": "GET",
                    "url": "https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}",
                    "description": "Get spreadsheet metadata.",
                    "parameters": {
                        "spreadsheetId": {
                            "required": True,
                            "location": "path",
                        }
                    },
                },
                {
                    "id": "gmail.users.messages.list",
                    "method": "GET",
                    "url": "https://gmail.googleapis.com/gmail/v1/users/{userId}/messages",
                    "description": "List messages.",
                    "parameters": {
                        "userId": {
                            "required": True,
                            "location": "path",
                            "default": "me",
                        }
                    },
                },
                {
                    "id": "gmail.users.messages.get",
                    "method": "GET",
                    "url": "https://gmail.googleapis.com/gmail/v1/users/{userId}/messages/{id}",
                    "description": "Fetch one message.",
                    "parameters": {
                        "userId": {
                            "required": True,
                            "location": "path",
                            "default": "me",
                        },
                        "id": {"required": True, "location": "path"},
                    },
                },
            ]
        }
        observations = [
            {
                "files": [
                    {
                        "id": "ss_rates",
                        "name": "FX Rates",
                        "mimeType": "application/vnd.google-apps.spreadsheet",
                    },
                    {
                        "id": "ss_hierarchy",
                        "name": "Account Hierarchy",
                        "mimeType": "application/vnd.google-apps.spreadsheet",
                    },
                ]
            },
            {"messages": [{"id": "msg_policy", "threadId": "thread_policy"}]},
            {"records": [{"Id": "006xx000004MER1", "Name": "Meridian Corp"}]},
        ]
        already = {
            call_fingerprint(
                "api_fetch",
                {"method": "GET", "url": "https://www.googleapis.com/drive/v3/files"},
            ),
            call_fingerprint(
                "api_fetch",
                {
                    "method": "GET",
                    "url": "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                },
            ),
        }
        plan = observation_expansion_plan(
            PROMPT,
            [payload],
            observations=observations,
            already_called=already,
            max_calls=6,
        )
        urls = [x["arguments"]["url"] for x in plan]
        self.assertIn(
            "https://sheets.googleapis.com/v4/spreadsheets/ss_rates",
            urls,
        )
        self.assertIn(
            "https://sheets.googleapis.com/v4/spreadsheets/ss_hierarchy",
            urls,
        )
        self.assertIn(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/msg_policy",
            urls,
        )
        self.assertFalse(any("006xx000004MER1" in url and "gmail" in url for url in urls))

    def test_third_wave_reads_discovered_sheet_ranges(self):
        payload = {
            "results": [
                {
                    "id": "sheets.spreadsheets.values.batchGet",
                    "method": "GET",
                    "url": "https://sheets.googleapis.com/v4/spreadsheets/{spreadsheetId}/values:batchGet",
                    "description": "Batch get spreadsheet values.",
                    "parameters": {
                        "spreadsheetId": {
                            "required": True,
                            "location": "path",
                        },
                        "ranges": {"required": False, "location": "query"},
                    },
                }
            ]
        }
        observations = [
            {
                "spreadsheetId": "ss_rates",
                "properties": {"title": "FX Rates"},
                "sheets": [{"properties": {"sheetId": 1, "title": "Rates"}}],
            }
        ]
        plan = observation_expansion_plan(
            PROMPT,
            [payload],
            observations=observations,
        )
        self.assertEqual(len(plan), 1)
        self.assertIn("/spreadsheets/ss_rates/values:batchGet", plan[0]["arguments"]["url"])
        params = json.loads(plan[0]["arguments"]["params"])
        self.assertEqual(params["ranges"], ["Rates!A1:Z1000"])

    def test_already_called_get_is_not_repeated(self):
        payload = {
            "results": [
                {
                    "id": "google_drive.files.list",
                    "method": "GET",
                    "url": "https://www.googleapis.com/drive/v3/files",
                    "description": "List files.",
                    "parameters": {},
                }
            ]
        }
        args = {"method": "GET", "url": "https://www.googleapis.com/drive/v3/files"}
        plan = observation_expansion_plan(
            PROMPT,
            [payload],
            already_called={call_fingerprint("api_fetch", args)},
        )
        self.assertEqual(plan, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
