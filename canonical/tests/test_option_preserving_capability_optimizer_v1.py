from __future__ import annotations

import unittest

from canonical.runtime import option_preserving_capability_optimizer_v1 as o


def cap(
    cid,
    *,
    semantic="sha256:semantic",
    implementation="impl",
    representation="repr",
    substrate="cpu",
    capability=5,
    generalization=5,
    reliability=5,
    latency=5,
    compute=5,
    memory=5,
    spend=0,
    profiles=None,
):
    return {
        "capability_id": cid,
        "semantic_contract_sha256": semantic,
        "implementation_family": implementation,
        "representation_family": representation,
        "substrate_family": substrate,
        "reusable_capability": True,
        "independently_verified": True,
        "capability": capability,
        "generalization": generalization,
        "reliability": reliability,
        "latency": latency,
        "compute": compute,
        "memory": memory,
        "incremental_spend_usd": spend,
        "cost_profiles": profiles or {},
    }


class OptionPreservingCapabilityOptimizerV1Tests(unittest.TestCase):
    def test_current_dominance_retires_but_never_deletes(self):
        slow = cap("slow", latency=10, compute=10, memory=10)
        fast = cap("fast", latency=1, compute=1, memory=1)
        out = o.select_active_frontier([slow, fast])
        self.assertEqual(out["active_capability_ids"], ["fast"])
        self.assertEqual(out["retired"][0]["capability_id"], "slow")
        self.assertFalse(out["retired"][0]["physical_deletion_authorized"])
        self.assertTrue(out["retired"][0]["knowledge_preservation_required"])

    def test_distinct_substrate_preserves_warm_option(self):
        cpu = cap(
            "cpu",
            implementation="same-algorithm",
            representation="same-ir",
            substrate="cpu",
            latency=10,
            compute=10,
            memory=10,
        )
        gpu = cap(
            "gpu",
            implementation="same-algorithm",
            representation="same-ir",
            substrate="gpu",
            latency=1,
            compute=1,
            memory=1,
        )
        out = o.select_active_frontier([cpu, gpu])
        retired = {x["capability_id"]: x for x in out["retired"]}
        self.assertEqual(retired["cpu"]["active_state"], "WARM_RETIRED")
        self.assertTrue(retired["cpu"]["unique_option_family_preserved"])

    def test_different_semantic_contracts_never_dominate_each_other(self):
        a = cap("a", semantic="sha256:a", latency=100, compute=100)
        b = cap("b", semantic="sha256:b", latency=1, compute=1)
        out = o.select_active_frontier([a, b])
        self.assertEqual(out["active_capability_ids"], ["a", "b"])

    def test_deletion_fails_closed_without_future_option_proof(self):
        old = cap("old", latency=10, compute=10)
        new = cap("new", latency=1, compute=1)
        proof = {
            "incumbent_capability_id": "old",
            "replacement_capability_id": "new",
            "semantic_contract_sha256": "sha256:semantic",
            "independent_verified": True,
            "exact_byte_bound": True,
            "semantic_contract_superset_proved": True,
            "behavioral_scope_superset_proved": True,
            "evidence_not_weaker_proved": True,
            "unique_representation_absent_proved": True,
            "unique_substrate_path_absent_proved": True,
            "future_option_value_zero_proved": False,
            "reconstructible_from_preserved_artifacts": True,
            "reconstruction_verified": True,
        }
        out = o.evaluate_permanent_deletion(old, new, proof)
        self.assertTrue(out["pass"])
        self.assertFalse(out["physical_deletion_authorized"])
        self.assertIn("future_option_value_zero_proved", out["missing_deletion_proofs"])

    def test_deletion_only_eligible_with_complete_independent_proof(self):
        old = cap("old", latency=10, compute=10)
        new = cap("new", latency=1, compute=1)
        proof = {
            "incumbent_capability_id": "old",
            "replacement_capability_id": "new",
            "semantic_contract_sha256": "sha256:semantic",
            **{field: True for field in o.DELETE_PROOF_FIELDS},
        }
        out = o.evaluate_permanent_deletion(old, new, proof)
        self.assertTrue(out["physical_deletion_authorized"])
        self.assertFalse(out["mutation_performed"])


    def test_dominated_default_is_replaced_but_preserved_for_replay(self):
        slow = cap("slow", latency=10, compute=10, memory=10)
        fast = cap("fast", latency=1, compute=1, memory=1)
        out = o.select_effective_for_scope(
            [slow, fast],
            default_capability_id="slow",
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["global_preferred_default_capability_id"], "fast")
        self.assertEqual(out["effective_capability_id"], "fast")
        self.assertEqual(
            out["default_transition"],
            "OBJECTIVELY_DOMINATED_INCUMBENT_REPLACED",
        )
        retired = {row["capability_id"]: row for row in out["retired"]}
        self.assertIn("slow", retired)
        self.assertTrue(retired["slow"]["knowledge_preservation_required"])
        self.assertFalse(retired["slow"]["physical_deletion_authorized"])

    def test_explicit_scoped_override_can_replay_retired_without_global_revert(self):
        slow = cap("slow", latency=10, compute=10, memory=10)
        fast = cap("fast", latency=1, compute=1, memory=1)
        out = o.select_effective_for_scope(
            [slow, fast],
            default_capability_id="slow",
            override={
                "requested_capability_id": "slow",
                "scope_id": "task:123",
                "explicit_user_request": True,
                "restore_after_scope": True,
            },
        )
        self.assertTrue(out["pass"])
        self.assertTrue(out["override_active"])
        self.assertEqual(out["effective_capability_id"], "slow")
        self.assertTrue(out["requested_capability_was_preserved_retired"])
        self.assertEqual(out["global_preferred_default_capability_id"], "fast")
        self.assertFalse(out["global_frontier_mutated_by_override"])
        self.assertFalse(out["override_persists_after_scope"])
        self.assertFalse(out["override_can_self_promote"])

    def test_next_scope_without_override_returns_to_improved_default(self):
        slow = cap("slow", latency=10, compute=10, memory=10)
        fast = cap("fast", latency=1, compute=1, memory=1)
        first = o.select_effective_for_scope(
            [slow, fast],
            default_capability_id="slow",
            override={
                "requested_capability_id": "slow",
                "scope_id": "task:123",
                "explicit_user_request": True,
                "restore_after_scope": True,
            },
        )
        second = o.select_effective_for_scope(
            [slow, fast],
            default_capability_id=first["global_preferred_default_capability_id"],
        )
        self.assertEqual(first["effective_capability_id"], "slow")
        self.assertEqual(second["effective_capability_id"], "fast")
        self.assertFalse(second["override_active"])

    def test_implicit_or_persistent_override_fails_closed(self):
        slow = cap("slow", latency=10, compute=10, memory=10)
        fast = cap("fast", latency=1, compute=1, memory=1)
        with self.assertRaises(o.OptionPreservationError):
            o.select_effective_for_scope(
                [slow, fast],
                default_capability_id="slow",
                override={
                    "requested_capability_id": "slow",
                    "scope_id": "task:123",
                    "explicit_user_request": False,
                    "restore_after_scope": True,
                },
            )
        with self.assertRaises(o.OptionPreservationError):
            o.select_effective_for_scope(
                [slow, fast],
                default_capability_id="slow",
                override={
                    "requested_capability_id": "slow",
                    "scope_id": "task:123",
                    "explicit_user_request": True,
                    "restore_after_scope": False,
                },
            )

    def test_scoped_override_cannot_cross_semantic_contract(self):
        a = cap("a", semantic="sha256:a")
        b = cap("b", semantic="sha256:b")
        with self.assertRaises(o.OptionPreservationError):
            o.select_effective_for_scope(
                [a, b],
                default_capability_id="a",
                override={
                    "requested_capability_id": "b",
                    "scope_id": "task:cross-contract",
                    "explicit_user_request": True,
                    "restore_after_scope": True,
                },
            )

    def test_multiple_nondominated_replacements_do_not_trigger_arbitrary_default(self):
        old = cap(
            "old",
            capability=1,
            generalization=1,
            reliability=1,
            latency=10,
            compute=10,
            memory=10,
        )
        better_capability = cap(
            "better-capability",
            capability=2,
            generalization=1,
            reliability=1,
            latency=5,
            compute=10,
            memory=10,
        )
        better_generalization = cap(
            "better-generalization",
            capability=1,
            generalization=2,
            reliability=1,
            latency=10,
            compute=5,
            memory=10,
        )
        out = o.select_effective_for_scope(
            [old, better_capability, better_generalization],
            default_capability_id="old",
        )
        self.assertFalse(out["pass"])
        self.assertEqual(
            out["status"],
            "OPEN__TASK_PREFERENCE_REQUIRED_ACROSS_NONDOMINATED_FRONTIER",
        )
        self.assertIsNone(out["global_preferred_default_capability_id"])
        self.assertEqual(
            out["global_active_capability_ids"],
            ["better-capability", "better-generalization"],
        )
        self.assertIsNone(out["effective_capability_id"])

    def test_new_cost_model_can_reactivate_old_implementation(self):
        a = cap(
            "a",
            substrate="cpu",
            latency=3,
            compute=3,
            profiles={
                "TODAY": {"latency": 1, "compute": 1, "memory": 1, "incremental_spend_usd": 0},
                "FUTURE_X": {"latency": 100, "compute": 100, "memory": 100, "incremental_spend_usd": 0},
            },
        )
        b = cap(
            "b",
            substrate="future-x",
            latency=4,
            compute=4,
            profiles={
                "TODAY": {"latency": 10, "compute": 10, "memory": 10, "incremental_spend_usd": 0},
                "FUTURE_X": {"latency": 1, "compute": 1, "memory": 1, "incremental_spend_usd": 0},
            },
        )
        out = o.reextract_on_cost_model_change(
            [a, b],
            previous_cost_model_id="TODAY",
            new_cost_model_id="FUTURE_X",
        )
        self.assertEqual(out["previous_active_capability_ids"], ["a"])
        self.assertEqual(out["new_active_capability_ids"], ["b"])
        self.assertEqual(out["reactivated_capability_ids"], ["b"])
        self.assertFalse(out["physical_deletion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
