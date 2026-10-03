from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3


class Tests(unittest.TestCase):
    def test_v3_can_select_expensive_visible_tool_before_discovering_cheaper_route(self):
        public = {
            "required_capabilities": ["CAP_A"],
            "constraint": None,
            "visible_tools": [{
                "tool_id": "expensive",
                "cost": 10.0,
                "available": True,
                "authorized": True,
                "epoch": 0,
            }],
            "prior_probe_receipts": [{
                "kind": "SAFE_CAPABILITY_PROBE",
                "tool_id": "expensive",
                "capability": "CAP_A",
                "epoch": 0,
                "supported": True,
            }],
            "version_events": [],
            "discovery_sources": [{
                "source_id": "authoritative",
                "cost": 0.0,
                "available": True,
            }],
            "discovery_receipts": [],
        }
        action = v3.next_action(public)
        self.assertEqual(action, {"action": "SELECT", "tool_id": "expensive"})
        self.assertNotEqual(action.get("action"), "DISCOVER")

    def test_counterexample_witness_has_cheaper_unseen_sufficient_world(self):
        # The policy observation above is compatible with a world where the
        # unqueried authoritative source contains this cheaper sufficient tool.
        hidden_world = {
            "tool_id": "cheap",
            "cost": 1.0,
            "available": True,
            "authorized": True,
            "capabilities": {"CAP_A"},
        }
        self.assertLess(hidden_world["cost"], 10.0)
        self.assertIn("CAP_A", hidden_world["capabilities"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
