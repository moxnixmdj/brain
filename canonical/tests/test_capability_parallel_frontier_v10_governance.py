from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class ParallelFrontierV10GovernanceTests(unittest.TestCase):
    def test_current_scheduler_binds_v10_interval_runtime(self):
        dev = json.loads(
            (ROOT / "canonical/governance/CURRENT_DEVELOPMENT_SCHEDULER.json").read_text()
        )
        self.assertEqual(
            dev["authoritative_activation"],
            "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V10.json",
        )
        self.assertEqual(
            dev["runtime"],
            "canonical/runtime/capability_parallel_frontier_v2.py",
        )
        self.assertIn("INTERVAL_ROBUST_PARETO", dev["live_selection_rule"])
        self.assertTrue(dev["parallel_frontier_policy"]["interval_robust_dominance"])
        self.assertTrue(
            dev["parallel_frontier_policy"]["read_only_incomplete_vector_parallelism"]
        )

    def test_activation_keeps_full_execution_fail_closed(self):
        activation = json.loads(
            (
                ROOT
                / "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V10.json"
            ).read_text()
        )
        state = activation["current_control_state"]
        self.assertFalse(state["full_execution_plan_authorized"])
        self.assertTrue(state["read_only_evidence_plan_authorized"])
        self.assertEqual(state["current_parallel_read_only_lane_count"], 7)
        self.assertEqual(state["current_parallel_full_execution_lane_count"], 0)
        self.assertIn(
            "A_BENEFIT_LCB_GE_B_BENEFIT_UCB",
            activation["primary_parallel_frontier"]["dominance_rule"],
        )

    def test_r2_bound_request_does_not_wake_generic_frontier(self):
        activation = json.loads(
            (
                ROOT
                / "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V10.json"
            ).read_text()
        )
        self.assertEqual(activation["r2_policy"]["generic_open_world_finance_frontier"], "SLEEPING")
        self.assertEqual(
            activation["r2_policy"]["exact_bounded_evidence_lane"],
            "R2_FINANCE_FOUR_WAY_GOVERNING_REQUIREMENT_OBSERVATION",
        )

    def test_mission_pointer_binds_v10(self):
        mission = json.loads(
            (ROOT / "canonical/governance/CURRENT_MISSION_OBJECTIVE.json").read_text()
        )
        self.assertEqual(
            mission["current_development_scheduler"]["activation"],
            "canonical/governance/CAPABILITY_FIRST_SCHEDULER_ACTIVATION_20261010_V10.json",
        )
        self.assertEqual(
            mission["current_development_scheduler"]["runtime"],
            "canonical/runtime/capability_parallel_frontier_v2.py",
        )
        self.assertIn("INTERVAL_ROBUST_DOMINANCE", mission["scheduler_precedence"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
