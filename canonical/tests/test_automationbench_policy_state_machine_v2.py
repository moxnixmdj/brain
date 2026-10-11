from __future__ import annotations

import json
import unittest

from canonical.runtime.automationbench_policy_state_machine_v2 import next_policy_action


def search_history(endpoints):
    return [{
        "kind":"tool_result",
        "name":"api_search",
        "content":json.dumps({"results":endpoints}),
    }]


class AutomationBenchPolicyStateMachineV2Tests(unittest.TestCase):
    def setUp(self):
        self.endpoints = [
            {
                "id":"objects.search",
                "method":"GET",
                "url":"https://opaque.invalid/orders",
                "description":"Search shipment orders by name and status.",
                "response":"{records:[{id,name,status}]}",
            },
            {
                "id":"objects.modify",
                "method":"PATCH",
                "url":"https://opaque.invalid/orders/{id}",
                "description":"Update shipment order status.",
                "parameters":{
                    "id":{"required":True,"location":"path","type":"string"}
                },
                "request":"{status?: string}",
                "response":"{id,name,status}",
            },
        ]
        self.goal = "Find the Acme shipment order, then set the shipment status to delivered."

    def test_full_generic_observe_mutate_verify_loop(self):
        history = search_history(self.endpoints)

        observe = next_policy_action(prompt=self.goal, history=history)
        self.assertEqual(observe["phase"], "OBSERVE_STATE")
        self.assertEqual(observe["planner_mode"], "GENERIC_FIELD_LEVEL_WORKFLOW_V2")
        self.assertEqual(observe["calls"][0]["arguments"]["method"], "GET")
        observe_semantic = observe["semantic"]

        history.extend([
            {
                "kind":"assistant_state",
                "metadata":{
                    "project_brain/automationbench_semantic":observe_semantic
                },
            },
            {
                "kind":"tool_result",
                "name":"api_fetch",
                "content":json.dumps({
                    "records":[
                        {"id":"ord_1","name":"Acme shipment order","status":"pending"}
                    ]
                }),
            },
        ])

        mutate = next_policy_action(prompt=self.goal, history=history)
        self.assertEqual(mutate["phase"], "MUTATE")
        self.assertEqual(mutate["calls"][0]["arguments"]["method"], "PATCH")
        self.assertIn("/orders/ord_1", mutate["calls"][0]["arguments"]["url"])
        mutate_semantic = mutate["semantic"]

        history.extend([
            {
                "kind":"assistant_state",
                "metadata":{
                    "project_brain/automationbench_semantic":mutate_semantic
                },
            },
            {
                "kind":"tool_result",
                "name":"api_fetch",
                "content":json.dumps({
                    "id":"ord_1",
                    "name":"Acme shipment order",
                    "status":"delivered",
                }),
            },
        ])

        verify = next_policy_action(prompt=self.goal, history=history)
        self.assertEqual(verify["phase"], "VERIFY_STATE")
        self.assertTrue(verify["calls"])
        self.assertTrue(all(
            call["arguments"]["method"] == "GET"
            for call in verify["calls"]
        ))
        verify_semantic = verify["semantic"]

        history.extend([
            {
                "kind":"assistant_state",
                "metadata":{
                    "project_brain/automationbench_semantic":verify_semantic
                },
            },
            {
                "kind":"tool_result",
                "name":"api_fetch",
                "content":json.dumps({
                    "records":[
                        {"id":"ord_1","name":"Acme shipment order","status":"delivered"}
                    ]
                }),
            },
        ])

        done = next_policy_action(prompt=self.goal, history=history)
        self.assertEqual(done["status"], "DONE_VERIFIED")
        self.assertEqual(done["phase"], "COMPLETE")
        self.assertTrue(done["verification"]["pass"])

    def test_tool_error_does_not_advance_plan_step(self):
        history = search_history(self.endpoints)
        observe = next_policy_action(prompt=self.goal, history=history)
        history.extend([
            {
                "kind":"assistant_state",
                "metadata":{
                    "project_brain/automationbench_semantic":observe["semantic"]
                },
            },
            {
                "kind":"tool_result",
                "name":"api_fetch",
                "content":json.dumps({
                    "error":{"code":500,"message":"simulated failure"}
                }),
            },
        ])
        out = next_policy_action(prompt=self.goal, history=history)
        self.assertEqual(out["status"], "NEEDS_POLICY_EXTENSION")
        self.assertEqual(out["phase"], "REPLAN")
        self.assertEqual(out["reason"], "GENERIC_PLAN_STEP_TOOL_ERROR")

    def test_constraint_only_goal_requires_and_uses_post_state_evidence(self):
        endpoints = [
            {
                "id":"orders.search",
                "method":"GET",
                "url":"https://opaque.invalid/orders",
                "description":"Search customer orders.",
                "response":"{records:[{id,name,status}]}",
            },
            {
                "id":"orders.delete",
                "method":"DELETE",
                "url":"https://opaque.invalid/orders/{id}",
                "description":"Delete customer order.",
                "parameters":{
                    "id":{"required":True,"location":"path","type":"string"}
                },
            },
        ]
        goal = "Do not delete the Acme order."
        history = search_history(endpoints)
        verify = next_policy_action(prompt=goal, history=history)
        self.assertEqual(verify["phase"], "VERIFY_CONSTRAINTS")
        self.assertTrue(verify["calls"])
        semantic = verify["semantic"]
        history.extend([
            {
                "kind":"assistant_state",
                "metadata":{
                    "project_brain/automationbench_semantic":semantic
                },
            },
            {
                "kind":"tool_result",
                "name":"api_fetch",
                "content":json.dumps({
                    "records":[
                        {"id":"ord_1","name":"Acme order","status":"open"}
                    ]
                }),
            },
        ])
        done = next_policy_action(prompt=goal, history=history)
        self.assertEqual(done["status"], "DONE_VERIFIED")
        self.assertTrue(done["verification"]["constraint_results"][0]["verified"])

    def test_no_application_specific_fallback_is_used(self):
        history = search_history([
            {
                "id":"catalog.read",
                "method":"GET",
                "url":"https://opaque.invalid/widgets",
                "description":"List widgets.",
                "response":"{items:[{id,name}]}",
            }
        ])
        out = next_policy_action(
            prompt="Delete the widget.",
            history=history,
        )
        self.assertEqual(out["status"], "NEEDS_POLICY_EXTENSION")
        self.assertEqual(out["planner_mode"], "GENERIC_FIELD_LEVEL_WORKFLOW_V2")
        self.assertNotIn("fallback", str(out).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
