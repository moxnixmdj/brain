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


    def test_discourse_make_sure_does_not_create_phantom_intent(self):
        out = compile_goal_contract(
            "Make sure you're following the latest guidelines before starting."
        )
        self.assertEqual(out["intents"], [], out)
        self.assertEqual(out["status"], "UNRESOLVED")

    def test_abstract_apply_is_not_association_but_relation_apply_is(self):
        abstract = compile_goal_contract("Apply our current market analysis methodology.")
        self.assertEqual(abstract["intents"], [], abstract)
        concrete = compile_goal_contract("Apply the compliance tag to the customer.")
        self.assertEqual(
            [x["action_class"] for x in concrete["intents"]],
            ["associate"],
        )

    def test_same_class_actions_in_one_clause_are_preserved_with_local_resources(self):
        out = compile_goal_contract(
            "Log the invoice in the tracker and create the support ticket."
        )
        creates = [x for x in out["intents"] if x["action_class"] == "create"]
        self.assertEqual(len(creates), 2, out)
        self.assertIn("invoice", creates[0]["resource_terms"])
        self.assertNotIn("ticket", creates[0]["resource_terms"])
        self.assertIn("ticket", creates[1]["resource_terms"])

    def test_action_local_scope_separates_create_and_update_objects(self):
        out = compile_goal_contract(
            "Match the requester, create the case with web origin, and set case priority high."
        )
        create_intent = next(x for x in out["intents"] if x["action_class"] == "create")
        update_intent = next(x for x in out["intents"] if x["action_class"] == "update")
        self.assertIn("case", create_intent["resource_terms"])
        self.assertNotIn("priority", create_intent["resource_terms"])
        self.assertIn("priority", update_intent["resource_terms"])

    def test_post_to_channel_is_notification(self):
        out = compile_goal_contract("Post the approved positions to #hiring-updates.")
        self.assertEqual(
            [x["action_class"] for x in out["intents"]],
            ["notify"],
        )
        self.assertIn("channel", out["intents"][0]["resource_terms"])

    def test_email_address_exposes_email_routing_semantic(self):
        out = compile_goal_contract("Send the analysis to ceo@company.example.com.")
        self.assertEqual(out["intents"][0]["action_class"], "notify")
        self.assertIn("email", out["intents"][0]["resource_terms"])
        for noise in ("company", "example", "com"):
            self.assertNotIn(noise, out["intents"][0]["resource_terms"])

    def test_endpoint_operation_name_can_override_http_method(self):
        cases = [
            (
                {
                    "id":"opaque.records.search",
                    "method":"POST",
                    "url":"https://opaque.invalid/records/search",
                    "description":"Search records.",
                },
                "observe",
            ),
            (
                {
                    "id":"opaque.items.batchUpdate",
                    "method":"POST",
                    "url":"https://opaque.invalid/items:batchUpdate",
                    "description":"Batch update items.",
                },
                "update",
            ),
            (
                {
                    "id":"opaque.requests.create",
                    "method":"PUT",
                    "url":"https://opaque.invalid/requests/create",
                    "description":"Create a request.",
                },
                "create",
            ),
        ]
        for endpoint, expected in cases:
            self.assertEqual(profile_endpoint(endpoint)["action_class"], expected)

    def test_common_discourse_tokens_do_not_drive_resource_overlap(self):
        out = compile_goal_contract(
            "We just closed the cobalt deal; mark it as won."
        )
        update = next(x for x in out["intents"] if x["action_class"] == "update")
        for noise in ("we", "just"):
            self.assertNotIn(noise, update["resource_terms"])
        self.assertIn("deal", update["resource_terms"])



    def test_compound_identity_preserves_whole_and_atoms(self):
        contract = compile_goal_contract(
            "Find the NovaGraph customer and update its batchUpdate status."
        )
        resources = {
            token
            for intent in contract["intents"]
            for token in intent["resource_terms"]
        }
        self.assertIn("novagraph", resources)
        self.assertIn("nova", resources)
        self.assertIn("graph", resources)
        self.assertIn("batchupdate", resources)
        self.assertIn("batch", resources)


    def test_endpoint_profile_exposes_compound_operation_terms(self):
        p = profile_endpoint({
            "id":"opaque.messages.postMessage",
            "method":"POST",
            "url":"https://opaque.invalid/messages/postMessage",
            "description":"Send a message to a channel.",
        })
        self.assertIn("postmessage", p["operation_terms"])
        self.assertIn("post", p["operation_terms"])
        self.assertIn("message", p["operation_terms"])


    def test_intra_clause_anaphor_inherits_prior_referent(self):
        out = compile_goal_contract(
            "Update the cobalt lead details and mark it as active."
        )
        updates = [x for x in out["intents"] if x["action_class"] == "update"]
        self.assertEqual(len(updates), 2, out)
        self.assertIn("lead", updates[1]["resource_terms"])
        self.assertIn("cobalt", updates[1]["resource_terms"])

    def test_intra_clause_shared_object_inherits_prior_context(self):
        out = compile_goal_contract(
            "Create the customer case in NovaCRM and set case priority high."
        )
        update = next(x for x in out["intents"] if x["action_class"] == "update")
        self.assertIn("case", update["resource_terms"])
        self.assertIn("novacrm", update["resource_terms"])

    def test_intra_clause_unrelated_actions_do_not_cross_contaminate(self):
        out = compile_goal_contract(
            "Create the cobalt ticket and send the amber summary."
        )
        notify = next(x for x in out["intents"] if x["action_class"] == "notify")
        self.assertIn("amber", notify["resource_terms"])
        self.assertNotIn("cobalt", notify["resource_terms"])
        self.assertNotIn("ticket", notify["resource_terms"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
