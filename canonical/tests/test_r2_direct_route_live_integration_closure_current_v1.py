from __future__ import annotations

import unittest

from canonical.runtime import r2_direct_route_live_integration_closure_v2 as closure


class R2DirectRouteLiveIntegrationClosureV2CurrentTests(unittest.TestCase):
    def test_current_verified_deployable_equals_default_executable(self):
        out = closure.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["baseline_activation_route_count"], 33)
        self.assertEqual(out["dynamic_admission_route_count"], 0)
        self.assertEqual(out["expected_deployable_route_count"], 33)
        self.assertEqual(out["effective_executable_route_count"], 33)
        self.assertTrue(out["verified_deployable_equals_default_executable"])
        self.assertEqual(out["missing_execution"], [])
        self.assertEqual(out["unauthorized_execution"], [])
        self.assertTrue(out["runtime_binding_ok"])
        self.assertTrue(out["fixed_point_binding_ok"])
        self.assertTrue(out["controller_fixed_point_binding_ok"])
        self.assertTrue(out["stable_dispatcher_import_live"])
        self.assertFalse(out["legacy_versioned_direct_import_live"])
        self.assertFalse(out["future_route_source_edit_required"])
        self.assertFalse(out["future_route_registry_edit_required"])
        self.assertFalse(out["legacy_version_chain_load_bearing"])
        self.assertFalse(out["open_world_semantic_coverage_claimed"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
