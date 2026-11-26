"""End-to-end real-execution tests for Waves 15-20 Frontier-Leapfrog Unification.

Zero mocks of core engines: exercises real hidden engines wired directly into
UnifiedModel, Spines 0D-0I, and Creature at K3 = 0 ($0 spend) plus optional
pluggable residual-proposer screening.
"""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from canonical.runtime.brain_unified_model_v1 import open_model


class TestFrontierLeapfrogWaves15To20(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = open_model()

    def test_01_wave15_memguard_and_world_expiry_revocation(self) -> None:
        bus = self.model.memory_bus
        sk = bus.crystallize_action_macro(
            trigger_key="deploy_widget_alpha",
            actions=["run_deploy_widget_alpha --strict"],
            provenance_episode_id="EP_WAVE15_EXPIRY",
        )
        sid = sk.skill_id
        reg = self.model.memguard_audit_and_expire(
            action="register",
            skill_id=sid,
            reward=1.0,
            confidence=0.95,
        )
        self.assertTrue(reg["pass"])
        self.assertEqual(reg["memguard"]["descriptor"]["lifecycle_state"], "active")

        # Active skill is found by FTS5 recall
        before = bus.fts5_recall("deploy_widget_alpha", top_k=5)
        self.assertTrue(before["pass"])
        self.assertTrue(any(h["doc_id"] == sid for h in before["hits"]))

        # Simulate material world-fingerprint drift (e.g., Python minor & OS shift)
        taught_fp = dict(reg["memguard"]["descriptor"]["world_fingerprint"])
        drifted_fp = dict(taught_fp)
        drifted_fp["python_version"] = "3.99.0"
        drifted_fp["platform"] = "SimulatedDriftOS-99"

        audit = self.model.memguard_audit_and_expire(
            action="audit",
            current_fingerprint=drifted_fp,
            quarantine_on_drift=True,
        )
        self.assertTrue(audit["pass"])
        self.assertIn(sid, audit["memguard"]["expired_skills"])
        self.assertTrue(audit["memguard"]["material_differences"][sid])

        # Expired skill is suppressed from default FTS5 recall (Memory-Rebirth-Attack immune!)
        after = bus.fts5_recall("deploy_widget_alpha", top_k=5, include_quarantined=False)
        self.assertFalse(any(h["doc_id"] == sid for h in after["hits"]))
        self.assertGreaterEqual(after["suppressed_quarantined_or_expired"], 1)

    def test_02_wave15_anti_skill_pruning_and_proved_composition(self) -> None:
        rec = self.model.anti_skill_record(
            domain="swe_patch",
            symbol_scope="calc.py::clamp",
            bad_hypothesis="return x + 1",
            error_signature="AssertionError: clamp(10, 0, 5) == 11 != 5",
            csp_pair={"positive": "return min(hi, max(lo, x))", "negative": "return x + 1"},
        )
        self.assertTrue(rec["pass"])

        pruned = self.model.anti_skill_prune(
            ["return x + 1", "return min(hi, max(lo, x))", "return max(lo, x)"],
            domain="swe_patch",
            symbol_scope="calc.py::clamp",
        )
        self.assertTrue(pruned["pass"])
        self.assertEqual(pruned["pruning"]["pruned_count"], 1)
        self.assertNotIn("return x + 1", pruned["pruning"]["kept"])
        self.assertIn("return min(hi, max(lo, x))", pruned["pruning"]["kept"])

        # Proved composition succeeds on real Python AST edits when premises & proofs survive, fails closed otherwise
        comp_ok = self.model.prove_composition(
            initial_text="def f(x):\n    a = x + 1\n    b = a + 2\n    return b\n",
            operations=[
                {"name": "op1", "needle": "a = x + 1", "replacement": "a = x * 10"},
                {"name": "op2", "needle": "b = a + 2", "replacement": "b = a * 20"},
            ],
        )
        self.assertTrue(comp_ok["pass"], msg=f"Proved composition failed: {comp_ok}")
        self.assertIn("a = x * 10", comp_ok["composition"]["output_text"])
        self.assertIn("b = a * 20", comp_ok["composition"]["output_text"])

        comp_fail = self.model.prove_composition(
            initial_text="def f(x):\n    return x\n",
            operations=[
                {"name": "op1", "needle": "return x", "replacement": "return x + 1"},
                {"name": "op2", "needle": "MISSING_TOKEN", "replacement": "X"},
            ],
        )
        self.assertFalse(comp_fail["pass"])
        self.assertFalse(comp_fail["composition"]["premise_ok"])

    def test_03_wave15_unified_fts5_recall_and_deterministic_find_source(self) -> None:
        # First call builds/attaches persistent SQLite FTS5 index; second call measures warm latency
        r1 = self.model.fts5_recall("angelic cegis egraph repair", top_k=6)
        self.assertTrue(r1["pass"])
        self.assertGreater(len(r1["hits"]), 0)

        r2 = self.model.fts5_recall("angelic cegis egraph repair", top_k=6)
        self.assertTrue(r2["pass"])
        self.assertEqual([h["doc_id"] for h in r1["hits"]], [h["doc_id"] for h in r2["hits"]])
        self.assertLess(r2["elapsed_ms"], 50.0)

        # find_source determinism (sorted(wanted) fix)
        f1 = self.model.find_source("causal egraph angelic repair verifier", top_k=5)
        f2 = self.model.find_source("causal egraph angelic repair verifier", top_k=5)
        self.assertEqual(
            [(c["path"], c["score"]) for c in f1["candidates"]],
            [(c["path"], c["score"]) for c in f2["candidates"]],
        )

    def test_04_wave16_swe_inverted_microscope_k3_0_solves_real_repo_bug(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wave16_k0_") as td:
            root = pathlib.Path(td)
            (root / "math_ops.py").write_text(
                "def safe_first(items):\n"
                "    return items[0]\n",
                encoding="utf-8",
            )
            (root / "test_math_ops.py").write_text(
                "from math_ops import safe_first\n"
                "def test_non_empty():\n"
                "    assert safe_first([7, 8]) == 7\n"
                "def test_none_or_empty():\n"
                "    assert safe_first([]) == None\n",
                encoding="utf-8",
            )
            res = self.model.solve_swe_inverted_microscope(
                root,
                goal="handle empty list safely",
                apply_to_source=True,
                residual_proposer=None,
            )
            self.assertTrue(res["pass"], msg=f"Expected K3=0 solve: {res}")
            self.assertEqual(res["microscope"]["model_calls"], 0)
            self.assertTrue(res["microscope"]["verified_by_cow_oracle"])

    def test_05_wave16_swe_inverted_microscope_abstain_and_residual_proposer_orthogonal_merge(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wave16_inv_") as td:
            root = pathlib.Path(td)
            (root / "part_a.py").write_text(
                "def encode_tag(name: str) -> str:\n"
                "    return f'BAD:{name.lower()}'\n",
                encoding="utf-8",
            )
            (root / "part_b.py").write_text(
                "def format_score(x: int) -> str:\n"
                "    return f'score={x + 999}'\n",
                encoding="utf-8",
            )
            (root / "test_coupled.py").write_text(
                "from part_a import encode_tag\n"
                "from part_b import format_score\n"
                "def test_coupled_contract():\n"
                "    assert encode_tag('Alpha') == 'TAG::ALPHA'\n"
                "    assert format_score(5) == 'SCORE[005]'\n",
                encoding="utf-8",
            )

            # 1) Without residual proposer: strict K3=0 honest abstention with compact AngelicHolePacket
            abstain = self.model.solve_swe_inverted_microscope(
                root,
                goal="fix coupled tag and score formatting",
                residual_proposer=None,
            )
            self.assertFalse(abstain["pass"])
            self.assertEqual(abstain["microscope"]["tier"], "K3_0_ABSTAIN_WITH_ANGELIC_PACKET")
            self.assertEqual(abstain["microscope"]["model_calls"], 0)
            pkt = abstain["microscope"]["angelic_hole_packet"]
            self.assertIn("faulty_files", pkt)
            self.assertIn("local_snippets", pkt)

            # 2) With pluggable residual proposer returning two orthogonal single-file patches (neither solves alone!)
            def orthogonal_proposer(_packet):
                return [
                    {
                        "part_a.py": (
                            "def encode_tag(name: str) -> str:\n"
                            "    return f'TAG::{name.upper()}'\n"
                        )
                    },
                    {
                        "part_b.py": (
                            "def format_score(x: int) -> str:\n"
                            "    return f'SCORE[{x:03d}]'\n"
                        )
                    },
                ]

            solved = self.model.solve_swe_inverted_microscope(
                root,
                goal="fix coupled tag and score formatting",
                apply_to_source=True,
                residual_proposer=orthogonal_proposer,
            )
            self.assertTrue(solved["pass"], msg=f"Expected orthogonal merge verify: {solved}")
            self.assertTrue(solved["microscope"]["verified_by_cow_oracle"])
            self.assertEqual(sorted(solved["microscope"]["patched_files"]), ["part_a.py", "part_b.py"])
            self.assertIn("TAG::", (root / "part_a.py").read_text(encoding="utf-8"))
            self.assertIn("SCORE[", (root / "part_b.py").read_text(encoding="utf-8"))

    def test_06_wave17_fork_reality_cow_speculation_and_rollback_safety(self) -> None:
        # Mode A: CoW speculative rollout over competing actions
        env0 = {"stage": "init", "html_dom": "<button id='go'>Go</button>", "fs_entries": {"a.txt": "0"}}

        def act_bad(st):
            nxt = dict(st)
            nxt["stage"] = "broken"
            return nxt

        def act_good(st):
            nxt = dict(st)
            nxt["stage"] = "deployed"
            nxt["fs_entries"] = {"a.txt": "1"}
            return nxt

        spec = self.model.fork_reality_speculate(
            env_state=env0,
            candidate_actions=[("bad_branch", act_bad), ("good_branch", act_good)],
            goal_facts=["kv:stage=deployed"],
        )
        self.assertTrue(spec["pass"], msg=f"Speculative rollout failed: {spec}")
        self.assertEqual(spec["speculation"]["winner"]["action"], "good_branch")
        self.assertTrue(spec["speculation"]["seccomp_posture"]["available"])
        self.assertGreater(spec["speculation"]["seccomp_posture"]["bpf_instructions"], 0)
        # Original env_state untouched!
        self.assertEqual(env0["stage"], "init")

        # Mode B: Transactional filesystem CoW action rolls back cleanly on failed verification
        with tempfile.TemporaryDirectory(prefix="wave17_tx_") as td:
            ws = pathlib.Path(td)
            (ws / "state.txt").write_text("original-bytes\n", encoding="utf-8")

            def bad_write(work_dir: pathlib.Path):
                (work_dir / "state.txt").write_text("corrupted!\n", encoding="utf-8")
                return {"wrote": True}

            rb = self.model.fork_reality_speculate(
                workspace_root=ws,
                action_fn=bad_write,
                verify_fn=lambda d, _r: (d / "state.txt").read_text(encoding="utf-8") == "valid!\n",
            )
            self.assertFalse(rb["pass"])
            self.assertTrue(rb["speculation"]["host_preserved_on_rollback"])
            self.assertEqual((ws / "state.txt").read_text(encoding="utf-8"), "original-bytes\n")

            def good_write(work_dir: pathlib.Path):
                (work_dir / "state.txt").write_text("valid!\n", encoding="utf-8")
                return {"wrote": True}

            cm = self.model.fork_reality_speculate(
                workspace_root=ws,
                action_fn=good_write,
                verify_fn=lambda d, _r: (d / "state.txt").read_text(encoding="utf-8") == "valid!\n",
            )
            self.assertTrue(cm["pass"])
            self.assertEqual((ws / "state.txt").read_text(encoding="utf-8"), "valid!\n")

    def test_07_wave17_gui_trace_elevation_and_partial_order_planner(self) -> None:
        trace = {
            "steps": [
                {"layer": "pixel_ui", "action": "click", "x": 120, "y": 40, "selector": "#submit"},
                {"layer": "pixel_ui", "action": "click", "x": 140, "y": 44, "selector": "#confirm"},
            ],
            "observed_effects": {
                "http_exchanges": [
                    {"method": "POST", "url": "/api/submit", "json_body": {"id": 7}},
                ]
            },
        }
        elev = self.model.elevate_gui_trace(
            trace,
            goal="submit record 7",
            postcondition={"status": "saved"},
        )
        self.assertTrue(elev["pass"], msg=f"Trace elevation failed: {elev}")
        self.assertEqual(elev["elevation"]["elevated"]["dominant_layer"], "http_request")
        self.assertTrue(elev["elevation"]["elevated"]["elevated_from_ui"])

        plan_res = self.model.plan_partial_order(
            initial=[("has_repo", "yes"), ("built", "no"), ("tested", "no")],
            goal=[("tested", "yes")],
            operators=[
                {
                    "ident": "build_pkg",
                    "pre": [("has_repo", "yes"), ("built", "no")],
                    "add": [("built", "yes")],
                    "delete": [("built", "no")],
                },
                {
                    "ident": "run_tests",
                    "pre": [("built", "yes"), ("tested", "no")],
                    "add": [("tested", "yes")],
                    "delete": [("tested", "no")],
                },
            ],
            max_steps=4,
        )
        self.assertTrue(plan_res["pass"], msg=f"Partial-order plan failed: {plan_res}")
        self.assertEqual(plan_res["plan"]["steps"], ["build_pkg", "run_tests"])

    def test_08_wave18_minimax_witness_interrogation_collapses_ambiguity(self) -> None:
        # Ambiguous examples: x, x*x, abs(x) all map 0->0 and 1->1
        amb = self.model.interrogate_minimax_witness(
            params=["x"],
            examples=[(0, 0), (1, 1)],
            candidate_bodies=["x", "x * x", "abs(x)", "x * x * x"],
        )
        self.assertTrue(amb["pass"])
        self.assertEqual(amb["interrogation"]["decision"], "REFUSE_AMBIGUOUS_NEED_PROBE")
        self.assertIsNotNone(amb["interrogation"]["minimax_probe"])
        self.assertGreater(amb["interrogation"]["information_gain_bits"], 0.0)
        self.assertLess(
            amb["interrogation"]["worst_case_remaining_classes"],
            amb["interrogation"]["equivalence_classes"],
        )

        # Unique explanation commits cleanly
        uniq = self.model.interrogate_minimax_witness(
            params=["x"],
            examples=[(0, 0), (2, 4)],
            candidate_bodies=["x * x"],
        )
        self.assertTrue(uniq["pass"])
        self.assertEqual(uniq["interrogation"]["decision"], "COMMIT_UNIQUE_EXPLANATION")
        self.assertEqual(uniq["interrogation"]["chosen_body"], "return x * x")

    def test_09_wave18_csp_hard_negatives_and_spec_gap_detection(self) -> None:
        src = (
            "def classify(x: int) -> str:\n"
            "    if x < 10:\n"
            "        return 'small'\n"
            "    return 'large'\n"
        )
        # Deliberately omits boundary x == 10 so `<` -> `<=` survives as a real spec gap!
        test_src = (
            "from subject_mod import classify\n"
            "def test_basic():\n"
            "    assert classify(3) == 'small'\n"
            "    assert classify(25) == 'large'\n"
        )
        csp = self.model.generate_csp_hard_negatives(source_text=src, test_source=test_src, max_mutants=8)
        self.assertTrue(csp["pass"], msg=f"CSP generation failed: {csp}")
        self.assertGreaterEqual(csp["csp"]["total_mutants"], 1)
        self.assertGreaterEqual(csp["csp"]["survived_spec_gap_count"], 1)

        # Now add boundary test x == 10 -> kills the mutant and produces a distillation pair!
        test_tight = test_src + "def test_boundary():\n    assert classify(10) == 'large'\n"
        csp2 = self.model.generate_csp_hard_negatives(source_text=src, test_source=test_tight, max_mutants=8)
        self.assertTrue(csp2["pass"])
        self.assertGreaterEqual(csp2["csp"]["caught_count"], 1)
        self.assertEqual(csp2["csp"]["survived_spec_gap_count"], 0)
        self.assertEqual(csp2["csp"]["kill_rate"], 1.0)

    def test_10_wave19_creature_gea_sea_organ_evolution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wave19_gea_") as td:
            creature = self.model.open_creature(td, identity="gea-test-creature", life=20.0)
            incumbent = "def clamp_pos(x):\n    return x\n"
            cand_unsafe = "import os\ndef clamp_pos(x):\n    return max(0, x)\n"
            cand_regressing = "def clamp_pos(x):\n    return 0\n"
            cand_winner = "def clamp_pos(x):\n    return 0 if x < 0 else x\n"

            test_cases = [((-i,), 0) for i in range(1, 9)] + [((i,), i) for i in range(0, 4)]
            anchor_cases = [((0,), 0), ((5,), 5), ((12,), 12)]

            res = creature.sleep_evolve_organs_gea(
                organ_name="clamp_pos",
                incumbent_source=incumbent,
                candidate_sources=[cand_unsafe, cand_regressing, cand_winner],
                test_cases=test_cases,
                anchor_cases=anchor_cases,
                alpha=0.05,
            )
            self.assertTrue(res["pass"], msg=f"GEA+SEA evolution failed: {res}")
            self.assertTrue(res["admitted"])
            self.assertEqual(res["winner"]["lineage_idx"], 2)
            self.assertEqual(res["winner"]["anchor_regressions"], 0)
            self.assertGreaterEqual(res["winner"]["sea_e_value"], 20.0)
            # Unsafe candidate blocked by Ring-0 referee!
            self.assertFalse(res["group_reports"][0]["ring0_admitted"])
            # Regressing candidate blocked by anchor regression gate!
            self.assertFalse(res["group_reports"][1]["sea_certified"])
            self.assertGreater(res["group_reports"][1]["anchor_regressions"], 0)
            # Certified event appended to verified_event_log
            self.assertIsNotNone(res["event_receipt"])

    def test_11_wave19_self_verify_dark_matter_unlocks_ten_hidden_engines(self) -> None:
        hidden_10 = [
            "canonical/swe_kernel/causal_cegis_inventor_v1.py",
            "canonical/swe_kernel/metamorphic_habitation_zipper_v1.py",
            "canonical/swe_kernel/multistep_repo_closed_loop_solver_v1.py",
            "canonical/swe_kernel/causal_nexus_v1.py",
            "canonical/swe_kernel/cow_impact_repair_engine_v1.py",
            "canonical/swe_kernel/rule_expiry_v1.py",
            "canonical/swe_kernel/transactional_parallel_execution_v1.py",
            "canonical/runtime/worker_syscall_allowlist_v1.py",
            "canonical/swe_kernel/partial_order_planner_v1.py",
            "canonical/runtime/evidence_demand_v1.py",
        ]
        res = self.model.self_verify_dark_matter(hidden_10, timeout_s=8.0)
        self.assertTrue(res["pass"], msg=f"Dark matter self-verify failed: {res}")
        self.assertEqual(res["counts"]["RAN_CLEAN"], 10)
        self.assertEqual(res["counts"]["FAILED"], 0)
        self.assertEqual(res["counts"]["MISSING_FILE"], 0)

    def test_12_wave20_unified_leapfrog_solve_auto_dispatch(self) -> None:
        # Memory dispatch
        r_mem = self.model.leapfrog_solve("reverse tomography algebra egraph", mode="memory", top_k=4)
        self.assertTrue(r_mem["pass"])
        # Interrogation dispatch
        r_int = self.model.leapfrog_solve(
            "disambiguate function",
            params=["x"],
            examples=[(0, 0), (1, 1)],
            candidate_bodies=["x", "x * x"],
        )
        self.assertTrue(r_int["pass"])
        self.assertEqual(r_int["interrogation"]["decision"], "REFUSE_AMBIGUOUS_NEED_PROBE")
        # Partial-order plan dispatch
        r_plan = self.model.leapfrog_solve(
            "deploy service",
            initial=[("ready", "no")],
            goal_conditions=[("ready", "yes")],
            operators=[{"ident": "init_svc", "pre": [("ready", "no")], "add": [("ready", "yes")], "delete": [("ready", "no")]}],
        )
        self.assertTrue(r_plan["pass"])
        self.assertEqual(r_plan["plan"]["steps"], ["init_svc"])

    def test_13_cross_process_pythonhashseed_determinism_find_source(self) -> None:
        import json
        import os
        import subprocess
        import sys

        probe = (
            "import json\n"
            "from canonical.runtime.brain_unified_model_v1 import open_model\n"
            "m = open_model()\n"
            "r = m.find_source('causal egraph angelic repair verifier', top_k=8)\n"
            "print(json.dumps([(c['path'], c['score']) for c in r['candidates']]))\n"
        )
        outputs = []
        for seed in ("1", "99999"):
            env = dict(os.environ)
            env["PYTHONHASHSEED"] = seed
            cp = subprocess.run(
                [sys.executable, "-c", probe],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
                check=True,
            )
            outputs.append(json.loads(cp.stdout.strip().splitlines()[-1]))
        self.assertGreater(len(outputs[0]), 0)
        self.assertEqual(outputs[0], outputs[1])

    def test_14_memory_bus_save_and_load_roundtrip_wave15(self) -> None:
        from canonical.swe_kernel.canonical_memory_crystallizer_v1 import VerificationFirstMemoryBus

        with tempfile.TemporaryDirectory(prefix="wave15_persist_") as td:
            p = pathlib.Path(td) / "bus.json"
            bus1 = VerificationFirstMemoryBus()
            sk = bus1.crystallize_action_macro(
                trigger_key="persist_widget_beta",
                actions=["echo beta"],
                provenance_episode_id="EP_PERSIST",
            )
            bus1.register_memguard_lifecycle(skill_id=sk.skill_id, reward=1.0, confidence=0.9)
            bus1.record_anti_skill(
                domain="swe_patch",
                symbol_scope="mod.py::fn",
                bad_hypothesis="return None",
                error_signature="TypeError: NoneType",
            )
            bus1.save(p)

            bus2 = VerificationFirstMemoryBus()
            bus2.load(p)
            self.assertIn(sk.skill_id, bus2._skill_lifecycle)
            self.assertGreaterEqual(len(bus2._anti_skills), 1)
            pruned = bus2.prune_by_anti_skills(["return None", "return 42"], domain="swe_patch", symbol_scope="mod.py::fn")
            self.assertEqual(pruned["kept"], ["return 42"])
            rec = bus2.fts5_recall("persist_widget_beta", top_k=3)
            self.assertTrue(rec["pass"])
            self.assertTrue(any(h["doc_id"] == sk.skill_id for h in rec["hits"]))

    def test_15_creature_gea_rejects_zero_gain_organ_under_sea_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wave19_nogain_") as td:
            creature = self.model.open_creature(td, identity="gea-nogain-creature", life=20.0)
            incumbent = "def id_fn(x):\n    return x\n"
            cand_same = "def id_fn(x):\n    return x + 0\n"
            test_cases = [((i,), i) for i in range(1, 6)]
            res = creature.sleep_evolve_organs_gea(
                organ_name="id_fn",
                incumbent_source=incumbent,
                candidate_sources=[cand_same],
                test_cases=test_cases,
                anchor_cases=test_cases[:2],
                alpha=0.05,
            )
            self.assertFalse(res["pass"])
            self.assertFalse(res["admitted"])
            self.assertEqual(res["status"], "FAIL_CLOSED__NO_CANDIDATE_PASSED_SEA_CERTIFICATE")

    def test_16_inverted_microscope_cow_never_mutates_host_on_rejected_proposals(self) -> None:
        with tempfile.TemporaryDirectory(prefix="wave16_nomut_") as td:
            root = pathlib.Path(td)
            orig_src = "def compute(x: int) -> int:\n    return x + 100\n"
            (root / "calc.py").write_text(orig_src, encoding="utf-8")
            (root / "test_calc.py").write_text(
                "from calc import compute\n"
                "def test_c():\n"
                "    assert compute(3) == 9\n",
                encoding="utf-8",
            )

            def bad_proposer(_pkt):
                return [
                    {"calc.py": "def compute(x: int) -> int:\n    return x + 1\n"},
                    {"calc.py": "def compute(x: int) -> int:\n    return x * 2\n"},
                ]

            res = self.model.solve_swe_inverted_microscope(
                root,
                goal="compute square",
                apply_to_source=True,
                residual_proposer=bad_proposer,
            )
            self.assertFalse(res["pass"])
            self.assertEqual(res["microscope"]["status"], "FAIL_CLOSED__RESIDUAL_PROPOSALS_REJECTED_BY_COW_ORACLE")
            # Host file MUST stay 100% byte-identical despite apply_to_source=True!
            self.assertEqual((root / "calc.py").read_text(encoding="utf-8"), orig_src)


if __name__ == "__main__":
    unittest.main()
