from __future__ import annotations

import unittest

from canonical.runtime.composition_cross_step_no_bypass_audit_v2 import evaluate


class CompositionCrossStepNoBypassAuditV2Tests(unittest.TestCase):
    def test_explicit_astra_step_projection_has_no_legacy_fallback(self):
        out = evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(
            out["status"],
            "PASS__EXPLICIT_ASTRA_SHELL_PRIOR_RESULT_PROJECTION_HAS_NO_LEGACY_BYPASS",
            out,
        )
        self.assertEqual(
            out["structural"]["astra_step_projection_site_count"], 1, out
        )
        self.assertEqual(out["structural"]["legacy_all_prior_loop_count"], 0, out)
        self.assertEqual(
            out["structural"]["legacy_context_results_return_count"], 0, out
        )
        self.assertGreaterEqual(
            out["structural"]["legacy_forbidden_guard_count"], 1, out
        )
        self.assertEqual(
            out["structural"]["step_context_calls_context_results"], 0, out
        )
        self.assertEqual(
            out["structural"]["step_context_calls_declared_context_results"], 1, out
        )
        self.assertIn(
            "EXHAUSTIVE_ACCOUNTING_OF_NON_RESULT_MUTABLE_CROSS_STEP_CHANNELS",
            out["remaining"],
        )
        self.assertEqual(out["terminal_credit_delta"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
