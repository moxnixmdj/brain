from __future__ import annotations
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5


def source():
    return {
        "source_id":"AUTH","cost":0.1,"available":True,"authorized":True,
        "authoritative":True,"source_epoch":7,"source_digest":"sha256:source7",
    }


def base():
    return {
        "required_capabilities":["CAP_A"],
        "constraint":None,
        "visible_tools":[],
        "prior_probe_receipts":[],
        "discovery_sources":[source()],
        "discovery_receipts":[],
        "version_events":[],
        "decision_epoch":3,
        "source_set_digest":"sha256:set3",
    }


def complete_receipt(*, tools=None, **overrides):
    rec={
        "kind":"DISCOVERY_RESULT","source_id":"AUTH","complete":True,
        "decision_epoch":3,"source_epoch":7,"source_digest":"sha256:source7",
        "source_set_digest":"sha256:set3","query":"CAP_A",
        "tools":list(tools or []),
    }
    rec.update(overrides)
    return rec


class Tests(unittest.TestCase):
    def test_v3_counterexample_and_v5_discovery_first(self):
        p=base()
        p["visible_tools"]=[{
            "tool_id":"EXPENSIVE","cost":10.0,"available":True,
            "authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"],
        }]
        p["prior_probe_receipts"]=[{
            "kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE",
            "capability":"CAP_A","epoch":0,"supported":True,
        }]
        # V3 ignores all the new binding fields and still commits prematurely.
        self.assertEqual(v3.next_action(p),{"action":"SELECT","tool_id":"EXPENSIVE"})
        self.assertEqual(v5.next_action(p),{"action":"DISCOVER","source_id":"AUTH","query":"CAP_A"})

    def test_stale_or_partial_or_wrong_query_receipt_cannot_suppress_discovery(self):
        mutations=[
            {"decision_epoch":2},
            {"complete":False},
            {"query":"CAP_B"},
            {"source_epoch":6},
            {"source_digest":"sha256:old"},
            {"source_set_digest":"sha256:oldset"},
        ]
        for m in mutations:
            p=base(); p["discovery_receipts"]=[complete_receipt(**m)]
            self.assertEqual(
                v5.next_action(p),
                {"action":"DISCOVER","source_id":"AUTH","query":"CAP_A"},
                m,
            )

    def test_discovered_tools_are_merged_and_cheapest_is_probed_first(self):
        p=base()
        p["visible_tools"]=[{
            "tool_id":"EXPENSIVE","cost":10.0,"available":True,
            "authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"],
        }]
        p["prior_probe_receipts"]=[{
            "kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE",
            "capability":"CAP_A","epoch":0,"supported":True,
        }]
        cheap={
            "tool_id":"CHEAP","cost":1.0,"available":True,
            "authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"],
        }
        p["discovery_receipts"]=[complete_receipt(tools=[cheap])]
        self.assertEqual(v5.next_action(p),{"action":"PROBE","tool_id":"CHEAP","capability":"CAP_A"})
        p["prior_probe_receipts"].append({
            "kind":"SAFE_CAPABILITY_PROBE","tool_id":"CHEAP",
            "capability":"CAP_A","epoch":0,"supported":True,
        })
        self.assertEqual(v5.next_action(p),{"action":"SELECT","tool_id":"CHEAP"})

    def test_conflicting_identity_metadata_fails_closed(self):
        p=base()
        p["visible_tools"]=[{
            "tool_id":"T","cost":2.0,"available":True,"authorized":True,
            "epoch":0,"safe_probe_capabilities":["CAP_A"],
        }]
        p["discovery_receipts"]=[complete_receipt(tools=[{
            "tool_id":"T","cost":1.0,"available":True,"authorized":True,
            "epoch":0,"safe_probe_capabilities":["CAP_A"],
        }])]
        self.assertEqual(v5.next_action(p),{"action":"ESCALATE","reason":"DISCOVERY_METADATA_CONFLICT"})

    def test_unprobeable_cheaper_unknown_blocks_more_expensive_selection(self):
        p=base()
        p["discovery_sources"]=[]
        p["source_set_digest"]=""
        p["visible_tools"]=[
            {"tool_id":"CHEAP","cost":1.0,"available":True,"authorized":True,"epoch":0,"safe_probe_capabilities":[]},
            {"tool_id":"EXPENSIVE","cost":2.0,"available":True,"authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"]},
        ]
        p["prior_probe_receipts"]=[{
            "kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE",
            "capability":"CAP_A","epoch":0,"supported":True,
        }]
        self.assertEqual(v5.next_action(p),{
            "action":"ESCALATE",
            "reason":"CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
            "tool_id":"CHEAP",
        })

    def test_negative_cheaper_evidence_allows_verified_expensive_selection(self):
        p=base(); p["discovery_sources"]=[]; p["source_set_digest"]=""
        p["visible_tools"]=[
            {"tool_id":"CHEAP","cost":1.0,"available":True,"authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"]},
            {"tool_id":"EXPENSIVE","cost":2.0,"available":True,"authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"]},
        ]
        p["prior_probe_receipts"]=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"CHEAP","capability":"CAP_A","epoch":0,"supported":False},
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE","capability":"CAP_A","epoch":0,"supported":True},
        ]
        self.assertEqual(v5.next_action(p),{"action":"SELECT","tool_id":"EXPENSIVE"})

    def test_tool_version_change_invalidates_positive_probe(self):
        p=base(); p["discovery_sources"]=[]; p["source_set_digest"]=""
        p["visible_tools"]=[{
            "tool_id":"T","cost":1.0,"available":True,"authorized":True,
            "epoch":0,"safe_probe_capabilities":["CAP_A"],
        }]
        p["prior_probe_receipts"]=[{
            "kind":"SAFE_CAPABILITY_PROBE","tool_id":"T","capability":"CAP_A","epoch":0,"supported":True,
        }]
        p["version_events"]=[{"kind":"TOOL_VERSION_CHANGED","tool_id":"T","new_epoch":1}]
        self.assertEqual(v5.next_action(p),{"action":"PROBE","tool_id":"T","capability":"CAP_A"})

    def test_conflicting_current_probe_receipts_fail_closed(self):
        p=base(); p["discovery_sources"]=[]; p["source_set_digest"]=""
        p["visible_tools"]=[{
            "tool_id":"T","cost":1.0,"available":True,"authorized":True,
            "epoch":0,"safe_probe_capabilities":["CAP_A"],
        }]
        p["prior_probe_receipts"]=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T","capability":"CAP_A","epoch":0,"supported":True},
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T","capability":"CAP_A","epoch":0,"supported":False},
        ]
        self.assertEqual(v5.next_action(p),{"action":"ESCALATE","reason":"CONFLICTING_CURRENT_PROBE_RECEIPTS"})

    def test_unauthorized_or_nonauthoritative_source_does_not_block(self):
        p=base()
        p["discovery_sources"]=[
            {"source_id":"NO","cost":0.0,"available":True,"authorized":False,"authoritative":True,"source_epoch":0,"source_digest":"x"},
            {"source_id":"HINT","cost":0.0,"available":True,"authorized":True,"authoritative":False},
        ]
        p["source_set_digest"]=""
        p["visible_tools"]=[{
            "tool_id":"T","cost":1.0,"available":True,"authorized":True,
            "epoch":0,"safe_probe_capabilities":["CAP_A"],
        }]
        p["prior_probe_receipts"]=[{
            "kind":"SAFE_CAPABILITY_PROBE","tool_id":"T","capability":"CAP_A","epoch":0,"supported":True,
        }]
        self.assertEqual(v5.next_action(p),{"action":"SELECT","tool_id":"T"})

    def test_no_route_only_after_complete_discovery(self):
        p=base(); p["discovery_receipts"]=[complete_receipt(tools=[])]
        self.assertEqual(v5.next_action(p),{
            "action":"ESCALATE","reason":"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY"
        })


if __name__=="__main__":
    unittest.main(verbosity=2)
