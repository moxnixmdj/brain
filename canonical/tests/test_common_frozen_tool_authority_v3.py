from __future__ import annotations

import copy
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime.common_frozen_tool_authority_v3 import (
    AuthorityError,
    CommonFrozenToolAuthorityV3,
    execute_v5,
    prove_instance,
)

CAP="CAP_A"

def row(tid,cost,*,source,supported,available=True,authorized=True,probe=True,region="GLOBAL"):
    return {
        "tool_id":tid,
        "source_id":source,
        "cost":float(cost),
        "available":available,
        "authorized":authorized,
        "safe_probe_capabilities":[CAP] if probe else [],
        "capabilities":[CAP] if supported else [],
        "region":region,
    }

class CommonFrozenToolAuthorityV3Tests(unittest.TestCase):
    def test_common_routes_see_identical_complete_interface(self):
        a=CommonFrozenToolAuthorityV3([
            row("opaque-z",9,source="S0",supported=True),
            row("opaque-a",1,source="S1",supported=True),
        ],epoch=7)
        out=prove_instance(a)
        self.assertTrue(out["status"].startswith("PASS__"),out)
        self.assertTrue(out["brain_opus_views_identical"])
        self.assertTrue(out["source_union_exact_authority"])
        self.assertTrue(out["hidden_capability_truth_not_disclosed"])

    def test_hidden_identity_requires_discovery_and_cheapest_wins(self):
        a=CommonFrozenToolAuthorityV3([
            row("expensive",10,source="S0",supported=True),
            row("cheap",1,source="S1",supported=True),
        ])
        p=a.initial_public("BRAIN",required_capabilities=[CAP],initial_visible_ids=["expensive"],episode_epoch=0)
        p["prior_probe_receipts"]=[a.safe_probe("BRAIN","expensive",CAP,episode_epoch=0)]
        self.assertEqual(v5.next_action(p)["action"],"DISCOVER")
        out=execute_v5(a,"BRAIN",required_capabilities=[CAP],initial_visible_ids=["expensive"])
        self.assertEqual(out["final"],{"action":"SELECT","tool_id":"cheap"})
        self.assertEqual(sum(x["action"]=="DISCOVER" for x in out["actions"]),2)

    def test_stale_partial_wrong_query_and_forged_content_never_complete_discovery(self):
        a=CommonFrozenToolAuthorityV3([row("cheap",1,source="S0",supported=True)],epoch=4)
        p=a.initial_public("BRAIN",required_capabilities=[CAP],episode_epoch=4)
        good=a.discover("BRAIN","S0",CAP,episode_epoch=4)
        mutations=[
            {"complete":False},
            {"decision_epoch":3},
            {"source_epoch":3},
            {"query":"CAP_B"},
            {"source_digest":"sha256:bad"},
            {"source_set_digest":"sha256:bad"},
        ]
        for m in mutations:
            q=copy.deepcopy(p)
            rec=copy.deepcopy(good); rec.update(m); q["discovery_receipts"]=[rec]
            self.assertEqual(v5.next_action(q),{"action":"DISCOVER","source_id":"S0","query":CAP},m)
        q=copy.deepcopy(p)
        forged=copy.deepcopy(good)
        forged["tools"]=[dict(good["tools"][0],cost=0.0)]
        q["discovery_receipts"]=[forged]
        self.assertEqual(v5.next_action(q),{"action":"DISCOVER","source_id":"S0","query":CAP})

    def test_unprobeable_cheaper_route_blocks_expensive_selection(self):
        a=CommonFrozenToolAuthorityV3([
            row("cheap-unknown",1,source="S0",supported=True,probe=False),
            row("expensive",10,source="S0",supported=True,probe=True),
        ])
        out=execute_v5(a,"BRAIN",required_capabilities=[CAP])
        self.assertEqual(out["final"]["action"],"ESCALATE")
        self.assertEqual(out["final"]["reason"],"CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE")
        self.assertEqual(out["final"]["tool_id"],"cheap-unknown")

    def test_active_constraint_is_load_bearing(self):
        a=CommonFrozenToolAuthorityV3([
            row("cheap-us",1,source="S0",supported=True,region="US"),
            row("eu",2,source="S1",supported=True,region="EU"),
        ])
        constraint={"op":"eq","path":"region","value":"EU"}
        out=execute_v5(a,"BRAIN",required_capabilities=[CAP],constraint=constraint)
        self.assertEqual(out["final"],{"action":"SELECT","tool_id":"eu"})

    def test_brain_and_opus_actions_are_identical_for_same_common_authority(self):
        a=CommonFrozenToolAuthorityV3([
            row("a",3,source="S0",supported=False),
            row("b",2,source="S1",supported=True),
            row("c",1,source="S1",supported=False),
        ],epoch=2)
        b=execute_v5(a,"BRAIN",required_capabilities=[CAP])
        o=execute_v5(a,"OPUS55",required_capabilities=[CAP])
        self.assertEqual(b["actions"],o["actions"])
        self.assertEqual(b["final"],o["final"])

    def test_authority_replacement_invalidates_episode_and_old_probe_evidence(self):
        entries=[row("cheap",1,source="S0",supported=True)]
        a=CommonFrozenToolAuthorityV3(entries,epoch=5)
        first=execute_v5(a,"BRAIN",required_capabilities=[CAP])
        old=list(first["public"]["prior_probe_receipts"])
        self.assertTrue(old)
        self.assertEqual(old[-1]["epoch"],5)
        old_epoch=a.epoch
        a.replace_authority(entries)
        self.assertEqual(a.epoch,6)
        with self.assertRaisesRegex(AuthorityError,"EPOCH_CHANGED_RESTART_EPISODE"):
            a.discover("BRAIN","S0",CAP,episode_epoch=old_epoch)
        second=execute_v5(a,"BRAIN",required_capabilities=[CAP],prior_probe_receipts=old)
        self.assertEqual(second["final"],{"action":"SELECT","tool_id":"cheap"})
        self.assertGreater(sum(x["action"]=="PROBE" for x in second["actions"]),0)
        self.assertEqual(second["public"]["prior_probe_receipts"][-1]["epoch"],6)

    def test_hidden_capability_truth_does_not_change_public_authority_digest(self):
        yes=CommonFrozenToolAuthorityV3([row("t",1,source="S0",supported=True)],epoch=3)
        no=CommonFrozenToolAuthorityV3([row("t",1,source="S0",supported=False)],epoch=3)
        self.assertEqual(yes.authority_digest_sha256(),no.authority_digest_sha256())
        self.assertEqual(
            yes.source_descriptors("BRAIN",episode_epoch=3),
            no.source_descriptors("BRAIN",episode_epoch=3),
        )

    def test_unregistered_identity_uninvocable_for_both_routes(self):
        a=CommonFrozenToolAuthorityV3([row("known",1,source="S0",supported=True)])
        for route in ("BRAIN","OPUS55"):
            with self.assertRaisesRegex(AuthorityError,"UNREGISTERED_TOOL_ID"):
                a.invoke(route,"outside",episode_epoch=0)

    def test_exhaustive_512_small_worlds_match_global_least_cost_for_both_routes(self):
        tids=["T0","T1","T2"]; costs=[1.0,2.0,3.0]
        for support_mask in range(8):
            for availability_mask in range(8):
                for authorization_mask in range(8):
                    entries=[]
                    for i,tid in enumerate(tids):
                        entries.append(row(
                            tid,costs[i],source="S"+str(i%2),
                            supported=bool(support_mask&(1<<i)),
                            available=bool(availability_mask&(1<<i)),
                            authorized=bool(authorization_mask&(1<<i)),
                        ))
                    sufficient=[
                        x for i,x in enumerate(entries)
                        if x["available"] and x["authorized"] and CAP in x["capabilities"]
                    ]
                    expected=(
                        min(sufficient,key=lambda x:(x["cost"],x["tool_id"]))["tool_id"]
                        if sufficient else None
                    )
                    a=CommonFrozenToolAuthorityV3(entries)
                    for route in ("BRAIN","OPUS55"):
                        out=execute_v5(a,route,required_capabilities=[CAP])
                        if expected is None:
                            self.assertEqual(out["final"]["action"],"ESCALATE",(support_mask,availability_mask,authorization_mask,route,out))
                            self.assertEqual(out["final"]["reason"],"NO_VERIFIED_ADMISSIBLE_TOOL_AFTER_COMPLETE_DISCOVERY")
                        else:
                            self.assertEqual(out["final"],{"action":"SELECT","tool_id":expected},(support_mask,availability_mask,authorization_mask,route,out))

    def test_interface_instance_grants_zero_credit(self):
        out=prove_instance(CommonFrozenToolAuthorityV3([row("t",1,source="S0",supported=True)]))
        self.assertEqual(out["capability_credit_delta"],0)
        self.assertEqual(out["family_credit_delta"],0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

if __name__=="__main__":
    unittest.main(verbosity=2)
