from __future__ import annotations

from copy import deepcopy
import unittest

from canonical.runtime import finance_bounded_concept_registry_v1 as registry
from canonical.runtime import unified_cognitive_fabric_v1 as fabric


SOURCE = (
    "Reserve buffer means RULE. "
    "Liquidity cushion refers to Reserve buffer. "
    "Hard floor means EXCEPTION."
)


class FinanceBoundedConceptRegistryFabricV1Tests(unittest.TestCase):
    def _claim(self):
        reg = registry.build_registry(
            source_id="finance:fabric:test",
            source_text=SOURCE,
        )
        claim = registry.make_identity_claim(
            reg,
            left_id="Reserve buffer",
            right_id="Liquidity cushion",
        )
        return reg, claim

    def test_fabric_auto_verifies_bounded_finance_concept_identity(self):
        reg, claim = self._claim()
        out = fabric.run({
            "mode": "SEMANTIC_RELATION",
            "payload": {
                "left_id": "Reserve buffer",
                "right_id": "Liquidity cushion",
                "scope_id": reg["scope_id"],
                "required_relation": "SEMANTIC_IDENTITY",
                "shared_concept_identity_receipt": claim,
            },
        })
        self.assertTrue(out["inner_pass"], out)
        self.assertEqual(out["mode"], "SEMANTIC_RELATION")
        self.assertEqual(
            out["result"]["strongest_proved_relation"],
            "SEMANTIC_IDENTITY",
        )
        self.assertTrue(
            out["result"]["shared_concept_identity"]["proved"],
            out,
        )

    def test_fabric_auto_verifier_rejects_registry_tamper(self):
        reg, claim = self._claim()
        tampered = deepcopy(claim)
        tampered["registry"]["bindings"][0]["concept_id"] = "FINANCE_ROLE::FACT"
        out = fabric.run({
            "mode": "SEMANTIC_RELATION",
            "payload": {
                "left_id": "Reserve buffer",
                "right_id": "Liquidity cushion",
                "scope_id": reg["scope_id"],
                "required_relation": "SEMANTIC_IDENTITY",
                "shared_concept_identity_receipt": tampered,
            },
        })
        self.assertFalse(out["inner_pass"], out)
        self.assertEqual(
            out["result"]["status"],
            "FAIL_CLOSED__SHARED_CONCEPT_IDENTITY_EVIDENCE_INVALID",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
