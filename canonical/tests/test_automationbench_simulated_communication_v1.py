from __future__ import annotations

import base64
import json
import unittest

from canonical.runtime.automationbench_simulated_communication_v1 import (
    SURFACE,
    compile_simulated_communication,
)


class AutomationBenchSimulatedCommunicationV1Tests(unittest.TestCase):
    def test_email_compiles_to_valid_gmail_payload_without_network_io(self):
        out = compile_simulated_communication(
            {
                "surface": SURFACE,
                "channel": "EMAIL",
                "destination": "ops@example.com",
                "subject": "Status",
                "content": "Maintenance window confirmed",
                "grounding_complete": True,
                "provenance_bound": True,
            }
        )
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["network_io_performed"])
        call = out["tool_call"]
        self.assertEqual(call["tool"], "api_fetch")
        self.assertEqual(call["arguments"]["method"], "POST")
        body = json.loads(call["arguments"]["body"])
        payload = body["payload"]
        headers = {x["name"]: x["value"] for x in payload["headers"]}
        self.assertEqual(headers["To"], "ops@example.com")
        self.assertEqual(headers["Subject"], "Status")
        data = payload["body"]["data"]
        padded = data + "=" * (-len(data) % 4)
        self.assertEqual(
            base64.urlsafe_b64decode(padded).decode("utf-8"),
            "Maintenance window confirmed",
        )

    def test_slack_compiles_to_simulated_post_message(self):
        out = compile_simulated_communication(
            {
                "surface": SURFACE,
                "channel": "SLACK",
                "destination": "#ops-updates",
                "content": "Reconciliation complete",
                "grounding_complete": True,
                "provenance_bound": True,
            }
        )
        self.assertTrue(out["pass"], out)
        body = json.loads(out["tool_call"]["arguments"]["body"])
        self.assertEqual(body, {
            "channel": "#ops-updates",
            "text": "Reconciliation complete",
        })
        self.assertFalse(out["network_io_performed"])

    def test_non_benchmark_surface_is_rejected(self):
        out = compile_simulated_communication(
            {
                "surface": "REAL_WORLD",
                "channel": "EMAIL",
                "destination": "ops@example.com",
                "content": "x",
                "grounding_complete": True,
                "provenance_bound": True,
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "BENCHMARK_SIMULATED_SURFACE_REQUIRED")

    def test_incomplete_grounding_is_rejected(self):
        out = compile_simulated_communication(
            {
                "surface": SURFACE,
                "channel": "SLACK",
                "destination": "#ops",
                "content": "x",
                "grounding_complete": False,
                "provenance_bound": True,
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "GROUNDING_INCOMPLETE")

    def test_missing_provenance_is_rejected(self):
        out = compile_simulated_communication(
            {
                "surface": SURFACE,
                "channel": "EMAIL",
                "destination": "ops@example.com",
                "content": "x",
                "grounding_complete": True,
                "provenance_bound": False,
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "GROUNDING_PROVENANCE_REQUIRED")

    def test_invalid_destination_is_rejected(self):
        out = compile_simulated_communication(
            {
                "surface": SURFACE,
                "channel": "EMAIL",
                "destination": "not-an-email",
                "content": "x",
                "grounding_complete": True,
                "provenance_bound": True,
            }
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "EMAIL_DESTINATION_INVALID")


if __name__ == "__main__":
    unittest.main(verbosity=2)
