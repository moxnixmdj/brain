#!/usr/bin/env python3
"""End-to-End Real-Execution Verification & Kill-Gate Suite for the 7-Move Frontier Leapfrog Plan.

Exercises all 7 Moves and newly federated hidden capabilities (`intake/*`, `execution_guard/*`,
`canonical/swe_kernel/*`, `canonical/tools/*`, `canonical/runtime/*`) directly through
`canonical.runtime.brain_unified_model_v1.open_model()` at `K3 = 0` (`model_calls == 0`, `$0` spend).
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import time
import unittest

from canonical.runtime import brain_unified_model_v1 as bum
from canonical.runtime import frontier_seven_moves_runtime_v1 as fsm


class SevenMovesFrontierMasterPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = bum.open_model()

    def test_move_1_trigram_bitset_search_impact_blast_radius_and_bloat_pareto(self) -> None:
        # Warm index once, then pin sub-millisecond search & <0.5ms depth-3 blast radius
        self.model.trigram_search("grader_may_retire", top_k=3)

        latencies = []
        for q in ("grader_may_retire", "simulate_ir_program", "synthesise_reader", "observed_domain"):
            res = self.model.trigram_search(q, top_k=5)
            self.assertGreaterEqual(res["hits_count"], 1, q)
            self.assertEqual(res["model_calls"], 0)
            latencies.append(float(res["elapsed_ms"]))
        latencies.sort()
        self.assertLess(latencies[len(latencies) // 2], 2.0, f"Expected <2ms median trigram search, got {latencies}")

        imp = self.model.impact_blast_radius("skill_contribution_ledger_v1", max_depth=3)
        self.assertGreaterEqual(imp["total_dependents"], 20)
        self.assertGreaterEqual(imp["impacted_tests_count"], 10)
        self.assertLess(imp["elapsed_ms"], 1.0)

        pareto = self.model.audit_bloat_pareto()
        self.assertGreater(pareto["unrouted_zero_importer_orphans"], 1000)
        self.assertGreater(pareto["superseded_clone_families"], 20)
        self.assertEqual(pareto["model_calls"], 0)

        # Verify `intake/` and `execution_guard/` are now indexed in UnifiedModel (`0` invisible leaders)
        ext = self.model.extended_source_index
        self.assertIn("intake/purpose_gate_v1.py", ext)
        self.assertIn("intake/authorized_answer_intake_v1.py", ext)
        self.assertIn("execution_guard/true_capability_harness_v1.py", ext)

        atlas = json.loads((bum.ROOT / "canonical/unified_model/DOMAIN_ATLAS_V1.json").read_text(encoding="utf-8"))
        for dom_name, dom_row in atlas["domains"].items():
            self.assertEqual(
                dom_row["invisible_to_model"],
                0,
                f"Expected 0 invisible modules in {dom_name}, got {dom_row['hidden_top']}",
            )

    def test_move_2_proof_mined_callability_clears_40pct_kill_floor_on_406_modules(self) -> None:
        surf = self.model.derive_and_verify_surface(workers=8)
        self.assertEqual(surf["attempted"], 406)
        self.assertGreaterEqual(surf["survivors"], 200)
        self.assertGreaterEqual(surf["survival_rate"], 0.40)
        self.assertEqual(surf["verdict"], "SURVIVES")
        self.assertEqual(surf["model_calls"], 0)

        # Pick a verified survivor and invoke it live through UnifiedModel
        sample = surf["sample_survivors"][0]
        inv = self.model.invoke_mined_surface(sample["module"])
        self.assertTrue(inv["pass"], inv)
        self.assertEqual(inv["model_calls"], 0)

    def test_move_3_speculative_multiverse_tier0_mental_model_and_emc_nogoods(self) -> None:
        base_src = "def compute_discount(price):\n    return price - 10\n"
        cands: list[tuple[str, str]] = [
            ("bad_syntax", "def compute_discount(price):\n    return (\n"),
            ("inf_loop", "def compute_discount(price):\n    while price >= 0:\n        pass\n    return 0\n"),
        ]
        # 55 isomorphic wrong candidates sharing behavioral conflict signatures -> pruned in O(1) by EMC nogoods!
        for i in range(55):
            cands.append((f"wrong_clone_{i}", f"def compute_discount(price):\n    x_{i} = price\n    return x_{i} - 10\n"))
        cands.append(("exact_winner", "def compute_discount(price):\n    return max(0, price - 10)\n"))

        with tempfile.TemporaryDirectory(prefix="pb_mv3_") as ws_dir:
            ws = pathlib.Path(ws_dir)
            (ws / "pricing.py").write_text(base_src, encoding="utf-8")
            res = self.model.speculate_multiverse(
                base_source=base_src,
                func_name="compute_discount",
                candidate_sources=cands,
                probe_inputs=[(5,), (25,), (0,)],
                postcondition=lambda inp, out: out == max(0, inp[0] - 10),
                workspace_dir=ws,
                target_rel_file="pricing.py",
            )
            self.assertTrue(res["pass"], res)
            self.assertGreaterEqual(res["tier0_nogood_emc_pruned"], 50)
            self.assertEqual(res["tier1_cow_evaluated"], 1)
            self.assertGreaterEqual(res["candidates_per_sec"], 500.0)
            self.assertIn("max(0, price - 10)", (ws / "pricing.py").read_text(encoding="utf-8"))

    def test_move_4_swe_breaks_no_traceback_insertion_inverse_and_sobeq_loop_walls(self) -> None:
        # Case 1: Transitive zero-source-frame traceback (`test -> facade -> core/calc.py` not imported in test!)
        with tempfile.TemporaryDirectory(prefix="pb_mv4_notb_") as d1:
            r1 = pathlib.Path(d1)
            (r1 / "core").mkdir()
            (r1 / "core" / "__init__.py").write_text("", encoding="utf-8")
            (r1 / "core" / "calc.py").write_text(
                "def clamp_positive(val):\n    if val > 0:\n        return 0\n    return val\n",
                encoding="utf-8",
            )
            (r1 / "facade.py").write_text(
                "from core.calc import clamp_positive\ndef run_pipe(v):\n    return clamp_positive(v)\n",
                encoding="utf-8",
            )
            (r1 / "test_pipe.py").write_text(
                "from facade import run_pipe\n"
                "def test_clamp():\n"
                "    assert run_pipe(-4) == 0\n"
                "    assert run_pipe(7) == 7\n",
                encoding="utf-8",
            )
            out1 = self.model.solve_swe_repo(r1, test_file="test_pipe.py")
            self.assertTrue(out1["pass"], out1)
            self.assertEqual(out1["canonical_swe_spine"]["modified_files"], ["core/calc.py"])

        # Case 2: AST Precondition Guard Insertion (`NEW_GUARD` for `assertRaises(ValueError)`)
        with tempfile.TemporaryDirectory(prefix="pb_mv4_guard_") as d2:
            r2 = pathlib.Path(d2)
            (r2 / "wallet.py").write_text(
                "def deposit(amount):\n    return amount * 2\n",
                encoding="utf-8",
            )
            (r2 / "test_wallet.py").write_text(
                "import unittest\nfrom wallet import deposit\n"
                "class WalletTests(unittest.TestCase):\n"
                "    def test_valid(self):\n"
                "        self.assertEqual(deposit(5), 10)\n"
                "        self.assertEqual(deposit(0), 0)\n"
                "    def test_reject_negative(self):\n"
                "        with self.assertRaises(ValueError):\n"
                "            deposit(-3)\n",
                encoding="utf-8",
            )
            out2 = self.model.solve_swe_repo(r2, test_file="test_wallet.py")
            self.assertTrue(out2["pass"], out2)
            self.assertIn("raise ValueError", (r2 / "wallet.py").read_text(encoding="utf-8"))

        # Case 3: Inverse-Pair Callable Completion (`NEW_CALLABLE` via `inverse_completion_v1`: `from_state(to_state(x))`)
        with tempfile.TemporaryDirectory(prefix="pb_mv4_inv_") as d3:
            r3 = pathlib.Path(d3)
            (r3 / "token_model.py").write_text(
                "class SessionToken:\n"
                "    def __init__(self, uid, role):\n"
                "        self.uid = uid\n"
                "        self.role = role\n"
                "    def __eq__(self, other):\n"
                "        return isinstance(other, SessionToken) and (self.uid, self.role) == (other.uid, other.role)\n"
                "    def to_state(self):\n"
                "        return {'uid': self.uid, 'role': self.role}\n",
                encoding="utf-8",
            )
            (r3 / "test_token.py").write_text(
                "from token_model import SessionToken\n"
                "def test_roundtrip():\n"
                "    t = SessionToken('u42', 'admin')\n"
                "    restored = SessionToken.from_state(t.to_state())\n"
                "    assert restored == t\n",
                encoding="utf-8",
            )
            out3 = self.model.solve_swe_repo(r3, test_file="test_token.py")
            self.assertTrue(out3["pass"], out3)
            self.assertIn("def from_state", (r3 / "token_model.py").read_text(encoding="utf-8"))

        # Case 4: SObEq Read-Without-Write Loop Progress Insertion (`visited.add(cur)`)
        with tempfile.TemporaryDirectory(prefix="pb_mv4_sobeq_") as d4:
            r4 = pathlib.Path(d4)
            (r4 / "graph_walk.py").write_text(
                "def reachable_nodes(adj, start):\n"
                "    visited = set()\n"
                "    stack = [start]\n"
                "    order = []\n"
                "    steps = 0\n"
                "    while stack and steps < 25:\n"
                "        steps += 1\n"
                "        cur = stack.pop()\n"
                "        if cur in visited:\n"
                "            continue\n"
                "        order.append(cur)\n"
                "        for nxt in adj.get(cur, ()):\n"
                "            stack.append(nxt)\n"
                "    return sorted(order)\n",
                encoding="utf-8",
            )
            (r4 / "test_graph.py").write_text(
                "from graph_walk import reachable_nodes\n"
                "def test_cycle():\n"
                "    g = {'a': ['b'], 'b': ['a', 'c'], 'c': []}\n"
                "    assert reachable_nodes(g, 'a') == ['a', 'b', 'c']\n",
                encoding="utf-8",
            )
            out4 = self.model.solve_swe_repo(r4, test_file="test_graph.py")
            self.assertTrue(out4["pass"], out4)
            self.assertIn("visited.add(cur)", (r4 / "graph_walk.py").read_text(encoding="utf-8"))
            self.assertIsNotNone(out4["canonical_swe_spine"]["version_space"])

    def test_move_5_zero_pixel_doors_first_and_executor_hidden_smc_commit(self) -> None:
        smc = fsm.SpeculativeMacroCommitEngine()
        steps = [
            {
                "op": "seed_config",
                "json_file": "cfg/app.json",
                "patch": {"mode": "production", "workers": 4},
            },
            {
                "op": "init_sqlite",
                "sqlite_db": "data/state.sqlite",
                "sql": "CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);",
            },
            {
                "op": "insert_sqlite",
                "sqlite_db": "data/state.sqlite",
                "sql": "INSERT OR REPLACE INTO kv VALUES (?, ?);",
                "params": ["ready", "true"],
            },
            {
                "op": "introspect_cli",
                "introspect_program": "gzip",
            },
        ]
        cap_count_before = len(self.model.capabilities)
        with tempfile.TemporaryDirectory(prefix="pb_mv5_") as td:
            ws1 = pathlib.Path(td) / "run1"
            r1 = self.model.execute_doors_first(ws1, steps, smc_engine=smc)
            self.assertTrue(r1["pass"], r1)
            self.assertEqual(r1["mode"], "STEP_BY_STEP_DOORS_FIRST")
            self.assertEqual(r1["screenshots_captured"], 0)
            self.assertIsNotNone(r1["learned_hidden_macro_id"])
            # Hidden SMC law: macro MUST NOT pollute top-level model capabilities!
            self.assertEqual(len(self.model.capabilities), cap_count_before)

            # Replay on fresh workspace -> commits entire 4-step macro in one verified shot!
            ws2 = pathlib.Path(td) / "run2"
            r2 = self.model.execute_doors_first(ws2, steps, smc_engine=smc)
            self.assertTrue(r2["pass"], r2)
            self.assertEqual(r2["mode"], "SPECULATIVE_MACRO_COMMIT")
            self.assertEqual(r2["macro_commit"]["steps_committed"], 4)
            self.assertEqual(json.loads((ws2 / "cfg/app.json").read_text())["workers"], 4)

            # Violated anchor guard -> SMC cleanly aborts with 0 corruption and falls back to Doors-First!
            ws3 = pathlib.Path(td) / "run3"
            r3 = self.model.execute_doors_first(
                ws3,
                steps,
                smc_engine=smc,
                require_guard_file="must_exist.lock",
            )
            self.assertTrue(r3["pass"], r3)
            self.assertEqual(r3["mode"], "STEP_BY_STEP_DOORS_FIRST")
            self.assertEqual(r3["smc_fallback_reason"], "ANCHOR_PRECONDITION_MISMATCH")

    def test_move_6_blind_curator_immune_continual_memory_dbsp_and_estitch(self) -> None:
        t0 = time.perf_counter()
        res = self.model.continual_memory_cycle(active_cap=32, num_adversarial_mutants=160)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(res["pass"], res)
        self.assertEqual(res["forget_eval_deletion_accuracy"], 1.0)
        self.assertEqual(res["forget_eval_residual_hits"], 0)
        self.assertEqual(res["stale_rule_regression_hits"], 0)
        self.assertEqual(res["blind_grader_curation"]["action"], "REFUSED")
        self.assertEqual(res["unblind_grader_curation"]["action"], "CURATED")
        self.assertEqual(res["unblind_grader_curation"]["retired_drifted_count"], 4)
        self.assertLessEqual(res["unblind_grader_curation"]["active_after"], 32)
        self.assertLess(res["oracle_certification"]["synthesized_grader"]["clopper_pearson_95_ub"], 0.02)
        self.assertTrue(res["estitch_sleep_compression"]["admitted"])
        self.assertLess(elapsed_ms, 1000.0)

    def test_move_7_global_extrapolation_blocker_and_minimum_probe_global_optimum(self) -> None:
        obs = [(0, 0), (1, 1), (2, 2)]
        hyps = {
            "local_linear": lambda x: x,
            "local_abs": lambda x: abs(x),
            "slow_local_relu": lambda x: max(0, x),
            "fast_10x_global_relu": lambda x: max(0, x),
        }
        costs = {
            "local_linear": 1.0,
            "local_abs": 1.0,
            "slow_local_relu": 10.0,
            "fast_10x_global_relu": 1.0,
        }

        # 1. Without probing outside [0, 2], UnifiedModel MUST block premature local extrapolation!
        blocked = self.model.evaluate_global_extrapolation(
            observed_points=obs,
            candidate_hypotheses=hyps,
            target_query_x=-5,
            probe_domain=[-3, -1, 0, 1, 2],
            world_oracle=None,
        )
        self.assertTrue(blocked["local_extrapolation_blocked"])
        self.assertEqual(blocked["status"], "LOCAL_EXTRAPOLATION_UNDERDETERMINED")
        self.assertEqual(blocked["purpose_gate_action"], "ASK_USER")

        # 2. With world probing enabled, discovers exact truth & 10x cheaper global route in <= 2 probes!
        solved = self.model.evaluate_global_extrapolation(
            observed_points=obs,
            candidate_hypotheses=hyps,
            target_query_x=-5,
            probe_domain=[-3, -1, 0, 1, 2],
            world_oracle=lambda x: max(0, x),
            route_costs=costs,
            max_probes=3,
        )
        self.assertEqual(solved["status"], "IDENTIFIED_GLOBAL_OPTIMUM")
        self.assertLessEqual(solved["probes_count"], 2)
        self.assertEqual(solved["selected_hypothesis"], "fast_10x_global_relu")
        self.assertEqual(solved["predicted_value"], 0)

    def test_federated_hidden_organs_and_cold_boot_speed_gate(self) -> None:
        # Cold open_model() p50 latency gate
        samples = []
        for _ in range(7):
            t0 = time.perf_counter()
            bum.open_model()
            samples.append((time.perf_counter() - t0) * 1000.0)
        samples.sort()
        self.assertLessEqual(samples[len(samples) // 2], 5.0, f"open_model p50={samples}")

        # Verify all 8 newly promoted hidden capability descriptors execute cleanly via UnifiedModel
        cases = [
            ("EXECUTABLE_RAM_MENTAL_MODEL", {"source": "def inc(x):\n    return x + 1\n", "func_name": "inc", "args": [41]}),
            ("INVERSE_PAIR_COMPLETION", {"name": "__getstate__", "writer_payloads": [{"a": 1, "b": 2}]}),
            ("REPAIR_VERSION_SPACE_DISCRIMINATOR", {}),
            ("DISTINGUISHING_PROJECTION_ORACLE", {"num_adversarial_mutants": 155}),
            ("SKILL_CONTRIBUTION_UNBLIND_CURATOR", {}),
            ("DOMAIN_OF_VERIFICATION_GATE", {"points": [([0], 0), ([2], 2)], "query_x": -4}),
            ("PURPOSE_CONTRAST_GATE", {"instruction": "normalize(-3)"}),
        ]
        for mode, inp in cases:
            out = self.model.run_federated_engine(mode, inp)
            self.assertTrue(out["pass"], f"{mode} failed: {out}")

        # Verify `invoke_frontier_organ` exposes all new Move organs while preserving exact 8 + 13 = 21 baseline counts
        organs = self.model.frontier_organs()
        self.assertEqual(organs["leapfrog_plays_count"], 8)
        self.assertEqual(organs["swe_kernel_organs_count"], 13)
        self.assertEqual(organs["total_organs"], 21)
        self.assertGreaterEqual(organs["leapfrog_moves_count"], 11)
        mv1 = self.model.invoke_frontier_organ("move_1_trigram_impact_pareto", {"target": "skill_contribution_ledger_v1"})
        self.assertGreaterEqual(mv1["total_dependents"], 20)


if __name__ == "__main__":
    unittest.main()
