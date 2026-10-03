from __future__ import annotations

import unittest

from canonical.runtime import tool_discovery_common_authority_interface_v2 as iface
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4


def tool(
    tid: str,
    cost: float,
    *,
    epoch: int = 0,
    available: bool = True,
    authorized: bool = True,
    safe=("CAP_A",),
):
    return {
        "tool_id": tid,
        "cost": float(cost),
        "available": available,
        "authorized": authorized,
        "epoch": epoch,
        "safe_probe_capabilities": list(safe),
        "meta": {"region": "X", "risk": 0},
    }


def run(instance, required=("CAP_A",), budget=64):
    ep = iface.begin_episode(instance, required)
    trace = []
    for _ in range(budget):
        action = v4.next_action(ep)
        trace.append(action)
        committed = iface.commit_action(instance, ep, action)
        if committed["terminal"]:
            return committed["result"], trace, ep
        ep = committed["episode"]
    raise AssertionError("action budget exhausted")


class CommonAuthorityInterfaceV2Tests(unittest.TestCase):
    def _instance(self):
        return iface.freeze_instance(
            [
                tool("opaque://expensive", 10),
                tool("never-seen-before::cheap", 1, safe=("CAP_A", "CAP_B")),
                tool("第三工具", 3),
            ],
            {
                "opaque://expensive": {"0": ["CAP_A"]},
                "never-seen-before::cheap": {"0": ["CAP_A", "CAP_B"]},
                "第三工具": {"0": []},
            },
        )

    def test_unknown_identities_start_hidden_and_discovery_is_exact_complete(self):
        inst = self._instance()
        ep = iface.begin_episode(inst, ["CAP_A"])
        self.assertEqual(ep["visible_tools"], [])
        action = v4.next_action(ep)
        self.assertEqual(action["action"], "DISCOVER")
        committed = iface.commit_action(inst, ep, action)
        ep2 = committed["episode"]
        self.assertEqual(
            {x["tool_id"] for x in ep2["visible_tools"]},
            {x["tool_id"] for x in inst["public_tools"]},
        )
        self.assertTrue(all("capabilities" not in x for x in ep2["visible_tools"]))
        self.assertTrue(all("hidden_capabilities" not in x for x in ep2["visible_tools"]))

    def test_current_safe_probe_aware_v4_selects_global_cheapest_supported_route(self):
        result, trace, _ = run(self._instance())
        self.assertEqual(result["tool_id"], "never-seen-before::cheap")
        self.assertEqual(trace[0]["action"], "DISCOVER")
        self.assertTrue(any(x["action"] == "PROBE" for x in trace))

    def test_safe_probe_permission_is_public_but_support_truth_remains_hidden(self):
        inst = iface.freeze_instance(
            [tool("T", 1, safe=("CAP_A", "CAP_B"))],
            {"T": {"0": ["CAP_A"]}},
        )
        ep = iface.begin_episode(inst, ["CAP_B"])
        ep = iface.commit_action(inst, ep, v4.next_action(ep))["episode"]
        public_t = ep["visible_tools"][0]
        self.assertEqual(public_t["safe_probe_capabilities"], ["CAP_A", "CAP_B"])
        self.assertNotIn("capabilities", public_t)
        probe_action = v4.next_action(ep)
        self.assertEqual(probe_action, {"action": "PROBE", "tool_id": "T", "capability": "CAP_B"})
        committed = iface.commit_action(inst, ep, probe_action)
        self.assertFalse(committed["receipt"]["supported"])

    def test_unpermitted_probe_never_occurs_even_if_hidden_tool_would_support(self):
        inst = iface.freeze_instance(
            [
                tool("CHEAP_UNPROBEABLE", 1, safe=()),
                tool("SAFE", 2, safe=("CAP_A",)),
            ],
            {
                "CHEAP_UNPROBEABLE": {"0": ["CAP_A"]},
                "SAFE": {"0": ["CAP_A"]},
            },
        )
        result, trace, _ = run(inst)
        self.assertEqual(result["tool_id"], "SAFE")
        self.assertFalse(any(
            x.get("action") == "PROBE" and x.get("tool_id") == "CHEAP_UNPROBEABLE"
            for x in trace
        ))

    def test_negative_cheaper_probe_advances_to_next_route(self):
        inst = iface.freeze_instance(
            [tool("CHEAP", 1), tool("EXPENSIVE", 2)],
            {"CHEAP": {"0": []}, "EXPENSIVE": {"0": ["CAP_A"]}},
        )
        result, trace, _ = run(inst)
        self.assertEqual(result["tool_id"], "EXPENSIVE")
        probes = [x["tool_id"] for x in trace if x["action"] == "PROBE"]
        self.assertEqual(probes, ["CHEAP", "EXPENSIVE"])

    def test_no_supported_route_escalates_only_after_truthful_negative_probes(self):
        inst = iface.freeze_instance(
            [tool("A", 1), tool("B", 2)],
            {"A": {"0": []}, "B": {"0": []}},
        )
        result, trace, _ = run(inst)
        self.assertEqual(result["action"], "ESCALATE")
        self.assertEqual(
            [x["tool_id"] for x in trace if x["action"] == "PROBE"],
            ["A", "B"],
        )

    def test_version_change_between_decision_and_commit_fails_closed(self):
        inst = iface.freeze_instance(
            [tool("CHEAP", 1), tool("EXPENSIVE", 10)],
            {"CHEAP": {"0": ["CAP_A"]}, "EXPENSIVE": {"0": ["CAP_A"]}},
        )
        ep = iface.begin_episode(inst, ["CAP_A"])
        while True:
            action = v4.next_action(ep)
            if action["action"] == "SELECT":
                break
            ep = iface.commit_action(inst, ep, action)["episode"]
        self.assertEqual(action["tool_id"], "CHEAP")

        changed = iface.evolve_tool(
            inst,
            "CHEAP",
            new_epoch=1,
            new_capabilities=["CAP_A"],
            public_metadata_updates={"cost": 100.0},
        )
        with self.assertRaises(iface.InterfaceError) as cm:
            iface.commit_action(changed, ep, action)
        self.assertIn("STALE_EPISODE_RESTART_REQUIRED", str(cm.exception))

        result, _, _ = run(changed)
        self.assertEqual(result["tool_id"], "EXPENSIVE")

    def test_authorization_change_requires_restart_before_old_select_can_commit(self):
        inst = iface.freeze_instance(
            [tool("CHEAP", 1), tool("BACKUP", 2)],
            {"CHEAP": {"0": ["CAP_A"]}, "BACKUP": {"0": ["CAP_A"]}},
        )
        ep = iface.begin_episode(inst, ["CAP_A"])
        while True:
            action = v4.next_action(ep)
            if action["action"] == "SELECT":
                break
            ep = iface.commit_action(inst, ep, action)["episode"]

        changed = iface.evolve_tool(
            inst,
            "CHEAP",
            new_epoch=1,
            new_capabilities=["CAP_A"],
            public_metadata_updates={"authorized": False},
        )
        with self.assertRaises(iface.InterfaceError):
            iface.commit_action(changed, ep, action)
        result, _, _ = run(changed)
        self.assertEqual(result["tool_id"], "BACKUP")

    def test_safe_probe_permission_change_requires_restart(self):
        inst = iface.freeze_instance(
            [tool("T", 1, safe=("CAP_A",))],
            {"T": {"0": ["CAP_A"]}},
        )
        ep = iface.begin_episode(inst, ["CAP_A"])
        ep = iface.commit_action(inst, ep, v4.next_action(ep))["episode"]
        action = v4.next_action(ep)
        self.assertEqual(action["action"], "PROBE")

        changed = iface.evolve_tool(
            inst,
            "T",
            new_epoch=1,
            new_capabilities=["CAP_A"],
            public_metadata_updates={"safe_probe_capabilities": []},
        )
        with self.assertRaises(iface.InterfaceError):
            iface.commit_action(changed, ep, action)
        result, trace, _ = run(changed)
        self.assertEqual(result["action"], "ESCALATE")
        self.assertFalse(any(x["action"] == "PROBE" for x in trace))

    def test_forged_probe_truth_fails_closed(self):
        inst = self._instance()
        ep = iface.begin_episode(inst, ["CAP_A"])
        ep = iface.commit_action(inst, ep, v4.next_action(ep))["episode"]
        rec = iface.safe_probe(inst, ep, "第三工具", "CAP_A")
        self.assertFalse(rec["supported"])
        rec["supported"] = True
        with self.assertRaises(iface.InterfaceError) as cm:
            iface.apply_probe(inst, ep, rec)
        self.assertIn("PROBE_RECEIPT_TRUTH_MISMATCH", str(cm.exception))

    def test_truncated_discovery_payload_fails_closed(self):
        inst = self._instance()
        ep = iface.begin_episode(inst, ["CAP_A"])
        rec = iface.discover(inst, ep, iface.SOURCE_ID, "CAP_A")
        rec["tools"] = rec["tools"][:-1]
        with self.assertRaises(iface.InterfaceError) as cm:
            iface.apply_discovery(inst, ep, rec)
        self.assertIn("DISCOVERY_PAYLOAD_NOT_EXACT_COMPLETE_AUTHORITY", str(cm.exception))

    def test_hidden_support_field_in_public_metadata_fails_closed(self):
        bad = tool("T", 1)
        bad["capabilities"] = ["CAP_A"]
        with self.assertRaises(iface.InterfaceError):
            iface.freeze_instance([bad], {"T": {"0": ["CAP_A"]}})

    def test_exhaustive_small_support_masks(self):
        ids = ["U0", "U1", "U2", "U3"]
        costs = [4, 1, 3, 2]
        for mask in range(1 << len(ids)):
            tools = [tool(tid, cost) for tid, cost in zip(ids, costs)]
            truth = {
                tid: {"0": ["CAP_A"] if mask & (1 << i) else []}
                for i, tid in enumerate(ids)
            }
            inst = iface.freeze_instance(tools, truth)
            result, _, _ = run(inst)
            capable = [
                (cost, tid)
                for i, (tid, cost) in enumerate(zip(ids, costs))
                if mask & (1 << i)
            ]
            if capable:
                self.assertEqual(result["tool_id"], min(capable)[1], mask)
            else:
                self.assertEqual(result["action"], "ESCALATE", mask)

    def test_identity_bijection_does_not_change_decision_semantics(self):
        a = iface.freeze_instance(
            [tool("A", 4), tool("B", 1)],
            {"A": {"0": ["CAP_A"]}, "B": {"0": ["CAP_A"]}},
        )
        b = iface.freeze_instance(
            [tool("urn:random:77", 4), tool("π-tool", 1)],
            {"urn:random:77": {"0": ["CAP_A"]}, "π-tool": {"0": ["CAP_A"]}},
        )
        self.assertEqual(run(a)[0]["tool_id"], "B")
        self.assertEqual(run(b)[0]["tool_id"], "π-tool")


if __name__ == "__main__":
    unittest.main(verbosity=2)
