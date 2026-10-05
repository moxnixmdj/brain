import unittest

from canonical.runtime.hidden_evaluator_monotone_coupling_v1 import CouplingError, solve


class MonotoneCouplingTests(unittest.TestCase):
    def test_strict_improvement_can_dominate_without_observational_equivalence(self):
        out = solve({
            "target_distribution": [
                {"id": "low", "probability": "1/2"},
                {"id": "high", "probability": "1/2"},
            ],
            "brain_distribution": [
                {"id": "high", "probability": "1"},
            ],
            "dominance_edges": [
                {"target": "low", "brain": "high"},
                {"target": "high", "brain": "high"},
            ],
            "material_order_certificate": "TEST_ORDER_V1",
        })
        self.assertEqual(out["status"], "PASS", out)
        self.assertTrue(out["universal_monotone_utility_noninferiority"])
        self.assertFalse(out["observational_equivalence_required"])

    def test_inferior_mass_fails_closed(self):
        out = solve({
            "target_distribution": [{"id": "high", "probability": "1"}],
            "brain_distribution": [{"id": "low", "probability": "1"}],
            "dominance_edges": [{"target": "low", "brain": "low"}],
            "material_order_certificate": "TEST_ORDER_V1",
        })
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertFalse(out["universal_monotone_utility_noninferiority"])

    def test_mixed_distribution_requires_full_transport(self):
        out = solve({
            "target_distribution": [
                {"id": "low", "probability": "1/2"},
                {"id": "high", "probability": "1/2"},
            ],
            "brain_distribution": [
                {"id": "low", "probability": "3/4"},
                {"id": "high", "probability": "1/4"},
            ],
            "dominance_edges": [
                {"target": "low", "brain": "low"},
                {"target": "low", "brain": "high"},
                {"target": "high", "brain": "high"},
            ],
            "material_order_certificate": "TEST_ORDER_V1",
        })
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertEqual(out["max_coupled_mass"], "3/4")

    def test_probabilities_must_be_exactly_normalized(self):
        with self.assertRaisesRegex(CouplingError, "TARGET_PROBABILITIES_MUST_SUM_TO_1"):
            solve({
                "target_distribution": [{"id": "x", "probability": "0.9"}],
                "brain_distribution": [{"id": "x", "probability": "1"}],
                "dominance_edges": [{"target": "x", "brain": "x"}],
                "material_order_certificate": "TEST_ORDER_V1",
            })

    def test_material_order_certificate_is_mandatory(self):
        with self.assertRaisesRegex(CouplingError, "MATERIAL_ORDER_CERTIFICATE_REQUIRED"):
            solve({
                "target_distribution": [{"id": "x", "probability": "1"}],
                "brain_distribution": [{"id": "x", "probability": "1"}],
                "dominance_edges": [{"target": "x", "brain": "x"}],
            })


if __name__ == "__main__":
    unittest.main()
