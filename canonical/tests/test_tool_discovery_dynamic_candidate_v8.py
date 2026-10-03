from __future__ import annotations

import copy
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v7 as v7
from canonical.runtime import tool_discovery_dynamic_candidate_v8 as v8

CAP="CAP_A"


def tool(tid,cost,*,epoch=0):
    return {
        "tool_id":tid,
        "epoch":epoch,
        "cost":cost,
        "available":True,
        "authorized":True,
        "safe_probe_capabilities":[CAP,"CAP_B"],
    }


def visible_two_route_state(*,cheap_receipt,cheap_epoch=0,cheap_cost=1.0):
    return {
        "required_capabilities":[CAP],
        "decision_epoch":0,
        "authority_epoch":0,
        "constraint":None,
        "visible_tools":[
            tool("CHEAP",cheap_cost,epoch=cheap_epoch),
            tool("EXPENSIVE",2.0,epoch=cheap_epoch),
        ],
        "discovery_sources":[],
        "discovery_receipts":[],
        "prior_probe_receipts":[
            cheap_receipt,
            {
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":"EXPENSIVE",
                "capability":CAP,
                "epoch":cheap_epoch,
                "supported":True,
            },
        ],
        "version_events":[],
    }


def transferable_state(required,decision_epoch):
    t={
        "tool_id":"T0",
        "epoch":0,
        "cost":1.0,
        "available":True,
        "authorized":True,
        "safe_probe_capabilities":["CAP_A","CAP_B"],
    }
    src={
        "source_id":"S0",
        "cost":0.0,
        "available":True,
        "authorized":True,
        "authoritative":True,
        "source_epoch":0,
        "source_digest":v5._tools_digest([t]),
        "catalog_query":"__FULL_AUTHORITY_CATALOG__",
    }
    digest=v7._source_set_digest([src],authority_epoch=0)
    return {
        "required_capabilities":[required],
        "decision_epoch":decision_epoch,
        "authority_epoch":0,
        "constraint":None,
        "visible_tools":[],
        "discovery_sources":[src],
        "discovery_receipts":[{
            "kind":"DISCOVERY_RESULT",
            "source_id":"S0",
            "complete":True,
            "authority_epoch":0,
            "source_epoch":0,
            "source_digest":src["source_digest"],
            "source_set_digest":digest,
            "query":src["catalog_query"],
            "tools":[t],
        }],
        "prior_probe_receipts":[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A","epoch":0,"supported":True},
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_B","epoch":0,"supported":True},
        ],
        "version_events":[],
    }


class ToolDiscoveryDynamicV8Tests(unittest.TestCase):
    def test_v7_malformed_supported_none_can_false_eliminate_cheaper_route(self):
        state=visible_two_route_state(cheap_receipt={
            "kind":"SAFE_CAPABILITY_PROBE",
            "tool_id":"CHEAP",
            "capability":CAP,
            "epoch":0,
            "supported":None,
        })
        self.assertEqual(v7.next_action(state),{"action":"SELECT","tool_id":"EXPENSIVE"})
        self.assertEqual(v8.next_action(state),{
            "action":"ESCALATE","reason":"PROBE_RECEIPT_SUPPORTED_NOT_BOOL",
        })

    def test_v7_integer_supported_one_is_not_true_and_can_false_eliminate(self):
        state=visible_two_route_state(cheap_receipt={
            "kind":"SAFE_CAPABILITY_PROBE",
            "tool_id":"CHEAP",
            "capability":CAP,
            "epoch":0,
            "supported":1,
        })
        self.assertEqual(v7.next_action(state),{"action":"SELECT","tool_id":"EXPENSIVE"})
        self.assertEqual(v8.next_action(state),{
            "action":"ESCALATE","reason":"PROBE_RECEIPT_SUPPORTED_NOT_BOOL",
        })

    def test_bool_epoch_can_alias_integer_epoch_in_v7(self):
        state=visible_two_route_state(
            cheap_epoch=1,
            cheap_receipt={
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":"CHEAP",
                "capability":CAP,
                "epoch":True,
                "supported":False,
            },
        )
        self.assertEqual(v7.next_action(state),{"action":"SELECT","tool_id":"EXPENSIVE"})
        self.assertEqual(v8.next_action(state),{
            "action":"ESCALATE","reason":"PROBE_RECEIPT_EPOCH_INVALID",
        })

    def test_v7_nan_tool_cost_can_be_selected(self):
        state={
            "required_capabilities":[CAP],
            "decision_epoch":0,
            "authority_epoch":0,
            "constraint":None,
            "visible_tools":[tool("NAN_ROUTE",float("nan"))],
            "discovery_sources":[],
            "discovery_receipts":[],
            "prior_probe_receipts":[{
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":"NAN_ROUTE",
                "capability":CAP,
                "epoch":0,
                "supported":True,
            }],
            "version_events":[],
        }
        self.assertEqual(v7.next_action(state),{"action":"SELECT","tool_id":"NAN_ROUTE"})
        self.assertEqual(v8.next_action(state),{
            "action":"ESCALATE","reason":"TOOL_COST_NOT_FINITE_NONNEGATIVE",
        })

    def test_v8_rejects_all_nonfinite_or_nonordered_tool_costs(self):
        for value in (float("nan"),float("inf"),float("-inf"),True,-1.0,"1",None):
            state=visible_two_route_state(
                cheap_cost=value,
                cheap_receipt={
                    "kind":"SAFE_CAPABILITY_PROBE",
                    "tool_id":"CHEAP",
                    "capability":CAP,
                    "epoch":0,
                    "supported":True,
                },
            )
            with self.subTest(value=value):
                self.assertEqual(v8.next_action(state),{
                    "action":"ESCALATE","reason":"TOOL_COST_NOT_FINITE_NONNEGATIVE",
                })

    def test_v8_rejects_nonfinite_source_cost_before_discovery(self):
        state=transferable_state("CAP_A",0)
        state["discovery_sources"][0]["cost"]=float("inf")
        state["discovery_receipts"]=[]
        self.assertEqual(v7.next_action(state)["action"],"DISCOVER")
        self.assertEqual(v8.next_action(state),{
            "action":"ESCALATE","reason":"DISCOVERY_SOURCE_COST_NOT_FINITE_NONNEGATIVE",
        })

    def test_nonobject_probe_receipt_fails_closed(self):
        state=transferable_state("CAP_A",0)
        state["prior_probe_receipts"].append(7)
        self.assertEqual(v8.next_action(state),{
            "action":"ESCALATE","reason":"PROBE_RECEIPT_NOT_OBJECT",
        })

    def test_transferable_catalog_and_probe_evidence_survive_task_change(self):
        a=transferable_state("CAP_A",0)
        b=transferable_state("CAP_B",17)
        self.assertEqual(v8.next_action(a),{"action":"SELECT","tool_id":"T0"})
        self.assertEqual(v8.next_action(b),{"action":"SELECT","tool_id":"T0"})

    def test_new_capability_needs_probe_not_catalog_rediscovery(self):
        state=transferable_state("CAP_A",0)
        state["required_capabilities"]=["CAP_C"]
        t=state["discovery_receipts"][0]["tools"][0]
        t["safe_probe_capabilities"].append("CAP_C")
        src=state["discovery_sources"][0]
        src["source_digest"]=v5._tools_digest([t])
        state["discovery_receipts"][0]["source_digest"]=src["source_digest"]
        state["discovery_receipts"][0]["source_set_digest"]=v7._source_set_digest(
            state["discovery_sources"],authority_epoch=0
        )
        state["prior_probe_receipts"]=[]
        self.assertEqual(v8.next_action(state),{
            "action":"PROBE","tool_id":"T0","capability":"CAP_C",
        })

    def test_restart_boundary_precedes_firewalls(self):
        state=transferable_state("CAP_A",0)
        state["discovery_receipts"][0]["tools"][0]["cost"]=float("nan")
        state["version_events"]=[{
            "kind":"TOOL_VERSION_CHANGED","tool_id":"T0","new_epoch":1,
        }]
        self.assertEqual(v8.next_action(state),{
            "action":"ESCALATE",
            "reason":"TOOL_VERSION_CHANGED_RESTART_EPISODE",
            "tool_id":"T0",
            "new_epoch":1,
        })

    def test_valid_finite_strict_evidence_behavior_matches_v7(self):
        for required in ("CAP_A","CAP_B"):
            state=transferable_state(required,3)
            self.assertEqual(v8.next_action(state),v7.next_action(state))

if __name__=="__main__":
    unittest.main(verbosity=2)
