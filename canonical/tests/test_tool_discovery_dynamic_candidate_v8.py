from __future__ import annotations

import copy
import math
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v7 as v7
from canonical.runtime import tool_discovery_dynamic_candidate_v8 as v8


def tool(tid="T0", cost=1.0, *, available=True, authorized=True, epoch=0):
    return {
        "tool_id":tid,
        "epoch":epoch,
        "cost":cost,
        "available":available,
        "authorized":authorized,
        "safe_probe_capabilities":["CAP_A","CAP_B","CAP_C"],
    }


def state(
    tools=None,
    *,
    required=("CAP_A",),
    authority_epoch=0,
    visible=None,
    probe_rows=None,
    source_cost=0.0,
):
    tools=list(tools or [tool()])
    source={
        "source_id":"S0",
        "cost":source_cost,
        "available":True,
        "authorized":True,
        "authoritative":True,
        "source_epoch":0,
        "source_digest":v5._tools_digest(tools),
        "catalog_query":"__FULL_AUTHORITY_CATALOG__",
    }
    source_set=v8._source_set_digest([source],authority_epoch=authority_epoch)
    if probe_rows is None:
        probe_rows=[
            {
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":t["tool_id"],
                "capability":cap,
                "epoch":t.get("epoch",0),
                "authority_epoch":authority_epoch,
                "supported":True,
            }
            for t in tools for cap in required
        ]
    return {
        "required_capabilities":list(required),
        "decision_epoch":99,
        "authority_epoch":authority_epoch,
        "constraint":None,
        "visible_tools":copy.deepcopy(list(visible or [])),
        "discovery_sources":[source],
        "discovery_receipts":[{
            "kind":"DISCOVERY_RESULT",
            "source_id":"S0",
            "complete":True,
            "authority_epoch":authority_epoch,
            "source_epoch":0,
            "source_digest":source["source_digest"],
            "source_set_digest":source_set,
            "query":source["catalog_query"],
            "tools":copy.deepcopy(tools),
        }],
        "prior_probe_receipts":copy.deepcopy(probe_rows),
        "version_events":[],
    }


class ToolDiscoveryDynamicV8Tests(unittest.TestCase):
    def test_v7_nan_cost_can_reach_selection_but_v8_fails_closed(self):
        bad=tool("NAN", float("nan"))
        expensive=tool("FINITE", 5.0)
        s=state([bad,expensive])
        # Python's tuple sort leaves this NaN route at the front because NaN is
        # unordered. V7 therefore commits to a route under a non-total cost order.
        self.assertEqual(v7.next_action(copy.deepcopy(s)),{"action":"SELECT","tool_id":"NAN"})
        self.assertEqual(v8.next_action(s),{"action":"ESCALATE","reason":"TOOL_COST_INVALID"})

    def test_v8_rejects_positive_infinite_tool_cost(self):
        s=state([tool("INF",float("inf")),tool("FINITE",5.0)])
        self.assertEqual(v8.next_action(s),{"action":"ESCALATE","reason":"TOOL_COST_INVALID"})

    def test_v8_rejects_nonfinite_source_cost(self):
        s=state([tool()],source_cost=float("inf"))
        self.assertEqual(v8.next_action(s),{"action":"ESCALATE","reason":"DISCOVERY_SOURCE_MALFORMED"})

    def test_v7_reuses_probe_across_authority_epoch_but_v8_does_not(self):
        t=tool()
        old_probe=[{
            "kind":"SAFE_CAPABILITY_PROBE",
            "tool_id":"T0",
            "capability":"CAP_A",
            "epoch":0,
            "authority_epoch":0,
            "supported":True,
        }]
        s=state([t],authority_epoch=1,probe_rows=old_probe)
        self.assertEqual(v7.next_action(copy.deepcopy(s)),{"action":"SELECT","tool_id":"T0"})
        self.assertEqual(
            v8.next_action(s),
            {"action":"PROBE","tool_id":"T0","capability":"CAP_A"},
        )

    def test_v7_can_select_visible_tool_outside_complete_catalog_but_v8_refuses(self):
        catalog_tool=tool("CATALOG",10.0)
        outside=tool("OUTSIDE",1.0)
        probes=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"CATALOG","capability":"CAP_A","epoch":0,"authority_epoch":0,"supported":True},
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"OUTSIDE","capability":"CAP_A","epoch":0,"authority_epoch":0,"supported":True},
        ]
        s=state([catalog_tool],visible=[outside],probe_rows=probes)
        self.assertEqual(v7.next_action(copy.deepcopy(s)),{"action":"SELECT","tool_id":"OUTSIDE"})
        self.assertEqual(
            v8.next_action(s),
            {"action":"ESCALATE","reason":"VISIBLE_TOOL_OUTSIDE_COMPLETE_CATALOG"},
        )

    def test_malformed_availability_cannot_be_silently_skipped_for_expensive_route(self):
        malformed=tool("CHEAP",1.0)
        malformed["available"]="yes"
        expensive=tool("EXPENSIVE",10.0)
        s=state([malformed,expensive])
        self.assertEqual(
            v8.next_action(s),
            {"action":"ESCALATE","reason":"TOOL_AVAILABLE_NOT_BOOLEAN"},
        )

    def test_task_change_reuses_catalog_and_current_authority_probe_receipts(self):
        s=state([tool()],required=("CAP_B",),authority_epoch=7)
        s["decision_epoch"]=123456
        self.assertEqual(v8.next_action(s),{"action":"SELECT","tool_id":"T0"})

    def test_new_capability_needs_probe_not_catalog_rediscovery(self):
        s=state([tool()],required=("CAP_C",),probe_rows=[],authority_epoch=4)
        self.assertEqual(
            v8.next_action(s),
            {"action":"PROBE","tool_id":"T0","capability":"CAP_C"},
        )

    def test_tool_version_change_still_forces_restart(self):
        s=state([tool()])
        s["version_events"]=[{"kind":"TOOL_VERSION_CHANGED","tool_id":"T0","new_epoch":1}]
        self.assertEqual(v8.next_action(s),{
            "action":"ESCALATE",
            "reason":"TOOL_VERSION_CHANGED_RESTART_EPISODE",
            "tool_id":"T0",
            "new_epoch":1,
        })

    def test_current_authority_probe_supported_must_be_boolean(self):
        s=state([tool()])
        s["prior_probe_receipts"][0]["supported"]="yes"
        self.assertEqual(
            v8.next_action(s),
            {"action":"ESCALATE","reason":"PROBE_SUPPORTED_NOT_BOOLEAN"},
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
