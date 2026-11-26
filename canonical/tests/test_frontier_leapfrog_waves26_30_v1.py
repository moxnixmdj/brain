#!/usr/bin/env python3
"""Zero-Mock End-to-End Verification Suite for Frontier-Leapfrog Waves 26-30.

Verifies:
  - Wave 26: Elon Speed Pass II (lazy spine imports, zero eager memory_bus on
             UnifiedModel.boundary_router, mmap FTS5, incremental mmap SQLite AST
             symbol + caller + 2-hop impact graph sidecar).
  - Wave 27: Contrast-carrying guard laws with O(1) anti-Catastrophic-Remembering pruning
             (`a_law_carries_its_reason_v1` + `the_width_of_a_guard_v1`), filing-key
             collision audit (`the_index_is_the_bottleneck_v1`), operand-unwelded
             alpha-safe transfer (`what_the_operand_names_cost_v1`), AgentHER hindsight
             lifted generalization (`perfect_algorithm_lifted_generalization_v1`), and
             JitRL closed-form non-parametric advantage scoring.
  - Wave 28: Backward Producer-Lineage Tracing + Typed Hole Inversion SWE Engine
             (`producer_lineage_graph_v1`, `the_name_is_a_hole_v1`,
             `the_constant_is_a_hole_v1`, `closed_loop_trace_abduction_repair_v1`,
             `the_value_that_was_rejected_had_a_producer_v1`, `causal_dependency_repair_v1`,
             `a_relation_over_two_guards_v1`).
  - Wave 29: Verifier Hunk-Pinning Audit (`what_the_verifier_actually_pins_v1`),
             Docstring Oracle Extraction & Live Roundtrip Probing
             (`the_docstring_states_the_oracle_v1`), Green-Suite Regression Oracle
             Synthesis, and Creature Red Queen hunk-pinning integration.
  - Wave 30: Purpose-Gated Active Inference (`intake/purpose_gate_v1`,
             `intake/residual_question_gate_v1`), Economic Cost Arbitrage
             (`what_a_decision_costs_v1`), Class-Level Two-Move Compositional Planning
             (`a_goal_that_needs_two_moves_v1`), Horizon Bridge
             (`perfect_algorithm_horizon_bridge_v1`), Transactional Goal DAG
             (`goal_dag_executor_v1`), OSWorld v2.1 Policy (`osworld_v21_workflow_policy_v2`),
             and `UnifiedModel.leapfrog_solve(..., mode="auto")` dispatch.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import brain_unified_model_v1 as bum


class TestFrontierLeapfrogWaves26To30(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = bum.open_model()

    # ------------------------------------------------------------------ Wave 26
    def test_wave26_elon_speed_lazy_router_and_mmap_symbol_graph(self) -> None:
        # 1. Verify fresh UnifiedModel.boundary_router NEVER eagerly boots memory_bus
        probe_script = (
            "import json, time\n"
            "from canonical.runtime import brain_unified_model_v1 as bum\n"
            "m = bum.open_model()\n"
            "t0 = time.perf_counter()\n"
            "br = m.boundary_router\n"
            "dt_ms = (time.perf_counter() - t0) * 1000.0\n"
            "lazy_ok = (m._memory_bus is None and br._memory_bus is None)\n"
            "shared_ok = (br.memory_bus is m.memory_bus)\n"
            "print(json.dumps({'dt_ms': round(dt_ms, 3), 'lazy_ok': lazy_ok, 'shared_ok': shared_ok}))\n"
        )
        raw = subprocess.check_output([sys.executable, "-c", probe_script], cwd=str(ROOT), text=True).strip()
        import json as _json

        info = _json.loads(raw.splitlines()[-1])
        self.assertTrue(info["lazy_ok"], f"boundary_router eagerly constructed memory_bus: {info}")
        self.assertTrue(info["shared_ok"], "boundary_router.memory_bus must share UnifiedModel.memory_bus")
        self.assertLess(info["dt_ms"], 80.0, f"lazy boundary_router took too long: {info['dt_ms']}ms")

        prof = self.model.elon_speed_profile()
        self.assertTrue(prof["pass"])
        self.assertTrue(prof["lazy_router_memory_bus"])
        self.assertTrue(prof["lazy_spine_imports"])
        self.assertTrue(prof["mmap_fts5_enabled"])

        # 2. Persistent mmap SQLite AST symbol + caller + 2-hop impact graph with incremental refresh
        with tempfile.TemporaryDirectory(prefix="wave26_sym_") as td:
            repo = Path(td)
            (repo / "core.py").write_text(
                "def compute_tax(amount):\n"
                '    """Calculate regional VAT tax."""\n'
                "    return amount * 0.15\n",
                encoding="utf-8",
            )
            (repo / "billing.py").write_text(
                "from core import compute_tax\n\n"
                "def build_invoice(subtotal):\n"
                "    return subtotal + compute_tax(subtotal)\n",
                encoding="utf-8",
            )
            (repo / "checkout.py").write_text(
                "from billing import build_invoice\n\n"
                "def finalize_order(subtotal):\n"
                "    return build_invoice(subtotal)\n",
                encoding="utf-8",
            )

            d1 = self.model.repo_symbol_graph_query(repo, kind="find_definition", query="compute_tax")
            self.assertTrue(d1["pass"])
            self.assertEqual(d1["hits"][0]["path"], "core.py")
            self.assertEqual(d1["index_stats"]["files_reparsed_this_call"], 3)

            # Second query on unchanged repo must reparse 0 files!
            c1 = self.model.repo_symbol_graph_query(repo, kind="find_callers", query="compute_tax")
            self.assertTrue(c1["pass"])
            self.assertEqual(c1["index_stats"]["files_reparsed_this_call"], 0)
            self.assertTrue(any(h["src_symbol"] == "build_invoice" for h in c1["hits"]))

            # 2-hop impact analysis: compute_tax -> build_invoice (hop 1) -> finalize_order (hop 2)
            imp = self.model.repo_symbol_graph_query(repo, kind="impact_of", query="compute_tax")
            self.assertTrue(imp["pass"])
            syms_by_hop = {(h["src_symbol"], h["hop"]) for h in imp["hits"]}
            self.assertIn(("build_invoice", 1), syms_by_hop)
            self.assertIn(("finalize_order", 2), syms_by_hop)

            # Fuzzy FTS5 symbol search + outline
            fz = self.model.repo_symbol_graph_query(repo, kind="fuzzy_search", query="regional VAT")
            self.assertTrue(fz["pass"])
            self.assertEqual(fz["hits"][0]["name"], "compute_tax")
            out = self.model.repo_symbol_graph_query(repo, kind="outline", target_path="billing.py")
            self.assertTrue(out["pass"])
            self.assertEqual(out["hits"][0]["name"], "build_invoice")

            # Modify 1 file -> incremental update must reparse ONLY 1 file!
            time.sleep(0.02)
            (repo / "core.py").write_text(
                "def compute_tax(amount):\n"
                '    """Calculate regional VAT tax updated."""\n'
                "    return amount * 0.20\n\n"
                "def compute_discount(amount):\n"
                "    return amount * 0.05\n",
                encoding="utf-8",
            )
            d2 = self.model.repo_symbol_graph_query(repo, kind="find_definition", query="compute_discount")
            self.assertTrue(d2["pass"])
            self.assertEqual(d2["index_stats"]["files_reparsed_this_call"], 1)

    # ------------------------------------------------------------------ Wave 27
    def test_wave27_contrast_carrying_memory_anti_catastrophic_remembering(self) -> None:
        # Two distinct state classes with different effects -> non-empty contrast set!
        obs = [
            {"atom": "open_door", "before": [["key", "red"]], "after": [["door", "open"]], "added": [["door", "open"]], "deleted": []},
            {"atom": "open_door", "before": [["key", "red"]], "after": [["door", "open"]], "added": [["door", "open"]], "deleted": []},
            {"atom": "open_door", "before": [["key", "blue"]], "after": [["door", "locked"]], "added": [["door", "locked"]], "deleted": []},
            {"atom": "open_door", "before": [["key", "blue"]], "after": [["door", "locked"]], "added": [["door", "locked"]], "deleted": []},
        ]
        res = self.model.contrast_memory_laws(
            observations=obs,
            domain="wave27_doors",
            query_atom="open_door",
            query_state=[["key", "red"]],
        )
        self.assertTrue(res["pass"])
        cl = res["contrast_laws"]
        self.assertGreater(cl["justified_count"], 0)
        self.assertEqual(cl["prediction"]["status"], "PREDICTS")
        self.assertEqual(cl["prediction"]["effect"]["added"], [["door", "open"]])

        # Shifted student world where the contrasting context disappeared -> O(1) pruning!
        shifted_student = [
            {"atom": "open_door", "before": [["key", "red"]], "after": [["door", "open"]], "added": [["door", "open"]], "deleted": []},
            {"atom": "open_door", "before": [["key", "red"]], "after": [["door", "open"]], "added": [["door", "open"]], "deleted": []},
        ]
        pruned = self.model.contrast_memory_laws(
            observations=obs,
            student_observations=shifted_student,
            domain="wave27_doors_shifted",
            repro_mode="contrast",
        )
        self.assertTrue(pruned["pass"])
        self.assertGreater(pruned["contrast_laws"]["pruned_count"], 0)
        self.assertEqual(pruned["contrast_laws"]["surviving_count"], 0)

        # Negative control: uniform observations with ZERO contrast are refused as ungrounded
        uniform_obs = [
            {"atom": "noop", "before": [["x", 1]], "after": [["x", 1]], "added": [], "deleted": []},
            {"atom": "noop", "before": [["x", 1]], "after": [["x", 1]], "added": [], "deleted": []},
        ]
        neg = self.model.contrast_memory_laws(observations=uniform_obs, domain="wave27_zero_contrast")
        self.assertFalse(neg["pass"])
        self.assertEqual(neg["contrast_laws"]["justified_count"], 0)

    def test_wave27_filing_key_alpha_unwelding_agenther_hindsight_and_jitrl(self) -> None:
        res = self.model.filing_key_hindsight_jitrl(
            feature_keys={"kind_a": "k_sort", "kind_b": "k_sort", "kind_c": "k_parse"},
            winners_by_kind={"kind_a": ["p1"], "kind_b": ["p2"], "kind_c": ["p3"]},
            alpha_example_before="def f(a, hi):\n    if a <= hi:\n        return a\n",
            alpha_example_after="def f(a, hi):\n    if a < hi:\n        return a\n",
            alpha_target="def clamp_check(val, limit):\n    if val <= limit:\n        return val\n    return limit\n",
            failed_trace=[
                {"action": "prepare_staging", "state_before": "init", "state_after": "staged"},
                {"action": "run_smoke_tests", "state_before": "staged", "state_after": "staging_verified"},
            ],
            failed_plan=["prepare_staging", "run_smoke_tests"],
            nominal_goal="deploy_production",
            achieved_goal="staging_verified",
            env_kind="ci_pipeline",
            jitrl_filing_key="ci:staging_verified",
            jitrl_observations=[
                {"action": "run_smoke_tests", "reward": 1.0},
                {"action": "run_smoke_tests", "reward": 0.9},
                {"action": "blind_retry", "reward": 0.0},
                {"action": "blind_retry", "reward": 0.1},
            ],
            jitrl_beta=2.0,
        )
        self.assertTrue(res["pass"])
        hj = res["hindsight_jitrl"]
        # 1. Filing key collision detected (`kind_a` vs `kind_b` collide under `k_sort`)
        self.assertEqual(hj["filing_key_audit"]["collisions"], 1)
        # 2. Operand-unwelded alpha-safe transfer rewrote `val <= limit` -> `val < limit`!
        self.assertTrue(hj["alpha_unwelded_rewrite"]["transferred"])
        self.assertIn("val < limit", hj["alpha_unwelded_rewrite"]["rewritten_source"])
        # 3. AgentHER hindsight relabeling crystallized achieved goal into Tier-0 memory!
        fk = hj["hindsight_lifted_skill"]["filing_key"]
        self.assertEqual(hj["hindsight_lifted_skill"]["relabelled_achieved_goal"], "staging_verified")
        tier0_hits = self.model.memory_bus.lookup_tier0_skills(fk)
        self.assertGreater(len(tier0_hits), 0)
        # 4. JitRL closed-form advantage ranks `run_smoke_tests` above `blind_retry`
        self.assertEqual(hj["jitrl_policy"]["best_action"], "run_smoke_tests")
        adv_map = {r["action"]: r for r in hj["jitrl_policy"]["action_advantages"]}
        self.assertGreater(adv_map["run_smoke_tests"]["logit_shift"], 0.0)
        self.assertLess(adv_map["blind_retry"]["logit_shift"], 0.0)

    # ------------------------------------------------------------------ Wave 28
    def test_wave28_producer_lineage_name_hole_and_constant_hole_inversion(self) -> None:
        # 1. Name Hole: returns `subtotal + discount` instead of `subtotal + tax`
        buggy_name = (
            "def compute_total(subtotal, tax):\n"
            "    discount = 0\n"
            "    return subtotal + discount\n"
        )
        test_name = (
            "assert compute_total(100, 15) == 115\n"
            "assert compute_total(200, 20) == 220\n"
        )
        r_name = self.model.solve_producer_lineage_holes(
            source=buggy_name,
            test_source=test_name,
            entry_func="compute_total",
            filename="invoice.py",
        )
        self.assertTrue(r_name["pass"], r_name)
        hi = r_name["hole_inversion"]
        self.assertTrue(hi["solved"])
        self.assertEqual(hi["hole_type"], "name_hole")
        self.assertEqual(hi["model_calls"], 0)
        self.assertIn("subtotal + tax", hi["repaired_source"])
        self.assertIsNotNone(hi["static_lineage_summary"])
        self.assertIn("compute_total", hi["static_lineage_summary"]["functions"])

        # 2. Constant Hole: subtracts 15 instead of 10
        buggy_const = (
            "def discount_price(price):\n"
            "    if price >= 100:\n"
            "        return price - 15\n"
            "    return price\n"
        )
        test_const = (
            "assert discount_price(100) == 90\n"
            "assert discount_price(200) == 190\n"
            "assert discount_price(50) == 50\n"
        )
        r_const = self.model.solve_producer_lineage_holes(
            source=buggy_const,
            test_source=test_const,
            entry_func="discount_price",
            filename="pricing.py",
        )
        self.assertTrue(r_const["pass"], r_const)
        self.assertEqual(r_const["hole_inversion"]["hole_type"], "constant_hole")
        self.assertIn("price - 10", r_const["hole_inversion"]["repaired_source"])

        # 3. Negative control: baseline already green fails closed
        r_green = self.model.solve_producer_lineage_holes(
            source="def ok(x):\n    return x + 1\n",
            test_source="assert ok(2) == 3\n",
            entry_func="ok",
        )
        self.assertFalse(r_green["pass"])
        self.assertEqual(r_green["hole_inversion"]["status"], "FAIL_CLOSED__BASELINE_ALREADY_GREEN")

    def test_wave28_causal_read_set_and_trace_abduction_repair(self) -> None:
        # Trace abduction / angelic expression synthesis on a wrong return expression
        buggy_expr = (
            "def linear_score(x, y):\n"
            "    return x\n"
        )
        test_expr = (
            "assert linear_score(2, 3) == 5\n"
            "assert linear_score(10, 7) == 17\n"
            "assert linear_score(0, 4) == 4\n"
        )
        res = self.model.solve_producer_lineage_holes(
            source=buggy_expr,
            test_source=test_expr,
            entry_func="linear_score",
            command_for_read_set="python3 tool.py config.json data.csv",
            file_state_bytes={"config.json": b"{}", "data.csv": b"a,b\n", "unused.txt": b"x"},
        )
        self.assertTrue(res["pass"], res)
        hi = res["hole_inversion"]
        self.assertTrue(hi["solved"])
        self.assertIn("config.json", hi["causal_read_set"])
        self.assertIn("data.csv", hi["causal_read_set"])
        self.assertNotIn("unused.txt", hi["causal_read_set"])

    # ------------------------------------------------------------------ Wave 29
    def test_wave29_verifier_pinning_catches_unpinned_hunk_and_docstring_oracle(self) -> None:
        before_src = (
            "def canonicalize_name(name):\n"
            "    return name.strip().lower().replace('_', '-')\n\n"
            "def is_normalized_name(name):\n"
            '    """Return True iff canonicalize_name leaves name unchanged."""\n'
            "    return False\n"
        )
        clean_after = (
            "def canonicalize_name(name):\n"
            "    return name.strip().lower().replace('_', '-')\n\n"
            "def is_normalized_name(name):\n"
            '    """Return True iff canonicalize_name leaves name unchanged."""\n'
            "    return name == canonicalize_name(name)\n"
        )
        bloated_after = (
            "def untested_dead_helper(z):\n"
            "    return z * 999\n\n"
            + clean_after
        )

        def _verifier(src_text: str) -> bool:
            ns: dict = {}
            try:
                exec(compile(src_text, "<v>", "exec"), ns)
                return bool(ns["is_normalized_name"]("foo-bar") is True and ns["is_normalized_name"]("Foo_Bar") is False)
            except Exception:
                return False

        # 1. Clean 1-hunk fix -> pin_ratio == 1.0 + docstring roundtrip oracle holds + green assertions synthesized!
        good = self.model.audit_verifier_pinning_and_oracles(
            before_source=before_src,
            after_source=clean_after,
            verifier_fn=_verifier,
            min_pin_ratio=1.0,
            docstring_source=clean_after,
            docstring_probe_inputs=["Foo_Bar", "  Alpha_Beta  ", "clean-name"],
            green_suite_source=clean_after,
            green_suite_entry="canonicalize_name",
            green_suite_inputs=[("Foo_Bar",), ("  A_B ",)],
        )
        self.assertTrue(good["pass"], good)
        po = good["pinning_oracles"]
        self.assertEqual(po["verifier_pinning"]["pin_ratio"], 1.0)
        self.assertEqual(po["verifier_pinning"]["pinned_hunks"], 1)
        self.assertGreater(len(po["docstring_oracles"]["claims_extracted"]), 0)
        self.assertTrue(po["docstring_oracles"]["all_probed_claims_hold"])
        self.assertEqual(po["green_suite_oracle"]["synthesized_assertion_count"], 2)

        # 2. Anti-reward-hacking negative control: unpinned dead hunk caught and REJECTED under min_pin_ratio=1.0!
        bad = self.model.audit_verifier_pinning_and_oracles(
            before_source=before_src,
            after_source=bloated_after,
            verifier_fn=_verifier,
            min_pin_ratio=1.0,
        )
        self.assertFalse(bad["pass"])
        vp_bad = bad["pinning_oracles"]["verifier_pinning"]
        self.assertEqual(vp_bad["behavioural_hunks"], 2)
        self.assertEqual(vp_bad["pinned_hunks"], 1)
        self.assertEqual(vp_bad["unpinned_hunks"], 1)
        self.assertAlmostEqual(vp_bad["pin_ratio"], 0.5)

    def test_wave29_creature_red_queen_hunk_pinning_integration(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wave29_creature_") as td:
            creature = self.model.open_creature(Path(td), identity="wave29_rq", life=40.0)
            incumbent = "def clamp_pos(x):\n    return x\n"
            clean_cand = (
                "def clamp_pos(x):\n"
                "    return 0 if (isinstance(x, (int, float)) and not isinstance(x, bool) and x < 0) else x\n"
            )
            res = creature.sleep_red_queen_coevolve(
                epoch_index=1,
                organ_name="clamp_pos",
                incumbent_source=incumbent,
                candidate_sources=[clean_cand],
                func_name="clamp_pos",
                test_cases=[((-5,), 0), ((-1,), 0), ((0,), 0), ((4,), 4), ((9,), 9)],
                anchor_cases=[((3,), 3), ((7,), 7)],
                mine_rewrite_laws=False,
                audit_hunk_pinning=True,
            )
            self.assertTrue(res["pass"], res)
            self.assertIsNotNone(res["hunk_pinning_audit"])
            self.assertTrue(res["hunk_pinning_audit"]["pass"])
            self.assertEqual(res["hunk_pinning_audit"]["verifier_pinning"]["pin_ratio"], 1.0)

    # ------------------------------------------------------------------ Wave 30
    def test_wave30_purpose_gate_and_economic_cost_arbitrage(self) -> None:
        # 1. Equivalent candidates on all real traces -> NO_QUESTION (zero wasted user turns!)
        same_cands = [
            ("keep positive", lambda tr: tr["x"] > 0),
            ("strictly above zero", lambda tr: tr["x"] >= 1),
        ]
        traces_agree = [{"x": 1}, {"x": 2}, {"x": -1}]
        r_noq = self.model.purpose_gate_and_cost_arbitrage(
            instruction="filter records",
            candidates=same_cands,
            traces=traces_agree,
            boundary_survivors=[["has_read", "is_file"], ["has_read"]],
            current_facts=["has_read", "is_file"],
        )
        self.assertTrue(r_noq["pass"])
        ai_noq = r_noq["active_inference"]
        self.assertEqual(ai_noq["purpose_gate"]["action"], "NO_QUESTION")
        # Both survivors satisfied -> decided with ZERO trial cost!
        self.assertTrue(ai_noq["cost_arbitrage"]["is_decided_without_trial"])
        self.assertEqual(ai_noq["cost_arbitrage"]["recommended_mode"], "ACT_DECIDED_NO_TRIAL_NEEDED")
        self.assertEqual(ai_noq["cost_arbitrage"]["expected_cost"], 0.0)

        # 2. Separating trace exists -> ASK -> then verify cryptographically bound authorized answer -> ACCEPTED!
        diff_cands = [
            ("allow zero", lambda tr: tr["x"] >= 0),
            ("strictly positive", lambda tr: tr["x"] > 0),
        ]
        traces_sep = [{"x": 1}, {"x": 0}, {"x": -1}]
        r_ask = self.model.purpose_gate_and_cost_arbitrage(
            instruction="filter numbers",
            candidates=diff_cands,
            traces=traces_sep,
            authorized_users=["alice"],
            boundary_survivors=[["has_write", "is_file"], ["has_read"]],
            current_facts=["has_read"],
            cow_trial_cost=0.05,
            ask_user_cost=5.0,
            guess_error_cost=10.0,
        )
        self.assertTrue(r_ask["pass"])
        pg_ask = r_ask["active_inference"]["purpose_gate"]
        self.assertEqual(pg_ask["action"], "ASK_USER")
        self.assertEqual(pg_ask["gate"]["first_distinguishing_run"], 1)
        # Ambiguous state with cheap CoW trial chooses COW_COPY_TRIAL over asking or blind guessing!
        self.assertEqual(r_ask["active_inference"]["cost_arbitrage"]["recommended_mode"], "COW_COPY_TRIAL")

        chosen_opt = pg_ask["payload"]["options"][0]["candidate_id"]
        r_acc = self.model.purpose_gate_and_cost_arbitrage(
            instruction="filter numbers",
            candidates=diff_cands,
            traces=traces_sep,
            authorized_users=["alice"],
            purpose_answer={
                "author": "alice",
                "kind": "RESIDUAL_STATEMENT_CHOICE",
                "instruction_sha256": pg_ask["instruction_sha256"],
                "question_fingerprint": pg_ask["question_fingerprint"],
                "candidate_id": chosen_opt,
            },
        )
        self.assertTrue(r_acc["pass"])
        self.assertEqual(r_acc["active_inference"]["purpose_gate"]["action"], "ANSWER_ACCEPTED")
        self.assertEqual(r_acc["active_inference"]["purpose_gate"]["chosen_candidate_id"], chosen_opt)

    def test_wave30_two_move_compositional_plan_horizon_bridge_dag_and_osworld(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wave30_dag_") as td:
            ws = Path(td)
            (ws / "app.py").write_text("X = 1\n", encoding="utf-8")

            def _stage_solver(stage_name: str, idx: int) -> dict:
                (ws / "app.py").write_text(f"X = {idx + 2}\n", encoding="utf-8")
                return {"pass": True, "status": "PASS", "stage": stage_name}

            res = self.model.plan_two_move_horizon_cu(
                # World with 1 readable file: goal needs READABLE >= 1 AND REMOVED >= 1!
                # No single move achieves both (rm alone destroys the only readable file,
                # cp alone removes nothing) -> requires ["cp", "rm"] in that exact order!
                two_move_start={"names": 1, "readable": 1, "contents": 1, "removed": 0},
                two_move_goal={"at_least": {"READABLE": 1, "REMOVED": 1}, "desc": "copy then remove"},
                two_move_moves=[
                    {"id": "cp", "tool": "cp", "signature": {"LOT": "RETAINED", "CARD": "INCREASED", "IDENT": "SAME"}},
                    {"id": "rm", "tool": "rm", "signature": {"LOT": "PARTIAL", "CARD": "DECREASED", "IDENT": "CHANGED"}},
                ],
                bridge_task_id="wave30_bridge_demo",
                bridge_goal=["artifact_ready"],
                bridge_constraints=[{"name": "no_secret_leak", "check": "secret_free", "must_hold_at": ("every_step",)}],
                bridge_subgoals=[
                    {
                        "subgoal_index": 0,
                        "description": "prepare workspace",
                        "precondition": [],
                        "postcondition": ["prepared"],
                        "step_budget": 3,
                        "constraint_names": ["no_secret_leak"],
                    },
                    {
                        "subgoal_index": 1,
                        "description": "emit artifact",
                        "precondition": ["prepared"],
                        "postcondition": ["artifact_ready"],
                        "step_budget": 3,
                        "constraint_names": ["no_secret_leak"],
                    },
                ],
                bridge_total_step_budget=10,
                bridge_initial_state={"init.txt": b"ok"},
                bridge_holdout_initial_states=[{"init.txt": b"alt_holdout_seed"}],
                dag_root=ws,
                dag_stages=["stage_a", "stage_b"],
                dag_stage_solver=_stage_solver,
                dag_scope_paths=["app.py"],
                osworld_state={"instruction": "Open settings", "history": []},
            )
            self.assertTrue(res["pass"], res)
            tm = res["two_move_cu"]["two_move_plan"]
            self.assertEqual(tm["one_move_answers"], [])
            self.assertTrue(tm["requires_multi_move"])
            self.assertEqual(tm["plan"], ["cp", "rm"])
            self.assertTrue(res["two_move_cu"]["horizon_bridge"]["pass"])
            self.assertIsNotNone(res["two_move_cu"]["goal_dag"])
            self.assertIsNotNone(res["two_move_cu"]["osworld_v21_decision"])

    def test_wave30_leapfrog_solve_auto_dispatch_all_waves_26_to_30(self) -> None:
        # Auto-dispatch Wave 26 symbol graph
        r26 = self.model.leapfrog_solve(
            "find UnifiedModel",
            mode="auto",
            inputs={"symgraph_root": str(ROOT / "intake"), "kind": "find_definition", "query": "decide"},
        )
        self.assertTrue(r26["pass"])
        self.assertEqual(r26["operation"], "REPO_SYMBOL_GRAPH_QUERY")

        # Auto-dispatch Wave 27 JitRL
        r27 = self.model.leapfrog_solve(
            "jitrl rank",
            mode="auto",
            inputs={"jitrl_filing_key": "auto_k", "jitrl_observations": [{"action": "a", "reward": 1.0}, {"action": "b", "reward": 0.0}]},
        )
        self.assertTrue(r27["pass"])
        self.assertEqual(r27["operation"], "FILING_KEY_HINDSIGHT_JITRL")

        # Auto-dispatch Wave 28 producer hole inversion
        r28 = self.model.leapfrog_solve(
            "fix constant hole",
            mode="auto",
            inputs={
                "source": "def add_five(x):\n    return x + 3\n",
                "test_source": "assert add_five(10) == 15\nassert add_five(0) == 5\n",
                "entry_func": "add_five",
            },
        )
        self.assertTrue(r28["pass"])
        self.assertEqual(r28["operation"], "PRODUCER_LINEAGE_HOLE_INVERSION")
        self.assertTrue(r28["hole_inversion"]["solved"])

        # Auto-dispatch Wave 29 docstring oracle
        r29 = self.model.leapfrog_solve(
            "audit docstring oracle",
            mode="auto",
            inputs={
                "docstring_source": (
                    "def norm_slug(s):\n    return s.lower()\n"
                    "def is_slug(s):\n"
                    '    """Return True iff s is unchanged by norm_slug."""\n'
                    "    return s == norm_slug(s)\n"
                ),
                "docstring_probe_inputs": ["Hello", "world"],
            },
        )
        self.assertTrue(r29["pass"])
        self.assertEqual(r29["operation"], "VERIFIER_PINNING_AND_ORACLES")

        # Auto-dispatch Wave 30 purpose gate & cost arbitrage
        r30 = self.model.leapfrog_solve(
            "decide trial vs ask",
            mode="auto",
            inputs={"boundary_survivors": [["a"], ["b"]], "current_facts": ["a"], "cow_trial_cost": 0.01, "ask_user_cost": 5.0},
        )
        self.assertTrue(r30["pass"])
        self.assertEqual(r30["operation"], "PURPOSE_GATE_AND_COST_ARBITRAGE")
        self.assertEqual(r30["active_inference"]["cost_arbitrage"]["recommended_mode"], "COW_COPY_TRIAL")


if __name__ == "__main__":
    unittest.main()
