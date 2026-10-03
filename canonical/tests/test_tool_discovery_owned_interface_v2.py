from __future__ import annotations

import unittest

from canonical.runtime.tool_discovery_owned_interface_v2 import (
    InterfaceError,
    OwnedToolDiscoveryInterfaceV2,
    prove_instance,
)


BASE = [
    {
        "tool_id": "cheap",
        "cost": 1.0,
        "available": True,
        "authorized": True,
        "region": "EU",
        "capabilities": ["CAP_A", "CAP_B"],
    },
    {
        "tool_id": "expensive",
        "cost": 10.0,
        "available": True,
        "authorized": True,
        "region": "EU",
        "capabilities": ["CAP_A", "CAP_B"],
    },
    {
        "tool_id": "denied",
        "cost": 0.1,
        "available": True,
        "authorized": False,
        "region": "EU",
        "capabilities": ["CAP_A"],
    },
]


class Tests(unittest.TestCase):
    def test_exact_owned_instance_satisfies_contract(self):
        g = OwnedToolDiscoveryInterfaceV2(BASE, epoch=7)
        out = prove_instance(g)
        self.assertTrue(out["status"].startswith("PASS"), out)
        self.assertEqual(out["tool_count"], 3)
        required = [
            "finite_discovery_source_set_per_decision_epoch",
            "discovery_receipt_identifies_queried_source",
            "discovery_results_monotonically_add_visible_tool_identities_within_epoch",
            "union_of_authoritative_discovery_results_is_complete_for_declared_target_scope",
            "discovered_tool_metadata_correct_for_availability_authorization_cost_and_constraint_fields",
            "safe_capability_probe_receipts_are_truthful_and_epoch_bound",
            "version_epoch_stable_during_one_selection_episode_or_restarts_episode",
        ]
        self.assertTrue(all(out[x] is True for x in required), out)

    def test_discovery_hides_capability_truth(self):
        g = OwnedToolDiscoveryInterfaceV2(BASE)
        receipt = g.discover(episode_epoch=0)
        self.assertTrue(receipt["complete"])
        self.assertEqual(
            [x["tool_id"] for x in receipt["tools"]],
            ["cheap", "denied", "expensive"],
        )
        self.assertTrue(all("capabilities" not in x for x in receipt["tools"]))

    def test_safe_probe_is_truthful_and_epoch_bound(self):
        g = OwnedToolDiscoveryInterfaceV2(BASE, epoch=3)
        self.assertTrue(
            g.safe_probe("cheap", "CAP_A", episode_epoch=3)["supported"]
        )
        self.assertFalse(
            g.safe_probe("cheap", "CAP_Z", episode_epoch=3)["supported"]
        )
        with self.assertRaisesRegex(InterfaceError, "TOOL_UNAUTHORIZED"):
            g.safe_probe("denied", "CAP_A", episode_epoch=3)

    def test_unregistered_tool_is_not_invocable(self):
        g = OwnedToolDiscoveryInterfaceV2(BASE)
        with self.assertRaisesRegex(InterfaceError, "UNREGISTERED_TOOL_ID"):
            g.invoke("outside", episode_epoch=0)

    def test_registry_replacement_invalidates_episode(self):
        g = OwnedToolDiscoveryInterfaceV2(BASE, epoch=4)
        old = g.epoch
        new = g.replace_authority(BASE)
        self.assertEqual(new, old + 1)
        with self.assertRaisesRegex(InterfaceError, "EPOCH_CHANGED_RESTART_EPISODE"):
            g.discover(episode_epoch=old)
        with self.assertRaisesRegex(InterfaceError, "EPOCH_CHANGED_RESTART_EPISODE"):
            g.safe_probe("cheap", "CAP_A", episode_epoch=old)
        with self.assertRaisesRegex(InterfaceError, "EPOCH_CHANGED_RESTART_EPISODE"):
            g.invoke("cheap", episode_epoch=old)

    def test_complete_materialization_repairs_v3_cheaper_unseen_counterexample(self):
        g = OwnedToolDiscoveryInterfaceV2(BASE, epoch=2)
        # The expensive route already has positive evidence. In raw Dynamic V3,
        # if cheap were still undiscovered this could cause premature SELECT.
        # The owned adapter exposes the whole authority first, so cheap is seen
        # and must be resolved before expensive can be selected.
        prior = [{
            "kind": "SAFE_CAPABILITY_PROBE",
            "tool_id": "expensive",
            "capability": "CAP_A",
            "epoch": 2,
            "supported": True,
        }]
        action = g.next_action(
            required_capabilities=["CAP_A"],
            prior_probe_receipts=prior,
            episode_epoch=2,
        )
        self.assertEqual(
            action,
            {"action": "PROBE", "tool_id": "cheap", "capability": "CAP_A"},
        )

    def test_after_cheapest_positive_v3_selects_global_cheapest(self):
        g = OwnedToolDiscoveryInterfaceV2(BASE, epoch=2)
        prior = [
            g.safe_probe("cheap", "CAP_A", episode_epoch=2),
            g.safe_probe("expensive", "CAP_A", episode_epoch=2),
        ]
        action = g.next_action(
            required_capabilities=["CAP_A"],
            prior_probe_receipts=prior,
            episode_epoch=2,
        )
        self.assertEqual(action, {"action": "SELECT", "tool_id": "cheap"})

    def test_constraint_filtering_uses_same_authority_metadata(self):
        g = OwnedToolDiscoveryInterfaceV2(BASE, epoch=1)
        action = g.next_action(
            required_capabilities=["CAP_A"],
            constraint={"op": "eq", "path": "region", "value": "EU"},
            episode_epoch=1,
        )
        self.assertEqual(
            action,
            {"action": "PROBE", "tool_id": "cheap", "capability": "CAP_A"},
        )

    def test_digest_changes_on_epoch_replacement(self):
        g = OwnedToolDiscoveryInterfaceV2(BASE, epoch=0)
        a = g.registry_digest_sha256()
        g.replace_authority(BASE)
        b = g.registry_digest_sha256()
        self.assertNotEqual(a, b)

    def test_zero_credit(self):
        out = prove_instance(OwnedToolDiscoveryInterfaceV2(BASE))
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
