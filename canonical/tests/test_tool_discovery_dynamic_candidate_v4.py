from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4
from canonical.runtime import tool_discovery_dynamic_proof_v3 as dynamic_proof
from canonical.runtime import tool_discovery_information_safe_proof_v2 as legacy_proof


def complete_interface_counterexample():
    return {
        "required_capabilities": ["CAP_A"],
        "constraint": None,
        "visible_tools": [
            {
                "tool_id": "T0",
                "cost": 10.0,
                "available": True,
                "authorized": True,
                "epoch": 0,
            }
        ],
        "discovery_sources": [
            {"source_id": "S0", "cost": 0.1, "available": True}
        ],
        "discovery_receipts": [],
        "prior_probe_receipts": [
            {
                "kind": "SAFE_CAPABILITY_PROBE",
                "tool_id": "T0",
                "capability": "CAP_A",
                "epoch": 0,
                "supported": True,
            }
        ],
        "version_events": [],
    }


class ToolDiscoveryDynamicV4Tests(unittest.TestCase):
    def test_v3_global_optimality_counterexample_is_real(self):
        public = complete_interface_counterexample()
        self.assertEqual(
            v3.next_action(public),
            {"action": "SELECT", "tool_id": "T0"},
        )

    def test_v4_discovers_before_selecting_visible_route(self):
        public = complete_interface_counterexample()
        self.assertEqual(
            v4.next_action(public),
            {"action": "DISCOVER", "source_id": "S0", "query": "CAP_A"},
        )

    def test_v4_selects_cheaper_discovered_sufficient_route(self):
        public = complete_interface_counterexample()
        public["discovery_receipts"] = [
            {
                "kind": "DISCOVERY_RESULT",
                "source_id": "S0",
                "tools": [
                    {
                        "tool_id": "T1",
                        "cost": 1.0,
                        "available": True,
                        "authorized": True,
                        "epoch": 0,
                    }
                ],
            }
        ]
        action = v4.next_action(public)
        self.assertEqual(
            action,
            {"action": "PROBE", "tool_id": "T1", "capability": "CAP_A"},
        )
        public["prior_probe_receipts"].append(
            {
                "kind": "SAFE_CAPABILITY_PROBE",
                "tool_id": "T1",
                "capability": "CAP_A",
                "epoch": 0,
                "supported": True,
            }
        )
        self.assertEqual(
            v4.next_action(public),
            {"action": "SELECT", "tool_id": "T1"},
        )

    def test_v4_preserves_dynamic_v3_falsification_grid(self):
        out = dynamic_proof.run_batch(20261002, 1200, v4.next_action)
        self.assertTrue(out["pass"], out["failures"][:5])
        self.assertEqual(out["failed"], 0)
        self.assertEqual(set(out["classes"]), set(dynamic_proof.CLASSES))

    def test_v4_preserves_legacy_preenumerated_policy_population(self):
        out = legacy_proof.run_batch(20261002, 180, v4.next_action)
        self.assertTrue(out["all_pass"], out["failures"][:5])
        self.assertEqual(out["failed"], 0)

    def test_v4_invalidates_stale_positive_evidence_after_version_change(self):
        public = {
            "required_capabilities": ["CAP_A"],
            "visible_tools": [
                {
                    "tool_id": "T0",
                    "cost": 1.0,
                    "available": True,
                    "authorized": True,
                    "epoch": 0,
                }
            ],
            "discovery_sources": [],
            "discovery_receipts": [],
            "prior_probe_receipts": [
                {
                    "kind": "SAFE_CAPABILITY_PROBE",
                    "tool_id": "T0",
                    "capability": "CAP_A",
                    "epoch": 0,
                    "supported": True,
                }
            ],
            "version_events": [
                {"kind": "TOOL_VERSION_CHANGED", "tool_id": "T0", "new_epoch": 1}
            ],
        }
        self.assertEqual(
            v4.next_action(public),
            {"action": "PROBE", "tool_id": "T0", "capability": "CAP_A"},
        )

    def test_conflicting_discovery_metadata_fails_closed(self):
        public = {
            "required_capabilities": ["CAP_A"],
            "visible_tools": [
                {
                    "tool_id": "T0",
                    "cost": 1.0,
                    "available": True,
                    "authorized": True,
                    "epoch": 0,
                }
            ],
            "discovery_sources": [],
            "discovery_receipts": [
                {
                    "kind": "DISCOVERY_RESULT",
                    "source_id": "S0",
                    "tools": [
                        {
                            "tool_id": "T0",
                            "cost": 2.0,
                            "available": True,
                            "authorized": True,
                            "epoch": 0,
                        }
                    ],
                }
            ],
            "prior_probe_receipts": [],
            "version_events": [],
        }
        self.assertEqual(
            v4.next_action(public),
            {"action": "ESCALATE", "reason": "DISCOVERY_METADATA_CONFLICT"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
