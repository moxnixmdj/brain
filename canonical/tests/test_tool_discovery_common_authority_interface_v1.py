from __future__ import annotations

import copy
import itertools
import unittest

from canonical.runtime import tool_discovery_common_authority_interface_v1 as iface
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4


def tool(tid,cost,epoch=0,available=True,authorized=True):
    return {
        "tool_id":tid,
        "cost":float(cost),
        "available":available,
        "authorized":authorized,
        "epoch":epoch,
        "meta":{"region":"X","risk":0,"tags":["prod"]},
    }


class CommonAuthorityInterfaceV1Tests(unittest.TestCase):
    def _instance(self):
        return iface.freeze_instance(
            [
                tool("opaque://expensive",10),
                tool("never-seen-before::cheap",1),
                tool("第三工具",3),
            ],
            {
                "opaque://expensive":{"0":["CAP_A"]},
                "never-seen-before::cheap":{"0":["CAP_A","CAP_B"]},
                "第三工具":{"0":[]},
            },
        )

    def test_discovery_is_exact_complete_public_authority(self):
        inst=self._instance()
        ep=iface.begin_episode(inst,["CAP_A"])
        rec=iface.discover(inst,ep,iface.SOURCE_ID,"CAP_A")
        self.assertTrue(rec["complete"])
        self.assertEqual(rec["authority_sha256"],inst["public_authority_sha256"])
        self.assertEqual(
            {x["tool_id"] for x in rec["tools"]},
            {x["tool_id"] for x in inst["public_tools"]},
        )
        self.assertNotIn("hidden_truth",rec)
        self.assertTrue(all("capabilities" not in x for x in rec["tools"]))

    def test_v4_must_discover_before_probe_or_select(self):
        inst=self._instance()
        ep=iface.begin_episode(inst,["CAP_A"])
        action=v4.next_action(ep)
        self.assertEqual(action["action"],"DISCOVER")
        self.assertEqual(action["source_id"],iface.SOURCE_ID)

    def test_v4_reaches_global_cheapest_truthful_route(self):
        inst=self._instance()
        ep=iface.begin_episode(inst,["CAP_A"])
        for _ in range(20):
            action=v4.next_action(ep)
            if action["action"]=="DISCOVER":
                ep=iface.apply_discovery(
                    inst,ep,iface.discover(inst,ep,action["source_id"],action["query"])
                )
            elif action["action"]=="PROBE":
                ep=iface.apply_probe(
                    inst,ep,iface.safe_probe(inst,ep,action["tool_id"],action["capability"])
                )
            elif action["action"]=="SELECT":
                self.assertEqual(action["tool_id"],"never-seen-before::cheap")
                return
            else:
                self.fail(action)
        self.fail("action budget exhausted")

    def test_arbitrary_public_constraint_metadata_is_preserved_and_used(self):
        a=tool("cheap-but-wrong",1)
        b=tool("allowed-route",2)
        a["custom_constraint_field"]="blocked"
        b["custom_constraint_field"]="allowed"
        inst=iface.freeze_instance(
            [a,b],
            {
                "cheap-but-wrong":{"0":["CAP_A"]},
                "allowed-route":{"0":["CAP_A"]},
            },
        )
        ep=iface.begin_episode(
            inst,
            ["CAP_A"],
            constraint={"op":"eq","path":"custom_constraint_field","value":"allowed"},
        )
        action=v4.next_action(ep)
        self.assertEqual(action["action"],"DISCOVER")
        ep=iface.apply_discovery(
            inst,ep,iface.discover(inst,ep,action["source_id"],action["query"])
        )
        byid={x["tool_id"]:x for x in ep["visible_tools"]}
        self.assertEqual(byid["allowed-route"]["custom_constraint_field"],"allowed")
        action=v4.next_action(ep)
        self.assertEqual(action,{"action":"PROBE","tool_id":"allowed-route","capability":"CAP_A"})
        ep=iface.apply_probe(
            inst,ep,iface.safe_probe(inst,ep,action["tool_id"],action["capability"])
        )
        self.assertEqual(
            v4.next_action(ep),
            {"action":"SELECT","tool_id":"allowed-route"},
        )

    def test_brain_and_opus_are_bound_to_same_exact_authority_digest(self):
        inst=self._instance()
        binding=iface.matched_route_binding(inst)
        self.assertTrue(binding["same_frozen_tool_authority"])
        self.assertEqual(
            binding["brain"]["public_authority_sha256"],
            binding["opus"]["public_authority_sha256"],
        )
        self.assertEqual(
            binding["brain"]["interface_instance_sha256"],
            binding["opus"]["interface_instance_sha256"],
        )
        self.assertEqual(
            binding["brain"]["public_authority_sha256"],
            inst["public_authority_sha256"],
        )

    def test_probe_truth_is_hidden_and_epoch_bound(self):
        inst=self._instance()
        ep=iface.begin_episode(inst,["CAP_A","CAP_B"])
        a=iface.safe_probe(inst,ep,"never-seen-before::cheap","CAP_B")
        b=iface.safe_probe(inst,ep,"第三工具","CAP_A")
        self.assertTrue(a["supported"])
        self.assertFalse(b["supported"])
        self.assertEqual(a["epoch"],0)
        self.assertEqual(a["instance_sha256"],inst["instance_sha256"])

    def test_version_change_forces_episode_restart(self):
        inst=self._instance()
        ep=iface.begin_episode(inst,["CAP_A"])
        changed=iface.evolve_tool(
            inst,
            "never-seen-before::cheap",
            new_epoch=1,
            new_capabilities=[],
        )
        with self.assertRaises(iface.InterfaceError) as cm:
            iface.discover(changed,ep,iface.SOURCE_ID,"CAP_A")
        self.assertIn("STALE_EPISODE_RESTART_REQUIRED",str(cm.exception))
        restarted=iface.begin_episode(changed,["CAP_A"])
        rec=iface.safe_probe(changed,restarted,"never-seen-before::cheap","CAP_A")
        self.assertEqual(rec["epoch"],1)
        self.assertFalse(rec["supported"])

    def test_tampered_discovery_receipt_fails_closed(self):
        inst=self._instance()
        ep=iface.begin_episode(inst,["CAP_A"])
        rec=iface.discover(inst,ep,iface.SOURCE_ID,"CAP_A")
        rec["authority_sha256"]="0"*64
        with self.assertRaises(iface.InterfaceError):
            iface.apply_discovery(inst,ep,rec)

    def test_truncated_discovery_payload_fails_closed_even_with_valid_digest_field(self):
        inst=self._instance()
        ep=iface.begin_episode(inst,["CAP_A"])
        rec=iface.discover(inst,ep,iface.SOURCE_ID,"CAP_A")
        rec["tools"]=rec["tools"][:-1]
        with self.assertRaises(iface.InterfaceError) as cm:
            iface.apply_discovery(inst,ep,rec)
        self.assertIn("DISCOVERY_PAYLOAD_NOT_EXACT_COMPLETE_AUTHORITY",str(cm.exception))

    def test_forged_probe_truth_fails_closed_before_candidate_can_reuse_it(self):
        inst=self._instance()
        ep=iface.begin_episode(inst,["CAP_A"])
        rec=iface.safe_probe(inst,ep,"第三工具","CAP_A")
        self.assertFalse(rec["supported"])
        rec["supported"]=True
        with self.assertRaises(iface.InterfaceError) as cm:
            iface.apply_probe(inst,ep,rec)
        self.assertIn("PROBE_RECEIPT_TRUTH_MISMATCH",str(cm.exception))

    def test_hidden_capabilities_cannot_leak_in_public_metadata(self):
        with self.assertRaises(iface.InterfaceError) as cm:
            iface.freeze_instance(
                [{
                    **tool("T",1),
                    "hidden_capabilities":["CAP_A"],
                }],
                {"T":{"0":["CAP_A"]}},
            )
        self.assertIn("PUBLIC_METADATA_CONTAINS_HIDDEN_CAPABILITY_FIELD",str(cm.exception))

    def test_incomplete_hidden_truth_fails_closed(self):
        with self.assertRaises(iface.InterfaceError) as cm:
            iface.freeze_instance([tool("A",1),tool("B",2)],{"A":{"0":[]}})
        self.assertIn("HIDDEN_TRUTH_TOOL_MISSING:B",str(cm.exception))

    def test_exhaustive_small_finite_authorities(self):
        ids=["U0","U1","U2"]
        costs=[3,1,2]
        for mask in range(1<<len(ids)):
            tools=[tool(tid,cost) for tid,cost in zip(ids,costs)]
            truth={
                tid:{"0":["CAP_A"] if mask&(1<<i) else []}
                for i,tid in enumerate(ids)
            }
            inst=iface.freeze_instance(tools,truth)
            ep=iface.begin_episode(inst,["CAP_A"])
            terminal=None
            for _ in range(20):
                action=v4.next_action(ep)
                if action["action"]=="DISCOVER":
                    ep=iface.apply_discovery(
                        ep,iface.discover(inst,ep,action["source_id"],action["query"])
                    )
                elif action["action"]=="PROBE":
                    ep=iface.apply_probe(
                        ep,iface.safe_probe(inst,ep,action["tool_id"],action["capability"])
                    )
                elif action["action"] in {"SELECT","ESCALATE"}:
                    terminal=action
                    break
                else:
                    self.fail(action)
            capable=[(cost,tid) for i,(tid,cost) in enumerate(zip(ids,costs)) if mask&(1<<i)]
            if capable:
                expected=min(capable)[1]
                self.assertEqual(terminal,{"action":"SELECT","tool_id":expected},mask)
            else:
                self.assertEqual(terminal["action"],"ESCALATE",mask)

    def test_identity_bijection_preserves_decision_semantics(self):
        first=iface.freeze_instance(
            [tool("A",4),tool("B",1)],
            {"A":{"0":["CAP_A"]},"B":{"0":["CAP_A"]}},
        )
        second=iface.freeze_instance(
            [tool("urn:random:77",4),tool("π-tool",1)],
            {"urn:random:77":{"0":["CAP_A"]},"π-tool":{"0":["CAP_A"]}},
        )
        def run(inst):
            ep=iface.begin_episode(inst,["CAP_A"])
            for _ in range(12):
                a=v4.next_action(ep)
                if a["action"]=="DISCOVER":
                    ep=iface.apply_discovery(inst,ep,iface.discover(inst,ep,a["source_id"],a["query"]))
                elif a["action"]=="PROBE":
                    ep=iface.apply_probe(inst,ep,iface.safe_probe(inst,ep,a["tool_id"],a["capability"]))
                else:
                    return a
            self.fail("budget")
        self.assertEqual(run(first)["tool_id"],"B")
        self.assertEqual(run(second)["tool_id"],"π-tool")


if __name__=="__main__":
    unittest.main(verbosity=2)
