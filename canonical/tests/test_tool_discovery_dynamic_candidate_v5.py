from __future__ import annotations
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4
from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5


def source(tools=None, **overrides):
    rows=list(tools or [])
    out={
        "source_id":"AUTH","cost":0.1,"available":True,"authorized":True,
        "authoritative":True,"source_epoch":7,"source_digest":v5._tools_digest(rows),
    }
    out.update(overrides)
    return out


def base(source_tools=None):
    return {
        "required_capabilities":["CAP_A"],
        "constraint":None,
        "visible_tools":[],
        "prior_probe_receipts":[],
        "discovery_sources":[source(source_tools)],
        "discovery_receipts":[],
        "version_events":[],
        "decision_epoch":3,
    }


def complete_receipt(*, tools=None, **overrides):
    rows=list(tools or [])
    src=source(rows)
    rec={
        "kind":"DISCOVERY_RESULT","source_id":"AUTH","complete":True,
        "decision_epoch":3,"source_epoch":7,"source_digest":src["source_digest"],
        "source_set_digest":v5._source_set_digest([src]),"query":"CAP_A",
        "tools":rows,
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
        cheap={
            "tool_id":"CHEAP","cost":1.0,"available":True,
            "authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"],
        }
        p=base([cheap])
        p["visible_tools"]=[{
            "tool_id":"EXPENSIVE","cost":10.0,"available":True,
            "authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"],
        }]
        p["prior_probe_receipts"]=[{
            "kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE",
            "capability":"CAP_A","epoch":0,"supported":True,
        }]
        p["discovery_receipts"]=[complete_receipt(tools=[cheap])]
        self.assertEqual(v5.next_action(p),{"action":"PROBE","tool_id":"CHEAP","capability":"CAP_A"})
        p["prior_probe_receipts"].append({
            "kind":"SAFE_CAPABILITY_PROBE","tool_id":"CHEAP",
            "capability":"CAP_A","epoch":0,"supported":True,
        })
        self.assertEqual(v5.next_action(p),{"action":"SELECT","tool_id":"CHEAP"})

    def test_conflicting_identity_metadata_fails_closed(self):
        discovered={
            "tool_id":"T","cost":1.0,"available":True,"authorized":True,
            "epoch":0,"safe_probe_capabilities":["CAP_A"],
        }
        p=base([discovered])
        p["visible_tools"]=[{
            "tool_id":"T","cost":2.0,"available":True,"authorized":True,
            "epoch":0,"safe_probe_capabilities":["CAP_A"],
        }]
        p["discovery_receipts"]=[complete_receipt(tools=[discovered])]
        self.assertEqual(v5.next_action(p),{"action":"ESCALATE","reason":"DISCOVERY_METADATA_CONFLICT"})

    def test_unprobeable_cheaper_unknown_blocks_more_expensive_selection(self):
        p=base()
        p["discovery_sources"]=[]
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
        empty=v5._tools_digest([])
        p["discovery_sources"]=[
            {"source_id":"NO","cost":0.0,"available":True,"authorized":False,"authoritative":True,"source_epoch":0,"source_digest":empty},
            {"source_id":"HINT","cost":0.0,"available":True,"authorized":True,"authoritative":False,"source_epoch":0,"source_digest":empty},
        ]
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


    def test_exact_current_v4_stale_receipt_suppresses_required_rediscovery(self):
        p=base()
        p["visible_tools"]=[{
            "tool_id":"EXPENSIVE","cost":10.0,"available":True,
            "authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"],
        }]
        p["prior_probe_receipts"]=[{
            "kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE",
            "capability":"CAP_A","epoch":0,"supported":True,
        }]
        p["discovery_receipts"]=[complete_receipt(decision_epoch=2)]
        self.assertEqual(v4.next_action(p),{"action":"SELECT","tool_id":"EXPENSIVE"})
        self.assertEqual(v5.next_action(p),{"action":"DISCOVER","source_id":"AUTH","query":"CAP_A"})

    def test_exact_current_v4_does_not_merge_discovered_cheaper_identity(self):
        cheap={
            "tool_id":"CHEAP","cost":1.0,"available":True,
            "authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"],
        }
        p=base([cheap])
        p["visible_tools"]=[{
            "tool_id":"EXPENSIVE","cost":10.0,"available":True,
            "authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"],
        }]
        p["prior_probe_receipts"]=[{
            "kind":"SAFE_CAPABILITY_PROBE","tool_id":"EXPENSIVE",
            "capability":"CAP_A","epoch":0,"supported":True,
        }]
        p["discovery_receipts"]=[complete_receipt(tools=[cheap])]
        self.assertEqual(v4.next_action(p),{"action":"SELECT","tool_id":"EXPENSIVE"})
        self.assertEqual(v5.next_action(p),{"action":"PROBE","tool_id":"CHEAP","capability":"CAP_A"})

    def test_exact_current_v4_issues_probe_without_explicit_safe_probe_permission(self):
        p=base()
        p["discovery_sources"]=[]
        p["visible_tools"]=[{
            "tool_id":"CHEAP","cost":1.0,"available":True,
            "authorized":True,"epoch":0,"safe_probe_capabilities":[],
        }]
        self.assertEqual(v4.next_action(p),{"action":"PROBE","tool_id":"CHEAP","capability":"CAP_A"})
        self.assertEqual(v5.next_action(p),{
            "action":"ESCALATE",
            "reason":"CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
            "tool_id":"CHEAP",
        })


    def test_receipt_result_digest_is_computed_not_trusted(self):
        p=base()
        forged=complete_receipt(tools=[{
            "tool_id":"FORGED","cost":0.0,"available":True,
            "authorized":True,"epoch":0,"safe_probe_capabilities":["CAP_A"],
        }])
        # Receipt claims the empty source digest, but its actual tool content differs.
        forged["source_digest"]=source([])["source_digest"]
        forged["source_set_digest"]=v5._source_set_digest([source([])])
        p["discovery_receipts"]=[forged]
        self.assertEqual(v5.next_action(p),{"action":"DISCOVER","source_id":"AUTH","query":"CAP_A"})

    def test_undeclared_source_authority_fails_closed(self):
        p=base()
        del p["discovery_sources"][0]["authoritative"]
        self.assertEqual(
            v5.next_action(p),
            {"action":"ESCALATE","reason":"DISCOVERY_SOURCE_AUTHORITATIVE_UNDECLARED"},
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
