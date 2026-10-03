from __future__ import annotations

import copy
import unittest

from canonical.runtime import tool_discovery_common_authority_interface_v2_v7 as iface
from canonical.runtime import tool_discovery_dynamic_candidate_v5 as v5
from canonical.runtime import tool_discovery_dynamic_candidate_v7 as v7


def instance():
    tools = [
        {
            "tool_id": "T0",
            "cost": 1.0,
            "available": True,
            "authorized": True,
            "epoch": 0,
            "safe_probe_capabilities": ["CAP_A", "CAP_B"],
            "meta": {"class": "alpha"},
        },
        {
            "tool_id": "T1",
            "cost": 2.0,
            "available": True,
            "authorized": True,
            "epoch": 0,
            "safe_probe_capabilities": ["CAP_A", "CAP_B"],
            "meta": {"class": "beta"},
        },
    ]
    truth = {
        "T0": {"0": ["CAP_A", "CAP_B"]},
        "T1": {"0": ["CAP_A", "CAP_B"]},
    }
    return iface.freeze_instance(tools, truth, authority_epoch=7)


class CommonAuthorityV2V7Tests(unittest.TestCase):
    def test_interface_digest_semantics_exactly_match_v7(self):
        frozen = instance()
        self.assertEqual(
            frozen["source"]["source_digest"],
            v5._tools_digest(frozen["public_tools"]),
        )
        self.assertEqual(
            frozen["source_set_digest"],
            v7._source_set_digest(
                [frozen["source"]],
                authority_epoch=frozen["authority_epoch"],
            ),
        )

    def test_episode_starts_with_zero_unbound_visible_routes(self):
        state = iface.begin_task(instance(), ["CAP_A"], decision_epoch=11)
        self.assertEqual(state["visible_tools"], [])
        self.assertEqual(len(state["discovery_sources"]), 1)
        self.assertEqual(
            state["discovery_sources"][0]["source_id"],
            iface.SOURCE_ID,
        )

    def test_v7_discovers_exact_common_catalog_before_probe_or_select(self):
        frozen = instance()
        state = iface.begin_task(frozen, ["CAP_A"], decision_epoch=11)
        self.assertEqual(
            v7.next_action(state),
            {
                "action": "DISCOVER",
                "source_id": iface.SOURCE_ID,
                "query": iface.CATALOG_QUERY,
                "authority_epoch": 7,
            },
        )
        receipt = iface.discover(
            frozen,
            state,
            iface.SOURCE_ID,
            iface.CATALOG_QUERY,
        )
        state = iface.apply_discovery(frozen, state, receipt)
        self.assertEqual(
            v7.next_action(state),
            {"action": "PROBE", "tool_id": "T0", "capability": "CAP_A"},
        )

    def test_safe_probe_truth_is_boolean_and_exactly_rederived(self):
        frozen = instance()
        state = iface.begin_task(frozen, ["CAP_A"])
        state = iface.apply_discovery(
            frozen,
            state,
            iface.discover(frozen, state, iface.SOURCE_ID, iface.CATALOG_QUERY),
        )
        receipt = iface.safe_probe(frozen, state, "T0", "CAP_A")
        self.assertIs(receipt["supported"], True)
        forged = copy.deepcopy(receipt)
        forged["supported"] = "true"
        with self.assertRaisesRegex(iface.InterfaceError, "PROBE_RECEIPT_NOT_EXACT_TRUTH"):
            iface.apply_probe(frozen, state, forged)
        state = iface.apply_probe(frozen, state, receipt)
        self.assertEqual(v7.next_action(state), {"action": "SELECT", "tool_id": "T0"})

    def test_catalog_transfers_across_task_change_without_rediscovery(self):
        frozen = instance()
        state = iface.begin_task(frozen, ["CAP_A"], decision_epoch=0)
        state = iface.apply_discovery(
            frozen,
            state,
            iface.discover(frozen, state, iface.SOURCE_ID, iface.CATALOG_QUERY),
        )
        state = iface.apply_probe(
            frozen,
            state,
            iface.safe_probe(frozen, state, "T0", "CAP_A"),
        )
        self.assertEqual(v7.next_action(state), {"action": "SELECT", "tool_id": "T0"})

        state = iface.retarget_task(
            frozen,
            state,
            ["CAP_B"],
            decision_epoch=1,
        )
        self.assertEqual(
            v7.next_action(state),
            {"action": "PROBE", "tool_id": "T0", "capability": "CAP_B"},
        )
        state = iface.apply_probe(
            frozen,
            state,
            iface.safe_probe(frozen, state, "T0", "CAP_B"),
        )
        self.assertEqual(v7.next_action(state), {"action": "SELECT", "tool_id": "T0"})

    def test_second_task_with_existing_probe_receipt_has_zero_reality_work(self):
        frozen = instance()
        state = iface.begin_task(frozen, ["CAP_A"], decision_epoch=0)
        state = iface.apply_discovery(
            frozen,
            state,
            iface.discover(frozen, state, iface.SOURCE_ID, iface.CATALOG_QUERY),
        )
        for cap in ("CAP_A", "CAP_B"):
            state = iface.apply_probe(
                frozen,
                state,
                iface.safe_probe(frozen, state, "T0", cap),
            )
        state = iface.retarget_task(frozen, state, ["CAP_B"], decision_epoch=99)
        self.assertEqual(v7.next_action(state), {"action": "SELECT", "tool_id": "T0"})

    def test_tampered_or_truncated_catalog_fails_before_policy_consumption(self):
        frozen = instance()
        state = iface.begin_task(frozen, ["CAP_A"])
        receipt = iface.discover(
            frozen,
            state,
            iface.SOURCE_ID,
            iface.CATALOG_QUERY,
        )
        receipt["tools"] = receipt["tools"][:1]
        with self.assertRaisesRegex(
            iface.InterfaceError,
            "DISCOVERY_RECEIPT_NOT_EXACT_AUTHORITY_RESULT",
        ):
            iface.apply_discovery(frozen, state, receipt)

    def test_hidden_support_cannot_be_smuggled_into_public_metadata(self):
        tools = [{
            "tool_id": "T0",
            "cost": 1.0,
            "available": True,
            "authorized": True,
            "epoch": 0,
            "safe_probe_capabilities": ["CAP_A"],
            "capabilities": ["CAP_A"],
        }]
        with self.assertRaisesRegex(
            iface.InterfaceError,
            "PUBLIC_METADATA_CONTAINS_HIDDEN_CAPABILITY_FIELD",
        ):
            iface.freeze_instance(
                tools,
                {"T0": {"0": ["CAP_A"]}},
            )

    def test_unsafe_probe_is_refused_by_environment_and_blocks_in_v7(self):
        frozen = iface.freeze_instance(
            [{
                "tool_id": "T0",
                "cost": 1.0,
                "available": True,
                "authorized": True,
                "epoch": 0,
                "safe_probe_capabilities": [],
            }],
            {"T0": {"0": ["CAP_A"]}},
        )
        state = iface.begin_task(frozen, ["CAP_A"])
        state = iface.apply_discovery(
            frozen,
            state,
            iface.discover(frozen, state, iface.SOURCE_ID, iface.CATALOG_QUERY),
        )
        self.assertEqual(
            v7.next_action(state),
            {
                "action": "ESCALATE",
                "reason": "CHEAPER_ADMISSIBLE_ROUTE_UNRESOLVED_NO_SAFE_PROBE",
                "tool_id": "T0",
            },
        )
        with self.assertRaisesRegex(iface.InterfaceError, "PROBE_NOT_EXPLICITLY_SAFE"):
            iface.safe_probe(frozen, state, "T0", "CAP_A")

    def test_tool_evolution_invalidates_old_episode_and_catalog(self):
        frozen = instance()
        state = iface.begin_task(frozen, ["CAP_A"])
        evolved = iface.evolve_tool(
            frozen,
            "T0",
            new_epoch=1,
            new_capabilities=["CAP_A"],
            public_metadata_updates={"cost": 3.0},
        )
        with self.assertRaisesRegex(iface.InterfaceError, "STALE_EPISODE_RESTART_REQUIRED"):
            iface.discover(
                evolved,
                state,
                iface.SOURCE_ID,
                iface.CATALOG_QUERY,
            )
        fresh = iface.begin_task(evolved, ["CAP_A"], decision_epoch=1)
        self.assertEqual(v7.next_action(fresh)["action"], "DISCOVER")
        self.assertEqual(fresh["authority_epoch"], 8)

    def test_matched_binding_is_exactly_same_for_brain_and_opus(self):
        binding = iface.matched_route_binding(instance())
        self.assertTrue(binding["same_frozen_tool_authority"])
        self.assertEqual(binding["brain"], binding["opus"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
