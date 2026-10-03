from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4
from canonical.runtime import tool_discovery_dynamic_proof_v3 as proof


def _expensive_visible_public():
    return {
        "required_capabilities": ["CAP_A"],
        "constraint": None,
        "visible_tools": [{
            "tool_id": "EXPENSIVE",
            "cost": 10.0,
            "available": True,
            "authorized": True,
            "epoch": 0,
            "meta": {},
        }],
        "prior_probe_receipts": [{
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": "EXPENSIVE",
            "capability": "CAP_A",
            "epoch": 0,
            "supported": True,
        }],
        "discovery_sources": [{
            "source_id": "AUTHORITATIVE",
            "cost": 0.0,
            "available": True,
        }],
        "discovery_receipts": [],
        "version_events": [],
    }


class ToolDiscoveryDynamicV4Tests(unittest.TestCase):
    def test_v3_selects_before_complete_discovery_counterexample(self):
        action = v3.next_action(_expensive_visible_public())
        self.assertEqual(
            action,
            {"action": "SELECT", "tool_id": "EXPENSIVE"},
        )

    def test_v4_refuses_selection_before_complete_discovery(self):
        action = v4.next_action(_expensive_visible_public())
        self.assertEqual(action["action"], "DISCOVER")
        self.assertEqual(action["source_id"], "AUTHORITATIVE")

    def test_v4_selects_cheaper_discovered_route_after_truthful_probe(self):
        public = _expensive_visible_public()
        public["visible_tools"].append({
            "tool_id": "CHEAP",
            "cost": 1.0,
            "available": True,
            "authorized": True,
            "epoch": 0,
            "meta": {},
        })
        public["discovery_receipts"] = [{
            "kind": "DISCOVERY_RESULT",
            "source_id": "AUTHORITATIVE",
            "tools": [{"tool_id": "CHEAP"}],
        }]
        first = v4.next_action(public)
        self.assertEqual(
            first,
            {"action": "PROBE", "tool_id": "CHEAP", "capability": "CAP_A"},
        )
        public["prior_probe_receipts"].append({
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": "CHEAP",
            "capability": "CAP_A",
            "epoch": 0,
            "supported": True,
        })
        second = v4.next_action(public)
        self.assertEqual(second, {"action": "SELECT", "tool_id": "CHEAP"})

    def test_v4_preserves_existing_dynamic_v3_generated_scope_suite(self):
        out = proof.run_batch(20261002, 1200, v4.next_action)
        self.assertTrue(out["pass"], out["failures"][:5])
        self.assertEqual(out["failed"], 0)
        self.assertEqual(set(out["classes"]), set(proof.CLASSES))


if __name__ == "__main__":
    unittest.main(verbosity=2)
