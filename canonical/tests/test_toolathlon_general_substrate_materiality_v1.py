from __future__ import annotations
import unittest
from canonical.runtime import toolathlon_brain_owned_selection_adapter_v1 as a
from canonical.runtime.acceptance_capability_source_gate_v2 import evaluate as source_gate

def tools():
    return a.normalize_gateway_tools([
        {"name":"expensive_search","description":"Search workspace","inputSchema":{"type":"object"},"cost":10},
        {"name":"cheap_search","description":"Search workspace","inputSchema":{"type":"object"},"cost":1},
        {"name":"forbidden_delete","description":"Delete object","inputSchema":{"type":"object"},"cost":0.1,"authorized":False},
    ])

def base_public():
    return {
        "tools":tools(),
        "subproblem_contract":{"goal":"Find document.","required_capabilities":["SEARCH_WORKSPACE"],"constraint":None},
        "task_context":"Find document.",
        "schema_judgment_receipts":[],
        "version_events":[],
    }

class Materiality(unittest.TestCase):
    def test_fixed_substrate_outputs_require_brain_binding_and_selection(self):
        p=base_public()
        for tid in ("cheap_search","expensive_search"):
            tool=next(x for x in p["tools"] if x["tool_id"]==tid)
            req=a.build_schema_judgment_request(tool=tool,capability="SEARCH_WORKSPACE",task_context=p["task_context"])
            p["schema_judgment_receipts"].append(a.bind_schema_judgment_receipt(
                tool_id=tid,epoch=0,capability="SEARCH_WORKSPACE",supported=True,
                request_hash=a.schema_judgment_request_hash(req)))
        self.assertEqual(a.next_action(p),{"action":"SELECT","tool_id":"cheap_search"})

    def test_same_substrate_interface_cannot_legally_supply_route_when_brain_selection_removed(self):
        req=a.build_subproblem_request(task_context="Find document.")
        schema=req["response_schema"]
        self.assertNotIn("selected_tool",schema)
        self.assertNotIn("tool_id",schema)
        self.assertNotIn("route",schema)
        illegal={"goal":"Find document.","required_capabilities":["SEARCH_WORKSPACE"],"selected_tool":"cheap_search"}
        ok,errors=a.validate_subproblem_contract(illegal,tools())
        self.assertFalse(ok)
        self.assertIn("SUBSTRATE_CONTRACT_CONTAINS_FORBIDDEN_ROUTE_KEY",errors)

    def test_brain_control_is_not_provider_routing_only(self):
        route=a.source_gate_v2_candidate_route(general_substrate_test_pass=True,benchmark_harness_zero_cost=True)
        out=source_gate(route)
        self.assertTrue(out["pass"],out)
        self.assertTrue(route["configuration_materially_constrains_execution"])
        self.assertFalse(route["external_hidden_target_capability_provider"])
        self.assertFalse(route["ownership_claim_relies_on_model_standalone_superiority"])

    def test_materiality_does_not_grant_terminal_credit(self):
        route=a.source_gate_v2_candidate_route(general_substrate_test_pass=True,benchmark_harness_zero_cost=True)
        out=source_gate(route)
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)

if __name__=="__main__":
    unittest.main(verbosity=2)
