from __future__ import annotations
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4
from canonical.runtime import tool_discovery_dynamic_proof_v3 as proof


def tool(tid,cost):
    return {
        "tool_id":tid,
        "cost":cost,
        "available":True,
        "authorized":True,
        "epoch":0,
        "region":"GLOBAL",
        "risk":0,
        "tags":[],
    }


class DynamicV4Tests(unittest.TestCase):
    def test_v3_counterexample_selects_visible_expensive_before_discovery(self):
        public={
            "required_capabilities":["CAP_A"],
            "constraint":None,
            "visible_tools":[tool("EXPENSIVE",10.0)],
            "discovery_sources":[{"source_id":"AUTH","cost":0.1,"available":True}],
            "discovery_receipts":[],
            "prior_probe_receipts":[{
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":"EXPENSIVE",
                "capability":"CAP_A",
                "epoch":0,
                "supported":True,
            }],
            "version_events":[],
        }
        self.assertEqual(
            v3.next_action(public),
            {"action":"SELECT","tool_id":"EXPENSIVE"},
        )
        self.assertEqual(v4.next_action(public)["action"],"DISCOVER")

    def test_v4_discovers_hidden_cheaper_then_selects_it(self):
        public={
            "required_capabilities":["CAP_A"],
            "constraint":None,
            "visible_tools":[tool("EXPENSIVE",10.0)],
            "discovery_sources":[{"source_id":"AUTH","cost":0.1,"available":True}],
            "discovery_receipts":[],
            "prior_probe_receipts":[{
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":"EXPENSIVE",
                "capability":"CAP_A",
                "epoch":0,
                "supported":True,
            }],
            "version_events":[],
        }
        a1=v4.next_action(public)
        self.assertEqual(a1["action"],"DISCOVER")
        self.assertEqual(a1["source_id"],"AUTH")

        public["discovery_receipts"]=[
            {"kind":"DISCOVERY_RESULT","source_id":"AUTH"}
        ]
        public["visible_tools"].append(tool("CHEAP",1.0))
        a2=v4.next_action(public)
        self.assertEqual(
            a2,
            {"action":"PROBE","tool_id":"CHEAP","capability":"CAP_A"},
        )

        public["prior_probe_receipts"].append({
            "kind":"SAFE_CAPABILITY_PROBE",
            "tool_id":"CHEAP",
            "capability":"CAP_A",
            "epoch":0,
            "supported":True,
        })
        self.assertEqual(
            v4.next_action(public),
            {"action":"SELECT","tool_id":"CHEAP"},
        )

    def test_all_available_sources_must_be_discovered_before_selection(self):
        public={
            "required_capabilities":["CAP_A"],
            "constraint":None,
            "visible_tools":[tool("VISIBLE",3.0)],
            "discovery_sources":[
                {"source_id":"S2","cost":2.0,"available":True},
                {"source_id":"S1","cost":1.0,"available":True},
            ],
            "discovery_receipts":[],
            "prior_probe_receipts":[{
                "kind":"SAFE_CAPABILITY_PROBE",
                "tool_id":"VISIBLE","capability":"CAP_A","epoch":0,"supported":True,
            }],
            "version_events":[],
        }
        self.assertEqual(v4.next_action(public)["source_id"],"S1")
        public["discovery_receipts"].append({"kind":"DISCOVERY_RESULT","source_id":"S1"})
        self.assertEqual(v4.next_action(public)["source_id"],"S2")
        public["discovery_receipts"].append({"kind":"DISCOVERY_RESULT","source_id":"S2"})
        self.assertEqual(v4.next_action(public),{"action":"SELECT","tool_id":"VISIBLE"})

    def test_v4_preserves_broad_v3_dynamic_suite(self):
        out=proof.run_batch(314159,1200,v4)
        self.assertTrue(out["pass"],out)
        self.assertEqual(out["failed"],0)
        self.assertEqual(out["count"],1200)


if __name__=="__main__":
    unittest.main(verbosity=2)
