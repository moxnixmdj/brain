"""Deterministic verification suite for Frontier Leapfrog Wave 2 (`K3 = 0`) substrates,
`domain_atlas_v1` federated engine stem resolution, and `BRAIN_UNIFIED_MODEL_V1` wiring.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import (  # noqa: E402
    brain_unified_model_v1 as unified,
    counterfactual_discr_tree_skill_router_v1 as play_a,
    cow_zygote_speculative_verifier_v1 as play_d,
    relational_guard_addition_symbolic_repair_v1 as play_c,
    unified_hidden_capability_federation_v1 as fed,
    verified_zero_screenshot_action_cache_v1 as play_b,
)
from canonical.tools import domain_atlas_v1 as atlas_tool  # noqa: E402


class FrontierLeapfrogWave2PlaysTests(unittest.TestCase):
    def test_play_a_189_commit_bound_and_witness_counterfactual_router(self) -> None:
        res = play_a.run({}, ROOT)
        self.assertEqual(res["status"], "OK")
        self.assertFalse(res["kill_criterion"]["kill_triggered"])
        self.assertEqual(res["model_dependency_count"], 0)

        p1 = res["part1_189_commit_syntax_only_bound"]
        self.assertEqual(p1["commits_audited"], 189)
        self.assertEqual(p1["repeating_skeleton_rewrites_ge_2"], 0)

        p2 = res["part2_witness_conditioned_counterfactual_router"]
        self.assertEqual(p2["evicted_safe_code_regression"], 3)
        self.assertEqual(p2["evicted_nonpositive_utility"], 1)
        self.assertEqual(p2["kept_active_skills"], 5)
        self.assertFalse(p2["split_ab_sign_flip"])

        heldout_gated = p2["counterfactual_gated_heldout_split_b"]
        heldout_ungated = p2["ungated_heldout_split_b"]
        self.assertEqual(heldout_gated["safe_code_regressions"], 0)
        self.assertEqual(heldout_gated["precision"], 1.0)
        self.assertEqual(heldout_gated["defective_repaired"], 15)
        self.assertGreater(heldout_ungated["safe_code_regressions"], 0)
        self.assertGreater(heldout_gated["net_causal_utility"], heldout_ungated["net_causal_utility"])

        scaling = res["discr_tree_scaling_1086_rules"]
        self.assertEqual(scaling["indexed_rules"], 1086)
        self.assertLess(scaling["discr_tree_lookup_p50_us"], 50.0)
        self.assertGreater(scaling["speedup_vs_linear_x"], 100.0)

    def test_play_b_zero_screenshot_data_layer_and_preprobed_cdp_cache(self) -> None:
        res = play_b.run({}, ROOT)
        self.assertEqual(res["status"], "OK")
        self.assertFalse(res["kill_criterion"]["kill_triggered"])
        self.assertEqual(res["screenshots_captured"], 0)
        self.assertEqual(res["model_dependency_count"], 0)

        t0 = res["tier0_data_layer"]
        self.assertEqual(t0["tier0_real_artifacts_verified"], 3)
        self.assertEqual(t0["elevated_trace_steps_kept"], 1)

        t1 = res["tier1_verified_cdp_cache"]
        self.assertEqual(t1["volatile_hits"], 20)
        self.assertEqual(t1["volatile_false_invalidation_rate"], 0.0)
        self.assertEqual(t1["blind_stale_executions"], 0)
        self.assertTrue(t1["evicted_on_third_miss"])
        self.assertEqual(t1["post_eviction_status"], "CACHE_MISS")
        self.assertEqual(t1["silent_backend_drop_status"], "FAIL_CLOSED_POST_CONTRACT")
        self.assertLess(t1["local_dispatch_p50_ms"], 5.0)

    def test_play_c_relational_guard_addition_and_guarddrop_mutation_gate(self) -> None:
        res = play_c.run({}, ROOT)
        self.assertEqual(res["status"], "OK")
        self.assertFalse(res["kill_criterion"]["kill_triggered"])
        self.assertEqual(res["model_dependency_count"], 0)

        p1 = res["part1_real_corpus_addition_audit"]
        self.assertEqual(p1["taxonomy_28_tasks"], 28)
        self.assertEqual(p1["taxonomy_add_sites"], 482)
        self.assertEqual(p1["real_fix_pairs_parsed"], 87)

        p2 = res["part2_closed_loop_non_substitution_synthesis"]
        self.assertEqual(p2["substitution_baseline_solved"], 0)
        self.assertEqual(p2["relational_addition_admitted"], 4)
        self.assertEqual(p2["admitted_with_surviving_guard_drop_mutant"], 0)
        self.assertEqual(p2["overall_mutation_kill_rate"], 1.0)
        self.assertEqual(p2["total_mutants_killed"], p2["total_mutants_tested"])

    def test_play_d_cow_zygote_speculative_verifier_and_impact_slicer(self) -> None:
        res = play_d.run({}, ROOT)
        self.assertEqual(res["status"], "OK")
        self.assertFalse(res["kill_criterion"]["kill_triggered"])
        self.assertEqual(res["model_dependency_count"], 0)

        sl = res["impact_slicing"]
        self.assertEqual(sl["selected_tests"], ["test_fee_zero_and_negative", "test_fee_standard_and_capped"])
        self.assertEqual(sl["reduction_ratio"], 0.5)

        bm = res["benchmark_48_candidates"]
        self.assertEqual(bm["candidates_evaluated"], 48)
        self.assertEqual(bm["valid_repairs_found"], 2)
        self.assertEqual(bm["verdict_disagreements_vs_subprocess"], 0)
        self.assertEqual(bm["cross_worker_state_leaks"], 0)
        self.assertLess(bm["cow_fork_p50_ms"], 5.0)
        self.assertGreater(bm["speedup_vs_subprocess_x"], 3.0)

    def test_unified_model_wires_21_organs_105_federated_engines_and_atlas_reachability(self) -> None:
        model = unified.open_model()
        inv = model.frontier_organs()
        self.assertEqual(inv["swe_kernel_organs_count"], 13)
        self.assertEqual(inv["leapfrog_plays_count"], 8)
        self.assertEqual(inv["total_organs"], 21)

        for oid in (
            "play_a_counterfactual_discr_tree_router",
            "play_b_verified_zero_screenshot_cache",
            "play_c_relational_guard_addition_repair",
            "play_d_cow_zygote_speculative_verifier",
        ):
            out = model.invoke_frontier_organ(oid, {})
            self.assertEqual(out["status"], "OK", oid)

        # Verify newly federated domain-leader engines execute cleanly via run_federated_engine
        fp_res = fed.run_federated_engine("RULE_EXPIRY_WORLD_FINGERPRINT", {})
        self.assertTrue(fp_res["pass"])
        self.assertIn("python_major_minor", fp_res["fingerprint"])

        mem_res = fed.run_federated_engine(
            "ASSOCIATIVE_EPISODIC_MEMORY",
            {"cue": "decode ooxml paragraph", "episodes": ["decode ooxml paragraph node safely"]},
        )
        self.assertTrue(mem_res["pass"])
        self.assertEqual(mem_res["count"], 1)

        proc_res = fed.run_federated_engine(
            "PROCEDURE_TRAJECTORY_MEMORY",
            {"text": "convert payload from json to yaml", "other_text": "convert payload from yaml to json"},
        )
        self.assertTrue(proc_res["pass"])
        self.assertFalse(proc_res["agrees_on_direction"])

        # Verify _model_status and stored DOMAIN_ATLAS_V1 reachability reflect federated engine stems
        raw_model = json.loads((ROOT / "canonical/unified_model/BRAIN_UNIFIED_MODEL_V1.json").read_text(encoding="utf-8"))
        mstatus = atlas_tool._model_status(raw_model)
        self.assertIn("counterfactual_discr_tree_skill_router_v1", mstatus["adapters"])
        self.assertIn("canonical/tools/the_refusal_is_the_curriculum_v1.py", mstatus["source_index"])

        atlas = json.loads((ROOT / "canonical/unified_model/DOMAIN_ATLAS_V1.json").read_text(encoding="utf-8"))
        for dom, r in atlas["reachability"].items():
            self.assertEqual(r["frontier_route_hit_recall"], 1.0, dom)
            self.assertGreaterEqual(r["native_route_hit_recall"], 0.667, dom)


if __name__ == "__main__":
    unittest.main()
