from __future__ import annotations

import copy
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4
from canonical.runtime import tool_discovery_dynamic_proof_v3 as proof


def _counterexample_public():
    return {
        "required_capabilities": ["CAP_A"],
        "constraint": None,
        "visible_tools": [
            {
                "tool_id": "EXPENSIVE_VISIBLE",
                "cost": 10.0,
                "available": True,
                "authorized": True,
                "epoch": 0,
            }
        ],
        "discovery_sources": [
            {
                "source_id": "AUTHORITATIVE_SOURCE_0",
                "cost": 0.1,
                "available": True,
            }
        ],
        "prior_probe_receipts": [
            {
                "kind": "SAFE_CAPABILITY_PROBE",
                "tool_id": "EXPENSIVE_VISIBLE",
                "capability": "CAP_A",
                "epoch": 0,
                "supported": True,
            }
        ],
        "discovery_receipts": [],
        "version_events": [],
    }


class ToolDiscoveryDynamicV4Tests(unittest.TestCase):
    def test_v3_complete_interface_counterexample_selects_before_discovery(self):
        public = _counterexample_public()
        self.assertEqual(
            v3.next_action(public),
            {"action": "SELECT", "tool_id": "EXPENSIVE_VISIBLE"},
        )

    def test_v4_discovers_before_visible_selection(self):
        public = _counterexample_public()
        self.assertEqual(
            v4.next_action(public),
            {
                "action": "DISCOVER",
                "source_id": "AUTHORITATIVE_SOURCE_0",
                "query": "CAP_A",
            },
        )

    def test_v4_reaches_cheaper_discovered_route(self):
        public = _counterexample_public()
        public["discovery_receipts"] = [
            {
                "kind": "DISCOVERY_RESULT",
                "source_id": "AUTHORITATIVE_SOURCE_0",
            }
        ]
        public["visible_tools"].append(
            {
                "tool_id": "CHEAP_DISCOVERED",
                "cost": 1.0,
                "available": True,
                "authorized": True,
                "epoch": 0,
            }
        )

        self.assertEqual(
            v4.next_action(public),
            {
                "action": "PROBE",
                "tool_id": "CHEAP_DISCOVERED",
                "capability": "CAP_A",
            },
        )

        public["prior_probe_receipts"].append(
            {
                "kind": "SAFE_CAPABILITY_PROBE",
                "tool_id": "CHEAP_DISCOVERED",
                "capability": "CAP_A",
                "epoch": 0,
                "supported": True,
            }
        )
        self.assertEqual(
            v4.next_action(public),
            {"action": "SELECT", "tool_id": "CHEAP_DISCOVERED"},
        )

    def test_v4_exhausts_multiple_sources_by_declared_cost(self):
        public = _counterexample_public()
        public["discovery_sources"] = [
            {"source_id": "S_HIGH", "cost": 9.0, "available": True},
            {"source_id": "S_LOW", "cost": 1.0, "available": True},
        ]
        self.assertEqual(v4.next_action(public)["source_id"], "S_LOW")
        public["discovery_receipts"] = [
            {"kind": "DISCOVERY_RESULT", "source_id": "S_LOW"}
        ]
        self.assertEqual(v4.next_action(public)["source_id"], "S_HIGH")

    def test_no_requirement_behavior_remains_fail_closed(self):
        public = _counterexample_public()
        public["required_capabilities"] = []
        self.assertEqual(
            v4.next_action(public),
            {"action": "ESCALATE", "reason": "NO_REQUIRED_CAPABILITIES"},
        )

    def test_existing_dynamic_v3_behavior_grid_is_preserved(self):
        out = proof.run_batch(20261002, 1200, v4.next_action)
        self.assertTrue(out["pass"], out["failures"][:5])
        self.assertEqual(out["failed"], 0)
        self.assertEqual(set(out["classes"]), set(proof.CLASSES))

    def test_v4_does_not_mutate_public_state(self):
        public = _counterexample_public()
        before = copy.deepcopy(public)
        v4.next_action(public)
        self.assertEqual(public, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
