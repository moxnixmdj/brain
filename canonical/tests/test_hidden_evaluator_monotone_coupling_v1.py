import unittest

from canonical.runtime.hidden_evaluator_monotone_coupling_v1 import (
    CouplingError,
    dominance_relation_sha256,
    solve,
)


def certificate(edges):
    return {
        "schema": "PROJECT_BRAIN_MATERIAL_ORDER_CERTIFICATE_BINDING_V1",
        "certificate_id": "TEST_ORDER_V1",
        "dominance_relation_sha256": dominance_relation_sha256(edges),
        "verification_receipt_sha256": "a" * 64,
        "scope_complete": True,
        "monotone_evaluator_class_bound": True,
    }


class MonotoneCouplingTests(unittest.TestCase):
    def test_strict_improvement_can_dominate_without_observational_equivalence(self):
        edges = [
            {"target": "low", "brain": "high"},
            {"target": "high", "brain": "high"},
        ]
        out = solve({
            "target_distribution": [
                {"id": "low", "probability": "1/2"},
                {"id": "high", "probability": "1/2"},
            ],
            "brain_distribution": [
                {"id": "high", "probability": "1"},
            ],
            "dominance_edges": edges,
            "material_order_certificate": certificate(edges),
        })
        self.assertEqual(out["status"], "PASS", out)
        self.assertEqual(out["max_coupled_mass"], "1")
        self.assertTrue(out["certificate_relation_binding_verified"])
        self.assertFalse(out["material_order_semantics_verified_by_kernel"])
        self.assertTrue(out["claim_is_conditional_on_external_material_order_semantics"])
        self.assertTrue(out["universal_monotone_utility_noninferiority"])
        self.assertFalse(out["observational_equivalence_required"])
        self.assertIsNone(out["min_cut_obstruction"])

    def test_inferior_mass_fails_closed_with_exact_dual_witness(self):
        edges = [
            {"target": "low", "brain": "low"},
            {"target": "low", "brain": "high"},
            {"target": "high", "brain": "high"},
        ]
        out = solve({
            "target_distribution": [
                {"id": "low", "probability": "0"},
                {"id": "high", "probability": "1"},
            ],
            "brain_distribution": [
                {"id": "low", "probability": "1"},
                {"id": "high", "probability": "0"},
            ],
            "dominance_edges": edges,
            "material_order_certificate": certificate(edges),
        })
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertFalse(out["universal_monotone_utility_noninferiority"])
        self.assertEqual(out["max_coupled_mass"], "0")
        self.assertEqual(out["min_cut_obstruction"], {
            "target_set": ["high"],
            "dominating_brain_neighborhood": ["high"],
            "target_mass": "1",
            "brain_capacity": "0",
            "deficit": "1",
        })

    def test_mixed_distribution_reports_exact_quarter_deficit(self):
        edges = [
            {"target": "low", "brain": "low"},
            {"target": "low", "brain": "high"},
            {"target": "high", "brain": "high"},
        ]
        out = solve({
            "target_distribution": [
                {"id": "low", "probability": "1/2"},
                {"id": "high", "probability": "1/2"},
            ],
            "brain_distribution": [
                {"id": "low", "probability": "3/4"},
                {"id": "high", "probability": "1/4"},
            ],
            "dominance_edges": edges,
            "material_order_certificate": certificate(edges),
        })
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertEqual(out["max_coupled_mass"], "3/4")
        self.assertEqual(out["min_cut_obstruction"]["target_set"], ["high"])
        self.assertEqual(out["min_cut_obstruction"]["deficit"], "1/4")

    def test_certificate_must_bind_exact_dominance_relation(self):
        edges = [{"target": "x", "brain": "x"}]
        cert = certificate(edges)
        cert["dominance_relation_sha256"] = "0" * 64
        with self.assertRaisesRegex(
            CouplingError,
            "MATERIAL_ORDER_CERTIFICATE_EDGE_BINDING_MISMATCH",
        ):
            solve({
                "target_distribution": [{"id": "x", "probability": "1"}],
                "brain_distribution": [{"id": "x", "probability": "1"}],
                "dominance_edges": edges,
                "material_order_certificate": cert,
            })

    def test_legacy_unbound_string_certificate_fails_closed(self):
        with self.assertRaisesRegex(
            CouplingError,
            "MATERIAL_ORDER_CERTIFICATE_BOUND_OBJECT_REQUIRED",
        ):
            solve({
                "target_distribution": [{"id": "x", "probability": "1"}],
                "brain_distribution": [{"id": "x", "probability": "1"}],
                "dominance_edges": [{"target": "x", "brain": "x"}],
                "material_order_certificate": "UNBOUND_LEGACY_STRING",
            })

    def test_probabilities_must_be_exactly_normalized(self):
        edges = [{"target": "x", "brain": "x"}]
        with self.assertRaisesRegex(
            CouplingError,
            "TARGET_PROBABILITIES_MUST_SUM_TO_1",
        ):
            solve({
                "target_distribution": [{"id": "x", "probability": "0.9"}],
                "brain_distribution": [{"id": "x", "probability": "1"}],
                "dominance_edges": edges,
                "material_order_certificate": certificate(edges),
            })

    def test_material_order_verification_receipt_digest_is_mandatory(self):
        edges = [{"target": "x", "brain": "x"}]
        cert = certificate(edges)
        cert["verification_receipt_sha256"] = "not-a-digest"
        with self.assertRaisesRegex(
            CouplingError,
            "MATERIAL_ORDER_VERIFICATION_RECEIPT_SHA256_REQUIRED",
        ):
            solve({
                "target_distribution": [{"id": "x", "probability": "1"}],
                "brain_distribution": [{"id": "x", "probability": "1"}],
                "dominance_edges": edges,
                "material_order_certificate": cert,
            })


if __name__ == "__main__":
    unittest.main()
