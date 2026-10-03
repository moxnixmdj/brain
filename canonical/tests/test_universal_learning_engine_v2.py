from fractions import Fraction
import unittest

from canonical.runtime import universal_learning_engine_v2 as u


class UniversalLearningEngineV2Tests(unittest.TestCase):
    def test_minimum_novelty_delta_reuses_known_structure(self):
        out = u.minimum_novelty_delta(
            required_primitives=["functions", "types", "ownership", "effects"],
            verified_primitives=["functions", "types", "ownership", "other"],
        )
        self.assertEqual(out["novelty_delta"], ["effects"])
        self.assertEqual(out["verified_primitives_reused"], ["functions", "ownership", "types"])

    def test_surface_label_transfer_is_forbidden(self):
        with self.assertRaises(u.LearningEngineError):
            u.admit_transfer_mapping(
                target_primitive="B:thing", source_primitive="A:thing",
                relation="EXACT", evidence_receipt="r1", provenance_chain=["p1"],
                mapping_basis="LABEL_MATCH",
            )

    def test_structural_transfer_preserves_provenance(self):
        out = u.admit_transfer_mapping(
            target_primitive="B:conservation-law", source_primitive="A:conservation-law",
            relation="PROVEN_STRONGER", evidence_receipt="receipt:123",
            provenance_chain=["domain-A:proof", "mapping:proof"], mapping_basis="CAUSAL_ISOMORPHISM",
        )
        self.assertTrue(out["transfer_admitted"])
        self.assertFalse(out["requires_full_rediscovery"])
        self.assertEqual(len(out["provenance_chain"]), 2)

    def test_decision_sufficiency_blocks_blanket_abstention(self):
        out = u.choose_learning_step(
            probabilities={"h1": "1/2", "h2": "1/2"},
            terminal_action_by_hypothesis={"h1": "SAFE_ACTION", "h2": "SAFE_ACTION"},
            actions=[],
        )
        self.assertEqual(out["status"], "DECISION_SUFFICIENT__EXECUTE")
        self.assertFalse(out["abstain"])
        self.assertEqual(out["authorized_action"], "SAFE_ACTION")

    def test_high_information_safe_probe_selected(self):
        actions = [
            u.LearningAction("weak", {"h1": "same", "h2": "same"}, time_cost=1),
            u.LearningAction("discriminate", {"h1": "left", "h2": "right"}, time_cost=1),
        ]
        out = u.choose_learning_step(
            probabilities={"h1": "1/2", "h2": "1/2"},
            terminal_action_by_hypothesis={"h1": "A", "h2": "B"}, actions=actions,
        )
        self.assertEqual(out["status"], "SAFE_DISCRIMINATOR_REQUIRED")
        self.assertEqual(out["probe"], "discriminate")
        self.assertEqual(out["ranking"][0]["decision_gain"], Fraction(1, 2))

    def test_unsafe_probe_never_selected(self):
        actions = [u.LearningAction("unsafe-perfect", {"h1": "l", "h2": "r"}, safe=False)]
        out = u.choose_learning_step(
            probabilities={"h1": "1/2", "h2": "1/2"},
            terminal_action_by_hypothesis={"h1": "A", "h2": "B"}, actions=actions,
        )
        self.assertTrue(out["abstain"])

    def test_nonidentifiable_case_abstains(self):
        actions = [u.LearningAction("uninformative", {"h1": "same", "h2": "same"}, time_cost=1)]
        out = u.choose_learning_step(
            probabilities={"h1": "1/2", "h2": "1/2"},
            terminal_action_by_hypothesis={"h1": "A", "h2": "B"}, actions=actions,
        )
        self.assertEqual(
            out["status"],
            "NONIDENTIFIABLE_OR_UNDERSPECIFIED__ABSTAIN_OR_REQUEST_DISCRIMINATOR",
        )
        self.assertTrue(out["abstain"])

    def test_cost_can_change_probe_choice(self):
        actions = [
            u.LearningAction("fast-perfect", {"h1": "l", "h2": "r"}, time_cost=1),
            u.LearningAction(
                "slow-perfect", {"h1": "l", "h2": "r"},
                time_cost=10, future_transfer_value=1,
            ),
        ]
        ranked = u.rank_learning_actions(
            probabilities={"h1": "1/2", "h2": "1/2"},
            terminal_action_by_hypothesis={"h1": "A", "h2": "B"}, actions=actions,
        )
        self.assertEqual(ranked[0]["action_id"], "fast-perfect")

    def test_dependency_cone_invalidation_preserves_unrelated_knowledge(self):
        out = u.dependency_cone_invalidation(
            changed_facts=["api-v1"],
            dependents={
                "api-v1": ["skill-call"],
                "skill-call": ["workflow"],
                "math-law": ["symbolic-skill"],
            },
        )
        self.assertEqual(
            out["invalidated_dependency_cone"],
            ["api-v1", "skill-call", "workflow"],
        )
        self.assertIn("math-law", out["preserved_outside_cone"])
        self.assertFalse(out["global_reset_required"])

    def test_skill_compile_rejects_unverified_transfer(self):
        with self.assertRaises(u.LearningEngineError):
            u.compile_proof_carrying_skill(
                skill_id="s", learned_primitives=["p"], applicability=["a"],
                verification_receipts=["v"], dependencies=[], invalidators=[],
                transfer_mappings=[{"transfer_admitted": False}],
            )

    def test_skill_compile_is_reusable_and_proof_carrying(self):
        mapping = u.admit_transfer_mapping(
            target_primitive="B:p", source_primitive="A:p", relation="EXACT",
            evidence_receipt="map-v", provenance_chain=["a-v"],
            mapping_basis="STRUCTURAL_EQUIVALENCE",
        )
        out = u.compile_proof_carrying_skill(
            skill_id="skill-B", learned_primitives=["B:p"], applicability=["domain-B"],
            verification_receipts=["skill-v"], dependencies=["B:p"],
            invalidators=["B-version-change"], transfer_mappings=[mapping],
        )
        self.assertEqual(out["state"], "VERIFIED_REUSABLE")
        self.assertFalse(out["rediscovery_required_until_invalidated"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
