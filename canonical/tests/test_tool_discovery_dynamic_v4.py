import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v4 as c
from canonical.runtime import tool_discovery_dynamic_proof_v3 as p


class ToolDiscoveryDynamicV4Tests(unittest.TestCase):
    def test_v3_full_grid_still_passes(self):
        out=p.run_batch(20261002,1200,c.next_action)
        self.assertTrue(out["pass"],out["failures"][:5])
        self.assertEqual(out["failed"],0)

    def test_hidden_cheaper_route_blocks_premature_visible_selection(self):
        public={
            "required_capabilities":["CAP_A"],
            "constraint":None,
            "visible_tools":[
                {"tool_id":"EXPENSIVE","cost":10.0,"available":True,"authorized":True,"epoch":0},
            ],
            "prior_probe_receipts":[
                {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE","capability":"CAP_A","epoch":0,"supported":True},
            ],
            "discovery_sources":[
                {"source_id":"AUTH","cost":0.1,"available":True},
            ],
            "discovery_receipts":[],
            "version_events":[],
        }
        self.assertEqual(
            c.next_action(public),
            {"action":"DISCOVER","source_id":"AUTH","query":"CAP_A"},
        )

    def test_after_complete_discovery_cheaper_route_is_probed_first(self):
        public={
            "required_capabilities":["CAP_A"],
            "constraint":None,
            "visible_tools":[
                {"tool_id":"CHEAP","cost":1.0,"available":True,"authorized":True,"epoch":0},
                {"tool_id":"EXPENSIVE","cost":10.0,"available":True,"authorized":True,"epoch":0},
            ],
            "prior_probe_receipts":[
                {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE","capability":"CAP_A","epoch":0,"supported":True},
            ],
            "discovery_sources":[{"source_id":"AUTH","cost":0.1,"available":True}],
            "discovery_receipts":[{"kind":"DISCOVERY_RESULT","source_id":"AUTH"}],
            "version_events":[],
        }
        self.assertEqual(
            c.next_action(public),
            {"action":"PROBE","tool_id":"CHEAP","capability":"CAP_A"},
        )
        public["prior_probe_receipts"].append(
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"CHEAP","capability":"CAP_A","epoch":0,"supported":True}
        )
        self.assertEqual(
            c.next_action(public),
            {"action":"SELECT","tool_id":"CHEAP"},
        )

    def test_negative_cheaper_probe_allows_evidenced_expensive_route(self):
        public={
            "required_capabilities":["CAP_A"],
            "constraint":None,
            "visible_tools":[
                {"tool_id":"CHEAP","cost":1.0,"available":True,"authorized":True,"epoch":0},
                {"tool_id":"EXPENSIVE","cost":10.0,"available":True,"authorized":True,"epoch":0},
            ],
            "prior_probe_receipts":[
                {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"CHEAP","capability":"CAP_A","epoch":0,"supported":False},
                {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE","capability":"CAP_A","epoch":0,"supported":True},
            ],
            "discovery_sources":[{"source_id":"AUTH","cost":0.1,"available":True}],
            "discovery_receipts":[{"kind":"DISCOVERY_RESULT","source_id":"AUTH"}],
            "version_events":[],
        }
        self.assertEqual(
            c.next_action(public),
            {"action":"SELECT","tool_id":"EXPENSIVE"},
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
