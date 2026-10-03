from __future__ import annotations

import unittest

from canonical.runtime.tool_invocation_choke_point_cut_v1 import evaluate


class ToolInvocationChokePointCutTests(unittest.TestCase):
    def test_live_runtime_fails_open_to_exact_coverage_obligation(self):
        out = evaluate()
        self.assertEqual(
            out["status"],
            "OPEN__TOTAL_INVOCATION_CHOKE_POINT_COVERAGE_REQUIRED",
            out,
        )
        self.assertGreater(out["runtime_python_files_scanned"], 0)
        self.assertGreater(out["surface_count"], 0)
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)

    def test_known_live_boundaries_cannot_disappear_silently(self):
        out = evaluate()
        paths = set(out["surface_paths"])
        self.assertIn("canonical/runtime/astra_runtime.py", paths)
        self.assertIn("canonical/runtime/external_tool_relay.py", paths)

        rows = out["surfaces"]
        astra = {
            x["function"] for x in rows
            if x["path"] == "canonical/runtime/astra_runtime.py"
            and x["kind"] == "SYSTEM_INVOCATION_BOUNDARY"
        }
        self.assertIn("_goal_action", astra)
        self.assertIn("_invoke_bound_capability", astra)

    def test_cut_grants_no_authority(self):
        out = evaluate()
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
