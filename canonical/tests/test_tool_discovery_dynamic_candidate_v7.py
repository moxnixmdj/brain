from __future__ import annotations

import copy
import unittest

from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v6 as v6
from canonical.runtime import tool_discovery_dynamic_candidate_v7 as v7


def _tool():
    return {
        "tool_id":"T0",
        "epoch":0,
        "cost":1.0,
        "available":True,
        "authorized":True,
        "safe_probe_capabilities":["CAP_A","CAP_B"],
    }


def _v5_source(tool):
    return {
        "source_id":"S0",
        "cost":0.0,
        "available":True,
        "authorized":True,
        "authoritative":True,
        "source_epoch":0,
        "source_digest":v5._tools_digest([tool]),
    }


def v6_task_a_state():
    tool=_tool()
    src=_v5_source(tool)
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
        "prior_probe_receipts":[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A","epoch":0,"supported":True},
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_B","epoch":0,"supported":True},
        ],
        "version_events":[],
    }


def v7_state(required=("CAP_A",), decision_epoch=0):
    tool=_tool()
    src={
        **_v5_source(tool),
        "catalog_query":"__FULL_AUTHORITY_CATALOG__",
    }
    authority_epoch=0
    source_set_digest=v7._source_set_digest([src],authority_epoch=authority_epoch)
    return {
        "required_capabilities":list(required),
        "decision_epoch":decision_epoch,
        "authority_epoch":authority_epoch,
        "constraint":None,
        "visible_tools":[],
        "discovery_sources":[src],
        "discovery_receipts":[{
            "kind":"DISCOVERY_RESULT",
            "source_id":"S0",
            "complete":True,
            "authority_epoch":authority_epoch,
            "source_epoch":0,
            "source_digest":src["source_digest"],
            "source_set_digest":source_set_digest,
            "query":src["catalog_query"],
            "tools":[tool],
        }],
        "prior_probe_receipts":[
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_A","epoch":0,"supported":True},
            {"kind":"SAFE_CAPABILITY_PROBE","tool_id":"T0","capability":"CAP_B","epoch":0,"supported":True},
        ],
        "version_events":[],
    }


class ToolDiscoveryDynamicV7Tests(unittest.TestCase):
    def test_v6_forces_rediscovery_on_second_task_query_and_decision_epoch(self):
        first=v6_task_a_state()
        self.assertEqual(v6.next_action(first),{"action":"SELECT","tool_id":"T0"})
        second=copy.deepcopy(first)
        second["required_capabilities"]=["CAP_B"]
        second["decision_epoch"]=1
        action=v6.next_action(second)
        self.assertEqual(action["action"],"DISCOVER")
        self.assertEqual(action["query"],"CAP_B")

    def test_v6_query_change_alone_forces_redundant_rediscovery(self):
        state=v6_task_a_state()
        state["required_capabilities"]=["CAP_B"]
        # Keep decision epoch unchanged: query coupling alone is sufficient.
        action=v6.next_action(state)
        self.assertEqual(action["action"],"DISCOVER")
        self.assertEqual(action["query"],"CAP_B")

    def test_v6_decision_epoch_change_alone_forces_redundant_rediscovery(self):
        state=v6_task_a_state()
        # Keep required capabilities unchanged: decision-epoch coupling alone is sufficient.
        state["decision_epoch"]=1
        action=v6.next_action(state)
        self.assertEqual(action["action"],"DISCOVER")
        self.assertEqual(action["query"],"CAP_A")

    def test_v7_reuses_catalog_and_probe_evidence_across_task_change(self):
        first=v7_state(("CAP_A",),0)
        second=v7_state(("CAP_B",),1)
        self.assertEqual(v7.next_action(first),{"action":"SELECT","tool_id":"T0"})
        self.assertEqual(v7.next_action(second),{"action":"SELECT","tool_id":"T0"})

    def test_task_change_with_new_capability_needs_probe_not_rediscovery(self):
        state=v7_state(("CAP_C",),9)
        state["discovery_receipts"][0]["tools"][0]["safe_probe_capabilities"].append("CAP_C")
        tool=state["discovery_receipts"][0]["tools"][0]
        src=state["discovery_sources"][0]
        src["source_digest"]=v5._tools_digest([tool])
        state["discovery_receipts"][0]["source_digest"]=src["source_digest"]
        state["discovery_receipts"][0]["source_set_digest"]=v7._source_set_digest(
            state["discovery_sources"],authority_epoch=state["authority_epoch"]
        )
        self.assertEqual(
            v7.next_action(state),
            {"action":"PROBE","tool_id":"T0","capability":"CAP_C"},
        )

    def test_authority_epoch_change_invalidates_catalog_receipt(self):
        state=v7_state(("CAP_B",),1)
        state["authority_epoch"]=1
        state["discovery_receipts"][0]["authority_epoch"]=0
        action=v7.next_action(state)
        self.assertEqual(action["action"],"DISCOVER")
        self.assertEqual(action["query"],"__FULL_AUTHORITY_CATALOG__")

    def test_source_epoch_or_content_change_invalidates_catalog_receipt(self):
        state=v7_state(("CAP_B",),1)
        state["discovery_sources"][0]["source_epoch"]=1
        action=v7.next_action(state)
        self.assertEqual(action["action"],"DISCOVER")

    def test_tool_version_change_preserves_v6_restart_boundary(self):
        state=v7_state(("CAP_B",),1)
        state["version_events"]=[{
            "kind":"TOOL_VERSION_CHANGED",
            "tool_id":"T0",
            "new_epoch":1,
        }]
        self.assertEqual(v7.next_action(state),{
            "action":"ESCALATE",
            "reason":"TOOL_VERSION_CHANGED_RESTART_EPISODE",
            "tool_id":"T0",
            "new_epoch":1,
        })

    def test_explicit_authority_change_restarts_episode(self):
        state=v7_state(("CAP_B",),1)
        state["version_events"]=[{
            "kind":"TOOL_AUTHORITY_CHANGED",
            "new_authority_epoch":1,
        }]
        self.assertEqual(v7.next_action(state),{
            "action":"ESCALATE",
            "reason":"TOOL_AUTHORITY_CHANGED_RESTART_EPISODE",
            "new_authority_epoch":1,
        })

    def test_catalog_query_is_task_independent_and_load_bearing(self):
        state=v7_state(("CAP_B",),99)
        state["discovery_receipts"][0]["query"]="CAP_B"
        action=v7.next_action(state)
        self.assertEqual(action["action"],"DISCOVER")
        self.assertEqual(action["query"],"__FULL_AUTHORITY_CATALOG__")


if __name__=="__main__":
    unittest.main(verbosity=2)
