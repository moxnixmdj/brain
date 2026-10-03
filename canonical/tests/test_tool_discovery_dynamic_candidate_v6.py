from __future__ import annotations
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v6 as v6


def stale_metadata_state():
    tool={
        "tool_id":"T0",
        "epoch":0,
        "cost":1.0,
        "available":True,
        "authorized":True,
        "safe_probe_capabilities":["CAP_A"],
    }
    src={
        "source_id":"S0",
        "cost":0.0,
        "available":True,
        "authorized":True,
        "authoritative":True,
        "source_epoch":0,
        "source_digest":v5._tools_digest([tool]),
    }
    return {
        "required_capabilities":["CAP_A"],
        "decision_epoch":0,
        "constraint":None,
        "visible_tools":[],
        "discovery_sources":[src],
        "discovery_receipts":[{
            "kind":"DISCOVERY_RESULT",
            "source_id":"S0",
            "complete":True,
            "decision_epoch":0,
            "source_epoch":0,
            "source_digest":src["source_digest"],
            "source_set_digest":v5._source_set_digest([src]),
            "query":"CAP_A",
            "tools":[tool],
        }],
        "prior_probe_receipts":[{
            "kind":"SAFE_CAPABILITY_PROBE",
            "tool_id":"T0",
            "capability":"CAP_A",
            "epoch":1,
            "supported":True,
        }],
        "version_events":[{
            "kind":"TOOL_VERSION_CHANGED",
            "tool_id":"T0",
            "new_epoch":1,
        }],
    }


class ToolDiscoveryDynamicV6Tests(unittest.TestCase):
    def test_exact_hardened_v5_counterexample_selects_using_stale_discovery_metadata(self):
        state=stale_metadata_state()
        self.assertEqual(v5.next_action(state),{"action":"SELECT","tool_id":"T0"})

    def test_v6_forces_restart_before_reusing_stale_metadata(self):
        state=stale_metadata_state()
        self.assertEqual(v6.next_action(state),{
            "action":"ESCALATE",
            "reason":"TOOL_VERSION_CHANGED_RESTART_EPISODE",
            "tool_id":"T0",
            "new_epoch":1,
        })

    def test_v6_delegates_to_hardened_v5_without_version_change(self):
        state=stale_metadata_state()
        state["version_events"]=[]
        self.assertEqual(v6.next_action(state),v5.next_action(state))

    def test_version_event_container_must_be_well_formed(self):
        state=stale_metadata_state()
        state["version_events"]={"bad":"shape"}
        self.assertEqual(
            v6.next_action(state),
            {"action":"ESCALATE","reason":"VERSION_EVENTS_NOT_LIST"},
        )

    def test_restart_is_independent_of_current_probe_polarity(self):
        for supported in (True,False):
            state=stale_metadata_state()
            state["prior_probe_receipts"][0]["supported"]=supported
            self.assertEqual(
                v6.next_action(state)["reason"],
                "TOOL_VERSION_CHANGED_RESTART_EPISODE",
            )

    def test_restart_is_independent_of_old_cost(self):
        for cost in (0.0,1.0,1000.0):
            state=stale_metadata_state()
            tool=state["discovery_receipts"][0]["tools"][0]
            tool["cost"]=cost
            src=state["discovery_sources"][0]
            src["source_digest"]=v5._tools_digest([tool])
            state["discovery_receipts"][0]["source_digest"]=src["source_digest"]
            state["discovery_receipts"][0]["source_set_digest"]=v5._source_set_digest([src])
            self.assertEqual(
                v6.next_action(state)["reason"],
                "TOOL_VERSION_CHANGED_RESTART_EPISODE",
            )


if __name__=="__main__":
    unittest.main(verbosity=2)
