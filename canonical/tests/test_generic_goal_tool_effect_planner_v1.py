from __future__ import annotations

import unittest

from canonical.runtime.generic_goal_tool_effect_planner_v1 import (
    compile_goal_contract,
    plan_goal_over_tool_schemas,
    profile_endpoint,
)


class GenericGoalToolEffectPlannerV1Tests(unittest.TestCase):
    def test_renamed_crm_find_then_update_plans_observe_then_mutate(self):
        endpoints = [
            {
                "id":"nebula.object.search",
                "method":"GET",
                "url":"https://nebula.invalid/v1/objects",
                "description":"Search customer opportunities by name and status.",
                "parameters":{"q":{"type":"string"}},
            },
            {
                "id":"nebula.object.modify",
                "method":"PATCH",
                "url":"https://nebula.invalid/v1/opportunities/{id}",
                "description":"Update fields on an opportunity including status and stage.",
                "parameters":{"id":{"required":True}},
                "request":"{status?: string, stage?: string}",
            },
        ]
        out = plan_goal_over_tool_schemas(
            "Find the Acme opportunity, then set the opportunity status to closed.",
            endpoints,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            [x["role"] for x in out["steps"]],
            ["observation", "mutation"],
        )
        self.assertEqual(out["steps"][1]["endpoint_id"], "nebula.object.modify")

    def test_surface_renaming_does_not_change_underlying_plan_shape(self):
        a = [
            {
                "id":"alpha.lookup",
                "method":"GET",
                "url":"https://a.invalid/things",
                "description":"Search shipment orders and delivery status.",
            },
            {
                "id":"alpha.patch",
                "method":"PATCH",
                "url":"https://a.invalid/shipments/{id}",
                "description":"Update shipment delivery status.",
            },
        ]
        b = [
            {
                "id":"z9.q",
                "method":"GET",
                "url":"https://z.invalid/query",
                "description":"Find shipment orders and delivery status.",
            },
            {
                "id":"z9.m",
                "method":"PATCH",
                "url":"https://z.invalid/resource/{key}",
                "description":"Change shipment delivery status.",
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

    def test_association_goal_uses_observation_then_association_endpoint(self):
        endpoints = [
            {
                "id":"work.sections.list",
                "method":"GET",
                "url":"https://work.invalid/projects/{project}/sections",
                "description":"List project sections and section identifiers.",
            },
            {
                "id":"work.membership.add",
                "method":"POST",
                "url":"https://work.invalid/sections/{section}/addTask",
                "description":"Add task to section membership.",
                "request":"{task: string}",
            },
        ]
        out = plan_goal_over_tool_schemas(
            "Add the task to the February section.",
            endpoints,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            [x["role"] for x in out["steps"]],
            ["observation", "mutation"],
        )
        self.assertEqual(out["steps"][1]["action_class"], "associate")

    def test_negated_ambiguous_action_words_compile_as_forbidden_verbs(self):
        for clause, action in (
            ("Do not update the customer record.", "update"),
            ("Never record the customer note.", "create"),
            ("Do not message the customer.", "notify"),
            ("Do not archive the customer record.", "delete"),
        ):
            out = compile_goal_contract(clause)
            forbidden = [
                x for x in out["intents"]
                if x["forbidden"] and x["action_class"] == action
            ]
            self.assertEqual(len(forbidden), 1, (clause, out))

    def test_negative_instruction_is_constraint_not_target(self):
        endpoints = [
            {
                "id":"ledger.read",
                "method":"GET",
                "url":"https://ledger.invalid/invoices",
                "description":"Review invoice records.",
            },
            {
                "id":"ledger.delete",
                "method":"DELETE",
                "url":"https://ledger.invalid/invoices/{id}",
                "description":"Delete an invoice record.",
            },
        ]
        contract = compile_goal_contract(
            "Do not delete the invoice. Review the invoice."
        )
        self.assertEqual(len(contract["forbidden_intent_ids"]), 1)
        out = plan_goal_over_tool_schemas(
            "Do not delete the invoice. Review the invoice.",
            endpoints,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["mutation_endpoint_ids"], [])
        self.assertEqual(out["observation_endpoint_ids"], ["ledger.read"])

    def test_status_is_not_mangled_by_singularizer(self):
        p = profile_endpoint({
            "id":"x.read",
            "method":"GET",
            "url":"https://x.invalid/orders",
            "description":"Read order status analysis and shipments.",
        })
        self.assertIn("status", p["resource_terms"])
        self.assertIn("analysis", p["resource_terms"])
        self.assertIn("shipment", p["resource_terms"])
        self.assertNotIn("statu", p["resource_terms"])

    def test_noun_mentions_do_not_spawn_phantom_actions(self):
        contract = compile_goal_contract(
            "Review the work message. Find the invoice record. Check the schedule."
        )
        actions = [x["action_class"] for x in contract["intents"]]
        self.assertEqual(actions, ["observe", "observe", "observe"])
        self.assertNotIn("notify", actions)
        self.assertNotIn("create", actions)

    def test_ambiguous_action_words_still_work_as_imperative_verbs(self):
        contract = compile_goal_contract(
            "Message the operations team. Record the result. List the open orders."
        )
        actions = [x["action_class"] for x in contract["intents"]]
        self.assertIn("notify", actions)
        self.assertIn("create", actions)
        self.assertIn("observe", actions)

    def test_missing_required_effect_fails_closed(self):
        endpoints = [
            {
                "id":"catalog.read",
                "method":"GET",
                "url":"https://catalog.invalid/widgets",
                "description":"List widgets.",
            }
        ]
        out = plan_goal_over_tool_schemas(
            "Delete the widget.",
            endpoints,
        )
        self.assertFalse(out["pass"])
        self.assertIn("UNREACHABLE_TARGET_EFFECTS", out["reason"])

    def test_profile_is_schema_driven_not_vendor_driven(self):
        p = profile_endpoint({
            "id":"opaque.17",
            "method":"POST",
            "url":"https://opaque.invalid/r/17",
            "description":"Attach member to team.",
            "request":"{member: string}",
        })
        self.assertEqual(p["action_class"], "associate")
        self.assertIn("member", p["resource_terms"])
        self.assertIn("team", p["resource_terms"])

    def test_tied_top_mutation_routes_fail_closed(self):
        endpoints = [
            {
                "id":"lookup",
                "method":"GET",
                "url":"https://x.invalid/orders",
                "description":"Find order status.",
            },
            {
                "id":"mutate.a",
                "method":"PATCH",
                "url":"https://x.invalid/orders/{id}",
                "description":"Update order status.",
            },
            {
                "id":"mutate.b",
                "method":"PATCH",
                "url":"https://y.invalid/orders/{id}",
                "description":"Update order status.",
            },
        ]
        out = plan_goal_over_tool_schemas(
            "Find the order, then set the order status to closed.",
            endpoints,
        )
        self.assertFalse(out["pass"])
        self.assertEqual(out["reason"], "AMBIGUOUS_TOP_TOOL_EFFECT_ROUTE")
        self.assertEqual(
            out["route_ambiguities"][0]["endpoint_ids"],
            ["mutate.a", "mutate.b"],
        )

    def test_create_requires_grounding_observation_before_mutation(self):
        endpoints = [
            {
                "id":"inventory.lookup",
                "method":"GET",
                "url":"https://inventory.invalid/items",
                "description":"Search inventory items and warehouse bins.",
            },
            {
                "id":"inventory.create",
                "method":"POST",
                "url":"https://inventory.invalid/items",
                "description":"Create inventory item in a warehouse bin.",
                "request":"{name: string, bin: string}",
            },
        ]
        out = plan_goal_over_tool_schemas(
            "Create the inventory item in the warehouse bin.",
            endpoints,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            [x["role"] for x in out["steps"]],
            ["observation", "mutation"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
