from __future__ import annotations

import unittest

from canonical.runtime import universal_recursive_learning_engine_v3 as v3


RECEIPT = {
    "receipt_id": "r1",
    "independent_verified": True,
    "exact_byte_bound": True,
    "conclusion": "success",
}


class UniversalRecursiveLearningEngineV3Tests(unittest.TestCase):
    def test_structural_transfer_accepts_verified_nonlabel_mapping(self):
        out = v3.structural_transfer_plan(
            target_requirements={"target-r1", "target-r2"},
            mappings=[
                {
                    "source_primitive_id": "source-a",
                    "target_requirement_id": "target-r1",
                    "mapping_basis": "CAUSAL_INVARIANT",
                    "label_only": False,
                    "source_verification_receipt": RECEIPT,
                    "mapping_verification_receipt": dict(RECEIPT, receipt_id="map-r1"),
                }
            ],
        )
        self.assertEqual(out["covered"], ["target-r1"])
        self.assertEqual(out["missing"], ["target-r2"])
        self.assertEqual(out["rejected_mappings"], [])

    def test_label_only_transfer_is_rejected_and_cannot_reduce_novelty(self):
        out = v3.structural_transfer_plan(
            target_requirements={"target-r1"},
            mappings=[
                {
                    "source_primitive_id": "same-name",
                    "target_requirement_id": "target-r1",
                    "mapping_basis": "NAME_MATCH",
                    "label_only": True,
                    "source_verification_receipt": RECEIPT,
                    "mapping_verification_receipt": dict(RECEIPT, receipt_id="map-r1"),
                }
            ],
        )
        self.assertEqual(out["covered"], [])
        self.assertEqual(out["missing"], ["target-r1"])
        self.assertEqual(out["rejected_mappings"][0]["reason"], "LABEL_ONLY_OR_NONSTRUCTURAL_MAPPING")

    def test_unverified_structural_mapping_is_rejected(self):
        bad = dict(RECEIPT)
        bad["independent_verified"] = False
        with self.assertRaises(v3.RecursiveLearningEngineError):
            v3.structural_transfer_plan(
                target_requirements={"x"},
                mappings=[{
                    "source_primitive_id": "s",
                    "target_requirement_id": "x",
                    "mapping_basis": "STATE_TRANSITION_INVARIANT",
                    "label_only": False,
                    "source_verification_receipt": RECEIPT,
                    "mapping_verification_receipt": bad,
                }],
            )

    def test_negative_transfer_distractor_does_not_get_credit(self):
        out = v3.structural_transfer_plan(
            target_requirements={"real"},
            mappings=[
                {
                    "source_primitive_id": "distractor",
                    "target_requirement_id": "other",
                    "mapping_basis": "CAUSAL_INVARIANT",
                    "label_only": False,
                    "source_verification_receipt": RECEIPT,
                    "mapping_verification_receipt": dict(RECEIPT, receipt_id="map-r1"),
                }
            ],
        )
        self.assertEqual(out["covered"], [])
        self.assertEqual(out["missing"], ["real"])

    def test_minimum_discriminator_selects_cheapest_probe_set_cover(self):
        hypotheses = [
            {"id": "h1", "plausible": True, "best_action": "A"},
            {"id": "h2", "plausible": True, "best_action": "B"},
            {"id": "h3", "plausible": True, "best_action": "C"},
        ]
        probes = [
            {"id": "p12", "safe": True, "time": 1, "cost": 0, "risk": 0,
             "outcomes": {"h1": "x", "h2": "y", "h3": "x"}},
            {"id": "p13", "safe": True, "time": 1, "cost": 0, "risk": 0,
             "outcomes": {"h1": "x", "h2": "x", "h3": "y"}},
            {"id": "expensive-all", "safe": True, "time": 5, "cost": 0, "risk": 0,
             "outcomes": {"h1": "a", "h2": "b", "h3": "c"}},
        ]
        out = v3.minimum_action_discriminator(hypotheses=hypotheses, probes=probes)
        self.assertTrue(out["identifiable"])
        self.assertEqual(out["probe_ids"], ["p12", "p13"])
        self.assertEqual(out["total_cost"], 2.0)

    def test_unsafe_probe_is_never_used_even_if_cheapest(self):
        hypotheses = [
            {"id": "h1", "plausible": True, "best_action": "A"},
            {"id": "h2", "plausible": True, "best_action": "B"},
        ]
        probes = [
            {"id": "unsafe", "safe": False, "time": 0.1, "cost": 0, "risk": 0,
             "outcomes": {"h1": "x", "h2": "y"}},
            {"id": "safe", "safe": True, "time": 2, "cost": 0, "risk": 0,
             "outcomes": {"h1": "x", "h2": "y"}},
        ]
        out = v3.minimum_action_discriminator(hypotheses=hypotheses, probes=probes)
        self.assertEqual(out["probe_ids"], ["safe"])

    def test_nonidentifiable_returns_abstention_not_fake_discriminator(self):
        hypotheses = [
            {"id": "h1", "plausible": True, "best_action": "A"},
            {"id": "h2", "plausible": True, "best_action": "B"},
        ]
        probes = [
            {"id": "useless", "safe": True, "time": 1, "cost": 0, "risk": 0,
             "outcomes": {"h1": "same", "h2": "same"}},
        ]
        out = v3.minimum_action_discriminator(hypotheses=hypotheses, probes=probes)
        self.assertFalse(out["identifiable"])
        self.assertEqual(out["route"], "ABSTAIN")
        self.assertEqual(out["probe_ids"], [])

    def test_same_action_hypotheses_need_no_discriminator(self):
        hypotheses = [
            {"id": "h1", "plausible": True, "best_action": "A"},
            {"id": "h2", "plausible": True, "best_action": "A"},
        ]
        out = v3.minimum_action_discriminator(hypotheses=hypotheses, probes=[])
        self.assertTrue(out["identifiable"])
        self.assertEqual(out["route"], "DECISION_SUFFICIENT")
        self.assertEqual(out["probe_ids"], [])

    def test_duplicate_probe_ids_fail_closed(self):
        hypotheses = [
            {"id": "h1", "plausible": True, "best_action": "A"},
            {"id": "h2", "plausible": True, "best_action": "B"},
        ]
        probes = [
            {"id": "p", "safe": True, "time": 1, "cost": 0, "risk": 0,
             "outcomes": {"h1": "x", "h2": "y"}},
            {"id": "p", "safe": True, "time": 2, "cost": 0, "risk": 0,
             "outcomes": {"h1": "y", "h2": "x"}},
        ]
        with self.assertRaises(v3.RecursiveLearningEngineError):
            v3.minimum_action_discriminator(hypotheses=hypotheses, probes=probes)

    def test_safe_probe_missing_live_hypothesis_outcome_fails_closed(self):
        hypotheses = [
            {"id": "h1", "plausible": True, "best_action": "A"},
            {"id": "h2", "plausible": True, "best_action": "B"},
        ]
        probes = [
            {"id": "p", "safe": True, "time": 1, "cost": 0, "risk": 0,
             "outcomes": {"h1": "x"}},
        ]
        with self.assertRaises(v3.RecursiveLearningEngineError):
            v3.minimum_action_discriminator(hypotheses=hypotheses, probes=probes)

    def test_abstraction_merge_requires_same_structural_signature_and_verified_receipts(self):
        skills = [
            {
                "skill_id": "s1", "structural_signature": "sig-x",
                "applicability": ["domain-a"], "verification_receipts": [RECEIPT],
            },
            {
                "skill_id": "s2", "structural_signature": "sig-x",
                "applicability": ["domain-b"], "verification_receipts": [dict(RECEIPT, receipt_id="r2")],
            },
        ]
        out = v3.merge_structurally_equivalent_skills(skills)
        self.assertEqual(out["status"], "VERIFIED_ABSTRACTION_CANDIDATE")
        self.assertEqual(out["structural_signature"], "sig-x")
        self.assertEqual(out["applicability"], ["domain-a", "domain-b"])
        self.assertFalse(out["promotion_authorized"])

    def test_abstraction_merge_rejects_mixed_signatures(self):
        with self.assertRaises(v3.RecursiveLearningEngineError):
            v3.merge_structurally_equivalent_skills([
                {"skill_id": "s1", "structural_signature": "a", "applicability": ["x"], "verification_receipts": [RECEIPT]},
                {"skill_id": "s2", "structural_signature": "b", "applicability": ["y"], "verification_receipts": [dict(RECEIPT, receipt_id="r2")]},
            ])


if __name__ == "__main__":
    unittest.main(verbosity=2)
