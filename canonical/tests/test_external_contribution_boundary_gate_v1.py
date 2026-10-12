from __future__ import annotations

import unittest
from canonical.runtime.ownership_promotion_cognition_provenance_gate_v1 import evaluate


class ExternalContributionBoundaryGateV1Tests(unittest.TestCase):
    def test_ambiguous_or_missing_classification_fails_closed(self) -> None:
        self.assertFalse(evaluate({})["pass"])

    def test_runtime_cognition_provider_always_fails_closed(self) -> None:
        out = evaluate(
            {
                "external_contribution_classification": "K3_RUNTIME_COGNITION",
                "external_contribution_census_complete": True,
                "full_runtime_dependency_inventory_complete": True,
            }
        )
        self.assertFalse(out["pass"])


if __name__ == "__main__":
    unittest.main()
