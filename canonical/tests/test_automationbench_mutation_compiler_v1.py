from __future__ import annotations

import json
import unittest

from canonical.runtime.automationbench_mutation_compiler_v1 import (
    compile_asana_add_tag,
    compile_asana_create_task,
    compile_salesforce_mark_won,
    compile_sheets_append,
    validate_nonnegative_action,
)


class AutomationBenchMutationCompilerV1Tests(unittest.TestCase):
    def test_sales_public_pattern_mark_won(self):
        prompt = "We just closed the Meridian Corp Platform Deal! Mark it as won in Salesforce."
        observations = [{
            "records": [
                {"Id":"006xx000004MER1","Name":"Meridian Corp - Platform Deal","StageName":"Negotiation"},
                {"Id":"006xx000004MRD1","Name":"Meridian Solutions - Platform Deal","StageName":"Negotiation"},
            ]
        }]
        out = compile_salesforce_mark_won(prompt, observations)
        self.assertIsNotNone(out)
        self.assertIn("006xx000004MER1", out["arguments"]["url"])
        self.assertEqual(json.loads(out["arguments"]["body"])["StageName"], "Closed Won")

    def test_sales_mark_won_fails_closed_without_matching_record(self):
        prompt = "Mark the Meridian Corp Platform Deal as won in Salesforce."
        self.assertIsNone(compile_salesforce_mark_won(prompt, [{"records": []}]))

    def test_ops_public_pattern_asana_task_creation(self):
        prompt = (
            "Add the fire drill to Asana workspace ws_ops project proj_facilities. "
            "Check the latest authoritative facilities email."
        )
        source = {
            "subject":"Fire drill reminder",
            "body_plain":"Please create task: Monthly Fire Drill Checklist - February. Due: 2026-02-18. Tag: Compliance.",
        }
        out = compile_asana_create_task(prompt, source)
        self.assertIsNotNone(out)
        body = json.loads(out["arguments"]["body"])
        self.assertEqual(body["name"], "Monthly Fire Drill Checklist - February")
        self.assertEqual(body["due_on"], "2026-02-18")
        self.assertEqual(body["projects"], ["proj_facilities"])
        self.assertEqual(out["grounding"]["tag_label_observed"], "Compliance")

    def test_asana_creation_requires_grounded_workspace_or_project(self):
        prompt = "Create the task in Asana."
        source = {"body_plain":"Create task: Safety Review. Due: 2026-02-18."}
        self.assertIsNone(compile_asana_create_task(prompt, source))

    def test_sheets_append_is_fully_grounded(self):
        out = compile_sheets_append(
            spreadsheet_id="ss_inv_tracker",
            range_a1="Pending Invoices!A:E",
            row_values=["Acme Supplies LLC","ACM-2026-0412","2026-01-28","4,750.00",""],
        )
        self.assertIsNotNone(out)
        body = json.loads(out["arguments"]["body"])
        self.assertEqual(body["values"][0][1], "ACM-2026-0412")
        self.assertIn("ss_inv_tracker", out["arguments"]["url"])

    def test_sheets_append_rejects_missing_cell(self):
        self.assertIsNone(
            compile_sheets_append(
                spreadsheet_id="ss",
                range_a1="Sheet1!A:B",
                row_values=["x", None],
            )
        )

    def test_asana_add_tag_uses_exact_created_task_and_source_tag(self):
        prompt = (
            "Check the latest fire drill email for the task details, due date, "
            "and what tag to use in Asana."
        )
        observations = [
            {
                "messages":[
                    {
                        "id":"source",
                        "body_plain":(
                            "Please create task: Monthly Fire Drill Checklist - February. "
                            "Due: 2026-02-18. Tag: Compliance."
                        )
                    }
                ]
            },
            {
                "data":{
                    "gid":"task_new",
                    "name":"Monthly Fire Drill Checklist - February",
                    "due_on":"2026-02-18"
                }
            },
        ]
        out = compile_asana_add_tag(prompt, observations)
        self.assertIsNotNone(out)
        self.assertIn("/tasks/task_new/addTag", out["arguments"]["url"])
        self.assertEqual(json.loads(out["arguments"]["body"]), {"tag":"Compliance"})
        self.assertEqual(out["grounding"]["tag"], "Compliance")

    def test_asana_add_tag_fails_closed_on_ambiguous_tag_labels(self):
        prompt = "Check what tag to use in Asana."
        observations = [
            {
                "id":"source1",
                "body_plain":"Create task: Safety Review. Due: 2026-02-18. Tag: Compliance."
            },
            {
                "id":"source2",
                "body_plain":"Create task: Safety Review. Due: 2026-02-18. Tag: Urgent."
            },
            {
                "data":{"gid":"task_new","name":"Safety Review","due_on":"2026-02-18"}
            },
        ]
        self.assertIsNone(compile_asana_add_tag(prompt, observations))

    def test_asana_add_tag_requires_matching_created_task(self):
        prompt = "Check what tag to use in Asana."
        observations = [
            {
                "id":"source",
                "body_plain":"Create task: Safety Review. Due: 2026-02-18. Tag: Compliance."
            },
            {
                "data":{"gid":"other","name":"Different Task","due_on":"2026-02-18"}
            },
        ]
        self.assertIsNone(compile_asana_add_tag(prompt, observations))

    def test_negative_prompt_guard_blocks_create(self):
        action = compile_asana_create_task(
            "Create the task in Asana project proj_facilities.",
            {"body_plain":"Create task: Safety Review. Due: 2026-02-18."},
        )
        self.assertIsNotNone(action)
        self.assertFalse(validate_nonnegative_action("Do not create any task.", action))


if __name__ == "__main__":
    unittest.main(verbosity=2)
