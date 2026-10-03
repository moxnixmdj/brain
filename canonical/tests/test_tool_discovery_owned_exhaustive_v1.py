from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime.tool_discovery_owned_exhaustive_v1 import (
    apply_discovery,
    gate_selection,
    new_episode,
    next_action,
    record_probe_result,
)
from canonical.runtime.tool_universe_gateway_v1 import (
    GatewayError,
    ToolUniverseGateway,
)


def entry(tid: str, cost: float, *, available: bool = True, authorized: bool = True):
    return {
        "tool_id": tid,
        "available": available,
        "authorized": authorized,
        "cost": cost,
        "constraints": {},
    }


class Tests(unittest.TestCase):
    def test_exact_v3_global_cost_counterexample_is_real(self):
        public = {
            "required_capabilities": ["CAP_A"],
            "visible_tools": [dict(entry("EXPENSIVE", 10), epoch=0)],
            "discovery_sources": [{"source_id": "S0", "cost": 0.1, "available": True}],
            "discovery_receipts": [],
            "prior_probe_receipts": [{
                "kind": "SAFE_CAPABILITY_PROBE",
                "tool_id": "EXPENSIVE",
                "capability": "CAP_A",
                "epoch": 0,
                "supported": True,
            }],
            "version_events": [],
        }
        self.assertEqual(
            v3.next_action(public),
            {"action": "SELECT", "tool_id": "EXPENSIVE"},
        )

    def test_owned_exhaustive_route_discovers_before_select_and_picks_cheapest(self):
        gateway = ToolUniverseGateway([
            entry("EXPENSIVE", 10),
            entry("CHEAP", 1),
        ])
        state = new_episode(gateway, required_capabilities=["CAP_A"])

        a1 = next_action(gateway, state)
        self.assertEqual(a1["action"], "DISCOVER")
        apply_discovery(gateway, state, a1)

        a2 = next_action(gateway, state)
        self.assertEqual(
            a2,
            {"action": "PROBE", "tool_id": "CHEAP", "capability": "CAP_A"},
        )
        record_probe_result(gateway, state, a2, supported=True)

        a3 = next_action(gateway, state)
        self.assertEqual(a3, {"action": "SELECT", "tool_id": "CHEAP"})
        selected = gate_selection(gateway, state, a3)
        self.assertEqual(selected.tool_id, "CHEAP")

    def test_cheaper_false_route_is_disproved_before_later_true_route(self):
        gateway = ToolUniverseGateway([entry("T0", 1), entry("T1", 2)])
        state = new_episode(gateway, required_capabilities=["CAP_A"])
        apply_discovery(gateway, state, next_action(gateway, state))

        first = next_action(gateway, state)
        self.assertEqual(first["tool_id"], "T0")
        record_probe_result(gateway, state, first, supported=False)

        second = next_action(gateway, state)
        self.assertEqual(second["tool_id"], "T1")
        record_probe_result(gateway, state, second, supported=True)

        final = next_action(gateway, state)
        self.assertEqual(final, {"action": "SELECT", "tool_id": "T1"})

    def test_registry_change_invalidates_entire_episode(self):
        gateway = ToolUniverseGateway([entry("T0", 1)], epoch=4)
        state = new_episode(gateway, required_capabilities=["CAP_A"])
        apply_discovery(gateway, state, next_action(gateway, state))
        probe = next_action(gateway, state)
        record_probe_result(gateway, state, probe, supported=True)
        self.assertEqual(next_action(gateway, state)["action"], "SELECT")

        gateway.replace_registry([entry("T0", 1), entry("NEW", 0.5)])
        out = next_action(gateway, state)
        self.assertEqual(out["action"], "ESCALATE")
        self.assertEqual(out["reason"], "REGISTRY_EPOCH_CHANGED_RESTART_EPISODE")
        with self.assertRaisesRegex(GatewayError, "EPOCH_CHANGED"):
            gate_selection(gateway, state, {"action": "SELECT", "tool_id": "T0"})

    def test_unregistered_identity_is_not_invocable(self):
        gateway = ToolUniverseGateway([entry("T0", 1)])
        state = new_episode(gateway, required_capabilities=["CAP_A"])
        with self.assertRaisesRegex(GatewayError, "UNREGISTERED_TOOL_ID"):
            gate_selection(gateway, state, {"action": "SELECT", "tool_id": "HIDDEN"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
