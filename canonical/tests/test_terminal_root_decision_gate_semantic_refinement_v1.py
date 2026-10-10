from __future__ import annotations

import unittest
from pathlib import Path

from canonical.runtime.terminal_root_decision_gate_refinement_proof_v1 import prove

ROOT = Path(__file__).resolve().parents[2]


class TerminalRootDecisionGateSemanticRefinementV1Tests(unittest.TestCase):
    def test_bounded_gate_refinement_is_verified(self):
        out = prove(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["refinement_verified"])
        self.assertEqual(out["assurance_level"], "FINITE_ABSTRACTION_TERMINAL_ROOT_GATE_REFINEMENT")
        self.assertEqual(out["legal_success_route_count"], 4)
        self.assertTrue(out["content_addressed_proof_required"])
        self.assertTrue(out["independent_verifier_required"])
        self.assertTrue(out["declaration_cannot_override_bound_proof"])
        self.assertTrue(out["terminal_nonamplification"])
        self.assertTrue(out["d_finality_preserved"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_receipt_is_content_bound(self):
        out = prove(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(len(out["concrete_gate_git_blob_sha"]), 40)
        self.assertEqual(len(out["abstract_spec_git_blob_sha"]), 40)
        self.assertEqual(len(out["receipt_sha256"]), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
