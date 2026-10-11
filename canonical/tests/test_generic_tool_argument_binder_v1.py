from __future__ import annotations

import json
import unittest

from canonical.runtime.generic_tool_argument_binder_v1 import (
    bind_endpoint_call,
    canonical_field,
    extract_records,
    endpoint_grounding_contract,
)


class GenericToolArgumentBinderV1Tests(unittest.TestCase):
    def test_generic_update_binds_record_id_and_explicit_status(self):
        endpoint = {
            "id":"opaque.modify",
            "method":"PATCH",
            "url":"https://opaque.invalid/shipments/{id}",
            "description":"Update shipment delivery status.",
            "parameters":{
                "id":{"required":True,"location":"path","type":"string"}
            },
            "request":"{status?: string}",
        }
        observations = [{
            "records":[
                {"id":"shp_123","name":"Acme shipment","status":"pending"},
                {"id":"shp_999","name":"Other shipment","status":"pending"},
            ]
        }]
        out = bind_endpoint_call(
            goal="Set the Acme shipment status to delivered.",
            endpoint=endpoint,
            observations=observations,
        )
        self.assertTrue(out["pass"], out)
        self.assertIn("/shipments/shp_123", out["arguments"]["url"])
        self.assertEqual(
            json.loads(out["arguments"]["body"])["status"],
            "delivered",
        )

    def test_generic_create_uses_observed_key_value_facts_and_goal_id(self):
        endpoint = {
            "id":"work.tasks.create",
            "method":"POST",
            "url":"https://work.invalid/tasks",
            "description":"Create task in a project.",
            "request":(
                "Body: {name (optional, string), due_on (optional, YYYY-MM-DD), "
                "projects (optional, array of project GIDs)}"
            ),
        }
        observations = [{
            "message":{
                "id":"msg_1",
                "body":"Create task: Safety Review. Due: 2026-12-01."
            }
        }]
        out = bind_endpoint_call(
            goal="Create the task in project proj_blue.",
            endpoint=endpoint,
            observations=observations,
        )
        self.assertTrue(out["pass"], out)
        body = json.loads(out["arguments"]["body"])
        self.assertEqual(body["name"], "Safety Review")
        self.assertEqual(body["due_on"], "2026-12-01")
        self.assertEqual(body["projects"], ["proj_blue"])

    def test_generic_association_disambiguates_section_and_created_task(self):
        endpoint = {
            "id":"work.membership.add",
            "method":"POST",
            "url":"https://work.invalid/sections/{section_gid}/addTask",
            "description":"Add task to section membership.",
            "parameters":{
                "section_gid":{"required":True,"location":"path","type":"string"}
            },
            "request":"Body: {task (required, string)}",
        }
        observations = [
            {
                "source":{
                    "id":"msg_1",
                    "body":"Create task: Safety Review. Due: 2026-12-01."
                }
            },
            {
                "sections":[
                    {"gid":"sec_feb","name":"February"},
                    {"gid":"sec_mar","name":"March"},
                ]
            },
            {
                "created":{"gid":"task_new","name":"Safety Review","due_on":"2026-12-01"}
            },
        ]
        out = bind_endpoint_call(
            goal="Add the task to the February section.",
            endpoint=endpoint,
            observations=observations,
        )
        self.assertTrue(out["pass"], out)
        self.assertIn("/sections/sec_feb/addTask", out["arguments"]["url"])
        self.assertEqual(json.loads(out["arguments"]["body"])["task"], "task_new")

    def test_grounding_contract_exposes_only_missing_required_evidence(self):
        endpoint = {
            "id":"opaque.modify",
            "method":"PATCH",
            "url":"https://opaque.invalid/orders/{id}",
            "parameters":{
                "id":{"required":True,"location":"path","type":"string"}
            },
            "request":"{status?: string}",
        }
        out = endpoint_grounding_contract(
            goal="Set the Acme order status to closed.",
            endpoint=endpoint,
        )
        self.assertEqual(out["required_evidence_semantics"], ["id"])
        self.assertIn("status", out["goal_grounded_semantics"])

    def test_create_optional_name_becomes_identity_grounding_obligation(self):
        endpoint = {
            "id":"opaque.create",
            "method":"POST",
            "url":"https://opaque.invalid/tasks",
            "request":"{name?: string, due_on?: string, project?: string}",
        }
        out = endpoint_grounding_contract(
            goal="Create the task in project proj_blue.",
            endpoint=endpoint,
        )
        self.assertIn("name", out["required_evidence_semantics"])
        self.assertIn("project", out["goal_grounded_semantics"])

    def test_required_unknown_body_field_fails_closed(self):
        endpoint = {
            "id":"opaque.create",
            "method":"POST",
            "url":"https://opaque.invalid/widgets",
            "description":"Create widget.",
            "request":"{secret_code: string}",
        }
        out = bind_endpoint_call(
            goal="Create the widget.",
            endpoint=endpoint,
            observations=[],
        )
        self.assertFalse(out["pass"])
        self.assertIn("REQUIRED_BODY_FIELD_UNGROUNDED", out["reason"])

    def test_required_default_path_parameter_uses_declared_default(self):
        endpoint = {
            "id":"mail.list",
            "method":"GET",
            "url":"https://mail.invalid/users/{userId}/messages",
            "description":"List messages.",
            "parameters":{
                "userId":{
                    "required":True,
                    "location":"path",
                    "default":"me",
                    "type":"string",
                }
            },
        }
        out = bind_endpoint_call(
            goal="Review messages.",
            endpoint=endpoint,
            observations=[],
        )
        self.assertTrue(out["pass"], out)
        self.assertIn("/users/me/messages", out["arguments"]["url"])

    def test_field_semantics_are_generic(self):
        self.assertEqual(canonical_field("StageName"), "status")
        self.assertEqual(canonical_field("project_gid"), "project")
        self.assertEqual(canonical_field("due_on"), "date")

    def test_record_extraction_is_recursive_and_deduplicated(self):
        observations = [{
            "data":{
                "items":[
                    {"id":"x_1","name":"X"},
                    {"id":"x_1","name":"X"},
                ]
            }
        }]
        rows = extract_records(observations)
        ids = [r.get("id") for r in rows if r.get("id")]
        self.assertEqual(ids.count("x_1"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
