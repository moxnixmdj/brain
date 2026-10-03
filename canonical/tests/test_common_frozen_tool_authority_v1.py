from __future__ import annotations

import itertools
import unittest

from canonical.runtime.common_frozen_tool_authority_v1 import (
    AuthorityError,
    CommonFrozenToolAuthority,
    prove_common_authority_instance,
)
from canonical.runtime import tool_discovery_dynamic_candidate_v4 as v4


BASE = [
    {
        "tool_id": "opaque::zeta",
        "cost": 9.0,
        "available": True,
        "authorized": True,
        "region": "X",
        "capabilities": ["CAP_A"],
    },
    {
        "tool_id": "opaque::alpha",
        "cost": 1.0,
        "available": True,
        "authorized": True,
        "region": "X",
        "capabilities": ["CAP_A", "CAP_B"],
    },
    {
        "tool_id": "opaque::denied",
        "cost": 0.1,
        "available": True,
        "authorized": False,
        "region": "X",
        "capabilities": ["CAP_A"],
    },
]


class CommonFrozenToolAuthorityTests(unittest.TestCase):
    def test_both_routes_get_exact_same_complete_authority(self):
        a = CommonFrozenToolAuthority(BASE, epoch=7)
        out = prove_common_authority_instance(a)
        self.assertTrue(out["status"].startswith("PASS__"), out)
        self.assertTrue(out["brain_opus_route_views_identical"])
        self.assertTrue(out["same_authority_digest"])
        self.assertTrue(out["common_frozen_authority_not_brain_only"])
        self.assertEqual(
            out["registry_ids"],
            ["opaque::alpha", "opaque::denied", "opaque::zeta"],
        )

    def test_unknown_identity_is_hidden_until_discover(self):
        a = CommonFrozenToolAuthority(BASE)
        public = a.initial_public_state(
            "BRAIN",
            required_capabilities=["CAP_A"],
            initial_visible_ids=["opaque::zeta"],
            episode_epoch=0,
        )
        self.assertEqual([x["tool_id"] for x in public["visible_tools"]], ["opaque::zeta"])
        action = v4.next_action(public)
        self.assertEqual(action["action"], "DISCOVER")
        public = a.apply_discover(public, action, "BRAIN", episode_epoch=0)
        self.assertEqual(
            {x["tool_id"] for x in public["visible_tools"]},
            {"opaque::alpha", "opaque::denied", "opaque::zeta"},
        )

    def test_v4_reaches_global_cheapest_sufficient_route_after_common_discovery(self):
        a = CommonFrozenToolAuthority(BASE)
        public = a.initial_public_state(
            "BRAIN",
            required_capabilities=["CAP_A"],
            initial_visible_ids=["opaque::zeta"],
            episode_epoch=0,
        )
        for _ in range(20):
            action = v4.next_action(public)
            if action["action"] == "DISCOVER":
                public = a.apply_discover(public, action, "BRAIN", episode_epoch=0)
            elif action["action"] == "PROBE":
                public = a.apply_probe(public, action, "BRAIN", episode_epoch=0)
            elif action["action"] == "SELECT":
                self.assertEqual(action["tool_id"], "opaque::alpha")
                break
            else:
                self.fail(action)
        else:
            self.fail("episode did not terminate")

    def test_same_truthful_probe_semantics_for_brain_and_opus(self):
        a = CommonFrozenToolAuthority(BASE, epoch=3)
        for tid in ("opaque::alpha", "opaque::zeta"):
            for cap in ("CAP_A", "CAP_B", "CAP_Z"):
                b = a.safe_probe("BRAIN", tid, cap, episode_epoch=3)
                o = a.safe_probe("OPUS55", tid, cap, episode_epoch=3)
                self.assertEqual(b, o)

    def test_unregistered_identity_cannot_be_invoked_by_either_route(self):
        a = CommonFrozenToolAuthority(BASE)
        for route in ("BRAIN", "OPUS55"):
            with self.assertRaisesRegex(AuthorityError, "UNREGISTERED_TOOL_ID"):
                a.invoke(route, "outside", episode_epoch=0)

    def test_epoch_replacement_invalidates_both_routes(self):
        a = CommonFrozenToolAuthority(BASE, epoch=4)
        old = a.epoch
        a.replace_authority(BASE)
        for route in ("BRAIN", "OPUS55"):
            with self.assertRaisesRegex(AuthorityError, "EPOCH_CHANGED_RESTART_EPISODE"):
                a.discover(route, episode_epoch=old)

    def test_all_v1_interface_properties_are_true_by_construction(self):
        out = prove_common_authority_instance(CommonFrozenToolAuthority(BASE))
        keys = [
            "finite_discovery_source_set_per_decision_epoch",
            "discovery_receipt_identifies_queried_source",
            "discovery_results_monotonically_add_visible_tool_identities_within_epoch",
            "union_of_authoritative_discovery_results_is_complete_for_declared_target_scope",
            "discovered_tool_metadata_correct_for_availability_authorization_cost_and_constraint_fields",
            "safe_capability_probe_receipts_are_truthful_and_epoch_bound",
            "version_epoch_stable_during_one_selection_episode_or_restarts_episode",
        ]
        self.assertTrue(all(out[k] is True for k in keys), out)

    def test_identity_names_are_semantically_opaque(self):
        entries = [
            {"tool_id": name, "cost": i + 1.0, "available": True, "authorized": True, "capabilities": ["C"]}
            for i, name in enumerate(["🜁", "7d91", "not-a-known-tool"])
        ]
        out = prove_common_authority_instance(CommonFrozenToolAuthority(entries))
        self.assertTrue(out["status"].startswith("PASS__"), out)
        self.assertEqual(set(out["registry_ids"]), {"🜁", "7d91", "not-a-known-tool"})

    def test_small_finite_authorities_always_discover_exact_registry(self):
        names = ["A", "B", "C", "D"]
        for mask in range(1 << len(names)):
            entries = [
                {
                    "tool_id": name,
                    "cost": i + 0.25,
                    "available": bool((mask >> i) & 1),
                    "authorized": True,
                    "capabilities": ["C"] if i % 2 == 0 else [],
                }
                for i, name in enumerate(names)
            ]
            a = CommonFrozenToolAuthority(entries, epoch=mask)
            out = prove_common_authority_instance(a)
            self.assertTrue(out["status"].startswith("PASS__"), (mask, out))
            self.assertEqual(set(out["discovered_ids"]), set(names))

    def test_zero_credit(self):
        out = prove_common_authority_instance(CommonFrozenToolAuthority(BASE))
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
