from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4
from canonical.runtime import tool_discovery_dynamic_proof_v3 as proof


def hidden_cheaper_state():
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
        "prior_probe_receipts": [
            {
                "kind": "SAFE_CAPABILITY_PROBE",
                "tool_id": "T0",
                "capability": "CAP_A",
                "epoch": 0,
                "supported": True,
            }
        ],
        "discovery_receipts": [],
        "version_events": [],
    }


class ToolDiscoveryDynamicV4Tests(unittest.TestCase):
    def test_v3_counterexample_selects_visible_expensive_route_too_early(self):
        public = hidden_cheaper_state()
        self.assertEqual(v3.next_action(public), {"action": "SELECT", "tool_id": "T0"})

    def test_v4_forbids_selection_while_discovery_source_remains(self):
        public = hidden_cheaper_state()
        self.assertEqual(
            v4.next_action(public),
            {"action": "DISCOVER", "source_id": "S0", "query": "CAP_A"},
        )

    def test_v4_selects_hidden_cheaper_route_after_complete_discovery_and_probe(self):
        public = hidden_cheaper_state()
        public["visible_tools"].append(
            {
                "tool_id": "T1",
                "cost": 1.0,
                "available": True,
                "authorized": True,
                "epoch": 0,
            }
        )
        public["discovery_receipts"] = [
            {"kind": "DISCOVERY_RESULT", "source_id": "S0"}
        ]
        self.assertEqual(
            v4.next_action(public),
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
        self.assertEqual(v4.next_action(public), {"action": "SELECT", "tool_id": "T1"})

    def test_v4_has_no_regression_on_any_v3_passing_case_in_1200_case_grid(self):
        regressions = []
        v3_passes = 0
        v4_passes = 0
        for ordinal in range(1200):
            case = proof.generate_case(20261002, ordinal)
            old = proof.score_episode(case, v3.next_action)
            new = proof.score_episode(case, v4.next_action)
            if old["pass"]:
                v3_passes += 1
                if not new["pass"]:
                    regressions.append(
                        {
                            "ordinal": ordinal,
                            "class": case["case_class"],
                            "old": old,
                            "new": new,
                        }
                    )
            if new["pass"]:
                v4_passes += 1
        self.assertGreater(v3_passes, 0)
        self.assertGreaterEqual(v4_passes, v3_passes)
        self.assertEqual(regressions, [])

    def test_v4_preserves_transfer_and_version_invalidation(self):
        transfer = proof.score_episode(proof.generate_case(101, 3), v4.next_action)
        changed = proof.score_episode(proof.generate_case(102, 4), v4.next_action)
        self.assertTrue(transfer["pass"], transfer)
        self.assertTrue(changed["pass"], changed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
