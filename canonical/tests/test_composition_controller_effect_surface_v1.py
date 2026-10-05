from __future__ import annotations

import unittest

from canonical.runtime.composition_controller_effect_surface_v1 import audit_runtime


class CompositionControllerEffectSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = audit_runtime()

    def test_allowed_and_implemented_controller_surface_is_exact(self):
        self.assertTrue(self.out["dispatch_surface_exact"], self.out)
        self.assertEqual(self.out["allowed_not_implemented"], [])
        self.assertEqual(self.out["implemented_not_allowed"], [])
        self.assertGreater(self.out["allowed_action_count"], 0)

    def test_bounded_loop_directory_tree_is_not_covered_by_current_path_whitelist(self):
        rows = {
            x["action_type"]: x
            for x in self.out["uncovered_effect_witnesses"]
        }
        self.assertIn("invoke_capability_until", rows)
        self.assertEqual(
            rows["invoke_capability_until"]["effect"],
            "ATTEMPTS_DIRECTORY_TREE",
        )
        self.assertEqual(
            rows["invoke_capability_until"]["missing_capture_key"],
            "attempts_dir",
        )

    def test_fanout_artifact_set_is_not_covered_by_current_path_whitelist(self):
        rows = {
            x["action_type"]: x
            for x in self.out["uncovered_effect_witnesses"]
        }
        self.assertIn("invoke_capability_fanout", rows)
        self.assertEqual(
            rows["invoke_capability_fanout"]["effect"],
            "FANOUT_ARTIFACT_SET",
        )
        self.assertEqual(
            rows["invoke_capability_fanout"]["missing_capture_key"],
            "output_dir",
        )

    def test_effectful_actions_fail_closed_for_global_p1_p2(self):
        self.assertGreater(len(self.out["stateful_action_types"]), 0)
        self.assertGreater(len(self.out["delegated_or_process_action_types"]), 0)
        self.assertFalse(self.out["global_p1_p2_no_bypass_proved"])
        self.assertEqual(
            self.out["status"],
            "FAIL_CLOSED__NO_BYPASS_NOT_PROVED",
        )

    def test_credit_and_authority_remain_zero(self):
        for key in (
            "acceptance_credit_delta",
            "family_credit_delta",
            "capability_credit_delta",
            "ownership_credit_delta",
        ):
            self.assertEqual(self.out[key], 0)
        self.assertFalse(self.out["execution_authority"])
        self.assertFalse(self.out["promotion_authority"])
        self.assertFalse(self.out["fresh_reality_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
