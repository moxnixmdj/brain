from __future__ import annotations
import unittest
from canonical.runtime import toolathlon_brain_owned_selection_adapter_v1 as a
from canonical.runtime.acceptance_capability_source_gate_v2 import evaluate as source_gate_v2

def catalog():
    return a.normalize_gateway_tools([
        {"name":"expensive_search","description":"Search workspace","inputSchema":{"type":"object"},"cost":10},
        {"name":"cheap_search","description":"Search workspace","inputSchema":{"type":"object"},"cost":1},
        {"name":"forbidden_delete","description":"Delete object","inputSchema":{"type":"object"},"cost":0.1,"authorized":False},
    ])

def public():
    return {
        "tools":catalog(),
        "subproblem_contract":{"required_capabilities":["SEARCH_WORKSPACE"],"goal":"Find document.","constraint":None},
        "task_context":"Find document.",
        "schema_judgment_receipts":[],
        "version_events":[],
    }

class Tests(unittest.TestCase):
    def test_subproblem_request_has_structural_catalog_nonexposure(self):
        payload=a.build_subproblem_request(task_context="Find document.",public_state_summary="Need the next operation.")
        encoded=repr(payload)
        self.assertNotIn("cheap_search",encoded)
        self.assertNotIn("expensive_search",encoded)
        self.assertNotIn("input_schema",encoded)
        self.assertNotIn("'cost'",encoded)

    def test_substrate_cannot_choose_route_via_contract_fields(self):
        p=public()
        p["subproblem_contract"]["selected_tool"]="cheap_search"
        self.assertEqual(a.next_action(p)["reason"],"SUBSTRATE_BOUNDARY_VIOLATION")

    def test_judgment_payload_hides_route_information(self):
        out=a.next_action(public())
        self.assertEqual(out["action"],"JUDGE_SCHEMA")
        self.assertEqual(out["internal_tool_id"],"cheap_search")
        encoded=repr(out["substrate_payload"])
        self.assertNotIn("cheap_search",encoded)
        self.assertNotIn("expensive_search",encoded)
        self.assertNotIn("'cost'",encoded)

    def test_brain_order_and_negative_evidence(self):
        p=public()
        first=a.next_action(p)
        p["schema_judgment_receipts"].append(a.bind_schema_judgment_receipt(
            tool_id="cheap_search",epoch=0,capability="SEARCH_WORKSPACE",supported=False,request_hash=first["request_hash"]))
        second=a.next_action(p)
        self.assertEqual(second["internal_tool_id"],"expensive_search")
        self.assertNotEqual(second.get("internal_tool_id"),"forbidden_delete")

    def test_positive_select_and_epoch_invalidation(self):
        p=public()
        first=a.next_action(p)
        p["schema_judgment_receipts"].append(a.bind_schema_judgment_receipt(
            tool_id="cheap_search",epoch=0,capability="SEARCH_WORKSPACE",supported=True,request_hash=first["request_hash"]))
        self.assertEqual(a.next_action(p),{"action":"SELECT","tool_id":"cheap_search"})
        p["version_events"].append({"kind":"TOOL_VERSION_CHANGED","tool_id":"cheap_search","new_epoch":1})
        out=a.next_action(p)
        self.assertEqual(out["action"],"JUDGE_SCHEMA")
        self.assertEqual(out["epoch"],1)

    def test_argument_request_is_selected_schema_only(self):
        t=next(x for x in catalog() if x["tool_id"]=="cheap_search")
        payload=a.build_selected_tool_argument_request(tool=t,task_context="Find document.",selected_capabilities=["SEARCH_WORKSPACE"])
        encoded=repr(payload)
        self.assertNotIn("cheap_search",encoded)
        self.assertNotIn("expensive_search",encoded)
        self.assertNotIn("'cost'",encoded)

    def test_source_gate_v2_remains_blocked_until_materiality(self):
        route=a.source_gate_v2_candidate_route(general_substrate_test_pass=False,benchmark_harness_zero_cost=True)
        out=source_gate_v2(route)
        self.assertFalse(out["pass"])
        self.assertIn("GENERAL_SUBSTRATE_TEST_NOT_PROVEN",out["errors"])

    def test_source_gate_v2_candidate_shape_can_pass_after_external_facts(self):
        route=a.source_gate_v2_candidate_route(general_substrate_test_pass=True,benchmark_harness_zero_cost=True)
        out=source_gate_v2(route)
        self.assertTrue(out["pass"],out)
        self.assertFalse(route["external_hidden_target_capability_provider"])

if __name__=="__main__":
    unittest.main(verbosity=2)
