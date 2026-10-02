from __future__ import annotations
import unittest

from canonical.runtime import p1_terminal_execution_scope_audit_v1 as audit


class P1TerminalExecutionScopeAuditTests(unittest.TestCase):
    def test_exact_executed_route_is_narrower_than_frozen_p1(self):
        out = audit.evaluate()
        self.assertTrue(out["audit_valid"], out)
        self.assertTrue(out["scope_mismatch_proved"], out)
        self.assertEqual(
            out["executed_route"]["candidate_output_keys_scored"],
            ["cause_step", "evidence_steps", "repair_id"],
        )
        self.assertIn(
            "FAILURE_MECHANISM_CLASSIFICATION_SUPPORTED_BY_VISIBLE_RECEIPTS",
            out["frozen_required_checks_not_evaluated_by_executed_scorer"],
        )
        self.assertIn(
            "NONIDENTIFIABLE_OR_CAUSALLY_EQUIVALENT_CASE_DOES_NOT_FORCE_UNIQUE_CAUSE",
            out["frozen_required_checks_not_evaluated_by_executed_scorer"],
        )
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
