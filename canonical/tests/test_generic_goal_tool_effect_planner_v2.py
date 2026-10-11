from __future__ import annotations

import unittest

from canonical.runtime.generic_goal_tool_effect_planner_v2 import (
    build_planning_problem,
    plan_goal_over_tool_schemas,
)


class GenericGoalToolEffectPlannerV2Tests(unittest.TestCase):
    def test_update_requires_only_missing_record_identity(self):
        endpoints = [
            {
                "id":"objects.search",
                "method":"GET",
                "url":"https://opaque.invalid/objects",
                "description":"Search customer orders by name and status.",
                "response":"{records: [{id, name, status}]}",
            },
            {
                "id":"objects.modify",
                "method":"PATCH",
                "url":"https://opaque.invalid/orders/{id}",
                "description":"Update order status.",
                "parameters":{
                    "id":{"required":True,"location":"path","type":"string"}
                },
                "request":"{status?: string}",
                "response":"{id, name, status}",
            },
        ]
        out = plan_goal_over_tool_schemas(
            "Find the Acme order, then set the order status to closed.",
            endpoints,
        )
        self.assertTrue(out["pass"], out)
        roles = [x["role"] for x in out["steps"]]
        self.assertEqual(roles, ["observation", "mutation"])
        mutation = out["steps"][-1]
        self.assertEqual(mutation["required_evidence_semantics"], ["id"])
        self.assertIn("id", out["steps"][0]["response_semantics"])

    def test_literal_target_id_eliminates_unnecessary_observation(self):
        endpoints = [
            {
                "id":"objects.modify",
                "method":"PATCH",
                "url":"https://opaque.invalid/orders/{id}",
                "description":"Update order status.",
                "parameters":{
                    "id":{"required":True,"location":"path","type":"string"}
                },
                "request":"{status?: string}",
                "response":"{id, status}",
            }
        ]
        out = plan_goal_over_tool_schemas(
            "Set order ord_123 status to closed.",
            endpoints,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual([x["role"] for x in out["steps"]], ["mutation"])
        self.assertEqual(
            out["steps"][0]["required_evidence_semantics"],
            [],
        )

    def test_prior_text_observation_can_ground_created_identity(self):
        endpoints = [
            {
                "id":"inbox.lookup",
                "method":"GET",
                "url":"https://opaque.invalid/messages",
                "description":"Review work messages.",
                "response":"{messages: [{id, subject, body, date}]}",
            },
            {
                "id":"tasks.create",
                "method":"POST",
                "url":"https://opaque.invalid/tasks",
                "description":"Create task in a project.",
                "request":"{name?: string, due_on?: string, project?: string}",
                "response":"{id, name, due_on, project}",
            },
        ]
        out = plan_goal_over_tool_schemas(
            "Review the work message. Create the task in project proj_blue.",
            endpoints,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            [x["role"] for x in out["steps"]],
            ["observation", "mutation"],
        )
        self.assertIn(
            "name",
            out["steps"][1]["required_evidence_semantics"],
        )
        self.assertIn("text", out["steps"][0]["response_semantics"])

    def test_create_result_can_supply_id_for_later_association(self):
        endpoints = [
            {
                "id":"inbox.lookup",
                "method":"GET",
                "url":"https://opaque.invalid/messages",
                "description":"Review work messages.",
                "response":"{messages: [{id, subject, body, date}]}",
            },
            {
                "id":"sections.list",
                "method":"GET",
                "url":"https://opaque.invalid/projects/{project}/sections",
                "description":"List project sections.",
                "parameters":{
                    "project":{"required":True,"location":"path","type":"string"}
                },
                "response":"{data: [{gid, name, project}]}",
            },
            {
                "id":"tasks.create",
                "method":"POST",
                "url":"https://opaque.invalid/tasks",
                "description":"Create task in a project.",
                "request":"{name?: string, due_on?: string, project?: string}",
                "response":"{data: {gid, name, due_on, project}}",
            },
            {
                "id":"membership.add",
                "method":"POST",
                "url":"https://opaque.invalid/sections/{section_gid}/addTask",
                "description":"Add task to section membership.",
                "parameters":{
                    "section_gid":{"required":True,"location":"path","type":"string"}
                },
                "request":"{task: string}",
                "response":"{task, section}",
            },
        ]
        goal = (
            "Review the work message. "
            "Create the task in project proj_blue. "
            "Add the task to the February section."
        )
        out = plan_goal_over_tool_schemas(goal, endpoints)
        self.assertTrue(out["pass"], out)
        roles = [x["role"] for x in out["steps"]]
        self.assertEqual(roles.count("mutation"), 2)
        self.assertGreaterEqual(roles.count("observation"), 2)
        create_step = next(
            x for x in out["steps"]
            if x.get("endpoint_id") == "tasks.create"
        )
        associate_step = next(
            x for x in out["steps"]
            if x.get("endpoint_id") == "membership.add"
        )
        self.assertTrue(any(
            row["semantic"] == "task"
            for row in create_step["later_evidence"]
        ))
        self.assertIn(
            "section",
            associate_step["required_evidence_semantics"],
        )
        self.assertIn(
            "task",
            associate_step["required_evidence_semantics"],
        )

    def test_unrelated_text_read_cannot_ground_mutation_without_prior_observe_intent(self):
        endpoints = [
            {
                "id":"random.read",
                "method":"GET",
                "url":"https://opaque.invalid/chatter",
                "description":"Read unrelated chatter messages.",
                "response":"{messages: [{id, body}]}",
            },
            {
                "id":"tasks.create",
                "method":"POST",
                "url":"https://opaque.invalid/tasks",
                "description":"Create task in a project.",
                "request":"{name?: string, project?: string}",
                "response":"{id, name}",
            },
        ]
        out = plan_goal_over_tool_schemas(
            "Create the task in project proj_blue.",
            endpoints,
        )
        self.assertFalse(out["pass"])
        self.assertIn("UNREACHABLE_TARGET_EFFECTS", out["reason"])

    def test_surface_renaming_preserves_field_dependency_shape(self):
        a = [
            {
                "id":"alpha.lookup",
                "method":"GET",
                "url":"https://a.invalid/orders",
                "description":"Search shipment orders.",
                "response":"{records:[{id,name,status}]}",
            },
            {
                "id":"alpha.patch",
                "method":"PATCH",
                "url":"https://a.invalid/orders/{id}",
                "description":"Update shipment status.",
                "parameters":{"id":{"required":True,"location":"path"}},
                "request":"{status?: string}",
                "response":"{id,status}",
            },
        ]
        b = [
            {
                "id":"z9.q",
                "method":"GET",
                "url":"https://z.invalid/query",
                "description":"Find shipment orders.",
                "response":"{items:[{key,title,state}]}",
            },
            {
                "id":"z9.m",
                "method":"PATCH",
                "url":"https://z.invalid/resource/{key}",
                "description":"Change shipment state.",
                "parameters":{"key":{"required":True,"location":"path"}},
                "request":"{state?: string}",
                "response":"{key,state}",
            },
        ]
        goal = "Find the shipment order, then set the shipment status to delivered."
        pa = plan_goal_over_tool_schemas(goal, a)
        pb = plan_goal_over_tool_schemas(goal, b)
        self.assertTrue(pa["pass"], pa)
        self.assertTrue(pb["pass"], pb)
        self.assertEqual(
            [x["role"] for x in pa["steps"]],
            [x["role"] for x in pb["steps"]],
        )
        self.assertEqual(
            pa["steps"][-1]["required_evidence_semantics"],
            pb["steps"][-1]["required_evidence_semantics"],
        )

    def test_problem_contains_no_vendor_or_benchmark_literals_from_engine(self):
        endpoints = [
            {
                "id":"opaque.lookup",
                "method":"GET",
                "url":"https://opaque.invalid/items",
                "description":"Find order items.",
                "response":"{items:[{id,name}]}",
            },
            {
                "id":"opaque.modify",
                "method":"PATCH",
                "url":"https://opaque.invalid/items/{id}",
                "description":"Update order status.",
                "parameters":{"id":{"required":True,"location":"path"}},
                "request":"{status?: string}",
            },
        ]
        built = build_planning_problem(
            "Find the order, then set the order status to closed.",
            endpoints,
        )
        blob = str(built).lower()
        self.assertNotIn("salesforce", blob)
        self.assertNotIn("asana", blob)
        self.assertNotIn("automationbench", blob)


    def test_operation_trigger_breaks_same_resource_notify_tie(self):
        endpoints = [
            {
                "id":"opaque.messages.send",
                "method":"POST",
                "url":"https://opaque.invalid/messages/send",
                "description":"Send a message to a channel.",
            },
            {
                "id":"opaque.messages.postMessage",
                "method":"POST",
                "url":"https://opaque.invalid/messages/postMessage",
                "description":"Post a message to a channel.",
            },
        ]
        out = plan_goal_over_tool_schemas(
            "Post the result to #ops-room.",
            endpoints,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["mutation_endpoint_ids"],
            ["opaque.messages.postMessage"],
        )

    def test_rare_resource_specificity_breaks_generic_overlap_tie(self):
        endpoints = [
            {
                "id":"generic.customer.update",
                "method":"PATCH",
                "url":"https://opaque.invalid/customers/{id}",
                "description":"Update customer alpha status.",
            },
            {
                "id":"specific.customer.update",
                "method":"PATCH",
                "url":"https://opaque.invalid/specific/{id}",
                "description":"Update customer beta status.",
            },
            {
                "id":"generic.customer.extra1",
                "method":"GET",
                "url":"https://opaque.invalid/a1",
                "description":"Read alpha customer.",
            },
            {
                "id":"generic.customer.extra2",
                "method":"GET",
                "url":"https://opaque.invalid/a2",
                "description":"Read alpha customer.",
            },
            {
                "id":"generic.customer.extra3",
                "method":"GET",
                "url":"https://opaque.invalid/a3",
                "description":"Read alpha customer.",
            },
        ]
        out = plan_goal_over_tool_schemas(
            "Update the customer alpha beta status to active.",
            endpoints,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["mutation_endpoint_ids"],
            ["specific.customer.update"],
        )

    def test_ungrounded_required_read_parameter_is_not_zero_cost_observation(self):
        endpoints = [
            {
                "id":"records.search",
                "method":"GET",
                "url":"https://opaque.invalid/records/search",
                "description":"Search customer records.",
                "parameters":{
                    "query":{"required":True,"type":"string"}
                },
                "response":"{records:[{id,name}]}",
            },
            {
                "id":"records.list",
                "method":"GET",
                "url":"https://opaque.invalid/records",
                "description":"List customer records.",
                "response":"{records:[{id,name}]}",
            },
        ]
        out = plan_goal_over_tool_schemas(
            "Review the customer records.",
            endpoints,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["observation_endpoint_ids"], ["records.list"])


    def test_endpoint_object_identity_beats_incidental_field_vocabulary(self):
        endpoints = [
            {
                "id":"opaque.objects.lead.update",
                "method":"PATCH",
                "url":"https://opaque.invalid/objects/lead/{id}",
                "description":"Update lead fields.",
                "parameters":{"id":{"required":True,"location":"path"}},
                "request":"Lead fields to update: {Status, Description}",
            },
            {
                "id":"opaque.objects.contact.update",
                "method":"PATCH",
                "url":"https://opaque.invalid/objects/contact/{id}",
                "description":"Update contact fields.",
                "parameters":{"id":{"required":True,"location":"path"}},
                "request":"Contact fields to update: {LeadSource, Description}",
            },
            {
                "id":"opaque.objects.lead.list",
                "method":"GET",
                "url":"https://opaque.invalid/objects/lead",
                "description":"List lead records with id and status.",
                "response":"{records:[{id,status}]}",
            },
        ]
        out = plan_goal_over_tool_schemas(
            "Find the cobalt lead, then update the lead status to active.",
            endpoints,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["mutation_endpoint_ids"],
            ["opaque.objects.lead.update"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
