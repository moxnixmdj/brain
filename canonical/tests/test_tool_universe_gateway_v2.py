from __future__ import annotations
import unittest
from canonical.runtime.tool_universe_gateway_v2 import (
    GatewayError, ToolUniverseGateway, prove_identity_completeness,
)

BASE=[
 {"tool_id":"alpha","available":True,"authorized":True,"cost":2.0},
 {"tool_id":"beta","available":True,"authorized":False,"cost":1.0},
 {"tool_id":"gamma","available":False,"authorized":True,"cost":0.5},
]

class Tests(unittest.TestCase):
    def test_exact_registry_discovery_and_invocable_subset(self):
        g=ToolUniverseGateway(BASE,epoch=7); out=prove_identity_completeness(g)
        self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertEqual(out["registry_ids"],["alpha","beta","gamma"])
        self.assertEqual(out["discovered_ids"],["alpha","beta","gamma"])
        self.assertEqual(out["invocable_ids"],["alpha"])
        self.assertTrue(out["discovery_epoch_bound"])
    def test_unregistered_unavailable_unauthorized_fail_closed(self):
        g=ToolUniverseGateway(BASE)
        with self.assertRaisesRegex(GatewayError,"UNREGISTERED"): g.gate_invoke("hidden",episode_epoch=0)
        with self.assertRaisesRegex(GatewayError,"UNAUTHORIZED"): g.gate_invoke("beta",episode_epoch=0)
        with self.assertRaisesRegex(GatewayError,"UNAVAILABLE"): g.gate_invoke("gamma",episode_epoch=0)
    def test_registry_change_advances_epoch_and_stale_episode_fails(self):
        g=ToolUniverseGateway(BASE,epoch=4); old=g.epoch
        new=g.replace_registry(BASE+[{"tool_id":"delta","available":True,"authorized":True,"cost":3.0}])
        self.assertEqual(new,old+1)
        with self.assertRaisesRegex(GatewayError,"EPOCH_CHANGED"): g.gate_invoke("alpha",episode_epoch=old)
        self.assertEqual(g.gate_invoke("delta",episode_epoch=new).tool_id,"delta")
    def test_invalid_registry_fails_closed(self):
        with self.assertRaisesRegex(GatewayError,"DUPLICATE"): ToolUniverseGateway(BASE+[BASE[0]])
        with self.assertRaisesRegex(GatewayError,"INVALID_COST"): ToolUniverseGateway([{"tool_id":"x","available":True,"authorized":True,"cost":-1}])
    def test_zero_credit(self):
        out=prove_identity_completeness(ToolUniverseGateway(BASE))
        self.assertEqual(out["capability_credit_delta"],0); self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"]); self.assertFalse(out["promotion_authority"])

if __name__=="__main__": unittest.main(verbosity=2)
