from __future__ import annotations
import unittest
from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime.tool_discovery_v3_owned_gateway_bridge_v1 import (
 BridgeError, apply_gateway_discovery, initial_public, prove_bridge_instance,
 validate_probe, validate_select,
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
        probe=v3.next_action(p)
        self.assertEqual(probe,{"action":"PROBE","tool_id":"a","capability":"x"})
        self.assertEqual(validate_probe(p,g,probe).tool_id,"a")
    def test_selected_identity_must_pass_gateway(self):
        g=ToolUniverseGateway(BASE); p=initial_public(g,["x"])
        p=apply_gateway_discovery(p,g,v3.next_action(p))
        p["prior_probe_receipts"]=[
          {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"a","capability":"x","epoch":0,"supported":True}
        ]
        a=v3.next_action(p); self.assertEqual(a,{"action":"SELECT","tool_id":"a"})
        self.assertEqual(validate_select(p,g,a).tool_id,"a")
    def test_registry_change_forces_restart_before_discovery_probe_or_select(self):
        g=ToolUniverseGateway(BASE); p=initial_public(g,["x"])
        p_discovered=apply_gateway_discovery(p,g,v3.next_action(p))
        stale_probe=v3.next_action(p_discovered)
        self.assertEqual(stale_probe["action"],"PROBE")
        g.replace_registry(BASE)
        with self.assertRaisesRegex(BridgeError,"EPOCH_CHANGED"):
            apply_gateway_discovery(p,g,{"action":"DISCOVER","source_id":"BRAIN_OWNED_TOOL_UNIVERSE_GATEWAY_V2"})
        with self.assertRaisesRegex(GatewayError,"EPOCH_CHANGED"):
            validate_probe(p_discovered,g,stale_probe)
        with self.assertRaisesRegex(GatewayError,"EPOCH_CHANGED"):
            validate_select(p_discovered,g,{"action":"SELECT","tool_id":"a"})
    def test_probe_and_select_reject_unregistered_identity(self):
        g=ToolUniverseGateway(BASE); p=initial_public(g,["x"])
        with self.assertRaisesRegex(GatewayError,"UNREGISTERED"):
            validate_probe(p,g,{"action":"PROBE","tool_id":"hidden","capability":"x"})
        with self.assertRaisesRegex(GatewayError,"UNREGISTERED"):
            validate_select(p,g,{"action":"SELECT","tool_id":"hidden"})
    def test_bridge_candidate_zero_credit(self):
        out=prove_bridge_instance(BASE); self.assertTrue(out["status"].startswith("PASS"),out)
        self.assertTrue(out["probe_must_pass_gateway"])
        self.assertEqual(out["capability_credit_delta"],0); self.assertFalse(out["promotion_authority"])

if __name__=="__main__": unittest.main(verbosity=2)
