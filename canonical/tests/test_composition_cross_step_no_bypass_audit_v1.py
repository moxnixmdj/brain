from __future__ import annotations

import unittest

from canonical.runtime.composition_cross_step_no_bypass_audit_v1 import evaluate


class Tests(unittest.TestCase):
    def test_known_raw_cross_step_counterexample_is_closed(self):
        out = evaluate()
        self.assertEqual(
            out["status"],
            "PASS__KNOWN_RAW_CROSS_STEP_BYPASS_CLOSED_BY_DECLARED_CONTENT_BOUND_PROJECTION",
            out,
        )
        self.assertTrue(out["known_counterexample_closed"], out)
        self.assertEqual(out["errors"], [], out)
        self.assertTrue(
            out["mission_checks"]["step0_body_dependency_declared_exactly"],
            out,
        )
        self.assertTrue(
            out["runtime_checks"]["source_result_content_hash"],
            out,
        )
        self.assertTrue(
            out["forbidden_runtime_checks"]["forward_loop_raw_all_context"],
            out,
        )
        self.assertIn(
            "EXHAUSTIVE_ACCOUNTING_OF_OTHER_MUTABLE_CROSS_STEP_CHANNELS",
            out["remaining"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
