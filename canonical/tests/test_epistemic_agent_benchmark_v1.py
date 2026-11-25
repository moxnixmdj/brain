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
        v2 = exp4["v2_first_principles_mental_cegis_full_corpus"]
        self.assertEqual(v2["calibration_attrs_seen"]["verified_genuine_repairs"], 2)
        self.assertEqual(
            v2["unseen_heldout_12_repos_deduplicated"]["fake_repairs_remaining_after_4layer_referee"], 0
        )

        exp5 = data["experiment_5_first_principles_mental_cegis_4leaps"]
        self.assertTrue(exp5["leap2_loop_comprehension_stream_canonical_equiv"])
        self.assertTrue(exp5["leap2_python_to_javascript_semantic_transfer"])
        self.assertTrue(exp5["leap3_coupled_two_file_cegis_verified"])
        self.assertTrue(exp5["leap4_destructive_cli_blocked_in_shadow"])
        self.assertTrue(exp5["leap4_inert_aria_decoy_pruned_in_shadow"])
        self.assertTrue(exp5["leap4_destructive_gui_wipe_blocked_in_shadow"])
        self.assertTrue(exp5["leap4_safe_gui_plan_admitted"])

        exp7 = data["experiment_7_v4_subtree_fuzzer_petri320_and_harbor"]
        self.assertEqual(exp7["multistatement_subtree_anti_unification"]["ablation_generalized_python_js_rust"], "5/5")
        self.assertEqual(exp7["multistatement_subtree_anti_unification"]["ablation_raw_traces"], "1/5")
        self.assertEqual(exp7["multistatement_subtree_anti_unification"]["ablation_disabled"], "0/5")
        self.assertTrue(exp7["multistatement_subtree_anti_unification"]["o1_skill_removal_verified"])
        self.assertTrue(exp7["bidirectional_codec_lens"]["caret_control_bytes_roundtrip_verified"])
        self.assertTrue(exp7["cow_64way_boundary_fuzzer"]["caught_empty_string_index_regression"])
        self.assertEqual(exp7["long_horizon_320_step_petri_dominator_slicer"]["steps_executed"], 320)
        self.assertTrue(exp7["harbor_front_door_epistemic_dispatch"]["pass"])
        self.assertEqual(exp7["harbor_front_door_epistemic_dispatch"]["model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
