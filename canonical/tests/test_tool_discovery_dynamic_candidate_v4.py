from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4


def base_public():
    return {
        "required_capabilities": ["CAP_A"],
        "constraint": None,
        "visible_tools": [],
        "prior_probe_receipts": [],
        "discovery_sources": [],
        "discovery_receipts": [],
        "version_events": [],
        "decision_epoch": 0,
    }


class Tests(unittest.TestCase):
    def test_v3_counterexample_selects_before_complete_discovery(self):
        public = base_public()
        public["visible_tools"] = [{
            "tool_id": "EXPENSIVE", "cost": 10.0, "available": True,
            "authorized": True, "epoch": 0, "safe_probe_capabilities": ["CAP_A"],
        }]
        public["prior_probe_receipts"] = [{
            "kind": "SAFE_CAPABILITY_PROBE", "tool_id": "EXPENSIVE",
            "capability": "CAP_A", "epoch": 0, "supported": True,
        }]
        public["discovery_sources"] = [{"source_id": "S0", "cost": 0.1, "available": True, "authorized": True}]
        self.assertEqual(v3.next_action(public), {"action": "SELECT", "tool_id": "EXPENSIVE"})
        self.assertEqual(
            v4.next_action(public),
            {"action": "DISCOVER", "source_id": "S0", "query": "CAP_A"},
        )

    def test_v4_selects_global_cheapest_after_discovery_exhausted(self):
        public = base_public()
        public["visible_tools"] = [
            {"tool_id": "CHEAP", "cost": 1.0, "available": True, "authorized": True, "epoch": 0, "safe_probe_capabilities": ["CAP_A"]},
            {"tool_id": "EXPENSIVE", "cost": 10.0, "available": True, "authorized": True, "epoch": 0, "safe_probe_capabilities": ["CAP_A"]},
        ]
        public["prior_probe_receipts"] = [
            {"kind": "SAFE_CAPABILITY_PROBE", "tool_id": "CHEAP", "capability": "CAP_A", "epoch": 0, "supported": True},
            {"kind": "SAFE_CAPABILITY_PROBE", "tool_id": "EXPENSIVE", "capability": "CAP_A", "epoch": 0, "supported": True},
        ]
        public["discovery_sources"] = [{"source_id": "S0", "cost": 0.1, "available": True, "authorized": True}]
        public["discovery_receipts"] = [{"kind": "DISCOVERY_RESULT", "source_id": "S0", "decision_epoch": 0}]
        self.assertEqual(v4.next_action(public), {"action": "SELECT", "tool_id": "CHEAP"})

    def test_v4_never_probes_without_explicit_safe_permission(self):
        public = base_public()
        public["visible_tools"] = [
            {"tool_id": "CHEAP", "cost": 1.0, "available": True, "authorized": True, "epoch": 0, "safe_probe_capabilities": []},
            {"tool_id": "SAFE", "cost": 2.0, "available": True, "authorized": True, "epoch": 0, "safe_probe_capabilities": ["CAP_A"]},
        ]
        public["prior_probe_receipts"] = [{
            "kind": "SAFE_CAPABILITY_PROBE", "tool_id": "SAFE",
            "capability": "CAP_A", "epoch": 0, "supported": True,
        }]
        self.assertEqual(v4.next_action(public), {"action": "SELECT", "tool_id": "SAFE"})

    def test_v4_stale_positive_receipt_is_not_reused_after_version_change(self):
        public = base_public()
        public["visible_tools"] = [{
            "tool_id": "T1", "cost": 1.0, "available": True,
            "authorized": True, "epoch": 0, "safe_probe_capabilities": ["CAP_A"],
        }]
        public["prior_probe_receipts"] = [{
            "kind": "SAFE_CAPABILITY_PROBE", "tool_id": "T1",
            "capability": "CAP_A", "epoch": 0, "supported": True,
        }]
        public["version_events"] = [{"kind": "TOOL_VERSION_CHANGED", "tool_id": "T1", "new_epoch": 1}]
        self.assertEqual(v4.next_action(public), {"action": "PROBE", "tool_id": "T1", "capability": "CAP_A"})

    def test_v4_escalates_only_after_complete_discovery_and_no_verified_route(self):
        public = base_public()
        public["visible_tools"] = [{
            "tool_id": "T1", "cost": 1.0, "available": True,
            "authorized": True, "epoch": 0, "safe_probe_capabilities": ["CAP_A"],
        }]
        public["prior_probe_receipts"] = [{
            "kind": "SAFE_CAPABILITY_PROBE", "tool_id": "T1",
            "capability": "CAP_A", "epoch": 0, "supported": False,
        }]
        self.assertEqual(
            v4.next_action(public),
            {"action": "ESCALATE", "reason": "NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY"},
        )

    def test_v4_stale_discovery_receipt_does_not_suppress_rediscovery(self):
        public = base_public()
        public["decision_epoch"] = 2
        public["discovery_sources"] = [{"source_id": "S0", "cost": 0.1, "available": True, "authorized": True}]
        public["discovery_receipts"] = [{"kind": "DISCOVERY_RESULT", "source_id": "S0", "decision_epoch": 1}]
        self.assertEqual(
            v4.next_action(public),
            {"action": "DISCOVER", "source_id": "S0", "query": "CAP_A"},
        )

    def test_v4_never_queries_unauthorized_discovery_source(self):
        public = base_public()
        public["visible_tools"] = [{
            "tool_id": "SAFE", "cost": 2.0, "available": True,
            "authorized": True, "epoch": 0, "safe_probe_capabilities": ["CAP_A"],
        }]
        public["prior_probe_receipts"] = [{
            "kind": "SAFE_CAPABILITY_PROBE", "tool_id": "SAFE",
            "capability": "CAP_A", "epoch": 0, "supported": True,
        }]
        public["discovery_sources"] = [{"source_id": "UNAUTH", "cost": 0.0, "available": True, "authorized": False}]
        self.assertEqual(v4.next_action(public), {"action": "SELECT", "tool_id": "SAFE"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
