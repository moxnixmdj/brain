from __future__ import annotations

import unittest

from canonical.runtime.hidden_evaluator_top_support_dominance_v1 import (
    verify_top_support_certificate,
)


def base():
    return {
        "outcomes": ["ZERO", "MINOR", "CRITICAL"],
        "dominance_edges": [
            ["ZERO", "MINOR"],
            ["MINOR", "CRITICAL"],
        ],
        "brain_top_support": ["ZERO"],
        "brain_support_receipt": {
            "path": "canonical/verification/example_scope_complete_zero_receipt.json",
            "git_blob_sha": "0123456789abcdef0123456789abcdef01234567",
            "scope_complete": True,
            "independent_or_objective": True,
        },
    }


class Tests(unittest.TestCase):
    def test_transitive_top_support_passes_without_target_distribution(self):
        verdict = verify_top_support_certificate(base())
        self.assertEqual(verdict["status"], "PASS", verdict)
        self.assertFalse(verdict["target_distribution_required"])
        self.assertFalse(verdict["target_case_level_outputs_required_for_this_monotone_conjunct"])

    def test_non_top_support_fails_closed(self):
        cert = base()
        cert["brain_top_support"] = ["MINOR"]
        verdict = verify_top_support_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("TOP_SUPPORT_DOES_NOT_DOMINATE_ALL", verdict["reason"])

    def test_incomplete_support_receipt_fails_closed(self):
        cert = base()
        cert["brain_support_receipt"]["scope_complete"] = False
        verdict = verify_top_support_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("NOT_SCOPE_COMPLETE", verdict["reason"])

    def test_nonindependent_support_receipt_fails_closed(self):
        cert = base()
        cert["brain_support_receipt"]["independent_or_objective"] = False
        verdict = verify_top_support_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("NOT_INDEPENDENT", verdict["reason"])

    def test_cyclic_declared_dominance_is_not_a_partial_order(self):
        cert = base()
        cert["dominance_edges"].append(["CRITICAL", "ZERO"])
        verdict = verify_top_support_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("DOMINANCE_NOT_ANTISYMMETRIC", verdict["reason"])

    def test_unknown_outcome_in_edge_fails_closed(self):
        cert = base()
        cert["dominance_edges"].append(["ZERO", "GHOST"])
        verdict = verify_top_support_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("UNKNOWN_OUTCOME", verdict["reason"])

    def test_multiple_equivalent_universal_top_classes_require_real_partial_order(self):
        cert = base()
        cert["outcomes"] = ["A", "B", "LOW"]
        cert["dominance_edges"] = [["A", "LOW"], ["B", "LOW"]]
        cert["brain_top_support"] = ["A", "B"]
        verdict = verify_top_support_certificate(cert)
        self.assertEqual(verdict["status"], "FAIL_CLOSED")
        self.assertIn("TOP_SUPPORT_DOES_NOT_DOMINATE_ALL", verdict["reason"])

    def test_singleton_universe_passes(self):
        cert = base()
        cert["outcomes"] = ["ONLY"]
        cert["dominance_edges"] = []
        cert["brain_top_support"] = ["ONLY"]
        verdict = verify_top_support_certificate(cert)
        self.assertEqual(verdict["status"], "PASS", verdict)


if __name__ == "__main__":
    unittest.main(verbosity=2)
