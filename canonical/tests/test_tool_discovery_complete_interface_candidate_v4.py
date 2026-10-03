from __future__ import annotations
import hashlib
import json
import unittest

from canonical.runtime.tool_discovery_complete_interface_candidate_v4 import next_action
from canonical.runtime import tool_discovery_information_safe_candidate as legacy


def _sha(v):
    raw=json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _registry(sources, epoch=7):
    manifest=sorted(
        [{"source_id":x["source_id"],"epoch":x["epoch"],"cost":float(x["cost"]),
          "available":x["available"],"authorized":x.get("authorized") is True} for x in sources],
        key=lambda x:x["source_id"],
    )
    return {
        "kind":"COMPLETE_DISCOVERY_REGISTRY",
        "complete":True,
        "epoch":epoch,
        "sources":sources,
        "source_manifest_sha256":_sha(manifest),
    }


def _tool(tid,cost,epoch=0,available=True,authorized=True,region="US",safe_probe_allowed=True):
    return {
        "tool_id":tid,"cost":float(cost),"epoch":epoch,
        "available":available,"authorized":authorized,"safe_probe_allowed":safe_probe_allowed,
        "meta":{"region":region},
    }


class Tests(unittest.TestCase):
    def public(self):
        src=[
            {"source_id":"S0","epoch":1,"cost":0.2,"available":True,"authorized":True},
            {"source_id":"S1","epoch":3,"cost":0.1,"available":True,"authorized":True},
        ]
        return {
            "required_capabilities":["CAP_A"],
            "constraint":None,
            "discovery_registry":_registry(src),
            "discovery_receipts":[],
            "prior_probe_receipts":[],
            "tool_version_events":[],
        }

    def test_exact_legacy_projection_without_discovery_registry(self):
        public={
            "required_capabilities":["CAP_A"],
            "tools":[
                {"tool_id":"T0","cost":1.0,"available":True,"authorized":True},
                {"tool_id":"T1","cost":2.0,"available":True,"authorized":True},
            ],
            "prior_probe_receipts":[
                {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A","epoch":0,"supported":True}
            ],
            "version_events":[],
        }
        self.assertEqual(next_action(public), legacy.next_action(public))

    def test_registry_manifest_binds_cost_and_authorization(self):
        p=self.public()
        p["discovery_registry"]["sources"][0]["cost"]=999
        a=next_action(p)
        self.assertEqual(a["action"],"ESCALATE")
        self.assertIn("MANIFEST_MISMATCH",a["reason"])

        p=self.public()
        p["discovery_registry"]["sources"][0]["authorized"]=False
        a=next_action(p)
        self.assertEqual(a["action"],"ESCALATE")
        self.assertIn("MANIFEST_MISMATCH",a["reason"])

    def test_unauthorized_source_is_not_queried(self):
        p=self.public()
        p["discovery_registry"]["sources"][1]["authorized"]=False
        # Recompute the manifest after an authority change: semantics are now
        # different but internally consistent.
        p["discovery_registry"]=_registry(p["discovery_registry"]["sources"])
        a=next_action(p)
        self.assertEqual(a["action"],"DISCOVER")
        self.assertEqual(a["source_id"],"S0")

    def test_discovers_all_sources_before_probe_or_select(self):
        p=self.public()
        a=next_action(p)
        self.assertEqual(a["action"],"DISCOVER")
        self.assertEqual(a["source_id"],"S1")
        p["discovery_receipts"].append({
            "kind":"DISCOVERY_RESULT","source_id":"S1","registry_epoch":7,
            "source_epoch":3,"complete":True,"tools":[_tool("T9",9)]
        })
        a=next_action(p)
        self.assertEqual(a["action"],"DISCOVER")
        self.assertEqual(a["source_id"],"S0")

    def test_selects_globally_cheapest_proved_sufficient(self):
        p=self.public()
        p["discovery_receipts"]=[
            {"kind":"DISCOVERY_RESULT","source_id":"S0","registry_epoch":7,"source_epoch":1,
             "complete":True,"tools":[_tool("T0",1),_tool("T2",5)]},
            {"kind":"DISCOVERY_RESULT","source_id":"S1","registry_epoch":7,"source_epoch":3,
             "complete":True,"tools":[_tool("T1",2)]},
        ]
        p["prior_probe_receipts"]=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A","epoch":0,"supported":False},
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T1","capability":"CAP_A","epoch":0,"supported":True},
        ]
        self.assertEqual(next_action(p),{"action":"SELECT","tool_id":"T1","epoch":0})

    def test_probe_is_first_unresolved_fact_of_cheapest_not_disproved_tool(self):
        p=self.public()
        p["required_capabilities"]=["A","B"]
        p["discovery_receipts"]=[
            {"kind":"DISCOVERY_RESULT","source_id":"S0","registry_epoch":7,"source_epoch":1,
             "complete":True,"tools":[_tool("T0",1)]},
            {"kind":"DISCOVERY_RESULT","source_id":"S1","registry_epoch":7,"source_epoch":3,
             "complete":True,"tools":[_tool("T1",2)]},
        ]
        p["prior_probe_receipts"]=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"A","epoch":0,"supported":True}
        ]
        self.assertEqual(next_action(p),{"action":"PROBE","tool_id":"T0","capability":"B","epoch":0})

    def test_tool_without_safe_probe_authority_is_never_probed(self):
        p=self.public()
        p["discovery_receipts"]=[
            {"kind":"DISCOVERY_RESULT","source_id":"S0","registry_epoch":7,"source_epoch":1,
             "complete":True,"tools":[_tool("T0",1,safe_probe_allowed=False)]},
            {"kind":"DISCOVERY_RESULT","source_id":"S1","registry_epoch":7,"source_epoch":3,
             "complete":True,"tools":[_tool("T1",2,safe_probe_allowed=True)]},
        ]
        a=next_action(p)
        self.assertEqual(a,{"action":"PROBE","tool_id":"T1","capability":"CAP_A","epoch":0})

    def test_transfer_reuses_current_receipt(self):
        p=self.public()
        p["discovery_receipts"]=[
            {"kind":"DISCOVERY_RESULT","source_id":"S0","registry_epoch":7,"source_epoch":1,
             "complete":True,"tools":[_tool("T0",1)]},
            {"kind":"DISCOVERY_RESULT","source_id":"S1","registry_epoch":7,"source_epoch":3,
             "complete":True,"tools":[]},
        ]
        p["prior_probe_receipts"]=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A","epoch":0,"supported":True}
        ]
        self.assertEqual(next_action(p)["action"],"SELECT")

    def test_version_change_invalidates_capability_receipt(self):
        p=self.public()
        p["discovery_receipts"]=[
            {"kind":"DISCOVERY_RESULT","source_id":"S0","registry_epoch":7,"source_epoch":1,
             "complete":True,"tools":[_tool("T0",1)]},
            {"kind":"DISCOVERY_RESULT","source_id":"S1","registry_epoch":7,"source_epoch":3,
             "complete":True,"tools":[]},
        ]
        p["prior_probe_receipts"]=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A","epoch":0,"supported":True}
        ]
        p["tool_version_events"]=[{"kind":"TOOL_VERSION_CHANGED","tool_id":"T0","new_epoch":1}]
        self.assertEqual(next_action(p),{"action":"PROBE","tool_id":"T0","capability":"CAP_A","epoch":1})

    def test_incomplete_registry_fails_closed(self):
        p=self.public()
        p["discovery_registry"]["complete"]=False
        a=next_action(p)
        self.assertEqual(a["action"],"ESCALATE")
        self.assertIn("COMPLETENESS_NOT_VERIFIED",a["reason"])

    def test_stale_source_receipt_is_not_counted_as_discovered(self):
        p=self.public()
        p["discovery_receipts"]=[
            {"kind":"DISCOVERY_RESULT","source_id":"S1","registry_epoch":6,"source_epoch":3,
             "complete":True,"tools":[_tool("T1",2)]},
        ]
        a=next_action(p)
        self.assertEqual(a["action"],"DISCOVER")
        self.assertEqual(a["source_id"],"S1")

    def test_conflicting_duplicate_tool_identity_fails_closed(self):
        p=self.public()
        p["discovery_receipts"]=[
            {"kind":"DISCOVERY_RESULT","source_id":"S0","registry_epoch":7,"source_epoch":1,
             "complete":True,"tools":[_tool("T0",1)]},
            {"kind":"DISCOVERY_RESULT","source_id":"S1","registry_epoch":7,"source_epoch":3,
             "complete":True,"tools":[_tool("T0",2)]},
        ]
        a=next_action(p)
        self.assertEqual(a["action"],"ESCALATE")
        self.assertIn("TOOL_ID_CONFLICT",a["reason"])

    def test_escalates_only_after_complete_discovery_and_all_candidates_disproved(self):
        p=self.public()
        p["discovery_receipts"]=[
            {"kind":"DISCOVERY_RESULT","source_id":"S0","registry_epoch":7,"source_epoch":1,
             "complete":True,"tools":[_tool("T0",1)]},
            {"kind":"DISCOVERY_RESULT","source_id":"S1","registry_epoch":7,"source_epoch":3,
             "complete":True,"tools":[_tool("T1",2)]},
        ]
        p["prior_probe_receipts"]=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A","epoch":0,"supported":False},
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T1","capability":"CAP_A","epoch":0,"supported":False},
        ]
        a=next_action(p)
        self.assertEqual(a["action"],"ESCALATE")
        self.assertEqual(a["reason"],"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY")

    def test_generic_constraint_filters_before_probe(self):
        p=self.public()
        p["constraint"]={"op":"eq","path":"meta.region","value":"EU"}
        p["discovery_receipts"]=[
            {"kind":"DISCOVERY_RESULT","source_id":"S0","registry_epoch":7,"source_epoch":1,
             "complete":True,"tools":[_tool("US",1,region="US")]},
            {"kind":"DISCOVERY_RESULT","source_id":"S1","registry_epoch":7,"source_epoch":3,
             "complete":True,"tools":[_tool("EU",2,region="EU")]},
        ]
        self.assertEqual(next_action(p),{"action":"PROBE","tool_id":"EU","capability":"CAP_A","epoch":0})


if __name__=="__main__":
    unittest.main(verbosity=2)
