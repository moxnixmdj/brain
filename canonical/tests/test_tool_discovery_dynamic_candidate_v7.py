from __future__ import annotations

import copy
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v6 as v6
from canonical.runtime import tool_discovery_dynamic_candidate_v7 as v7


def base():
    return {
        "required_capabilities":["CAP_A"],
        "decision_epoch":0,
        "constraint":None,
        "visible_tools":[],
        "discovery_sources":[],
        "discovery_receipts":[],
        "prior_probe_receipts":[],
        "version_events":[],
    }


def tool(tid,cost,*,safe=()):
    return {
        "tool_id":tid,
        "cost":float(cost),
        "available":True,
        "authorized":True,
        "epoch":0,
        "safe_probe_capabilities":list(safe),
    }


def receipt(tid,supported):
    return {
        "kind":"SAFE_CAPABILITY_PROBE",
        "tool_id":tid,
        "capability":"CAP_A",
        "epoch":0,
        "supported":supported,
    }


class ToolDiscoveryDynamicV7Tests(unittest.TestCase):
    def test_exact_v6_equal_cost_unprobeable_counterexample(self):
        p=base()
        p["visible_tools"]=[
            tool("A_UNKNOWN",1,safe=[]),
            tool("Z_VERIFIED",1,safe=["CAP_A"]),
        ]
        p["prior_probe_receipts"]=[receipt("Z_VERIFIED",True)]
        self.assertEqual(v6.next_action(p),{
            "action":"ESCALATE",
            "reason":"CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
            "tool_id":"A_UNKNOWN",
        })
        self.assertEqual(v7.next_action(p),{
            "action":"SELECT","tool_id":"Z_VERIFIED"
        })

    def test_equal_cost_safe_unknown_does_not_force_unnecessary_probe_when_peer_verified(self):
        p=base()
        p["visible_tools"]=[
            tool("A_UNKNOWN",1,safe=["CAP_A"]),
            tool("Z_VERIFIED",1,safe=["CAP_A"]),
        ]
        p["prior_probe_receipts"]=[receipt("Z_VERIFIED",True)]
        self.assertEqual(v6.next_action(p),{
            "action":"PROBE","tool_id":"A_UNKNOWN","capability":"CAP_A"
        })
        self.assertEqual(v7.next_action(p),{
            "action":"SELECT","tool_id":"Z_VERIFIED"
        })

    def test_same_cost_mixed_safe_and_unsafe_frontier_uses_safe_progress(self):
        p=base()
        p["visible_tools"]=[
            tool("A_UNSAFE",1,safe=[]),
            tool("B_SAFE",1,safe=["CAP_A"]),
            tool("EXPENSIVE",2,safe=["CAP_A"]),
        ]
        p["prior_probe_receipts"]=[receipt("EXPENSIVE",True)]
        self.assertEqual(v6.next_action(p),{
            "action":"ESCALATE",
            "reason":"CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
            "tool_id":"A_UNSAFE",
        })
        self.assertEqual(v7.next_action(p),{
            "action":"PROBE","tool_id":"B_SAFE","capability":"CAP_A"
        })

    def test_strictly_cheaper_unprobeable_route_still_blocks_expensive_verified_route(self):
        p=base()
        p["visible_tools"]=[
            tool("CHEAP",1,safe=[]),
            tool("EXPENSIVE",2,safe=["CAP_A"]),
        ]
        p["prior_probe_receipts"]=[receipt("EXPENSIVE",True)]
        out=v7.next_action(p)
        self.assertEqual(out["action"],"ESCALATE")
        self.assertEqual(out["reason"],"LEAST_COST_FRONTIER_UNRESOLVED_NO_SAFE_PROBE")
        self.assertEqual(out["frontier_cost"],1.0)
        self.assertEqual(out["tool_ids"],["CHEAP"])

    def test_negative_cheaper_evidence_advances_to_verified_next_cost(self):
        p=base()
        p["visible_tools"]=[
            tool("CHEAP",1,safe=["CAP_A"]),
            tool("EXPENSIVE",2,safe=["CAP_A"]),
        ]
        p["prior_probe_receipts"]=[
            receipt("CHEAP",False),
            receipt("EXPENSIVE",True),
        ]
        self.assertEqual(v7.next_action(p),{
            "action":"SELECT","tool_id":"EXPENSIVE"
        })

    def test_all_falsified_routes_preserve_no_route_escalation(self):
        p=base()
        p["visible_tools"]=[
            tool("A",1,safe=["CAP_A"]),
            tool("B",2,safe=["CAP_A"]),
        ]
        p["prior_probe_receipts"]=[receipt("A",False),receipt("B",False)]
        self.assertEqual(v7.next_action(p),{
            "action":"ESCALATE",
            "reason":"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY",
        })

    def test_version_change_preserves_v6_restart_boundary(self):
        p=base()
        p["visible_tools"]=[tool("T",1,safe=["CAP_A"])]
        p["prior_probe_receipts"]=[receipt("T",True)]
        p["version_events"]=[{
            "kind":"TOOL_VERSION_CHANGED",
            "tool_id":"T",
            "new_epoch":1,
        }]
        self.assertEqual(v7.next_action(p),v6.next_action(p))
        self.assertEqual(
            v7.next_action(p)["reason"],
            "TOOL_VERSION_CHANGED_RESTART_EPISODE",
        )

    def test_discovery_first_is_preserved(self):
        p=base()
        latent=tool("T",1,safe=["CAP_A"])
        src={
            "source_id":"S0",
            "cost":0.0,
            "available":True,
            "authorized":True,
            "authoritative":True,
            "source_epoch":0,
            "source_digest":v5._tools_digest([latent]),
        }
        p["discovery_sources"]=[src]
        self.assertEqual(v7.next_action(p),{
            "action":"DISCOVER","source_id":"S0","query":"CAP_A"
        })

    def test_nonfinite_tool_cost_fails_closed_before_frontier_ranking(self):
        for bad in (float("nan"),float("inf")):
            p=base()
            row=tool("BAD",1,safe=["CAP_A"])
            row["cost"]=bad
            p["visible_tools"]=[row]
            p["prior_probe_receipts"]=[receipt("BAD",True)]
            self.assertEqual(v7.next_action(p),{
                "action":"ESCALATE","reason":"TOOL_COST_INVALID"
            })

    def test_identity_renaming_within_equal_cost_frontier_does_not_change_validity(self):
        for unknown_id,known_id in (("A","Z"),("Z","A"),("π","urn:x")):
            p=base()
            p["visible_tools"]=[
                tool(unknown_id,1,safe=[]),
                tool(known_id,1,safe=["CAP_A"]),
            ]
            p["prior_probe_receipts"]=[receipt(known_id,True)]
            self.assertEqual(
                v7.next_action(p),
                {"action":"SELECT","tool_id":known_id},
                (unknown_id,known_id),
            )

    def test_mixed_two_capability_frontier_consumes_safe_fact_before_irreducible_one(self):
        p=base()
        p["required_capabilities"]=["CAP_A","CAP_B"]
        p["visible_tools"]=[
            {
                **tool("CHEAP",1,safe=["CAP_B"]),
            },
            {
                **tool("KNOWN",2,safe=["CAP_A","CAP_B"]),
            },
        ]
        p["prior_probe_receipts"]=[
            {
                "kind":"SAFE_CAPABILITY_PROBE","tool_id":"KNOWN",
                "capability":"CAP_A","epoch":0,"supported":True,
            },
            {
                "kind":"SAFE_CAPABILITY_PROBE","tool_id":"KNOWN",
                "capability":"CAP_B","epoch":0,"supported":True,
            },
        ]
        self.assertEqual(v7.next_action(p),{
            "action":"PROBE","tool_id":"CHEAP","capability":"CAP_B"
        })
        p["prior_probe_receipts"].append({
            "kind":"SAFE_CAPABILITY_PROBE","tool_id":"CHEAP",
            "capability":"CAP_B","epoch":0,"supported":True,
        })
        out=v7.next_action(p)
        self.assertEqual(out["reason"],"LEAST_COST_FRONTIER_UNRESOLVED_NO_SAFE_PROBE")


if __name__=="__main__":
    unittest.main(verbosity=2)
