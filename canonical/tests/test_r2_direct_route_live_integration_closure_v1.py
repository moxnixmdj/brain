from __future__ import annotations

import unittest

from canonical.runtime import r2_direct_route_live_integration_closure_v1 as closure


class R2DirectRouteLiveIntegrationClosureV1Tests(unittest.TestCase):
    def test_current_direct_route_live_integration_is_closed(self):
        out = closure.evaluate()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["verified_deployable_route_count"], 28)
        self.assertEqual(out["active_registry_route_count"], 28)
        self.assertEqual(out["executable_dispatch_route_count"], 28)
        self.assertTrue(
            out["verified_deployable_equals_active_equals_executable"]
        )
        self.assertEqual(out["missing_promotion"], [])
        self.assertEqual(out["registry_not_in_verified_universe"], [])
        self.assertEqual(out["missing_execution"], [])
        self.assertEqual(out["unauthorized_execution"], [])
        self.assertTrue(out["runtime_binding_ok"])
        self.assertTrue(out["fixed_point_blob_ok"])
        self.assertTrue(out["stable_dispatcher_import_live"])
        self.assertFalse(out["legacy_version_chain_import_live"])
        self.assertFalse(out["future_route_source_edit_required"])
        self.assertFalse(out["legacy_version_chain_load_bearing"])
        self.assertFalse(out["open_world_semantic_coverage_claimed"])
        self.assertFalse(out["terminal_authority"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
