from __future__ import annotations
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v3 as v3
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4


def base_state():
    return {
        "required_capabilities": ["CAP_A"],
        "constraint": None,
        "visible_tools": [
            {"tool_id":"T0","cost":10.0,"available":True,"authorized":True,"epoch":0}
        ],
        "discovery_sources": [
            {"source_id":"S0","cost":0.1,"available":True}
        ],
        "discovery_receipts": [],
        "prior_probe_receipts": [],
        "version_events": [],
    }


class ToolDiscoveryDynamicV4Tests(unittest.TestCase):
    def test_v3_counterexample_visible_expensive_route_preempts_cheaper_undiscovered(self):
        state=base_state()
        self.assertEqual(v3.next_action(state)["action"], "PROBE")
        state["prior_probe_receipts"]=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A","epoch":0,"supported":True}
        ]
        self.assertEqual(v3.next_action(state), {"action":"SELECT","tool_id":"T0"})
        # S0 is still unqueried. Under a complete authoritative interface S0 may
        # contain a cheaper sufficient route, so V3 cannot prove least-cost.
        self.assertEqual(state["discovery_receipts"], [])

    def test_v4_discovers_before_probe_or_select(self):
        state=base_state()
        self.assertEqual(
            v4.next_action(state),
            {"action":"DISCOVER","source_id":"S0","query":"CAP_A"},
        )

    def test_v4_selects_cheapest_after_discovery_closure(self):
        state=base_state()
        state["discovery_receipts"]=[{"kind":"DISCOVERY_RESULT","source_id":"S0"}]
        state["visible_tools"].append(
            {"tool_id":"T1","cost":1.0,"available":True,"authorized":True,"epoch":0}
        )
        self.assertEqual(
            v4.next_action(state),
            {"action":"PROBE","tool_id":"T1","capability":"CAP_A"},
        )
        state["prior_probe_receipts"]=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T1","capability":"CAP_A","epoch":0,"supported":True}
        ]
        self.assertEqual(v4.next_action(state), {"action":"SELECT","tool_id":"T1"})

    def test_v4_falsified_cheapest_advances_to_next(self):
        state=base_state()
        state["discovery_receipts"]=[{"kind":"DISCOVERY_RESULT","source_id":"S0"}]
        state["visible_tools"].append(
            {"tool_id":"T1","cost":1.0,"available":True,"authorized":True,"epoch":0}
        )
        state["prior_probe_receipts"]=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T1","capability":"CAP_A","epoch":0,"supported":False}
        ]
        self.assertEqual(
            v4.next_action(state),
            {"action":"PROBE","tool_id":"T0","capability":"CAP_A"},
        )

    def test_v4_never_uses_stale_epoch_evidence(self):
        state=base_state()
        state["discovery_receipts"]=[{"kind":"DISCOVERY_RESULT","source_id":"S0"}]
        state["prior_probe_receipts"]=[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A","epoch":0,"supported":True}
        ]
        state["version_events"]=[
            {"kind":"TOOL_VERSION_CHANGED","tool_id":"T0","new_epoch":1}
        ]
        self.assertEqual(
            v4.next_action(state),
            {"action":"PROBE","tool_id":"T0","capability":"CAP_A"},
        )


if __name__=="__main__":
    unittest.main(verbosity=2)
