from __future__ import annotations

import unittest

from canonical.runtime.automationbench_communication_grounder_v1 import (
    resolve_communication,
)


def fire_drill_observations():
    return [
        {
            "messages": [
                {
                    "id": "source",
                    "subject": "Fire drill reminder",
                    "body_plain": (
                        "Please create task: Monthly Fire Drill Checklist - February. "
                        "Due: 2026-02-18. Tag: Compliance."
                    ),
                }
            ]
        },
        {
            "data": {
                "gid": "task_new",
                "name": "Monthly Fire Drill Checklist - February",
                "due_on": "2026-02-18",
                "completed": False,
            }
        },
    ]


class AutomationBenchCommunicationGrounderV1Tests(unittest.TestCase):
    def test_created_task_notification_derives_name_and_due(self):
        communication = {
            "channel": "SLACK",
            "destination": "#ops-updates",
            "content_literal": None,
            "grounding_complete": False,
            "source_clause": "Let #ops-updates know once it's created.",
        }
        out = resolve_communication(
            communication,
            prompt="Create the fire drill task and let #ops-updates know once it's created.",
            observations=fire_drill_observations(),
        )
        self.assertTrue(out["grounding_complete"], out)
        self.assertEqual(
            out["content_literal"],
            "Monthly Fire Drill Checklist - February\nDue: 2026-02-18",
        )
        self.assertTrue(out["provenance_bound"])
        self.assertIn("TASK_GID:task_new", out["provenance"])

    def test_explicit_task_name_and_due_request_uses_matching_task(self):
        observations = fire_drill_observations() + [
            {
                "data": {
                    "gid": "noise",
                    "name": "Unrelated Task",
                    "due_on": "2026-02-19",
                }
            }
        ]
        communication = {
            "channel": "SLACK",
            "destination": "#ops-updates",
            "content_literal": None,
            "grounding_complete": False,
            "source_clause": "Notify #ops-updates with the task name and due date.",
        }
        out = resolve_communication(
            communication,
            prompt="Notify #ops-updates with the task name and due date.",
            observations=observations,
        )
        self.assertTrue(out["grounding_complete"], out)
        self.assertIn("Monthly Fire Drill Checklist - February", out["content_literal"])
        self.assertNotIn("Unrelated Task", out["content_literal"])

    def test_two_matching_distinct_created_tasks_fail_closed(self):
        observations = fire_drill_observations() + [
            {
                "data": {
                    "gid": "task_duplicate",
                    "name": "Monthly Fire Drill Checklist - February",
                    "due_on": "2026-02-18",
                }
            }
        ]
        communication = {
            "channel": "SLACK",
            "destination": "#ops-updates",
            "content_literal": None,
            "grounding_complete": False,
            "source_clause": "Let #ops-updates know once it's created.",
        }
        out = resolve_communication(
            communication,
            prompt="Let #ops-updates know once it's created.",
            observations=observations,
        )
        self.assertFalse(out["grounding_complete"])
        self.assertEqual(out["reason"], "TASK_RECORD_AMBIGUOUS")

    def test_missing_due_date_fails_closed(self):
        observations = [
            {
                "body_plain": "Create task: Monthly Fire Drill Checklist - February.",
                "id": "source",
            },
            {
                "data": {
                    "gid": "task_new",
                    "name": "Monthly Fire Drill Checklist - February",
                }
            },
        ]
        communication = {
            "channel": "SLACK",
            "destination": "#ops-updates",
            "content_literal": None,
            "grounding_complete": False,
            "source_clause": "Let #ops-updates know once it's created.",
        }
        out = resolve_communication(
            communication,
            prompt="Let #ops-updates know once it's created.",
            observations=observations,
        )
        self.assertFalse(out["grounding_complete"])
        self.assertEqual(out["reason"], "TASK_RECORD_NOT_GROUNDED")

    def test_literal_obligation_passes_through_with_provenance(self):
        communication = {
            "channel": "EMAIL",
            "destination": "ops@example.com",
            "content_literal": "Ready",
            "grounding_complete": True,
            "source_clause": "Email ops@example.com with the message 'Ready'.",
        }
        out = resolve_communication(
            communication,
            prompt="Email ops@example.com with the message 'Ready'.",
            observations=[],
        )
        self.assertTrue(out["grounding_complete"])
        self.assertEqual(out["content_literal"], "Ready")
        self.assertEqual(out["provenance"], ["TASK_PROMPT_LITERAL"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
