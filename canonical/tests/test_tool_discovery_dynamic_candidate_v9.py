from __future__ import annotations

import copy
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v8 as v8
from canonical.runtime import tool_discovery_dynamic_candidate_v9 as v9


def tool(tid, cost, *, safe=("CAP_A",), available=True, authorized=True, epoch=0):
    return {
        "tool_id": tid,
        "epoch": epoch,
        "cost": cost,
        "available": available,
        "authorized": authorized,
        "safe_probe_capabilities": list(safe),
    }


def state(tools, *, required=("CAP_A",), authority_epoch=0, probes=None, visible=None):
    source = {
        "source_id": "S0",
        "cost": 0.0,
        "available": True,
        "authorized": True,
        "authoritative": True,
        "source_epoch": 0,
        "source_digest": v5._tools_digest(tools),
        "catalog_query": "__FULL_AUTHORITY_CATALOG__",
    }
    source_set = v8._source_set_digest([source], authority_epoch=authority_epoch)
    if probes is None:
        probes = []
    return {
        "required_capabilities": list(required),
        "decision_epoch": 11,
        "authority_epoch": authority_epoch,
        "constraint": None,
        "visible_tools": copy.deepcopy(list(visible or [])),
        "discovery_sources": [source],
        "discovery_receipts": [{
            "kind": "DISCOVERY_RESULT",
            "source_id": "S0",
            "complete": True,
            "authority_epoch": authority_epoch,
            "source_epoch": 0,
            "source_digest": source["source_digest"],
            "source_set_digest": source_set,
            "query": source["catalog_query"],
            "tools": copy.deepcopy(tools),
        }],
        "prior_probe_receipts": copy.deepcopy(probes),
        "version_events": [],
    }


def positive(tid, *, cap="CAP_A", epoch=0, authority_epoch=0):
    return {
        "kind": "SAFE_CAPABILITY_PROBE",
        "tool_id": tid,
        "capability": cap,
        "epoch": epoch,
        "authority_epoch": authority_epoch,
        "supported": True,
    }


def negative(tid, *, cap="CAP_A", epoch=0, authority_epoch=0):
    x = positive(tid, cap=cap, epoch=epoch, authority_epoch=authority_epoch)
    x["supported"] = False
    return x


class ToolDiscoveryDynamicV9Tests(unittest.TestCase):
    def test_v8_equal_cost_unprobeable_peer_false_block_is_repaired(self):
        tools = [
            tool("A_UNKNOWN", 1.0, safe=()),
            tool("Z_VERIFIED", 1.0),
        ]
        s = state(tools, probes=[positive("Z_VERIFIED")])
        self.assertEqual(v8.next_action(copy.deepcopy(s)), {
            "action": "ESCALATE",
            "reason": "CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
            "tool_id": "A_UNKNOWN",
        })
        self.assertEqual(v9.next_action(s), {
            "action": "SELECT", "tool_id": "Z_VERIFIED"
        })

    def test_equal_cost_safe_unknown_does_not_force_probe_if_peer_verified(self):
        tools = [tool("A_UNKNOWN", 1.0), tool("Z_VERIFIED", 1.0)]
        s = state(tools, probes=[positive("Z_VERIFIED")])
        self.assertEqual(v8.next_action(copy.deepcopy(s)), {
            "action": "PROBE", "tool_id": "A_UNKNOWN", "capability": "CAP_A"
        })
        self.assertEqual(v9.next_action(s), {
            "action": "SELECT", "tool_id": "Z_VERIFIED"
        })

    def test_mixed_equal_cost_frontier_consumes_safe_fact_before_matched(self):
        tools = [
            tool("A_UNSAFE", 1.0, safe=()),
            tool("B_SAFE", 1.0),
            tool("EXPENSIVE", 2.0),
        ]
        s = state(tools, probes=[positive("EXPENSIVE")])
        self.assertEqual(v9.next_action(s), {
            "action": "PROBE", "tool_id": "B_SAFE", "capability": "CAP_A"
        })

    def test_strictly_cheaper_irreducible_frontier_blocks_expensive_verified(self):
        tools = [tool("CHEAP", 1.0, safe=()), tool("EXPENSIVE", 2.0)]
        s = state(tools, probes=[positive("EXPENSIVE")])
        out = v9.next_action(s)
        self.assertEqual(out["action"], "ESCALATE")
        self.assertEqual(out["reason"], "LEAST_COST_FRONTIER_UNRESOLVED_NO_SAFE_PROBE")
        self.assertEqual(out["frontier_cost"], 1.0)
        self.assertEqual(out["tool_ids"], ["CHEAP"])

    def test_negative_cheaper_evidence_advances_to_next_cost(self):
        tools = [tool("CHEAP", 1.0), tool("EXPENSIVE", 2.0)]
        s = state(tools, probes=[negative("CHEAP"), positive("EXPENSIVE")])
        self.assertEqual(v9.next_action(s), {
            "action": "SELECT", "tool_id": "EXPENSIVE"
        })

    def test_all_falsified_routes_preserve_no_route_escalation(self):
        tools = [tool("A", 1.0), tool("B", 2.0)]
        s = state(tools, probes=[negative("A"), negative("B")])
        self.assertEqual(v9.next_action(s), {
            "action": "ESCALATE",
            "reason": "NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY",
        })

    def test_v8_authority_epoch_binding_is_preserved(self):
        tools = [tool("T0", 1.0)]
        s = state(tools, authority_epoch=1, probes=[positive("T0", authority_epoch=0)])
        self.assertEqual(v9.next_action(s), {
            "action": "PROBE", "tool_id": "T0", "capability": "CAP_A"
        })

    def test_v8_complete_catalog_identity_firewall_is_preserved(self):
        catalog = tool("CATALOG", 10.0)
        outside = tool("OUTSIDE", 1.0)
        s = state([catalog], visible=[outside], probes=[positive("CATALOG")])
        self.assertEqual(v9.next_action(s), {
            "action": "ESCALATE",
            "reason": "VISIBLE_TOOL_OUTSIDE_COMPLETE_CATALOG",
        })

    def test_v8_version_restart_is_preserved(self):
        s = state([tool("T0", 1.0)], probes=[positive("T0")])
        s["version_events"] = [{
            "kind": "TOOL_VERSION_CHANGED", "tool_id": "T0", "new_epoch": 1
        }]
        self.assertEqual(v9.next_action(s), {
            "action": "ESCALATE",
            "reason": "TOOL_VERSION_CHANGED_RESTART_EPISODE",
            "tool_id": "T0",
            "new_epoch": 1,
        })

    def test_v8_nonfinite_cost_firewall_is_preserved(self):
        s = state([tool("BAD", float("nan"))])
        self.assertEqual(v9.next_action(s), {
            "action": "ESCALATE", "reason": "TOOL_COST_INVALID"
        })

    def test_task_change_keeps_transferable_catalog(self):
        s = state([tool("T0", 1.0)], required=("CAP_A",), probes=[positive("T0")])
        s["decision_epoch"] = 999
        self.assertEqual(v9.next_action(s), {
            "action": "SELECT", "tool_id": "T0"
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
