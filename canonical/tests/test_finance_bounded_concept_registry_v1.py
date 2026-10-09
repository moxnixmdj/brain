from __future__ import annotations

from copy import deepcopy
import unittest

from canonical.runtime import finance_bounded_concept_registry_v1 as registry
from canonical.runtime import finance_bounded_concept_registry_verify_v1 as verify
from canonical.runtime import semantic_relation_control_v1 as relation


SOURCE = (
    "Reserve buffer means RULE. "
    "Liquidity cushion refers to Reserve buffer. "
    "Hard floor is defined as EXCEPTION."
)


class FinanceBoundedConceptRegistryV1Tests(unittest.TestCase):
    def test_complete_explicit_definition_registry_and_shared_identity(self):
        reg = registry.build_registry(
            source_id="finance-policy-1",
            source_text=SOURCE,
        )
        self.assertEqual(reg["explicit_definition_count"], 3)
        self.assertTrue(
            reg["scope_completeness"][
                "all_explicit_definitions_resolve_to_verified_role_universe"
            ]
        )
        self.assertFalse(
            reg["scope_completeness"]["open_world_finance_ontology_complete"]
        )
        claim = registry.make_identity_claim(
            reg,
            left_id="Reserve buffer",
            right_id="Liquidity cushion",
        )
        receipt = verify.verify_claim(claim)
        self.assertTrue(receipt["pass"], receipt)
        self.assertEqual(receipt["shared_concept_id"], "FINANCE_ROLE::RULE")
        self.assertTrue(receipt["bounded_registry_scope_complete"])
        self.assertFalse(receipt["open_world_ontology_complete"])

    def test_different_roles_cannot_be_claimed_identical(self):
        reg = registry.build_registry(
            source_id="finance-policy-2",
            source_text=SOURCE,
        )
        with self.assertRaisesRegex(
            registry.ConceptRegistryError,
            "TERMS_DO_NOT_SHARE_CONCEPT",
        ):
            registry.make_identity_claim(
                reg,
                left_id="Reserve buffer",
                right_id="Hard floor",
            )

    def test_unresolved_definition_fails_registry_construction(self):
        with self.assertRaisesRegex(
            registry.ConceptRegistryError,
            "DEFINITION_OUTSIDE_VERIFIED_FINANCE_ROLE_UNIVERSE",
        ):
            registry.build_registry(
                source_id="finance-policy-3",
                source_text="Reserve buffer means an adequate amount.",
            )

    def test_source_tamper_breaks_independent_verification(self):
        reg = registry.build_registry(
            source_id="finance-policy-4",
            source_text=SOURCE,
        )
        claim = registry.make_identity_claim(
            reg,
            left_id="Reserve buffer",
            right_id="Liquidity cushion",
        )
        tampered = deepcopy(claim)
        tampered["source_text"] = tampered["source_text"].replace(
            "Liquidity cushion refers to Reserve buffer",
            "Liquidity cushion refers to EXCEPTION",
        )
        receipt = verify.verify_claim(tampered)
        self.assertFalse(receipt["pass"])
        self.assertIn(
            receipt["reason"],
            {
                "REGISTRY_RECOMPUTATION_MISMATCH",
                "SOURCE_TEXT_SHA256_MISMATCH",
                "CLAIM_SHA256_MISMATCH",
            },
        )

    def test_verified_claim_is_consumable_by_semantic_relation_control(self):
        reg = registry.build_registry(
            source_id="finance-policy-5",
            source_text=SOURCE,
        )
        claim = registry.make_identity_claim(
            reg,
            left_id="Reserve buffer",
            right_id="Liquidity cushion",
        )
        out = relation.resolve(
            {
                "left_id": "Reserve buffer",
                "right_id": "Liquidity cushion",
                "scope_id": reg["scope_id"],
                "required_relation": "SEMANTIC_IDENTITY",
                "shared_concept_identity_receipt": claim,
            },
            concept_identity_verifier=verify.verify_claim,
        )
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["strongest_proved_relation"], "SEMANTIC_IDENTITY")
        self.assertTrue(out["shared_concept_identity"]["proved"])

    def test_registry_scope_does_not_claim_general_finance_ontology(self):
        reg = registry.build_registry(
            source_id="finance-policy-6",
            source_text=SOURCE,
        )
        self.assertEqual(
            reg["semantic_boundary"],
            "EXACT_EXPLICIT_DEFINITION_CHAIN_TO_VERIFIED_V32_FINANCE_ROLE_ONLY",
        )
        self.assertFalse(
            reg["scope_completeness"]["open_world_finance_ontology_complete"]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
