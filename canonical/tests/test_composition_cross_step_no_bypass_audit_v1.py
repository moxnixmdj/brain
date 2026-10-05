from __future__ import annotations

import unittest

from canonical.runtime.composition_cross_step_no_bypass_audit_v1 import evaluate


class Tests(unittest.TestCase):
    def test_current_runtime_counterexample_is_mechanical(self):
        out = evaluate()
        self.assertEqual(
            out["status"],
            "PASS__CURRENT_ASTRA_CROSS_STEP_CHANNEL_FALSIFIES_NO_BYPASS_PREMISE",
            out,
        )
        self.assertTrue(out["counterexample_holds"], out)
        self.assertFalse(out["capsule_bound_at_shell_boundary"], out)
        self.assertTrue(
            out["mission_checks"]["later_shell_consumes_step0_body"],
            out,
        )
        self.assertTrue(
            out["runtime_checks"]["mission_loop_passes_all_context"],
            out,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
