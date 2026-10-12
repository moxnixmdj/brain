from __future__ import annotations

import json
from pathlib import Path
import unittest

from canonical.runtime.one_shot_sky_impact_planner_v1 import (
    ROOT,
    SCHEMA,
    compile_sky_impact_plan,
)

PLAN_PATH = ROOT / "canonical/governance/ONE_SHOT_SKY_IMPACT_PLAN_20261012_V1.json"


class OneShotSkyImpactPlannerV1Tests(unittest.TestCase):
    def test_live_plan_compiles_all_eight_steps_and_twenty_four_propositions(self):
        out = compile_sky_impact_plan(ROOT)
        self.assertTrue(out["pass"], out)
        self.assertEqual(out["schema"], SCHEMA)
        self.assertEqual(
            out["status"],
            "PASS__ONE_SHOT_8_STEP_MATHEMATICAL_AND_UNCERTAINTY_RESOLUTION_PLAN_VERIFIED",
        )
        summary = out["summary"]
        self.assertEqual(summary["step_count"], 8)
        self.assertEqual(summary["certificate_count"], 6)
        self.assertEqual(summary["covered_propositions"], 24)
        self.assertEqual(summary["required_propositions"], 24)
        self.assertEqual(summary["total_covered_weight"], 80)
        self.assertEqual(summary["total_reusable_coverage_bonus"], 84)
        self.assertEqual(summary["transplant_frontier_count"], 11)
        self.assertEqual(summary["serial_wall_clock_seconds"], 11.7)
        self.assertEqual(summary["parallel_critical_path_seconds"], 4.0)
        self.assertGreater(summary["joint_k3_probability_lower"], 0.9999)
        self.assertEqual(summary["total_shannon_entropy_bits_resolved"], 163.0)
        self.assertEqual(summary["incremental_spend_usd"], 0.0)
        self.assertEqual(summary["external_runtime_cognition_count"], 0)
        self.assertFalse(out["terminal_authority"])
        self.assertEqual(out["terminal_credit_delta"], 0)

    def test_persisted_governance_plan_matches_live_compilation(self):
        live = compile_sky_impact_plan(ROOT)
        persisted = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        self.assertEqual(persisted, live)


if __name__ == "__main__":
    unittest.main(verbosity=2)
