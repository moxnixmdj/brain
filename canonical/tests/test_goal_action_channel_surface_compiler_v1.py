from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

import canonical.runtime.goal_action_channel_surface_compiler_v1 as surface


class GoalActionChannelSurfaceCompilerTests(unittest.TestCase):
    def source(self):
        return (surface.ROOT / "canonical/runtime/astra_runtime.py").read_text(
            encoding="utf-8"
        )

    def test_exact_bound_surface_compiles_48_of_48(self):
        out = surface.evaluate()
        self.assertEqual(
            out["status"],
            "PASS__DIRECT_SYNTACTIC_CHANNEL_SURFACE_COMPILED",
            out,
        )
        self.assertEqual(out["action_count"], 48)
        self.assertEqual(out["allowed_type_count"], 48)
        self.assertTrue(out["allowed_types_match_handlers"])
        self.assertEqual(out["channel_counts"]["HOST_READ"], 40)
        self.assertEqual(out["channel_counts"]["HOST_WRITE"], 15)
        self.assertEqual(out["channel_counts"]["PROCESS"], 1)
        self.assertEqual(out["channel_counts"]["BOUND_CAPABILITY_DYNAMIC"], 9)
        self.assertEqual(out["channel_counts"]["NETWORK_OR_EXTERNAL"], 6)
        self.assertEqual(
            out["channel_counts"]["NO_OBVIOUS_AMBIENT_PRIMITIVE"], 3
        )
        self.assertFalse(out["no_bypass_credit"])

    def test_new_allowed_type_without_handler_fails_closed(self):
        src = self.source().replace(
            'allowed_types={',
            'allowed_types={"NEW_UNCLASSIFIED_ACTION",',
            1,
        )
        out = surface.compile_surface(src)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertIn("NEW_UNCLASSIFIED_ACTION", out["missing_handlers"])

    def test_handler_removed_from_allowlist_fails_closed(self):
        src = self.source().replace(
            '"write_json_records",',
            "",
            1,
        )
        out = surface.compile_surface(src)
        self.assertEqual(out["status"], "FAIL_CLOSED", out)
        self.assertIn("write_json_records", out["handlers_not_allowed"])

    def test_runtime_blob_drift_fails_closed(self):
        bad = "0" * 40
        with patch.object(surface, "EXPECTED_BLOB", bad):
            out = surface.evaluate()
        self.assertEqual(out["status"], "FAIL_CLOSED__RUNTIME_BLOB_DRIFT")
        self.assertFalse(out.get("no_bypass_credit", False))

    def test_no_obvious_primitive_is_not_called_pure(self):
        out = surface.compile_surface(self.source())
        names = {
            row["action_type"]
            for row in out["rows"]
            if row["direct_syntactic_channels"]
            == ["NO_OBVIOUS_AMBIENT_PRIMITIVE"]
        }
        self.assertEqual(
            names,
            {
                "verify_with_independent_pypi_codec",
                "verify_with_independent_npm_codec",
                "finish",
            },
        )
        self.assertIn("LOWER_BOUND_ONLY", out["interpretation"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
