from __future__ import annotations

import unittest
from pathlib import Path

from canonical.runtime.terminal_autopilot_executor_refinement_proof_v1 import prove

ROOT = Path(__file__).resolve().parents[2]


class TerminalAutopilotExecutorSemanticRefinementV1Tests(unittest.TestCase):
    def test_bounded_executor_refinement_is_verified(self):
        out = prove(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertTrue(out["refinement_verified"])
        self.assertEqual(
            out["assurance_level"],
            "FINITE_ABSTRACTION_EXECUTOR_AUTHORITY_REFINEMENT",
        )
        self.assertTrue(out["runner_boundary_explicit"])
        self.assertFalse(out["runner_semantics_reproved"])
        self.assertTrue(out["irreversible_benchmark_autoexecution_excluded"])
        self.assertTrue(out["promotion_requires_exact_content_bound_authority"])
        self.assertTrue(out["route_completion_cannot_fabricate_result_present"])
        self.assertTrue(out["promotion_completion_cannot_self_mint_promoted"])
        self.assertTrue(out["terminal_credit_nonamplification"])
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_receipt_binds_exact_executor_and_supervisor_dependency(self):
        out = prove(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(len(out["concrete_route_git_blob_sha"]), 40)
        self.assertEqual(len(out["runner_dependency_git_blob_sha"]), 40)
        self.assertEqual(len(out["receipt_sha256"]), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
