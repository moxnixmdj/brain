from __future__ import annotations

import unittest

from canonical.runtime.tool_universe_gateway_v1 import (
    GatewayError,
    ToolUniverseGateway,
    prove_identity_completeness,
)


BASE = [
    {"tool_id": "alpha", "available": True, "authorized": True, "cost": 2.0, "constraints": {}},
    {"tool_id": "beta", "available": True, "authorized": False, "cost": 1.0, "constraints": {}},
    {"tool_id": "gamma", "available": False, "authorized": True, "cost": 0.5, "constraints": {}},
]


class Tests(unittest.TestCase):
    def test_discovery_is_exact_registry_and_covers_all_invocable_ids(self):
        g = ToolUniverseGateway(BASE, epoch=7)
        out = prove_identity_completeness(g)
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertEqual(out["registry_ids"], ["alpha", "beta", "gamma"])
        self.assertEqual(out["discovered_ids"], ["alpha", "beta", "gamma"])
        self.assertEqual(out["invocable_ids"], ["alpha"])
        self.assertTrue(out["every_invocable_discoverable"])

    def test_unregistered_tool_cannot_be_invoked(self):
        g = ToolUniverseGateway(BASE)
        with self.assertRaisesRegex(GatewayError, "UNREGISTERED_TOOL_ID"):
            g.gate_invoke("hidden", episode_epoch=0)

    def test_unavailable_and_unauthorized_tools_cannot_be_invoked(self):
        g = ToolUniverseGateway(BASE)
        with self.assertRaisesRegex(GatewayError, "TOOL_UNAUTHORIZED"):
            g.gate_invoke("beta", episode_epoch=0)
        with self.assertRaisesRegex(GatewayError, "TOOL_UNAVAILABLE"):
            g.gate_invoke("gamma", episode_epoch=0)

    def test_registry_change_advances_epoch_and_forces_restart(self):
        g = ToolUniverseGateway(BASE, epoch=4)
        old = g.epoch
        new = g.replace_registry(BASE + [
            {"tool_id": "delta", "available": True, "authorized": True, "cost": 3.0, "constraints": {}},
        ])
        self.assertEqual(new, old + 1)
        with self.assertRaisesRegex(GatewayError, "EPOCH_CHANGED_RESTART_EPISODE"):
            g.gate_invoke("alpha", episode_epoch=old)
        self.assertEqual(g.gate_invoke("delta", episode_epoch=new).tool_id, "delta")

    def test_duplicate_ids_fail_closed(self):
        with self.assertRaisesRegex(GatewayError, "DUPLICATE_TOOL_ID"):
            ToolUniverseGateway(BASE + [BASE[0]])

    def test_discovery_digest_changes_with_registry_epoch(self):
        g = ToolUniverseGateway(BASE)
        a = g.discover()["registry_digest_sha256"]
        g.replace_registry(BASE)
        b = g.discover()["registry_digest_sha256"]
        self.assertNotEqual(a, b)

    def test_zero_credit_and_no_authority(self):
        out = prove_identity_completeness(ToolUniverseGateway(BASE))
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
