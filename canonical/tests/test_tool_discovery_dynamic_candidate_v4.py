from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4


def counterexample_public():
    return {
        "required_capabilities":["CAP_A"],
        "constraint":None,
        "visible_tools":[
            {"tool_id":"EXPENSIVE","cost":10.0,"available":True,"authorized":True,"epoch":0}
        ],
        "discovery_sources":[
            {"source_id":"S0","cost":0.1,"available":True}
        ],
        "discovery_receipts":[],
        "prior_probe_receipts":[
            {
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":"EXPENSIVE",
                "capability":"CAP_A",
                "epoch":0,
                "supported":True,
            }
        ],
        "version_events":[],
    }


class Tests(unittest.TestCase):
    def test_v3_counterexample_selects_before_discovery(self):
        out=v3.next_action(counterexample_public())
        self.assertEqual(out,{"action":"SELECT","tool_id":"EXPENSIVE"})

    def test_v4_discovers_before_any_probe_or_select(self):
        out=v4.next_action(counterexample_public())
        self.assertEqual(out,{"action":"DISCOVER","source_id":"S0","query":"CAP_A"})

    def test_v4_then_probes_and_selects_cheaper_discovered_tool(self):
        p=counterexample_public()
        p["visible_tools"].append(
            {"tool_id":"CHEAP","cost":1.0,"available":True,"authorized":True,"epoch":0}
        )
        p["discovery_receipts"].append(
            {"kind":"DISCOVERY_RESULT","source_id":"S0","tools":[{"tool_id":"CHEAP"}]}
        )
        probe=v4.next_action(p)
        self.assertEqual(probe,{"action":"PROBE","tool_id":"CHEAP","capability":"CAP_A"})
        p["prior_probe_receipts"].append(
            {
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":"CHEAP",
                "capability":"CAP_A",
                "epoch":0,
                "supported":True,
            }
        )
        self.assertEqual(v4.next_action(p),{"action":"SELECT","tool_id":"CHEAP"})

    def test_v4_exhausts_multiple_sources_in_stable_order(self):
        p=counterexample_public()
        p["discovery_sources"]=[
            {"source_id":"S1","cost":2.0,"available":True},
            {"source_id":"S0","cost":1.0,"available":True},
        ]
        self.assertEqual(v4.next_action(p)["source_id"],"S0")
        p["discovery_receipts"].append({"kind":"DISCOVERY_RESULT","source_id":"S0","tools":[]})
        self.assertEqual(v4.next_action(p)["source_id"],"S1")

    def test_no_required_capability_does_not_discover_pointlessly(self):
        p=counterexample_public()
        p["required_capabilities"]=[]
        self.assertEqual(v4.next_action(p)["reason"],"NO_REQUIRED_CAPABILITIES")


if __name__=="__main__":
    unittest.main(verbosity=2)
