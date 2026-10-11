from __future__ import annotations

import json
import unittest

from canonical.runtime.automationbench_policy_state_machine_v1 import next_policy_action


class GenericWorkflowClosedLoopV1Tests(unittest.TestCase):
    def test_renamed_update_flow_reobserves_then_verifies(self):
        goal = "Find the Acme shipment, then set the shipment status to delivered."
        search = {
            "results":[
                {
                    "id":"opaque.lookup",
                    "method":"GET",
                    "url":"https://opaque.invalid/shipments",
                    "description":"Find shipment orders and delivery status.",
                    "parameters":{}
                },
                {
                    "id":"opaque.modify",
                    "method":"PATCH",
                    "url":"https://opaque.invalid/shipments/{id}",
                    "description":"Update shipment delivery status.",
                    "parameters":{
                        "id":{"required":True,"location":"path","type":"string"}
                    },
                    "request":"{status?: string}"
                }
            ]
        }
        history = [
            {"kind":"tool_result","name":"api_search","content":json.dumps(search)},
            {
                "kind":"tool_result","name":"api_fetch",
                "content":json.dumps({
                    "records":[
                        {"id":"shp_123","name":"Acme shipment","status":"pending"}
                    ]
                }),
            },
        ]

        mutate = next_policy_action(prompt=goal, history=history)
        self.assertEqual(mutate["binder_mode"], "GENERIC_SCHEMA_DRIVEN_ARGUMENT_BINDER")
        self.assertEqual(mutate["calls"][0]["arguments"]["method"], "PATCH")
        self.assertIn("/shipments/shp_123", mutate["calls"][0]["arguments"]["url"])
        self.assertEqual(
            json.loads(mutate["calls"][0]["arguments"]["body"])["status"],
            "delivered",
        )

        history += [
            {
                "kind":"assistant_state",
                "metadata":{
                    "project_brain/automationbench_semantic":mutate["semantic"]
                },
            },
            {
                "kind":"tool_result","name":"api_fetch",
                "content":json.dumps({
                    "id":"shp_123","name":"Acme shipment","status":"delivered"
                }),
            },
        ]
        verify_request = next_policy_action(prompt=goal, history=history)
        self.assertEqual(verify_request["phase"], "VERIFY_STATE")
        self.assertEqual(verify_request["calls"][0]["arguments"]["method"], "GET")

        history += [
            {
                "kind":"assistant_state",
                "metadata":{
                    "project_brain/automationbench_semantic":
                        verify_request["semantic"]
                },
            },
            {
                "kind":"tool_result","name":"api_fetch",
                "content":json.dumps({
                    "records":[
                        {"id":"shp_123","name":"Acme shipment","status":"delivered"}
                    ]
                }),
            },
        ]
        done = next_policy_action(prompt=goal, history=history)
        self.assertEqual(done["status"], "DONE_VERIFIED")
        self.assertTrue(done["verification"]["pass"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
