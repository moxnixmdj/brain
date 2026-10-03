from __future__ import annotations
import unittest
from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime.tool_discovery_v3_owned_gateway_bridge_v1 import (
 BridgeError, apply_gateway_discovery, initial_public, prove_bridge_instance, validate_select,
)
from canonical.runtime.tool_universe_gateway_v2 import GatewayError,ToolUniverseGateway

BASE=[
 {"tool_id":"a","available":True,"authorized":True,"cost":1.0},
 {"tool_id":"b","available":True,"authorized":True,"cost":2.0},
]
class Tests(unittest.TestCase):
    def test_v3_discovers_owned_gateway_then_sees_exact_registry(self):
        g=ToolUniverseGateway(BASE); p=initial_public(g,["x"])
        a=v3.next_action(p); self.assertEqual(a["action"],"DISCOVER")
        p=apply_gateway_discovery(p,g,a)
        self.assertEqual(sorted(x["tool_id"] for x in p["visible_tools"]),["a","b"])
        self.assertEqual(v3.next_action(p),{"action":"PROBE","tool_id":"a","capability":"x"})
    def test_selected_identity_must_pass_gateway(self):
        g=ToolUniverseGateway(BASE); p=initial_public(g,["x"])
        p=apply_gateway_discovery(p,g,v3.next_action(p))
        p["prior_probe_receipts"]=[
          {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"a","capability":"x","epoch":0,"supported":True}
        ]
        a=v3.next_action(p); self.assertEqual(a,{"action":"SELECT","tool_id":"a"})
        self.assertEqual(validate_select(p,g,a).tool_id,"a")
    def test_registry_change_forces_restart(self):
        g=ToolUniverseGateway(BASE); p=initial_public(g,["x"])
        g.replace_registry(BASE)
        with self.assertRaisesRegex(BridgeError,"EPOCH_CHANGED"):
            apply_gateway_discovery(p,g,{"action":"DISCOVER","source_id":"BRAIN_OWNED_TOOL_UNIVERSE_GATEWAY_V2"})
        with self.assertRaisesRegex(GatewayError,"EPOCH_CHANGED"):
            validate_select(p,g,{"action":"SELECT","tool_id":"a"})
    def test_bridge_candidate_zero_credit(self):
        out=prove_bridge_instance(BASE); self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertEqual(out["capability_credit_delta"],0); self.assertFalse(out["promotion_authority"])

if __name__=="__main__": unittest.main(verbosity=2)
