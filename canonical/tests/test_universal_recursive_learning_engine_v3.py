from __future__ import annotations

import unittest

from canonical.runtime import universal_recursive_learning_engine_v3 as v3


class UniversalRecursiveLearningEngineV3Tests(unittest.TestCase):
    def test_structural_signature_ignores_surface_labels(self):
        a = v3.structural_signature(
            primitive_roles=["producer", "consumer"],
            relation_roles=["producer->consumer"],
            invariants=["ordered-transfer"],
        )
        b = v3.structural_signature(
            primitive_roles=["producer", "consumer"],
            relation_roles=["producer->consumer"],
            invariants=["ordered-transfer"],
        )
        self.assertEqual(a["signature"], b["signature"])

    def test_transfer_accepts_required_structural_invariants(self):
        src = v3.structural_signature(
            primitive_roles=["p", "c"],
            relation_roles=["p->c"],
            invariants=["single-owner", "ordered-transfer"],
        )
        tgt = v3.structural_signature(
            primitive_roles=["x", "y"],
            relation_roles=["x->y"],
            invariants=["single-owner", "ordered-transfer"],
        )
        out = v3.assess_transfer(
            source_signature=src,
            target_signature=tgt,
            required_target_invariants=["single-owner", "ordered-transfer"],
        )
        self.assertTrue(out["accepted"])
        self.assertFalse(out["surface_label_evidence_used"])

    def test_negative_transfer_contradiction_is_rejected(self):
        src = v3.structural_signature(
            primitive_roles=["a"],
            relation_roles=[],
            invariants=["monotonic"],
        )
        tgt = v3.structural_signature(
            primitive_roles=["b"],
            relation_roles=[],
            invariants=["monotonic"],
        )
        out = v3.assess_transfer(
            source_signature=src,
            target_signature=tgt,
            required_target_invariants=["monotonic"],
            contradicted_invariants=["monotonic"],
        )
        self.assertFalse(out["accepted"])
        self.assertEqual(out["reason"], "REQUIRED_INVARIANT_CONTRADICTED")

    def test_distractor_only_transfer_is_rejected(self):
        src = v3.structural_signature(
            primitive_roles=["a"],
            relation_roles=[],
            invariants=["causal"],
        )
        tgt = v3.structural_signature(
            primitive_roles=["b"],
            relation_roles=[],
            invariants=["causal"],
        )
        out = v3.assess_transfer(
            source_signature=src,
            target_signature=tgt,
            required_target_invariants=["causal"],
            distractor_features=["same-color", "same-name"],
            claimed_support_features=["same-color"],
        )
        self.assertFalse(out["accepted"])
        self.assertEqual(out["reason"], "TRANSFER_SUPPORTED_ONLY_BY_DISTRACTORS")

    def test_discriminator_stops_when_action_already_agrees(self):
        out = v3.minimum_cost_safe_discriminator(
            hypotheses=[
                {"id": "h1", "plausible": True, "best_action": "stop"},
                {"id": "h2", "plausible": True, "best_action": "stop"},
            ],
            discriminators=[],
        )
        self.assertEqual(out["status"], "DECISION_ALREADY_SUFFICIENT")
        self.assertEqual(out["total_cost"], 0.0)

    def test_exact_cheapest_safe_discriminator_selected(self):
        out = v3.minimum_cost_safe_discriminator(
            hypotheses=[
                {"id": "h1", "plausible": True, "best_action": "left"},
                {"id": "h2", "plausible": True, "best_action": "right"},
                {"id": "h3", "plausible": True, "best_action": "left"},
            ],
            discriminators=[
                {"id": "d1", "safe": True, "cost": 2, "outcomes": {"h1": "A", "h2": "B", "h3": "A"}},
                {"id": "d2", "safe": True, "cost": 1, "outcomes": {"h1": "A", "h2": "A", "h3": "B"}},
                {"id": "d3", "safe": True, "cost": 1, "outcomes": {"h1": "A", "h2": "B", "h3": "A"}},
                {"id": "unsafe", "safe": False, "cost": 0, "outcomes": {"h1": "A", "h2": "B", "h3": "A"}},
            ],
        )
        self.assertEqual(out["status"], "EXACT_MINIMUM_COST_SAFE_DISCRIMINATOR")
        self.assertEqual(out["selected_ids"], ["d3"])
        self.assertEqual(out["total_cost"], 1.0)

    def test_safe_but_insufficient_discriminators_fail_closed(self):
        out = v3.minimum_cost_safe_discriminator(
            hypotheses=[
                {"id": "h1", "plausible": True, "best_action": "left"},
                {"id": "h2", "plausible": True, "best_action": "right"},
            ],
            discriminators=[
                {"id": "d1", "safe": True, "cost": 1, "outcomes": {"h1": "A", "h2": "A"}},
            ],
        )
        self.assertEqual(out["status"], "SAFE_DISCRIMINATION_INSUFFICIENT")

    def test_abstraction_only_inherits_common_proofs(self):
        out = v3.compress_verified_abstraction(
            abstraction_id="common",
            members=[
                {
                    "id": "s1",
                    "verified": True,
                    "guarantees": ["safe", "fast"],
                    "invariants": ["verified-before-use", "fail-closed"],
                    "applicability": ["A"],
                    "verification_receipts": ["r1"],
                },
                {
                    "id": "s2",
                    "verified": True,
                    "guarantees": ["safe"],
                    "invariants": ["verified-before-use"],
                    "applicability": ["B"],
                    "verification_receipts": ["r2"],
                },
            ],
        )
        self.assertEqual(out["guarantees"], ["safe"])
        self.assertEqual(out["invariants"], ["verified-before-use"])
        self.assertEqual(out["applicability_union"], ["A", "B"])
        self.assertFalse(out["new_guarantees_introduced"])

    def test_unverified_member_cannot_be_compressed(self):
        with self.assertRaises(v3.RecursiveLearningError):
            v3.compress_verified_abstraction(
                abstraction_id="bad",
                members=[
                    {
                        "id": "s1",
                        "verified": True,
                        "guarantees": ["safe"],
                        "invariants": ["x"],
                        "verification_receipts": ["r1"],
                    },
                    {
                        "id": "s2",
                        "verified": False,
                        "guarantees": ["safe"],
                        "invariants": ["x"],
                        "verification_receipts": ["r2"],
                    },
                ],
            )

    def test_v3_invariant_bundle_passes_with_zero_authority(self):
        out = v3.prove_v3_invariants()
        self.assertTrue(out["pass"], out)
        self.assertFalse(out["promotion_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertEqual(out["acceptance_credit_delta"], 0)
        self.assertEqual(out["ownership_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
