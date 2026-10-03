from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4
from canonical.runtime import tool_discovery_dynamic_proof_v3 as proof


def _public(*, discovered: bool, t1_positive: bool = False):
    tools = [
        {
            "tool_id": "T0", "cost": 10.0, "available": True, "authorized": True,
            "epoch": 0, "meta": {}, "schema_tags": ["CAP_A"],
        }
    ]
    discoveries = []
    receipts = [{
        "kind": "SAFE_CAPABILITY_PROBE", "tool_id": "T0",
        "capability": "CAP_A", "epoch": 0, "supported": True,
    }]
    if discovered:
        tools.append({
            "tool_id": "T1", "cost": 1.0, "available": True, "authorized": True,
            "epoch": 0, "meta": {}, "schema_tags": ["CAP_A"],
        })
        discoveries.append({"kind": "DISCOVERY_RESULT", "source_id": "S0"})
        if t1_positive:
            receipts.append({
                "kind": "SAFE_CAPABILITY_PROBE", "tool_id": "T1",
                "capability": "CAP_A", "epoch": 0, "supported": True,
            })
    return {
        "required_capabilities": ["CAP_A"],
        "constraint": None,
        "visible_tools": tools,
        "discovery_sources": [{"source_id": "S0", "cost": 0.0, "available": True}],
        "prior_probe_receipts": receipts,
        "discovery_receipts": discoveries,
        "version_events": [],
    }


class ToolDiscoveryV4ScopeRepairTests(unittest.TestCase):
    def test_v3_selects_expensive_visible_route_before_complete_discovery(self):
        action = v3.next_action(_public(discovered=False))
        self.assertEqual(action, {"action": "SELECT", "tool_id": "T0"})

    def test_v4_discovers_before_selecting_visible_route(self):
        action = v4.next_action(_public(discovered=False))
        self.assertEqual(action["action"], "DISCOVER")
        self.assertEqual(action["source_id"], "S0")

    def test_v4_probes_then_selects_cheapest_discovered_route(self):
        action = v4.next_action(_public(discovered=True))
        self.assertEqual(
            action,
            {"action": "PROBE", "tool_id": "T1", "capability": "CAP_A"},
        )
        action = v4.next_action(_public(discovered=True, t1_positive=True))
        self.assertEqual(action, {"action": "SELECT", "tool_id": "T1"})

    def test_v4_passes_existing_1200_case_dynamic_grid(self):
        out = proof.run_batch(20261002, 1200, v4.next_action)
        self.assertTrue(out["pass"], out["failures"][:5])
        self.assertEqual(out["failed"], 0)
        self.assertEqual(set(out["classes"]), set(proof.CLASSES))


if __name__ == "__main__":
    unittest.main(verbosity=2)
