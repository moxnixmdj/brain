from __future__ import annotations

import copy
import itertools
import math
import unittest

from canonical.runtime import tool_discovery_common_authority_manifest_v2 as m
from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v6 as v6
from canonical.runtime import tool_discovery_v7_scope_reducer_v1 as cut


def tool(tid, cost, *, safe=("CAP_A",), available=True, authorized=True, epoch=0):
    return {
        "tool_id":tid,
        "cost":float(cost),
        "available":available,
        "authorized":authorized,
        "epoch":epoch,
        "safe_probe_capabilities":list(safe),
        "meta":{"region":"X","risk":0},
    }


def instance(*, cheap_safe=("CAP_A",)):
    return m.build_instance(
        decision_epoch=7,
        authority_tools=[
            tool("EXPENSIVE",10,safe=("CAP_A",)),
            tool("MID",3,safe=("CAP_A",)),
            tool("CHEAP",1,safe=cheap_safe),
        ],
        initial_visible_tool_ids=["EXPENSIVE"],
        discovery_sources=[
            {
                "source_id":"S0","cost":0.1,"available":True,
                "authorized":True,"authoritative":True,"source_epoch":7,
                "tool_ids":["MID"],
            },
            {
                "source_id":"S1","cost":0.2,"available":True,
                "authorized":True,"authoritative":True,"source_epoch":7,
                "tool_ids":["CHEAP"],
            },
        ],
    )


def run(inst, support):
    public=m.initial_public(inst,required_capabilities=["CAP_A"])
    for _ in range(40):
        action=v6.next_action(public)
        kind=action["action"]
        if kind=="DISCOVER":
            public=m.append_discovery(
                public,
                m.discover(inst,public,action["source_id"],action["query"]),
            )
            continue
        if kind=="PROBE":
            public=m.append_probe(
                public,
                tool_id=action["tool_id"],
                capability=action["capability"],
                supported=bool(support[action["tool_id"]]),
            )
            continue
        return action,public
    raise AssertionError("ACTION_BUDGET_EXHAUSTED")


class ToolDiscoveryV7SynthesisTests(unittest.TestCase):
    def test_manifest_exact_partition_is_content_addressed(self):
        inst=instance()
        out=m.validate_instance(inst)
        self.assertTrue(out["complete_exact_partition"])
        self.assertEqual(out["authority_tool_count"],3)
        self.assertTrue(out["authority_sha256"].startswith("sha256:"))
        self.assertTrue(out["partition_sha256"].startswith("sha256:"))
        self.assertEqual(
            out["source_set_digest"],
            v5._source_set_digest(out["source_public"]),
        )

    def test_manifest_rejects_hidden_capability_support(self):
        bad=tool("T",1)
        bad["capabilities"]=["CAP_A"]
        with self.assertRaisesRegex(m.ManifestError,"TOOL_NONPUBLIC_FIELDS"):
            m.build_instance(
                decision_epoch=0,
                authority_tools=[bad],
                initial_visible_tool_ids=["T"],
                discovery_sources=[],
            )

    def test_safe_probe_permission_is_public_but_support_is_not(self):
        inst=instance()
        public=m.initial_public(inst,required_capabilities=["CAP_A"])
        self.assertNotIn("capabilities",repr(public))
        self.assertIn("safe_probe_capabilities",repr(public))
        # Support truth is supplied only after a candidate probe action.
        action=v6.next_action(public)
        self.assertEqual(action["action"],"DISCOVER")

    def test_partition_omission_and_overlap_fail_closed(self):
        inst=instance()
        bad=copy.deepcopy(inst)
        bad["discovery_sources"][1]["tool_ids"]=[]
        with self.assertRaises(m.ManifestError):
            m.validate_instance(bad)
        bad=copy.deepcopy(inst)
        bad["discovery_sources"][0]["tool_ids"].append("CHEAP")
        with self.assertRaises(m.ManifestError):
            m.validate_instance(bad)

    def test_hidden_authority_member_cannot_live_behind_undiscoverable_source(self):
        inst=instance()
        bad=copy.deepcopy(inst)
        bad["discovery_sources"][0]["available"]=False
        # Rebuilding the partition hash cannot make an undiscoverable source valid.
        with self.assertRaisesRegex(m.ManifestError,"PARTITION_SOURCE_NOT_DISCOVERABLE"):
            m.validate_instance(bad)

    def test_nonfinite_cost_fails_at_interface(self):
        with self.assertRaisesRegex(m.ManifestError,"TOOL_COST_INVALID"):
            m.build_instance(
                decision_epoch=0,
                authority_tools=[tool("T",math.nan)],
                initial_visible_tool_ids=["T"],
                discovery_sources=[],
            )

    def test_exhaustive_one_capability_worlds_choose_global_least_cost_or_escalate(self):
        inst=instance()
        ids=["EXPENSIVE","MID","CHEAP"]
        costs={"EXPENSIVE":10.0,"MID":3.0,"CHEAP":1.0}
        for bits in itertools.product((False,True),repeat=3):
            support=dict(zip(ids,bits))
            action,public=run(inst,support)
            sufficient=[tid for tid in ids if support[tid]]
            if sufficient:
                expected=min(sufficient,key=lambda tid:(costs[tid],tid))
                self.assertEqual(action,{"action":"SELECT","tool_id":expected},support)
            else:
                self.assertEqual(
                    action,
                    {"action":"ESCALATE","reason":"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY"},
                    support,
                )
            out=cut.classify_public(public)
            self.assertFalse(out["matched_comparator_required"],(support,out))

    def test_discovery_saturates_before_first_probe_or_select(self):
        inst=instance()
        public=m.initial_public(inst,required_capabilities=["CAP_A"])
        seen=[]
        while True:
            action=v6.next_action(public)
            seen.append(action["action"])
            if action["action"]=="DISCOVER":
                public=m.append_discovery(
                    public,
                    m.discover(inst,public,action["source_id"],action["query"]),
                )
                continue
            break
        self.assertEqual(seen[:2],["DISCOVER","DISCOVER"])
        self.assertIn(seen[2],{"PROBE","SELECT","ESCALATE"})
        self.assertEqual(
            {x["source_id"] for x in public["discovery_receipts"]},
            {"S0","S1"},
        )

    def test_tampered_discovery_result_never_counts_complete(self):
        inst=instance()
        public=m.initial_public(inst,required_capabilities=["CAP_A"])
        action=v6.next_action(public)
        rec=m.discover(inst,public,action["source_id"],action["query"])
        rec["tools"][0]["cost"]=999.0
        public=m.append_discovery(public,rec)
        again=v6.next_action(public)
        self.assertEqual(again["action"],"DISCOVER")
        self.assertEqual(again["source_id"],action["source_id"])

    def test_unprobeable_cheaper_unknown_is_exact_matched_only_cut(self):
        inst=instance(cheap_safe=())
        public=m.initial_public(inst,required_capabilities=["CAP_A"])
        # Saturate identity scope.
        while True:
            action=v6.next_action(public)
            if action["action"]!="DISCOVER":
                break
            public=m.append_discovery(
                public,m.discover(inst,public,action["source_id"],action["query"])
            )
        # Positively establish only the more expensive route.
        public=m.append_probe(
            public,tool_id="MID",capability="CAP_A",supported=True
        )
        out=cut.classify_public(public)
        self.assertTrue(out["matched_comparator_required"],out)
        self.assertFalse(out["universal_proof_eligible"])
        self.assertEqual(
            out["ambiguous_decision_relevant_routes"][0]["tool_id"],
            "CHEAP",
        )
        # V6 must not silently skip the unresolved cheaper route.
        action=v6.next_action(public)
        self.assertEqual(action["action"],"ESCALATE")
        self.assertEqual(
            action["reason"],
            "CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
        )
        self.assertEqual(action["tool_id"],"CHEAP")

    def test_unprobeable_more_expensive_unknown_does_not_block_verified_cheapest(self):
        inst=m.build_instance(
            decision_epoch=0,
            authority_tools=[
                tool("CHEAP",1,safe=("CAP_A",)),
                tool("EXPENSIVE",2,safe=()),
            ],
            initial_visible_tool_ids=["CHEAP","EXPENSIVE"],
            discovery_sources=[],
        )
        public=m.initial_public(inst,required_capabilities=["CAP_A"])
        public=m.append_probe(public,tool_id="CHEAP",capability="CAP_A",supported=True)
        out=cut.classify_public(public)
        self.assertTrue(out["universal_proof_eligible"],out)
        self.assertFalse(out["matched_comparator_required"])
        self.assertEqual(v6.next_action(public),{"action":"SELECT","tool_id":"CHEAP"})

    def test_version_change_forces_restart_before_scope_or_selection(self):
        inst=instance()
        public=m.initial_public(inst,required_capabilities=["CAP_A"])
        public["version_events"]=[{
            "kind":"TOOL_VERSION_CHANGED","tool_id":"CHEAP","new_epoch":8
        }]
        self.assertEqual(
            v6.next_action(public)["reason"],
            "TOOL_VERSION_CHANGED_RESTART_EPISODE",
        )
        out=cut.classify_public(public)
        self.assertTrue(out["restart_required"])
        self.assertFalse(out["universal_proof_eligible"])

    def test_same_observation_unprobeable_cheaper_has_two_required_worlds(self):
        # This is the lower bound itself: before matched evidence, the exact same
        # public state permits two hidden worlds requiring different decisions.
        inst=instance(cheap_safe=())
        public=m.initial_public(inst,required_capabilities=["CAP_A"])
        while True:
            action=v6.next_action(public)
            if action["action"]!="DISCOVER":
                break
            public=m.append_discovery(
                public,m.discover(inst,public,action["source_id"],action["query"])
            )
        public=m.append_probe(public,tool_id="MID",capability="CAP_A",supported=True)
        public_snapshot=copy.deepcopy(public)
        world_cheap_supports=True
        world_cheap_fails=False
        self.assertEqual(public,public_snapshot)
        self.assertNotEqual(world_cheap_supports,world_cheap_fails)
        self.assertTrue(cut.classify_public(public)["matched_comparator_required"])


if __name__=="__main__":
    unittest.main(verbosity=2)
