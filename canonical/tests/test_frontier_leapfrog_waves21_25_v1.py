#!/usr/bin/env python3
"""Zero-mock end-to-end verification suite for Waves 21-25 Frontier Leapfrog.

Covers:
  - Wave 21: Elon Speed Pass (os.scandir compile speedup + bit-identical digest + lazy CLI imports + compile-time FTS5 sidecar prewarm)
  - Wave 22: Universal Reachability Bridge (verified_capability_bridge_index_v1 + source_contract_compiler + learned_skill_verdict_v1 + FTS5 extended source)
  - Wave 23: Repo-Native Multi-File SWE Engine (0D: causal_dataflow_graph + assertion/line localization + arm online transfer + git history templates + repo petri + angelic OE + CoW Zygote)
  - Wave 24: Bitemporal Memory + Counterfactual Credit + SkillBank + Effect Chains + Red Queen Evaluator Co-Evolution + Creature.sleep_red_queen_coevolve
  - Wave 25: Systematic Exploration + Safe Action Model + Demonstration Sufficiency + K6 Decision Quotient + Horizon-Bounded Zero-Screenshot CU + leapfrog_solve
"""
from __future__ import annotations

import json
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

import canonical.runtime.brain_unified_model_v1 as bum
from canonical.runtime.creature_runtime_v1 import Creature
from canonical.swe_kernel import effect_contract_composition_v1 as ecc


class _MiniDeterministicEnv:
    """Tiny real deterministic state machine (no mocks) for systematic_exploration_v1."""

    def __init__(self) -> None:
        self._state = 0

    def reset(self) -> int:
        self._state = 0
        return self._state

    def state(self) -> int:
        return self._state

    def act(self, action: str) -> int:
        if action == "inc":
            self._state = min(3, self._state + 1)
        elif action == "dec":
            self._state = max(0, self._state - 1)
        elif action == "jump" and self._state == 2:
            self._state = 3
        return self._state


class TestWave21ElonSpeedPass(unittest.TestCase):
    def test_lazy_cli_imports_not_loaded_on_fresh_open(self) -> None:
        code = (
            "import sys, time\n"
            "t0 = time.perf_counter()\n"
            "import canonical.runtime.brain_unified_model_v1 as bum\n"
            "m = bum.open_model()\n"
            "t_open = (time.perf_counter() - t0) * 1000\n"
            "t1 = time.perf_counter()\n"
            "r = m.fts5_recall('canonical boundary router', top_k=5)\n"
            "t_fts = (time.perf_counter() - t1) * 1000\n"
            "import json\n"
            "print(json.dumps({\n"
            "  'argparse_loaded': 'argparse' in sys.modules,\n"
            "  'open_ms': round(t_open, 2),\n"
            "  'fts_ms': round(t_fts, 2),\n"
            "  'fts_pass': bool(r.get('pass')),\n"
            "  'fts_hits': len(r.get('hits') or ()),\n"
            "}))\n"
        )
        # Ensure sidecars (including FTS5) are prewarmed first
        bum.prewarm_sidecar_caches()
        proc = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        out = json.loads(proc.stdout.strip())
        self.assertFalse(out["argparse_loaded"], "argparse must remain lazily deferred until CLI main()")
        self.assertTrue(out["fts_pass"])
        self.assertGreater(out["fts_hits"], 0)
        # Prewarmed FTS5 + zero-full-model _envelope should be <25 ms (down from 185 ms!)
        self.assertLess(out["fts_ms"], 25.0, f"Prewarmed FTS5 unexpectedly slow: {out}")

    def test_elon_speed_profile_and_extended_source_in_fts5(self) -> None:
        bum.prewarm_sidecar_caches()
        model = bum.open_model()
        prof = model.elon_speed_profile()
        self.assertTrue(prof["pass"])
        self.assertTrue(prof["core_marshal_warm"])
        self.assertTrue(prof["fts5_sidecar_warm"])
        self.assertTrue(prof["lazy_cli_imports_deferred"])
        self.assertGreater(prof["fts5_sidecar_bytes"], 4096)
        # Verify extended_source_index (`swe_kernel`) is searchable directly via FTS5
        hit_res = model.fts5_recall("canonical_swe_spine_v1", top_k=8, include_memory_bus=False)
        self.assertTrue(hit_res["pass"])
        paths = [str(h.get("path") or "") for h in hit_res.get("hits") or ()]
        self.assertTrue(any("canonical_swe_spine_v1" in p for p in paths), f"Expected swe_kernel hit in {paths}")


class TestWave22UniversalReachabilityBridge(unittest.TestCase):
    def test_universal_capability_bridge_roles_contracts_repo_nav_and_fts5(self) -> None:
        model = bum.open_model()
        contract_doc = (
            "The system MUST preserve host immutability during speculative repair.\n"
            "The verifier SHALL fail closed when evidence is missing.\n"
        )
        res = model.universal_capability_bridge(
            "Verify deterministic code repair and inspect canonical swe spine symbols",
            contract_text=contract_doc,
            repo_nav_root=ROOT / "canonical" / "swe_kernel",
            repo_nav_kind="find_symbol",
            repo_nav_target="solve_swe_repo_native_multifile",
            top_k=6,
        )
        self.assertTrue(res["pass"])
        self.assertEqual(res["bridge"]["model_calls"], 0)
        self.assertGreaterEqual(res["admitted_capabilities_visible"], 400)
        br = res["bridge"]
        self.assertIsInstance(br["semantic_roles"], dict)
        self.assertIsNotNone(br["source_contract"])
        self.assertTrue(br["source_contract"]["roundtrip_exact"])
        self.assertGreaterEqual(br["source_contract"]["normative_atoms"], 1)
        self.assertIsNotNone(br["repo_navigation"])
        self.assertGreater(len(res["fts5_hits"]), 0)


class TestWave23RepoNativeMultiFileSWE(unittest.TestCase):
    def _make_buggy_repo(self, td: str, *, bug_op: str = "-", init_git: bool = False) -> Path:
        repo = Path(td) / "mini_repo"
        repo.mkdir(parents=True, exist_ok=True)
        (repo / "calc.py").write_text(
            f"def compute_total(price, tax):\n    return price {bug_op} tax\n",
            encoding="utf-8",
        )
        (repo / "test_calc.py").write_text(
            "import unittest\n"
            "from calc import compute_total\n\n"
            "class TestCalc(unittest.TestCase):\n"
            "    def test_total(self):\n"
            "        self.assertEqual(compute_total(10, 2), 12)\n"
            "        self.assertEqual(compute_total(5, 3), 8)\n\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n",
            encoding="utf-8",
        )
        if init_git:
            subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True)
            subprocess.run(["git", "config", "user.email", "test@brain.local"], cwd=str(repo), check=True)
            subprocess.run(["git", "config", "user.name", "Brain Test"], cwd=str(repo), check=True)
            subprocess.run(["git", "add", "."], cwd=str(repo), check=True)
            subprocess.run(["git", "commit", "-q", "-m", "initial buggy calc"], cwd=str(repo), check=True)
        return repo

    def test_repo_native_swe_repairs_in_cow_and_crystallizes_vocab(self) -> None:
        model = bum.open_model()
        with tempfile.TemporaryDirectory(prefix="wave23_swe_") as td:
            repo = self._make_buggy_repo(td, bug_op="-", init_git=True)
            orig_bytes = (repo / "calc.py").read_bytes()
            res = model.solve_swe_repo_native(
                repo,
                test_targets=["test_calc.py"],
                candidate_files=["calc.py"],
                witness_envs=[{"price": 10, "tax": 2}, {"price": 5, "tax": 3}],
                witness_targets=[12, 8],
                keep_patch_applied=False,
            )
            self.assertTrue(res["pass"], f"Expected repair PASS, got: {res}")
            swe = res["swe_result"]
            self.assertEqual(swe["model_calls"], 0)
            self.assertIn("calc.py", swe["patched_files"])
            # Host file must remain untouched when keep_patch_applied=False
            self.assertEqual((repo / "calc.py").read_bytes(), orig_bytes)
            # Online vocabulary crystallization must return a non-empty repair vocab
            vocab = swe.get("updated_repair_vocab")
            self.assertIsInstance(vocab, dict)
            self.assertGreaterEqual(swe.get("crystallized_demo_count", 0), 1)

            # Now test Wave 23 Stage 1 online transfer onto an analogous renamed bug using the crystallized vocab!
            repo2 = Path(td) / "mini_repo_renamed"
            repo2.mkdir(parents=True, exist_ok=True)
            (repo2 / "billing.py").write_text(
                "def gross_amount(base, fee):\n    return base - fee\n",
                encoding="utf-8",
            )
            (repo2 / "test_billing.py").write_text(
                "import unittest\n"
                "from billing import gross_amount\n\n"
                "class TestBilling(unittest.TestCase):\n"
                "    def test_gross(self):\n"
                "        self.assertEqual(gross_amount(20, 5), 25)\n"
                "        self.assertEqual(gross_amount(7, 4), 11)\n",
                encoding="utf-8",
            )
            res2 = model.solve_swe_repo_native(
                repo2,
                test_targets=["test_billing.py"],
                candidate_files=["billing.py"],
                in_run_repair_vocab=vocab,
                witness_envs=[{"base": 20, "fee": 5}, {"base": 7, "fee": 4}],
                witness_targets=[25, 11],
                mine_git_history=False,
                keep_patch_applied=False,
            )
            self.assertTrue(res2["pass"], f"Expected online transfer PASS, got: {res2}")
            self.assertEqual(res2["swe_result"]["model_calls"], 0)
            self.assertIn("STAGE_1_IN_RUN_ALPHA_CANONICAL_TRANSFER", res2["swe_result"]["stages_run"])

    def test_repo_native_swe_fails_closed_without_host_mutation(self) -> None:
        model = bum.open_model()
        with tempfile.TemporaryDirectory(prefix="wave23_fc_") as td:
            repo = Path(td) / "unsolvable_repo"
            repo.mkdir()
            (repo / "hard.py").write_text("def magic(x):\n    return 0\n", encoding="utf-8")
            (repo / "test_hard.py").write_text(
                "import unittest\nfrom hard import magic\n"
                "class T(unittest.TestCase):\n"
                "    def test_m(self):\n"
                "        self.assertEqual(magic(7), 991827364)\n"
                "        self.assertEqual(magic(11), 135792468)\n",
                encoding="utf-8",
            )
            orig = (repo / "hard.py").read_bytes()
            res = model.solve_swe_repo_native(
                repo,
                test_targets=["test_hard.py"],
                candidate_files=["hard.py"],
                mine_git_history=False,
                residual_proposer=None,
            )
            self.assertFalse(res["pass"])
            self.assertEqual((repo / "hard.py").read_bytes(), orig)


class TestWave24BitemporalAndRedQueen(unittest.TestCase):
    def test_bitemporal_memory_versioning_and_point_in_time_query(self) -> None:
        model = bum.open_model()
        r1 = model.bitemporal_memory_record(
            entity="service:auth",
            attribute="protocol",
            value="v1_cookie",
            valid_from=10.0,
            tx_time=10.0,
        )
        self.assertTrue(r1["pass"])
        r2 = model.bitemporal_memory_record(
            entity="service:auth",
            attribute="protocol",
            value="v2_oidc_jwt",
            valid_from=20.0,
            tx_time=20.0,
        )
        self.assertTrue(r2["pass"])
        self.assertEqual(len(r2["bitemporal"]["superseded_ids"]), 1)

        # Query at valid_time=15 must return v1_cookie; at valid_time=25 must return v2_oidc_jwt
        q_old = model.bitemporal_memory_query(entity="service:auth", attribute="protocol", as_of_valid=15.0)
        q_new = model.bitemporal_memory_query(entity="service:auth", attribute="protocol", as_of_valid=25.0)
        self.assertTrue(q_old["pass"])
        self.assertTrue(q_new["pass"])
        self.assertEqual(q_old["bitemporal"]["facts"][0]["value"], "v1_cookie")
        self.assertEqual(q_new["bitemporal"]["facts"][0]["value"], "v2_oidc_jwt")

    def test_bitemporal_skill_bank_and_effect_contract_chain(self) -> None:
        model = bum.open_model()
        # SkillBank success + failure lesson
        sb1 = model.bitemporal_skill_bank_update(
            skill_name="patch_off_by_one",
            skill_type="swe_repair",
            pattern="range_bounds",
            preconditions=["index_error_present"],
            operations=["adjust_upper_bound"],
            succeeded=True,
            valid_from=1.0,
        )
        self.assertTrue(sb1["pass"])
        sb2 = model.bitemporal_skill_bank_update(
            skill_name="patch_off_by_one",
            succeeded=False,
            failure_lesson="do_not_decrement_empty_slice",
            valid_from=2.0,
        )
        self.assertTrue(sb2["pass"])
        self.assertEqual(sb2["skill_bank"]["applications"], 2)
        self.assertIn("do_not_decrement_empty_slice", sb2["skill_bank"]["failure_lessons"])

        # Formal effect contract composition using real measured advancing pair
        c_a, c_b = ecc.measured_advance_pair()
        specs = [
            {
                "skill_id": c_a.skill_id,
                "preconditions": list(c_a.preconditions),
                "observables": list(c_a.observables),
                "actions": list(c_a.actions),
                "verdict": c_a.verdict,
                "effects": [{"kind": e.kind, "subject": e.subject} for e in c_a.effects],
            },
            {
                "skill_id": c_b.skill_id,
                "preconditions": list(c_b.preconditions),
                "observables": list(c_b.observables),
                "actions": list(c_b.actions),
                "verdict": c_b.verdict,
                "effects": [{"kind": e.kind, "subject": e.subject} for e in c_b.effects],
            },
        ]
        chain_res = model.verify_effect_contract_chain(specs)
        self.assertIn("chain", chain_res)
        self.assertEqual(chain_res["chain"]["contract_count"], 2)
        self.assertEqual(chain_res["chain"]["model_calls"], 0)

    def test_red_queen_evaluator_coevolution_and_creature_sleep_cycle(self) -> None:
        model = bum.open_model()
        incumbent_src = "def safe_double(x):\n    return x * 2 if x > 0 else 0\n"
        better_src = "def safe_double(x):\n    return x * 2 if x >= 0 else -x * 2\n"
        rq = model.red_queen_coevolve_evaluators(
            epoch_index=0,
            orig_source=incumbent_src,
            patched_source=better_src,
            func_name="safe_double",
            lens_witness_pairs=[("abc", "ABC"), ("hello", "HELLO"), ("world", "WORLD")],
            mine_rewrite_laws=True,
            rewrite_max_size=3,
            rewrite_term_limit=64,
        )
        self.assertTrue(rq["pass"], f"Red Queen evaluator co-evolution failed: {rq}")
        inner = rq["red_queen"]
        self.assertTrue(inner["intra_epoch_mutation_forbidden"])
        self.assertNotEqual(inner["intra_epoch_frozen_judge_digest"], inner["next_epoch_judge_digest"])
        self.assertGreater(inner["stdlib_judges_discovered"], 0)
        self.assertIsNotNone(inner["cow_boundary_fuzz"])
        self.assertTrue(inner["cow_boundary_fuzz"]["passed"])
        self.assertIsNotNone(inner["mined_rewrite_theory"])
        self.assertGreater(inner["mined_rewrite_theory"]["mined_rule_count"], 0)

        # Creature full sleep_red_queen_coevolve cycle
        with tempfile.TemporaryDirectory(prefix="wave24_creature_") as td:
            c = model.open_creature(Path(td), identity="red_queen", life=100.0)
            sleep_res = c.sleep_red_queen_coevolve(
                epoch_index=1,
                organ_name="safe_double",
                incumbent_source=incumbent_src,
                candidate_sources=[better_src],
                func_name="safe_double",
                test_cases=[((2,), 4), ((0,), 0), ((-3,), 6), ((-5,), 10), ((-1,), 2)],
                anchor_cases=[((2,), 4), ((3,), 6)],
                lens_witness_pairs=[("a", "A"), ("b", "B")],
                mine_rewrite_laws=True,
            )
            self.assertTrue(sleep_res["pass"], f"Creature Red Queen sleep failed: {sleep_res}")
            self.assertEqual(sleep_res["next_epoch_index"], 2)
            self.assertTrue(sleep_res["bitemporal_skill_bank"]["pass"])


class TestWave25AgentS4AndDecisionQuotient(unittest.TestCase):
    def test_safe_exploration_decision_quotient_and_zero_screenshot_cu(self) -> None:
        model = bum.open_model()

        # 1. Systematic exploration + demonstration sufficiency + interventional probe
        env = _MiniDeterministicEnv()
        exp_res = model.explore_safe_action_model(
            env=env,
            actions=["inc", "dec", "jump"],
            is_goal=lambda s: s == 3,
            action_budget=24,
            demo_state={"a.txt": b"hello"},
            interventional_probe=("scale", [4, 2], 8),
        )
        self.assertIn("exploration", exp_res)
        self.assertIsNotNone(exp_res["exploration"]["exploration"])
        self.assertIsNotNone(exp_res["exploration"]["demonstration_sufficiency"])

        # 2. K6 Decision Quotient — common action ready
        dq_common = model.compile_decision_quotient(
            actions_by_world={"w1": ["a", "b"], "w2": ["b", "c"]},
            verify_theorem=True,
        )
        self.assertTrue(dq_common["pass"], f"DQ common failed: {dq_common}")
        self.assertFalse(dq_common["quotient"]["refinement_needed"])
        self.assertEqual(dq_common["quotient"]["common_action"], "b")
        self.assertTrue(dq_common["quotient"]["finite_theorem"]["same_signature_worlds_merge_without_loss"])
        self.assertTrue(dq_common["quotient"]["finite_theorem"]["disjoint_acceptable_sets_require_refinement"])

        # 3. K6 Decision Quotient — refinement needed + discriminator compiled under deadline
        dq_ref = model.compile_decision_quotient(
            actions_by_world={"w1": ["a"], "w2": ["b"]},
            discriminators=[
                {
                    "id": "probe_header",
                    "cost": 1.0,
                    "arrival": 0.5,
                    "authorized": True,
                    "owned_operator": True,
                    "observations": {"w1": "x", "w2": "y"},
                },
            ],
            commitment_deadline=5.0,
        )
        self.assertTrue(dq_ref["pass"], f"DQ refinement failed: {dq_ref}")
        self.assertTrue(dq_ref["quotient"]["refinement_needed"])
        self.assertIsNotNone(dq_ref["quotient"]["refinement_plan"])

        # 4. Horizon-bounded CU + Zero-Screenshot DOM Cache + Vocabulary Growth
        cu_res = model.execute_horizon_zero_screenshot_cu(
            task_id="wave25_cu_check",
            target_url="https://app.example.com/items/12345?tab=settings",
            dom_observation={"role": "button", "name": "Save", "tag": "button", "children": []},
            run_tier0_cache_suite=True,
            goal=["done"],
            subgoals=[
                {
                    "subgoal_index": 0,
                    "description": "prepare",
                    "precondition": [],
                    "postcondition": ["prepared"],
                    "step_budget": 3,
                },
                {
                    "subgoal_index": 1,
                    "description": "finalize",
                    "precondition": ["prepared"],
                    "postcondition": ["done"],
                    "step_budget": 3,
                },
            ],
            total_step_budget=8,
            initial_state={"state.txt": b"init"},
            vocabulary_invocation="cp a.txt b.txt",
            vocabulary_states={"s1": {"a.txt": b"abc"}, "s2": {"a.txt": b"xyz"}},
        )
        self.assertTrue(cu_res["pass"], f"Horizon Zero-Screenshot CU failed: {cu_res}")
        inner_cu = cu_res["cu_execution"]
        self.assertIsNotNone(inner_cu["zero_screenshot_cache"]["dom_fingerprint"])
        self.assertIsNotNone(inner_cu["horizon_execution"])
        self.assertIsNotNone(inner_cu["vocabulary_growth"])

    def test_leapfrog_solve_auto_dispatch(self) -> None:
        model = bum.open_model()
        # Dispatch to Decision Quotient
        r1 = model.leapfrog_solve(
            "choose safe action across candidate worlds",
            inputs={"actions_by_world": {"w0": ["go", "wait"], "w1": ["wait"]}},
        )
        self.assertTrue(r1["pass"])
        self.assertEqual(r1["operation"], "DECISION_QUOTIENT_COMPILE")
        self.assertEqual(r1["quotient"]["common_action"], "wait")

        # Dispatch to Zero-Screenshot CU
        r2 = model.leapfrog_solve(
            "fingerprint dom and run tier0 cache",
            inputs={
                "target_url": "https://shop.example.org/order/999",
                "dom_observation": {"role": "link", "name": "Checkout"},
                "run_tier0_cache_suite": True,
            },
        )
        self.assertTrue(r2["pass"])
        self.assertEqual(r2["operation"], "HORIZON_ZERO_SCREENSHOT_CU")


if __name__ == "__main__":
    unittest.main()
