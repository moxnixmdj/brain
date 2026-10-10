from __future__ import annotations

import unittest
from pathlib import Path

from canonical.runtime.brain_owned_semantic_edge_refinement_proof_v1 import prove

ROOT = Path(__file__).resolve().parents[2]


class BrainOwnedSemanticEdgeSemanticRefinementProofV1Tests(unittest.TestCase):
    def test_bounded_controller_semantic_refinement_is_verified(self):
        out = prove(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["refinement_verified"])
        self.assertEqual(out["assurance_level"], "FINITE_ABSTRACTION_CONTROLLER_REFINEMENT")
        self.assertEqual(out["declared_transition_case_count"], 15)
        self.assertEqual(out["dynamic_transition_case_count"], 15)
        self.assertTrue(out["static_fail_reason_space_exact"])
        self.assertTrue(out["delegated_dependency_boundary_explicit"])
        self.assertFalse(out["semantic_truth_authority"])
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_receipt_is_content_bound(self):
        out = prove(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(len(out["certificate_git_blob_sha"]), 40)
        self.assertEqual(len(out["abstract_spec_git_blob_sha"]), 40)
        self.assertEqual(len(out["concrete_route_git_blob_sha"]), 40)
        self.assertEqual(len(out["receipt_sha256"]), 64)
        self.assertTrue(out["proof_dependencies"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
