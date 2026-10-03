from __future__ import annotations

import math
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v6 as v6
from canonical.runtime import tool_discovery_dynamic_candidate_v7 as v7
from canonical.tests.test_tool_discovery_dynamic_candidate_v6 import stale_metadata_state


def visible_state(cost):
    return {
        "required_capabilities": ["CAP_A"],
        "decision_epoch": 0,
        "constraint": None,
        "visible_tools": [{
            "tool_id": "T0",
            "epoch": 0,
            "cost": cost,
            "available": True,
            "authorized": True,
            "safe_probe_capabilities": ["CAP_A"],
        }],
        "discovery_sources": [],
        "discovery_receipts": [],
        "prior_probe_receipts": [{
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": "T0",
            "capability": "CAP_A",
            "epoch": 0,
            "supported": True,
        }],
        "version_events": [],
    }


class ToolDiscoveryDynamicV7Tests(unittest.TestCase):
    def test_exact_v6_nan_counterexample_selects(self):
        state = visible_state(float("nan"))
        self.assertEqual(v6.next_action(state), {"action": "SELECT", "tool_id": "T0"})

    def test_v7_rejects_all_nonfinite_and_nonordered_tool_costs(self):
        for value in (float("nan"), float("inf"), float("-inf"), True, -1.0, "1"):
            with self.subTest(value=value):
                out = v7.next_action(visible_state(value))
                self.assertEqual(out, {
                    "action": "ESCALATE",
                    "reason": "TOOL_COST_NOT_FINITE_NONNEGATIVE",
                })

    def test_v7_rejects_nonfinite_source_cost(self):
        state = visible_state(1.0)
        state["discovery_sources"] = [{
            "source_id": "S0",
            "cost": float("nan"),
            "available": True,
            "authorized": True,
            "authoritative": True,
            "source_epoch": 0,
            "source_digest": "sha256:x",
        }]
        self.assertEqual(v7.next_action(state), {
            "action": "ESCALATE",
            "reason": "DISCOVERY_SOURCE_COST_NOT_FINITE_NONNEGATIVE",
        })

    def test_v7_rejects_nonfinite_discovered_tool_cost(self):
        state = visible_state(1.0)
        state["visible_tools"] = []
        state["discovery_receipts"] = [{
            "kind": "DISCOVERY_RESULT",
            "source_id": "S0",
            "tools": [{
                "tool_id": "T1",
                "epoch": 0,
                "cost": float("inf"),
                "available": True,
                "authorized": True,
                "safe_probe_capabilities": ["CAP_A"],
            }],
        }]
        self.assertEqual(v7.next_action(state), {
            "action": "ESCALATE",
            "reason": "TOOL_COST_NOT_FINITE_NONNEGATIVE",
        })

    def test_finite_nonnegative_domain_is_exact(self):
        for value in (0, 0.0, 1, 1.5, 1e300):
            self.assertTrue(v7._finite_nonnegative_cost(value), value)
        for value in (True, False, -0.1, float("nan"), float("inf"), float("-inf"), "0", None):
            self.assertFalse(v7._finite_nonnegative_cost(value), value)

    def test_valid_finite_behavior_is_observationally_identical_to_v6(self):
        for value in (0.0, 1.0, 1000.0):
            state = visible_state(value)
            self.assertEqual(v7.next_action(state), v6.next_action(state))

    def test_v6_version_restart_semantics_are_preserved_before_cost_validation(self):
        state = stale_metadata_state()
        state["discovery_receipts"][0]["tools"][0]["cost"] = float("nan")
        self.assertEqual(v7.next_action(state), v6.next_action(state))
        self.assertEqual(
            v7.next_action(state)["reason"],
            "TOOL_VERSION_CHANGED_RESTART_EPISODE",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
