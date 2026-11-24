#!/usr/bin/env python3
"""Verification tests for EPISTEMIC_COMPUTER_AGENT_BENCHMARK_20261124_V1."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPT_PATH = ROOT / "canonical" / "verification" / "EPISTEMIC_COMPUTER_AGENT_BENCHMARK_20261124_V1.json"


class EpistemicAgentBenchmarkReceiptTests(unittest.TestCase):
    def test_receipt_invariants_and_controls(self) -> None:
        self.assertTrue(RECEIPT_PATH.is_file())
        data = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["schema"], "EPISTEMIC_COMPUTER_AGENT_BENCHMARK_20261124_V1")

        inv = data["invariants"]
        self.assertEqual(inv["model_calls"], 0)
        self.assertEqual(inv["api_spend_usd"], 0.0)
        self.assertEqual(inv["parameters_stored"], 0)
        self.assertEqual(inv["raw_coordinates_saved"], 0)
        self.assertEqual(inv["raw_trajectories_saved"], 0)

        exp1 = data["experiment_1_goal_directed_room_learning"]
        self.assertEqual(exp1["empty_memory_control_unread_rate"], 1.0)
        self.assertEqual(exp1["goal_directed"]["valid_verified"], "8/8")
        self.assertEqual(exp1["goal_directed"]["corrupt_decoys_caught"], "8/8")
        self.assertLess(
            exp1["goal_directed"]["total_probes"],
            exp1["upfront_all_baseline"]["total_probes"],
        )
        self.assertIn("py:bz2:lazy_open", exp1["lazy_trap_audit"]["lazy_traps_refused"])
        self.assertIn("py:sqlite3:connect_lazy", exp1["lazy_trap_audit"]["lazy_traps_refused"])

        exp2 = data["experiment_2_cli_action_grammar"]
        self.assertTrue(exp2["cold_episode"]["pass"])
        self.assertEqual(exp2["warm_unseen_episodes"]["passed"], "4/4")
        self.assertEqual(exp2["warm_unseen_episodes"]["binaries_probed_total"], 0)
        self.assertEqual(exp2["warm_unseen_episodes"]["raw_argv_replay_control_passed"], "0/4")

        exp3 = data["experiment_3_w3c_aria_osworld_gui_transfer"]
        self.assertEqual(exp3["v1_cold_pass"], "6/6")
        self.assertEqual(exp3["v2_unseen_redesign_schema_transfer_pass"], "6/6")
        self.assertEqual(exp3["naive_aria_without_state_diff_control_pass"], "0/6")
        self.assertEqual(exp3["v2_raw_xy_coordinate_replay_control_pass"], "0/6")
        self.assertEqual(exp3["store_audit"]["raw_coordinates_saved"], 0)

        exp4 = data["experiment_4_blind_unseen_swe_commits"]
        self.assertEqual(exp4["aggregate_unseen_heldout"]["fake_repairs_after_canary_gate"], 0)
        self.assertEqual(
            exp4["heldout_unseen_single_line_round1"]["verified_genuine_repairs"], 2
        )


if __name__ == "__main__":
    unittest.main()
