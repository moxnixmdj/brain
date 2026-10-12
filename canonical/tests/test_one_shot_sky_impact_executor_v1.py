from __future__ import annotations

import json
from pathlib import Path
import unittest

from canonical.runtime.one_shot_sky_impact_executor_v1 import (
    ROOT,
    SCHEMA,
    execute_all_steps,
)

RECEIPT_PATH = (
    ROOT / "canonical/verification/ONE_SHOT_SKY_IMPACT_EXECUTION_RECEIPT_20261012_V1.json"
)


class OneShotSkyImpactExecutorV1Tests(unittest.TestCase):
    def test_all_eight_steps_execute_and_pass(self):
        out = execute_all_steps(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(
            out["status"],
            "PASS__ALL_8_SKY_IMPACT_STEPS_EXECUTED_AND_VERIFIED",
        )
        self.assertEqual(out["executed_step_count"], 8)
        self.assertEqual(out["passed_step_count"], 8)
        self.assertEqual(len(out["step_receipts"]), 8)
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)
        self.assertEqual(out["incremental_spend_usd"], 0.0)

    def test_persisted_execution_receipt_matches_live_execution(self):
        live = execute_all_steps(ROOT)
        persisted = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(persisted, live)


if __name__ == "__main__":
    unittest.main(verbosity=2)
