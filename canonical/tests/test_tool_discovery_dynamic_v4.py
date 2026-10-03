from __future__ import annotations
import copy
import itertools
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4


def tool(tid, cost, *, available=True, authorized=True, epoch=0):
    return {
        "tool_id": tid,
        "cost": float(cost),
        "available": available,
        "authorized": authorized,
        "epoch": epoch,
        "meta": {"region": "X", "risk": 0, "tags": ["prod"], "provider": "P"},
    }


class ToolDiscoveryDynamicV4Tests(unittest.TestCase):
    def _initial(self):
        return {
            "required_capabilities": ["CAP_A"],
            "constraint": None,
            "visible_tools": [tool("EXPENSIVE", 10)],
            "discovery_sources": [{"source_id": "S0", "cost": 0.1, "available": True}],
            "prior_probe_receipts": [],
            "discovery_receipts": [],
            "version_events": [],
        }

    def test_v3_counterexample_selects_before_cheaper_discovery(self):
        public = self._initial()
        first = v3.next_action(public)
        self.assertEqual(first["action"], "PROBE")
        public["prior_probe_receipts"].append({
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": "EXPENSIVE",
            "capability": "CAP_A",
            "epoch": 0,
            "supported": True,
        })
        second = v3.next_action(public)
        self.assertEqual(second, {"action": "SELECT", "tool_id": "EXPENSIVE"})
        self.assertEqual(public["discovery_receipts"], [])

    def test_v4_discovery_first_fixes_counterexample(self):
        public = self._initial()
        self.assertEqual(v4.next_action(public)["action"], "DISCOVER")
        cheap = tool("CHEAP", 1)
        public["visible_tools"].append(cheap)
        public["discovery_receipts"].append({
            "kind": "DISCOVERY_RESULT", "source_id": "S0", "tools": [cheap]
        })
        self.assertEqual(v4.next_action(public), {
            "action": "PROBE", "tool_id": "CHEAP", "capability": "CAP_A"
        })
        public["prior_probe_receipts"].append({
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": "CHEAP",
            "capability": "CAP_A",
            "epoch": 0,
            "supported": True,
        })
        self.assertEqual(v4.next_action(public), {"action": "SELECT", "tool_id": "CHEAP"})

    def _run(self, tools, sources, support):
        by_id = {t["tool_id"]: t for t in tools}
        initial_ids = {tools[0]["tool_id"]}
        public = {
            "required_capabilities": ["CAP_A"],
            "constraint": None,
            "visible_tools": [copy.deepcopy(by_id[x]) for x in initial_ids],
            "discovery_sources": [
                {"source_id": sid, "cost": float(i+1)/10, "available": True}
                for i, (sid, _) in enumerate(sources)
            ],
            "prior_probe_receipts": [],
            "discovery_receipts": [],
            "version_events": [],
        }
        source_map = dict(sources)
        for _ in range(100):
            action = v4.next_action(public)
            kind = action["action"]
            if kind == "DISCOVER":
                ids = source_map[action["source_id"]]
                rows = [copy.deepcopy(by_id[x]) for x in ids]
                present = {x["tool_id"] for x in public["visible_tools"]}
                public["visible_tools"].extend(x for x in rows if x["tool_id"] not in present)
                public["discovery_receipts"].append({
                    "kind": "DISCOVERY_RESULT",
                    "source_id": action["source_id"],
                    "tools": rows,
                })
            elif kind == "PROBE":
                tid = action["tool_id"]
                public["prior_probe_receipts"].append({
                    "kind": "SAFE_CAPABILITY_PROBE",
                    "tool_id": tid,
                    "capability": action["capability"],
                    "epoch": by_id[tid]["epoch"],
                    "supported": bool(support[tid]),
                })
            elif kind == "SELECT":
                return action["tool_id"], public
            elif kind == "ESCALATE":
                return None, public
            else:
                self.fail(action)
        self.fail("action budget exceeded")

    def test_exhaustive_small_finite_ecosystems_choose_global_least_cost_sufficient(self):
        base = [tool("T0", 4), tool("T1", 3), tool("T2", 2), tool("T3", 1)]
        sources = [("S0", ["T1", "T2"]), ("S1", ["T3"])]
        for mask in range(16):
            support = {f"T{i}": bool(mask & (1 << i)) for i in range(4)}
            selected, _ = self._run(base, sources, support)
            sufficient = [t for t in base if support[t["tool_id"]]]
            expected = min(sufficient, key=lambda t: (t["cost"], t["tool_id"]))["tool_id"] if sufficient else None
            self.assertEqual(selected, expected, (mask, support))

    def test_unavailable_or_unauthorized_cheaper_tool_is_not_selected(self):
        tools = [
            tool("T0", 5),
            tool("T1", 1, available=False),
            tool("T2", 2, authorized=False),
            tool("T3", 3),
        ]
        sources = [("S0", ["T1", "T2", "T3"])]
        selected, _ = self._run(tools, sources, {t["tool_id"]: True for t in tools})
        self.assertEqual(selected, "T3")

    def test_current_epoch_receipt_reused_but_version_change_invalidates(self):
        public = {
            "required_capabilities": ["CAP_A"],
            "constraint": None,
            "visible_tools": [tool("T0", 1)],
            "discovery_sources": [],
            "discovery_receipts": [],
            "prior_probe_receipts": [{
                "kind": "SAFE_CAPABILITY_PROBE", "tool_id": "T0",
                "capability": "CAP_A", "epoch": 0, "supported": True,
            }],
            "version_events": [],
        }
        self.assertEqual(v4.next_action(public), {"action": "SELECT", "tool_id": "T0"})
        public["version_events"] = [{"kind": "TOOL_VERSION_CHANGED", "tool_id": "T0", "new_epoch": 1}]
        self.assertEqual(v4.next_action(public), {
            "action": "PROBE", "tool_id": "T0", "capability": "CAP_A"
        })

    def test_no_route_escalates_only_after_discovery_and_negative_evidence(self):
        tools = [tool("T0", 1), tool("T1", 2)]
        selected, public = self._run(tools, [("S0", ["T1"])], {"T0": False, "T1": False})
        self.assertIsNone(selected)
        self.assertEqual({x["source_id"] for x in public["discovery_receipts"]}, {"S0"})
        self.assertEqual(
            {(x["tool_id"], x["supported"]) for x in public["prior_probe_receipts"]},
            {("T0", False), ("T1", False)},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
