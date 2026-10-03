from __future__ import annotations

import copy
import itertools
import unittest

from canonical.runtime import tool_discovery_common_authority_adapter_v1 as a


def tool(tid,cost,*,available=True,authorized=True,epoch=0,region="X"):
    return {
        "tool_id":tid,
        "cost":float(cost),
        "available":available,
        "authorized":authorized,
        "epoch":epoch,
        "meta":{"region":region},
    }


def case(tools,truth,*,initial=(),required=("CAP_A",),constraint=None,epoch="E0"):
    return {
        "decision_epoch":epoch,
        "required_capabilities":list(required),
        "constraint":constraint,
        "tool_boundary":copy.deepcopy(tools),
        "hidden_capabilities":copy.deepcopy(truth),
        "initially_visible_tool_ids":list(initial),
    }


class CommonAuthorityAdapterTests(unittest.TestCase):
    def test_discovery_reveals_complete_boundary_public_metadata_atomically(self):
        tools=[tool("T0",3),tool("T1",2),tool("T2",1)]
        truth={x["tool_id"]:{"CAP_A":True} for x in tools}
        st=a.build(case(tools,truth,initial=("T0",)))
        self.assertEqual({x["tool_id"] for x in st["public"]["visible_tools"]},{"T0"})
        st=a.step(st)
        self.assertEqual(st["last_action"]["action"],"DISCOVER")
        self.assertEqual(
            {x["tool_id"] for x in st["public"]["visible_tools"]},
            {"T0","T1","T2"},
        )
        self.assertEqual(len(st["public"]["discovery_receipts"]),1)
        receipt=st["public"]["discovery_receipts"][0]
        self.assertEqual(receipt["source_id"],st["private"]["source_id"])
        self.assertEqual({x["tool_id"] for x in receipt["tools"]},{"T1","T2"})

    def test_private_capability_truth_is_not_candidate_visible(self):
        tools=[tool("T0",1)]
        truth={"T0":{"CAP_A":True,"SECRET_CAP":False}}
        st=a.build(case(tools,truth,initial=()))
        public_text=repr(st["public"])
        self.assertNotIn("SECRET_CAP",public_text)
        self.assertNotIn("capability_truth",public_text)

    def test_exhaustive_three_tool_identity_visibility_and_support_masks(self):
        tools=[tool("T0",3),tool("T1",2),tool("T2",1)]
        ids=[x["tool_id"] for x in tools]
        for visible_mask in range(8):
            initial=[ids[i] for i in range(3) if visible_mask & (1<<i)]
            for support_mask in range(8):
                truth={
                    ids[i]:{"CAP_A":bool(support_mask & (1<<i))}
                    for i in range(3)
                }
                c=case(tools,truth,initial=initial)
                out=a.run(c)
                expected=a.oracle_least_cost_sufficient(c)
                if expected is None:
                    self.assertEqual(out["terminal"]["action"],"ESCALATE",(visible_mask,support_mask))
                else:
                    self.assertEqual(
                        out["terminal"],
                        {"action":"SELECT","tool_id":expected},
                        (visible_mask,support_mask),
                    )

    def test_availability_authority_and_constraint_are_respected(self):
        tools=[
            tool("CHEAP_UNAVAILABLE",0.5,available=False),
            tool("CHEAP_UNAUTHORIZED",0.75,authorized=False),
            tool("WRONG_REGION",0.9,region="Y"),
            tool("GOOD",1.0,region="X"),
        ]
        truth={x["tool_id"]:{"CAP_A":True} for x in tools}
        c=case(
            tools,truth,initial=(),
            constraint={"op":"eq","path":"meta.region","value":"X"},
        )
        out=a.run(c)
        self.assertEqual(out["terminal"],{"action":"SELECT","tool_id":"GOOD"})
        self.assertEqual(a.oracle_least_cost_sufficient(c),"GOOD")

    def test_no_sufficient_route_escalates_after_complete_discovery_and_probes(self):
        tools=[tool("T0",1),tool("T1",2)]
        truth={"T0":{"CAP_A":False},"T1":{"CAP_A":False}}
        out=a.run(case(tools,truth,initial=()))
        self.assertEqual(out["terminal"]["action"],"ESCALATE")
        self.assertEqual(
            {x["tool_id"] for x in out["public"]["prior_probe_receipts"]},
            {"T0","T1"},
        )

    def test_second_task_reuses_same_epoch_receipts_without_rediscovery_or_reprobe(self):
        tools=[tool("T0",1),tool("T1",2)]
        truth={"T0":{"CAP_A":True},"T1":{"CAP_A":False}}
        first=a.run(case(tools,truth,initial=()))
        probes_before=list(first["public"]["prior_probe_receipts"])
        discovers_before=list(first["public"]["discovery_receipts"])
        second=a.start_next_task(first,["CAP_A"])
        second=a.step(second)
        self.assertEqual(second["last_action"],{"action":"SELECT","tool_id":"T0"})
        self.assertEqual(second["public"]["prior_probe_receipts"],probes_before)
        self.assertEqual(second["public"]["discovery_receipts"],discovers_before)

    def test_duplicate_tool_identity_fails_closed_before_v4(self):
        tools=[tool("DUP",1),tool("DUP",2)]
        truth={"DUP":{"CAP_A":True}}
        with self.assertRaisesRegex(a.AdapterError,"TOOL_ID_EMPTY_OR_DUPLICATE"):
            a.build(case(tools,truth))

    def test_nonfinite_cost_fails_closed_before_v4(self):
        tools=[tool("T0",1)]
        tools[0]["cost"]=float("nan")
        truth={"T0":{"CAP_A":True}}
        with self.assertRaisesRegex(a.AdapterError,"NONFINITE"):
            a.build(case(tools,truth))

    def test_hidden_capability_matrix_must_cover_required_caps(self):
        tools=[tool("T0",1)]
        truth={"T0":{"OTHER":True}}
        with self.assertRaisesRegex(a.AdapterError,"HIDDEN_CAPABILITY_MATRIX_INCOMPLETE"):
            a.build(case(tools,truth))


if __name__=="__main__":
    unittest.main(verbosity=2)
