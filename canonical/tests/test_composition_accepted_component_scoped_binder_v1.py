from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

import canonical.runtime.composition_accepted_component_scoped_binder_v1 as m

ROOT = Path(__file__).resolve().parents[2]


class CompositionAcceptedComponentScopedBinderTests(unittest.TestCase):
    def test_live_two_exact_bridges_pass(self):
        out = m.evaluate_live()
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["scoped_proved_interface_count"], 2)
        self.assertEqual(out["open_interface_count"], 10)
        self.assertFalse(out["composition_component_predicate_closed"])
        self.assertEqual(
            {
                (r["component_id"], r["interface_id"])
                for r in out["slicer_result"]["interfaces"]
                if r["state"] == "SCOPED_PROVED"
            },
            {
                ("delegation", "delegation+evidence synthesis+artifact production"),
                ("tool discovery", "coding+debugging+tool discovery"),
            },
        )

    def test_zero_credit_and_no_authority(self):
        out = m.evaluate_live()
        self.assertEqual(out["capability_credit_delta"], 0)
        self.assertEqual(out["family_credit_delta"], 0)
        self.assertFalse(out["execution_authority"])
        self.assertFalse(out["promotion_authority"])

    def test_only_two_receipts_emitted(self):
        out = m.evaluate_live()
        self.assertEqual(len(out["admissible_receipts"]), 2)
        for row in out["admissible_receipts"]:
            self.assertTrue(row["verified"])
            self.assertTrue(row["independent"])
            self.assertTrue(row["contamination_clean"])
            self.assertTrue(row["acceptance_scoped"])
            self.assertEqual(
                row["binds_frozen_claim"],
                "MULTI_CAPABILITY_COMPOSITION::FROZEN_PROTOCOL_V1",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
