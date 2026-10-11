from __future__ import annotations

import inspect
import json
import unittest

import canonical.runtime.automationbench_policy_state_machine_v3 as state_machine_v3
from canonical.runtime.automationbench_policy_state_machine_v3 import next_policy_action


def search_history(endpoints):
    return [{
        "kind":"tool_result",
        "name":"api_search",
        "content":json.dumps({"results":endpoints}),
    }]


class AutomationBenchPolicyStateMachineV3Tests(unittest.TestCase):
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

    def test_discovery_phase_uses_generic_query_generator(self):
        out = next_policy_action(
            prompt="Find the cobalt shipment and update the status to complete.",
            history=[],
        )
        self.assertEqual(out["phase"], "DISCOVER_ENDPOINTS")
        queries = [x["arguments"]["query"] for x in out["calls"]]
        joined = " | ".join(queries)
        self.assertIn("shipment", joined)
        self.assertTrue("update" in joined or "patch" in joined)
        self.assertNotIn("gmail", joined.lower())
        self.assertNotIn("salesforce", joined.lower())
        self.assertNotIn("asana", joined.lower())

    def test_full_generic_observe_mutate_verify_loop(self):
        history = search_history(self.endpoints)

        observe = next_policy_action(prompt=self.goal, history=history)
        self.assertEqual(observe["phase"], "OBSERVE_STATE")
        self.assertEqual(observe["planner_mode"], "GENERIC_FIELD_LEVEL_WORKFLOW_V3")
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

    def test_v2_source_has_no_legacy_app_specific_compiler_import(self):
        source = inspect.getsource(state_machine_v3)
        self.assertNotIn("automationbench_mutation_compiler_v1", source)
        self.assertNotIn("automationbench_owned_policy_kernel_v1", source)
        self.assertNotIn("compile_salesforce", source)
        self.assertNotIn("compile_asana", source)

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
        self.assertEqual(out["planner_mode"], "GENERIC_FIELD_LEVEL_WORKFLOW_V3")
        self.assertNotIn("fallback", str(out).lower())


    def test_constraint_only_nondelete_completes_from_empty_mutation_trace(self):
        out = next_policy_action(
            prompt="Do not create the cobalt widget.",
            history=[],
        )
        self.assertEqual(out["status"], "DONE_VERIFIED")
        self.assertEqual(out["phase"], "COMPLETE")
        self.assertEqual(out["completion_basis"], "COMPLETE_EMPTY_MUTATION_TRACE")
        self.assertTrue(out["verification"]["constraint_results"][0]["verified"])

    def test_constraint_only_delete_keeps_strong_state_verification(self):
        out = next_policy_action(
            prompt="Do not delete order ord_100.",
            history=[],
        )
        self.assertEqual(out["phase"], "DISCOVER_ENDPOINTS")
        self.assertEqual(out["status"], "CALL_TOOLS")

    def test_ambiguous_mixed_forbidden_update_blocks_before_mutation(self):
        endpoints = [
            {
                "id":"objects.search",
                "method":"GET",
                "url":"https://opaque.invalid/customers",
                "description":"Search customer records by name and status.",
                "response":"{records:[{id,name,status}]}",
            },
            {
                "id":"objects.modify",
                "method":"PATCH",
                "url":"https://opaque.invalid/customers/{id}",
                "description":"Update customer record status.",
                "parameters":{
                    "id":{"required":True,"location":"path","type":"string"}
                },
                "request":"{status?: string}",
                "response":"{id,name,status}",
            },
        ]
        goal = (
            "Find the cobalt customer record, then set the customer status to active. "
            "Do not update the cobalt customer record."
        )
        history = search_history(endpoints)
        observe = next_policy_action(prompt=goal, history=history)
        self.assertEqual(observe["phase"], "OBSERVE_STATE")
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
                    "records":[
                        {"id":"cust_1","name":"cobalt customer record","status":"pending"}
                    ]
                }),
            },
        ])
        blocked = next_policy_action(prompt=goal, history=history)
        self.assertEqual(blocked["phase"], "CONSTRAINT_GUARD")
        self.assertEqual(blocked["status"], "NEEDS_POLICY_EXTENSION")
        self.assertEqual(
            blocked["reason"],
            "POTENTIAL_FORBIDDEN_ACTION_CONFLICT",
        )

    def test_v3_source_uses_trace_verifier_and_generic_constraint_guard(self):
        source = inspect.getsource(state_machine_v3)
        self.assertIn("generic_goal_state_verifier_v3", source)
        self.assertIn("generic_goal_constraint_guard_v1", source)
        self.assertNotIn("generic_goal_state_verifier_v2", source)
        self.assertNotIn("automationbench_owned_policy_kernel_v1", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
