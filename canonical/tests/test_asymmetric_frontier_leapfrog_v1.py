#!/usr/bin/env python3
"""End-to-end verification suite for the Asymmetric Frontier-Leapfrog Spine (7 Pillars, K3=0)."""
from __future__ import annotations

import fractions
import pathlib
import tempfile
import time
import unittest

from canonical.runtime import asymmetric_frontier_leapfrog_v1 as afl
from canonical.runtime import brain_unified_model_v1 as bum
from canonical.runtime import browser_v1
from canonical.runtime import creature_runtime_v1 as cr
from canonical.runtime import osworld_v21_browser_cdp_v1 as cdp
from canonical.runtime.bound_capabilities import python_iterative_software_repair_loop_v1 as repair_loop

ROOT = pathlib.Path(__file__).resolve().parents[2]


class _KeyDoorUnknownGridEnv:
    """Undocumented 2D grid world: 0=floor, 1=avatar, 2=wall, 3=key, 4=locked_door, 5=goal."""

    def __init__(self) -> None:
        self.has_key = False
        self.grid: list[list[int]] = []
        self.reset()

    def reset(self) -> list[list[int]]:
        self.has_key = False
        self.grid = [
            [2, 2, 2, 2, 2, 2],
            [2, 1, 0, 3, 2, 2],
            [2, 0, 2, 2, 2, 2],
            [2, 4, 0, 0, 5, 2],
            [2, 2, 2, 2, 2, 2],
        ]
        return [list(r) for r in self.grid]

    def step(self, action: str) -> tuple[list[list[int]], bool]:
        dr, dc = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}[action]
        r, c = next((r, c) for r in range(5) for c in range(6) if self.grid[r][c] == 1)
        nr, nc = r + dr, c + dc
        cell = self.grid[nr][nc]
        if cell == 2 or (cell == 4 and not self.has_key):
            return [list(row) for row in self.grid], False
        if cell == 3:
            self.has_key = True
        done = cell == 5
        self.grid[r][c] = 0
        self.grid[nr][nc] = 1
        return [list(row) for row in self.grid], done


class TestAsymmetricFrontierLeapfrogV1(unittest.TestCase):
    def test_01_elon_law_speed_and_lazy_unified_model_invariants(self) -> None:
        bum.open_model()  # ensure disk marshal sidecars warm
        bum._OPEN_MODEL_MEM_CACHE.clear()
        t0 = time.perf_counter()
        m = bum.open_model()
        dt_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(dt_ms, 5.0, f"Warm open_model() regressed to {dt_ms:.3f} ms")
        self.assertIsNone(m._capabilities_dict)
        self.assertIsNone(m._raw_bytes_backing)
        bum_lines = len((ROOT / "canonical/runtime/brain_unified_model_v1.py").read_text().splitlines())
        self.assertLess(bum_lines, 7534, f"Elon Law violated: brain_unified_model_v1.py grew to {bum_lines} lines")

    def test_02_wave1_repair_loop_score_refusal_and_name_scope_round_robin(self) -> None:
        # 1. Collection errors, wrapped pytest exit, and vacuous 0-test runs are refused (`None`), never scored 0 or 1!
        self.assertIsNone(repair_loop._score({"returncode": 2, "stdout": "ERROR collecting test_pkg.py\n", "stderr": ""}))
        self.assertIsNone(repair_loop._score({"returncode": 1, "stdout": "RuntimeError: PYTEST_EXECUTION_FAILED:4\n1 failed\n", "stderr": ""}))
        self.assertIsNone(repair_loop._score({"returncode": 0, "stdout": "no tests ran in 0.01s\n", "stderr": ""}))
        self.assertEqual(repair_loop._score({"returncode": 0, "stdout": "3 passed in 0.02s\n", "stderr": ""}), 0)

        # 2. Live `NAME_SCOPE` repair (`holder.bonus -> bonus`) via round-robin family scheduling!
        with tempfile.TemporaryDirectory() as td:
            repo = pathlib.Path(td)
            (repo / "calc.py").write_text(
                "class Holder:\n"
                "    def __init__(self):\n"
                "        self.bonus = 0\n\n"
                "def compute(holder, bonus):\n"
                "    x = 1 + 2 + 3 + 4 + 5\n"
                "    return x + holder.bonus\n",
                encoding="utf-8",
            )
            (repo / "test_calc.py").write_text(
                "import unittest\n"
                "from calc import Holder, compute\n"
                "class T(unittest.TestCase):\n"
                "    def test_scope(self):\n"
                "        self.assertEqual(compute(Holder(), 7), 22)\n"
                "        self.assertEqual(compute(Holder(), 11), 26)\n"
                "if __name__ == '__main__':\n"
                "    unittest.main()\n",
                encoding="utf-8",
            )
            out = repair_loop.run(
                {
                    "source_root": ".",
                    "test_paths": ["test_calc.py"],
                    "output_path": "report.json",
                    "max_candidates_per_file": 25,
                },
                repo,
            )
            self.assertTrue(str(out["status"]).startswith("PASS"))
            self.assertEqual(out["accepted_edits"][0]["mutation"]["family"], "name_scope")

    def test_03_pillar1_abductive_refusal_contract_autobinder(self) -> None:
        m = bum.open_model()
        cli_res = m.solve(
            "sign digest",
            mode="REFUSAL_AUTOBIND",
            inputs={
                "cli_argv": ["openssl", "rmd160", "-out=out.bin"],
                "cli_refusal_text": "No signature to verify: use the -signature option",
            },
        )
        self.assertTrue(cli_res["pass"])
        self.assertIn("-signature", cli_res["epistemic_result"]["cli_contract"]["repaired_argv"])

        py_res = m.abductive_refusal_autobind(
            "compute order total",
            source_text=(
                "def calc_order(payload, factor):\n"
                "    if factor <= 2:\n"
                "        raise ValueError('factor must be > 2')\n"
                "    return (payload['subtotal'] + 5) * factor\n"
            ),
            fn_name="calc_order",
        )
        self.assertTrue(py_res["pass"])
        self.assertGreater(py_res["mutant_sensitivity"]["mutants_killed"], 0)
        self.assertEqual(py_res["model_calls"], 0)

    def test_04_pillar2_angelic_zygote_concolic_version_space_swe(self) -> None:
        m = bum.open_model()
        buggy = (
            "def clamp_positive(val):\n"
            "    if val < 1:\n"
            "        return 0\n"
            "    return val\n"
        )
        res = m.solve(
            "fix boundary off-by-one in clamp_positive",
            mode="ANGELIC_ZYGOTE_SWE",
            inputs={
                "source_text": buggy,
                "fn_name": "clamp_positive",
                "visible_tests": [((5,), 5), ((-4,), 0)],
                "oracle_predicate": lambda args, out: out == max(0, args[0]),
            },
        )
        self.assertTrue(res["pass"])
        ep = res["epistemic_result"]
        self.assertGreaterEqual(ep["overfit_candidates_pruned"], 1)
        self.assertIsNotNone(ep["distinguishing_witness"])
        fed = m.run_federated_engine(
            "ANGELIC_ZYGOTE_VERSION_SPACE_SWE",
            {"source_text": buggy, "fn_name": "clamp_positive", "visible_tests": [((5,), 5), ((-4,), 0)]},
        )
        self.assertTrue(fed["pass"])

    def test_05_wave3_browser_loopback_cdp_and_zero_pixel_shadow_transducer(self) -> None:
        self.assertTrue(browser_v1._is_local("http://127.0.0.1:8000/index.html"))
        self.assertTrue(browser_v1._is_local("http://localhost:3000/app"))
        self.assertTrue(browser_v1._is_local("http://todomvc.local/"))
        self.assertFalse(browser_v1._is_local("https://example.com/"))
        self.assertIn("textbox", cdp.TEXT_ROLES)

        m = bum.open_model()
        res = m.shadow_transducer_cu(
            'add "ship leapfrog" and mark complete then click Completed',
            dom_snapshot={
                "pages": [
                    {
                        "elements": [
                            {"tag": "input", "role": "textbox", "aria_name": "What needs to be done?"},
                            {"tag": "a", "role": "link", "aria_name": "Completed", "text": "Completed"},
                        ],
                        "rows": [{"text": "ship leapfrog", "control_role": "checkbox", "control_checked": False}],
                    }
                ]
            },
            trace_1=[
                {"layer": "GUI", "cmd": "hover_header"},
                {"layer": "CLI", "cmd": "echo done > state.txt"},
            ],
            outcome_oracle=lambda steps: any("state.txt" in str(s.get("cmd", "")) for s in steps),
            petri_edges=[("start", "gate"), ("gate", "b1"), ("gate", "b2"), ("b1", "done"), ("b2", "done")],
            start_node="start",
            goal_node="done",
            mealy_oracle=lambda seq: ["LOCKED" if a != "AUTH" else "OPEN" for a in seq],
            mealy_alphabet=["AUTH", "ACT"],
        )
        self.assertTrue(res["pass"])
        self.assertEqual(res["pixels_read"], 0)
        op_types = [op["type"] for op in res["declarative_cdp_ops"]]
        self.assertEqual(op_types, ["FILL_NAME", "PRESS_NAME", "CHECK_IN_ROW", "CLICK_NAME"])
        self.assertIn("gate", res["petri_dominator_checkpoints"]["cut_vertices"])
        self.assertTrue(res["lsharp_mealy_transducer"]["pass"])

    def test_06_pillar4_opine_twin_unknown_game_and_arc_nest_estitch(self) -> None:
        m = bum.open_model()
        game_res = m.digital_twin_arc_solve(interactive_env=_KeyDoorUnknownGridEnv(), max_steps=40)
        self.assertTrue(game_res["pass"])
        self.assertTrue(game_res["replay_verified_100pct"])
        self.assertLessEqual(game_res["steps_taken"], 20)
        self.assertEqual(game_res["learned_color_ontology"][4], "LOCKED_DOOR")
        self.assertEqual(game_res["learned_color_ontology"][3], "PICKUP")
        self.assertEqual(game_res["learned_color_ontology"][5], "GOAL")

        arc_res = m.digital_twin_arc_solve(
            arc_train_pairs=[
                ([[1, 2], [0, 3]], [[0, 1], [3, 2]]),
                ([[4, 0], [5, 6]], [[5, 4], [6, 0]]),
                ([[7, 8], [9, 0]], [[9, 7], [0, 8]]),
            ],
            arc_test_inputs=[[[2, 9], [4, 1]]],
            prior_program_exprs=["rot90(x)", "flip_h(rot90(x))"],
        )
        self.assertTrue(arc_res["pass"])
        self.assertEqual(arc_res["predictions"][0], [[4, 2], [1, 9]])
        self.assertEqual(arc_res["loo_cv_score"], 1.0)

    def test_07_pillar5_exact_rational_sheaf_h1_srmu_and_dual_nnf_semiring(self) -> None:
        # 12-hop multiplicative cycle with 2^-45 discrepancy: float64 rounding misses tiny rational drift,
        # whereas exact Q cellular sheaf RREF catches 100% of cyclic contradictions!
        fw = afl.ExactRationalSheafFirewall()
        for idx in range(12):
            r = fw.admit_constraint(u=f"n{idx}", v=f"n{idx + 1}", alpha=2, beta=0)
            self.assertTrue(r["admitted"])
        # Pin n0 = 1 so nontrivial section is forced, then close loop n12 = (2^12 + 2^-30) * n0 -> contradiction!
        self.assertTrue(fw.admit_constraint(u=None, v="n0", alpha=0, beta=1)["admitted"])
        bad = fw.admit_constraint(
            u="n0",
            v="n12",
            alpha=fractions.Fraction(1 << 12) + fractions.Fraction(1, 1 << 30),
            beta=0,
        )
        self.assertFalse(bad["admitted"])
        self.assertEqual(bad["status"], "QUARANTINED__SHEAF_H1_NONZERO_CONTRADICTION")
        self.assertGreaterEqual(bad["h1_obstruction_dim"], 1)

        m = bum.open_model()
        episodes = [
            {"key": "vault_policy", "text": "production database credentials rotate every twenty four hours"},
            {"key": "network_law", "text": "loopback local browser endpoints skip remote tls certificate pinning"},
        ] + [{"key": "dup", "text": "production database credentials rotate every twenty four hours"} for _ in range(30)]
        mem_res = m.non_malleable_memory_op(
            "SHEAF_SRMU_CYCLE",
            {
                "episodes": episodes,
                "query": "how often do production database credentials rotate",
                "base_facts": {"tests_green": 1, "tampered_harness": 1},
                "rules": [{"head": "admit_patch", "pos": ["tests_green", "mutant_killed"], "neg": ["tampered_harness"]}],
                "provenance_query": "admit_patch",
            },
        )
        self.assertTrue(mem_res["pass"])
        self.assertEqual(mem_res["stored_count"], 2)
        self.assertEqual(mem_res["suppressed_redundant_writes"], 30)
        self.assertEqual(mem_res["srmu_hits"][0]["key"], "vault_policy")
        self.assertEqual(
            mem_res["dual_nnf_provenance"]["why_absent_minimal_repairs"],
            [["blocked_by:tampered_harness"], ["missing:mutant_killed"]],
        )

    def test_08_pillars_6_and_7_creature_pc_dgm_supercompile_and_eggmind_prover(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            c = cr.Creature("leapfrog-agent", pathlib.Path(td), 10.0)
            c.boot()
            dgm = c.sleep_pc_dgm_supercompile(
                domain="numeric",
                fn_name="scaled_energy",
                incumbent_source='def scaled_energy(xs):\n    return sum([(x * 1 + 0) * CFG["gain"] for x in xs])',
                candidate_sources=[
                    "import subprocess\ndef scaled_energy(xs): return 0",
                    "def scaled_energy(xs):\n    xs.clear()\n    return 0",
                ],
                static_env={"CFG": {"gain": 4}},
                test_cases=[(([1, 2, 3],), 24), (([5],), 20)],
                rubin_rent_scores={"useful_organ": (0.95, 0.65), "negative_rent_organ": (0.60, 0.64)},
            )
            self.assertTrue(dgm["pass"])
            self.assertIn("x * 4", dgm["best_stepping_stone"]["source"])
            self.assertNotIn("[", dgm["best_stepping_stone"]["source"])  # ListComp deforested to GeneratorExp!
            self.assertEqual(len(dgm["rejected_candidates"]), 2)
            self.assertEqual(dgm["rubin_rent_evicted"], ["negative_rent_organ"])

            laws = [
                ("mul_one", "(mul ?x 1)", "?x"),
                ("add_zero", "(add ?x 0)", "?x"),
                ("comm_add", "(add ?x ?y)", "(add ?y ?x)"),
            ]
            sat = afl.EggMindProofSaturator()
            cold = sat.prove_egraph_equality("(add 0 (mul alpha 1))", "alpha", laws)
            warm = sat.prove_egraph_equality("(add 0 (mul beta 1))", "beta", laws)
            self.assertTrue(cold["proved"] and warm["proved"])
            self.assertLess(warm["rounds_used"], cold["rounds_used"])

            proof = c.route_goal_via_spine(
                "eggmind_proof",
                goal_tree={
                    "kind": "conj",
                    "subgoals": [
                        {"kind": "ring_eq", "lhs": "(a + b)**2 - (a - b)**2", "rhs": "4 * a * b"},
                        {
                            "kind": "linarith",
                            "hypotheses_le_zero": [{"x": 1, "_const": -3}, {"y": 1, "_const": -5}],
                            "negated_conclusion_le_zero": {"x": -1, "y": -1, "_const": 9},
                        },
                        {"kind": "egraph_eq", "lhs": "(add 0 (mul gamma 1))", "rhs": "gamma", "laws": laws},
                    ],
                },
                saturator=sat,
            )
            self.assertTrue(proof["pass"])

            disc = c.discover_dark_matter("cellular sheaf cohomology srmu opine digital twin eggmind")
            self.assertIn("engine:ALGEBRAIC_SHEAF_SRMU_MEMORY", disc["recommended_targets"])
            self.assertIn("engine:EPISTEMIC_DIGITAL_TWIN_AND_ARC", disc["recommended_targets"])


if __name__ == "__main__":
    unittest.main()
