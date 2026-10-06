import unittest

from canonical.runtime.v7_evaluator_certification_trichotomy_v1 import (
    EvaluatorCertificationError,
    certify,
)


RECEIPT = {
    "path": "canonical/governance/example.json",
    "git_blob_sha": "1234567890abcdef1234567890abcdef12345678",
}
SUCCESS = {"failure": 0.0, "success": 1.0}


class V7EvaluatorCertificationTrichotomyTests(unittest.TestCase):
    def test_explicit_complete_route_can_certify_nonidentical_better_law(self):
        result = certify({
            "mode": "E",
            "semantic_receipts": [RECEIPT],
            "target_law": {"failure": 0.1, "success": 0.9},
            "brain_law": {"success": 1.0},
            "evaluators": [SUCCESS],
        })
        self.assertTrue(result["conditional_noninferiority"])
        self.assertEqual(result["route"], "E_EXPLICIT_COMPLETE")
        self.assertFalse(result["semantic_premise_verified_by_this_runtime"])

    def test_explicit_route_rejects_inferior_law(self):
        result = certify({
            "mode": "EXPLICIT",
            "semantic_receipts": [RECEIPT],
            "target_law": {"failure": 0.01, "success": 0.99},
            "brain_law": {"failure": 0.4, "success": 0.6},
            "evaluators": [SUCCESS],
        })
        self.assertFalse(result["conditional_noninferiority"])

    def test_explicit_route_requires_content_addressed_semantic_receipt(self):
        with self.assertRaises(EvaluatorCertificationError):
            certify({
                "mode": "E",
                "semantic_receipts": [{"path": "x", "git_blob_sha": "not-a-sha"}],
                "target_law": {"success": 1.0},
                "brain_law": {"success": 1.0},
                "evaluators": [SUCCESS],
            })

    def test_monotone_hidden_route_certifies_strict_improvement(self):
        result = certify({
            "mode": "M",
            "semantic_receipts": [RECEIPT],
            "coupling_task": {
                "target_distribution": [
                    {"id": "failure", "probability": "1/10"},
                    {"id": "success", "probability": "9/10"},
                ],
                "brain_distribution": [
                    {"id": "success", "probability": "1"},
                ],
                "dominance_edges": [
                    {"target": "failure", "brain": "success"},
                    {"target": "success", "brain": "success"},
                ],
            },
        })
        self.assertTrue(result["conditional_noninferiority"])
        self.assertEqual(result["route"], "M_HIDDEN_RESTRICTED_MONOTONE")
        self.assertFalse(result["semantic_premise_verified_by_this_runtime"])

    def test_monotone_route_without_proof_receipt_fails_closed(self):
        with self.assertRaises(EvaluatorCertificationError):
            certify({
                "mode": "M",
                "semantic_receipts": [],
                "coupling_task": {},
            })

    def test_arbitrary_hidden_equal_laws_certify_without_evaluator_enumeration(self):
        result = certify({
            "mode": "U",
            "target_distribution_exact": {"a": "1/3", "b": "2/3"},
            "brain_distribution_exact": {"a": "1/3", "b": "2/3"},
        })
        self.assertTrue(result["conditional_noninferiority"])
        self.assertEqual(result["route"], "U_ARBITRARY_OR_UNCLASSIFIED_HIDDEN")
        self.assertTrue(result["semantic_premise_verified_by_this_runtime"])

    def test_arbitrary_hidden_mass_shift_is_rejected(self):
        result = certify({
            "mode": "ARBITRARY_HIDDEN",
            "target_distribution_exact": {"a": "1/2", "b": "1/2"},
            "brain_distribution_exact": {"a": "3/4", "b": "1/4"},
        })
        self.assertFalse(result["conditional_noninferiority"])

    def test_auto_mode_is_conservative_equality_fallback(self):
        result = certify({
            "mode": "AUTO",
            "target_distribution_exact": {"a": 1},
            "brain_distribution_exact": {"a": 1},
        })
        self.assertTrue(result["conditional_noninferiority"])
        self.assertEqual(result["route"], "U_ARBITRARY_OR_UNCLASSIFIED_HIDDEN")

    def test_auto_mode_does_not_guess_easier_route(self):
        with self.assertRaises(EvaluatorCertificationError):
            certify({
                "mode": "AUTO",
                "target_law": {"failure": 0.1, "success": 0.9},
                "brain_law": {"success": 1.0},
                "evaluators": [SUCCESS],
            })


if __name__ == "__main__":
    unittest.main(verbosity=2)
