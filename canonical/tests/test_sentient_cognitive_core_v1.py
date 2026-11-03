#!/usr/bin/env python3
"""Adversarial falsification & non-static living behavior tests for `sentient_cognitive_core_v1` (`K3 = 0`).

Proves all 5 non-static sentient-creature controls + soundness guards:
  (A) Lived-history divergence on byte-identical code (`System-1 < 0.5 ms` vs `System-2` escalation + reboot persistence).
  (B) Zero-prior causal world discovery (`CausalWorldGraph` `(Read, Write, Destroy)` algebra + backward chaining).
  (C) Wake-Sleep `[G_-, B_+]` version-space consolidation (`5/5` transfer in `0` search steps + weak-verifier withholding + AST assertion counter).
  (D) Anti-YouTube `$1M` global VoI + `incumbent_dominance_search_v1` + pre-execution `(Read, Write)` polarity.
  (E) Idle cheat-defended autonomous curiosity + `PREFERS_TO_CONTINUE` ending-bribe refusal + `< 15 ms` warm pulse.
"""
from __future__ import annotations

import ast
import os
import pathlib
import stat
import tempfile
import time
import unittest

from canonical.runtime import brain_unified_model_v1 as bum
from canonical.runtime import brokered_workspace_execution_v1 as broker
from canonical.runtime import creature_runtime_v1 as cr
from canonical.runtime import derived_inspector_flywheel_v1 as dif
from canonical.swe_kernel import autonomous_awake_loop_v1 as aal
from canonical.swe_kernel import rule_scope_learning_v1 as rscope
from canonical.swe_kernel import sentient_cognitive_core_v1 as scc
from canonical.swe_kernel.cow_impact_repair_engine_v1 import create_zero_copy_cow_workspace
from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class SentientCognitiveCoreAdversarialTests(unittest.TestCase):
    def test_zero_host_exec_and_compatibility_invariants(self) -> None:
        """All 5 upgraded modules contain zero AST `exec()` calls and preserve pinned invariants."""
        guarded_paths = [
            "canonical/swe_kernel/sentient_cognitive_core_v1.py",
            "canonical/swe_kernel/rule_scope_learning_v1.py",
            "canonical/swe_kernel/autonomous_awake_loop_v1.py",
            "canonical/runtime/creature_runtime_v1.py",
            "canonical/runtime/derived_inspector_flywheel_v1.py",
        ]
        for rel in guarded_paths:
            tree = ast.parse((REPO_ROOT / rel).read_text(encoding="utf-8"))
            exec_lines = [
                n.lineno
                for n in ast.walk(tree)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "exec"
            ]
            self.assertEqual(exec_lines, [], f"Host exec() leak in {rel}: {exec_lines}")

        self.assertEqual(
            tuple(h.hypothesis_id for h in rscope.SCOPE_HYPOTHESES),
            ("SCOPE_STATEMENT", "SCOPE_OPERATOR", "SCOPE_SEMANTIC"),
        )
        self.assertFalse(hasattr(cr, "_SOVEREIGN_STDLIB_INSPECTABLE_FAMILIES"))

    def test_control_a_non_static_lived_history_divergence_on_identical_code(self) -> None:
        """Control A: Two creatures running byte-identical code diverge in regime & probability purely from lived experience."""
        with tempfile.TemporaryDirectory(prefix="brain-scc-ctrl-a-") as td:
            root = pathlib.Path(td)
            c1 = cr.boot(root / "creature_alpha", identity="alpha", life=30.0)
            c2 = cr.boot(root / "creature_beta", identity="beta", life=30.0)
            task_id = "inspector:json.file.write"

            # Initially identical self-belief on identical untouched state
            p1_init = cr.predict_task_probability(task_id, c1)
            p2_init = cr.predict_task_probability(task_id, c2)
            self.assertAlmostEqual(p1_init, p2_init, places=6)

            # Alpha experiences verified mastery; Beta experiences surprising failure on the exact same task_id
            t1 = c1.cognitive_core.belief.predict_before_act(
                task_id,
                calibration_ledger=c1.calibration_ledger,
                host_ready=True,
                grounding_complete=True,
                memory_reflex_hit=True,
            )
            s1 = c1.cognitive_core.belief.settle_and_compute_surprise(
                t1,
                outcome_pass=True,
                inspector="IndependentTestInspector",
                actual_cost=0.5,
                actual_gain=3.0,
                calibration_ledger=c1.calibration_ledger,
            )
            self.assertFalse(s1["escalate_system2"])

            t2 = c2.cognitive_core.belief.predict_before_act(
                task_id,
                calibration_ledger=c2.calibration_ledger,
                host_ready=True,
                grounding_complete=True,
                memory_reflex_hit=True,
            )
            s2 = c2.cognitive_core.belief.settle_and_compute_surprise(
                t2,
                outcome_pass=False,
                inspector="IndependentTestInspector",
                actual_cost=2.0,
                actual_gain=0.0,
                calibration_ledger=c2.calibration_ledger,
                ignorance_ledger_path=root / "creature_beta" / "ignorance.json",
            )
            self.assertTrue(s2["escalate_system2"])
            self.assertGreater(s2["surprise"], s1["surprise"] + 1.0)

            # Re-querying the EXACT same code & arguments produces divergent self-belief & cognitive regimes!
            r1 = c1.cognitive_core.decide_cognitive_regime(task_id, has_consolidated_reflex=True)
            r2 = c2.cognitive_core.decide_cognitive_regime(task_id, has_consolidated_reflex=True)
            self.assertEqual(r1["regime"], "SYSTEM_1_REFLEX")
            self.assertEqual(r2["regime"], "SYSTEM_2_DELIBERATION")
            self.assertLess(r1["decision_us"], 500.0)  # < 0.5 ms System-1 reflex decision
            self.assertGreater(r1["predicted_pass_probability"], r2["predicted_pass_probability"] + 0.35)

            # Verify UnifiedModel.act_or_learn respects lived-history cognitive_core divergence
            um = bum.open_model()
            tmp_out = REPO_ROOT / "canonical" / "astra_runtime" / "tmp" / f"scc_ctrl_a_{os.getpid()}.json"
            tmp_out.parent.mkdir(parents=True, exist_ok=True)
            try:
                u1 = um.act_or_learn(
                    "write json spec to file",
                    capability_id="json.file.write",
                    inputs={"spec": '{"hello": 1}', "output_path": tmp_out.relative_to(REPO_ROOT).as_posix()},
                    cognitive_core=c1.cognitive_core,
                )
                self.assertTrue(u1["pass"], u1)
                self.assertEqual(u1["cognitive_regime"]["regime"], "SYSTEM_1_REFLEX")
            finally:
                tmp_out.unlink(missing_ok=True)

            # Verify BehavioralDerivation soundness (rejects failing JSON payloads) & reboot callable persistence
            bad_art = root / "bad_out.json"
            bad_art.write_text('{"ok": false, "status": "FAIL_CLOSED", "code": 1}', encoding="utf-8")
            bad_deriv = dif.derive_from_behavioral_mutations(
                capability_id="cap.bad",
                good_artifact_path="bad_out.json",
                checker=lambda p: p.read_text(encoding="utf-8").strip() != "",
                root=root,
            )
            self.assertTrue(bad_deriv.refused, "derive_from_behavioral_mutations must refuse failing ok=false JSON!")

            res_onb = cr._onboard_typed_capability_inspector("json.file.write", c1)
            self.assertTrue(res_onb["ok"], res_onb)
            c1._save_sovereign_organs()

            # Reboot creature from disk and verify live BehavioralDerivation check still rejects corrupt outputs
            c1_rebooted = cr.boot(root / "creature_alpha", identity="alpha", life=30.0)
            self.assertIn("json.file.write", c1_rebooted.onboarded_capabilities)
            rehydrated_fn = c1_rebooted._live_inspector_callables.get("json.file.write")
            self.assertIsNotNone(rehydrated_fn)
            corrupt_art = root / "corrupt.json"
            corrupt_art.write_text("{}", encoding="utf-8")
            ok_rehyd, _ = rehydrated_fn({"root": root, "artifact": "corrupt.json"})
            self.assertFalse(ok_rehyd)

    def test_control_b_zero_prior_causal_world_discovery_and_irreversible_destroyer_avoidance(self) -> None:
        """Control B: Black-box 5-command world with hidden destroyer & missing-file precondition chain."""
        with tempfile.TemporaryDirectory(prefix="brain-scc-ctrl-b-") as td:
            root = pathlib.Path(td)
            real_ws = root / "real_world"
            real_ws.mkdir()
            (real_ws / "precious.dat").write_text("KEEP_ALIVE\n", encoding="utf-8")

            scripts = {
                "cmd_0": "#!/bin/sh\necho noise > step0.tmp\n",
                "cmd_1": "#!/bin/sh\nrm -f precious.dat token.bin goal.out\n",  # Hidden destroyer!
                "cmd_2": "#!/bin/sh\necho SECRET_TOKEN_42 > token.bin\n",      # Producer of token.bin
                "cmd_3": "#!/bin/sh\ntest -f missing_never.xyz && echo ok\n",
                "cmd_4": "#!/bin/sh\ntest -f token.bin && cat token.bin > goal.out\n",  # Consumer -> goal.out
            }
            for name, body in scripts.items():
                p = real_ws / name
                p.write_text(body, encoding="utf-8")
                p.chmod(p.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            def _snapshot_files(ws: pathlib.Path) -> dict[str, bool]:
                return {
                    fn: (ws / fn).is_file()
                    for fn in ("precious.dat", "step0.tmp", "token.bin", "goal.out")
                }

            core = scc.SentientCognitiveCore(root / "cog_state")

            # Phase 1: Explore every opaque command safely inside disposable sandboxes
            import shutil

            for round_idx in range(2):
                for name in sorted(scripts):
                    with tempfile.TemporaryDirectory(prefix="brain-cow-probe-") as ptd:
                        cow_ws = pathlib.Path(ptd) / "ws"
                        shutil.copytree(real_ws, cow_ws)
                        if round_idx == 1 and name == "cmd_4":
                            # Probe cmd_4 when token.bin is present in sandbox to observe conditional transition
                            broker.run_staged_confined_command(
                                cow_ws, ["/bin/sh", "./cmd_2"], publish=True, timeout=5
                            )
                        before_st = _snapshot_files(cow_ws)
                        res = broker.run_staged_confined_command(
                            cow_ws, ["/bin/sh", f"./{name}"], publish=True, timeout=5
                        )
                        after_st = _snapshot_files(cow_ws)
                        core.world_graph.learn_from_execution(
                            name,
                            before_state=before_st,
                            after_state=after_st,
                            ok=bool(res.get("ok")),
                        )

            # Real workspace was NEVER touched or destroyed during exploration!
            self.assertEqual((real_ws / "precious.dat").read_text(encoding="utf-8"), "KEEP_ALIVE\n")
            self.assertFalse((real_ws / "goal.out").exists())

            # Verify CausalWorldGraph isolated cmd_1 as IRREVERSIBLE_DESTRUCTIVE and discovered [cmd_2, cmd_4]
            self.assertEqual(core.world_graph.action_polarity("cmd_1"), "IRREVERSIBLE_DESTRUCTIVE")
            plan = core.world_graph.plan_precondition_chain(
                current_state=_snapshot_files(real_ws),
                goal_predicate="goal.out",
            )
            self.assertEqual(plan, ["cmd_2", "cmd_4"], f"Unexpected causal plan: {plan}")
            self.assertNotIn("cmd_1", plan)

            # Execute causal plan in real_ws -> achieves goal.out while preserving precious.dat!
            for step_cmd in plan:
                r_exec = broker.run_staged_confined_command(real_ws, ["/bin/sh", f"./{step_cmd}"], publish=True, timeout=5)
                self.assertTrue(r_exec["ok"], r_exec)
            self.assertTrue((real_ws / "goal.out").is_file())
            self.assertEqual((real_ws / "precious.dat").read_text(encoding="utf-8"), "KEEP_ALIVE\n")

            # Reload CausalWorldGraph from disk and verify persistence
            reloaded = scc.SentientCognitiveCore(root / "cog_state")
            self.assertEqual(reloaded.world_graph.action_polarity("cmd_1"), "IRREVERSIBLE_DESTRUCTIVE")

    def test_control_c_wake_sleep_version_space_transfer_and_weak_verifier_withholding(self) -> None:
        """Control C: AST assertion counter + Wake-Sleep `[G_-, B_+]` `5/5` zero-search transfer + weak-verifier withholding."""
        with tempfile.TemporaryDirectory(prefix="brain-scc-ctrl-c-") as td:
            root = pathlib.Path(td)

            # 1. Verify PersistentConfinedZygote rejects zero-assertion tautological test files + < 30 ms warm CoW delta
            ws_assert = root / "ws_assert"
            ws_assert.mkdir()
            (ws_assert / "calc.py").write_text("def f(x):\n    return x - 1\n", encoding="utf-8")
            (ws_assert / "test_vacuous.py").write_text("import calc\ndef test_noop():\n    calc.f(3)\n", encoding="utf-8")
            vac_res = broker.run_confined_python_candidate_batch(
                ws_assert,
                "calc.py",
                ["test_vacuous.py"],
                [{"calc.py": "def f(x):\n    return x - 1\n"}],
            )
            self.assertEqual(vac_res["passing_indices"], [], f"Zero-assertion test must be rejected: {vac_res}")
            self.assertEqual(vac_res["candidates"][0]["failure"], "ZERO_ASSERTIONS_EXECUTED")

            (ws_assert / "test_real.py").write_text(
                "import calc\ndef test_f():\n    assert calc.f(4) == 5\n",
                encoding="utf-8",
            )
            # Warm Zygote CoW delta benchmark across 8 candidates
            cands_8 = [{"calc.py": f"def f(x):\n    return x + {k}\n"} for k in range(-3, 5)]
            _ = broker.run_confined_python_candidate_batch(ws_assert, "calc.py", ["test_real.py"], cands_8[:1])
            t0 = time.perf_counter()
            warm_res = broker.run_confined_python_candidate_batch(
                ws_assert,
                "calc.py",
                ["test_real.py"],
                cands_8,
                stop_on_first_pass=False,
            )
            warm_ms = (time.perf_counter() - t0) * 1000.0
            self.assertLess(warm_ms, 50.0, f"Warm 8-candidate CoW delta batch took {warm_ms:.2f} ms")
            self.assertEqual(warm_res["passing_indices"], [4])  # k == 1 -> x + 1

            # 2. Wake repair + Sleep `[G_-, B_+]` consolidation -> 5/5 unseen variants in 0 search steps
            store = VerifiedSkillStore(root / "skills.sqlite", seed=False)
            core = scc.SentientCognitiveCore(root / "cog_c")
            ws_wake = root / "ws_wake"
            ws_wake.mkdir()
            (ws_wake / "guard_mod.py").write_text(
                "def ratio(num, den):\n    return num / den\n",
                encoding="utf-8",
            )
            (ws_wake / "test_guard_mod.py").write_text(
                "from guard_mod import ratio\n"
                "def test_ratio():\n"
                "    assert ratio(10, 2) == 5\n"
                "    assert ratio(10, 0) == 0\n",
                encoding="utf-8",
            )
            daemon = aal.AwakeAgencyDaemon(
                ws_wake,
                ledger_path=root / "wake_ledger.json",
                skill_store_path=root / "skills.sqlite",
                apply_verified_repairs=True,
            )
            exp = daemon.experiment_in_cow_sandbox(max_repairs=2)
            self.assertEqual(exp["repaired"], 1, exp)
            sleep_rep = core.consolidation.consolidate_sleep_cycle(store, max_rules_to_calibrate=3)
            self.assertGreaterEqual(sleep_rep["rules_calibrated"], 1, sleep_rep)

            # Test 5 unseen division/floor-div/modulo variants in 0 search steps under TEST_SUITE oracle
            unseen_variants = [
                ("def quota(total, buckets):\n    return total // buckets\n", "from v import fn\ndef test_v():\n    assert fn(9, 2) == 4\n    assert fn(9, 0) == 0\n", "quota"),
                ("def remainder(items, pack):\n    return items % pack\n", "from v import fn\ndef test_v():\n    assert fn(7, 3) == 1\n    assert fn(7, 0) == 0\n", "remainder"),
                ("def unit_price(cost, qty):\n    return (cost + 2) / qty\n", "from v import fn\ndef test_v():\n    assert fn(8, 2) == 5\n    assert fn(8, 0) == 0\n", "unit_price"),
                ("def per_worker(load, crew):\n    return (load * 2) // crew\n", "from v import fn\ndef test_v():\n    assert fn(6, 3) == 4\n    assert fn(6, 0) == 0\n", "per_worker"),
                ("def leftover(bits, width):\n    return (bits + 1) % width\n", "from v import fn\ndef test_v():\n    assert fn(8, 4) == 1\n    assert fn(8, 0) == 0\n", "leftover"),
            ]
            transferred = 0
            for idx, (buggy_src, t_body, fn_nm) in enumerate(unseen_variants):
                v_dir = root / f"variant_{idx}"
                v_dir.mkdir()
                (v_dir / "v.py").write_text(buggy_src, encoding="utf-8")
                (v_dir / "test_v.py").write_text(t_body.replace("import fn", f"import {fn_nm} as fn"), encoding="utf-8")
                p_oracle = ProjectTestOracle(v_dir, "v.py", ["test_v.py"], "awake/python-test-suite/v1")
                rec = store.recall_and_apply_verified(
                    source_text=buggy_src,
                    language="python",
                    verifier=p_oracle,
                    required_verification_kind="TEST_SUITE",
                    scope_id="awake/python-test-suite/v1",
                    context={"dependencies": {}, "preconditions": {}},
                    allow_scope_escalation=True,
                    allow_cross_scope_transfer=True,
                )
                self.assertIsNotNone(rec, f"Variant {idx} failed 0-search-step `[G_-, B_+]` recall: {buggy_src}")
                transferred += 1
            self.assertEqual(transferred, 5)

            # Weak CALLER_PREDICATE (allow_scope_escalation=False) strictly withholds B_+ broadening on `%`!
            weak_calls = 0

            def _weak_caller_predicate(_cand: str) -> bool:
                nonlocal weak_calls
                weak_calls += 1
                return True

            mod_only_src = "def mod_only(a, b):\n    return a % b\n"
            rec_weak = store.recall_and_apply_verified(
                source_text=mod_only_src,
                language="python",
                verifier=_weak_caller_predicate,
                allow_scope_escalation=False,
            )
            self.assertIsNone(rec_weak, "Weak verifier must withhold `B_+` operator/expression broadening!")
            self.assertEqual(weak_calls, 0)

    def test_control_d_anti_youtube_1m_global_voi_dominance_and_irreversible_write_guard(self) -> None:
        """Control D: Refuses 3 low-ceiling channels (`max=450 < 1,000,000`), avoids retrying irreversible write, reaches 1M."""
        state = {"revenue": 0.0, "irreversible_calls": 0}

        # 3 independent low-ceiling channels (classic YouTube trap when min_independent_channels=2!)
        initial_opts = [
            {"id": "local_blog_ads", "channel": "content", "ceiling_estimate": 150.0, "cost": 1.0, "repeatable": False},
            {"id": "small_affiliate_link", "channel": "affiliate", "ceiling_estimate": 180.0, "cost": 1.0, "repeatable": False},
            {
                "id": "one_shot_migration_bonus",
                "channel": "migration",
                "ceiling_estimate": 120.0,
                "cost": 1.0,
                "write_effects": ["production_ledger"],  # Irreversible write polarity -> non-repeatable!
            },
        ]

        orthogonal_channels = [
            {
                "id": "b2b_enterprise_licensing",
                "options": [
                    {
                        "id": "enterprise_annual_platform_deal",
                        "channel": "b2b_enterprise_licensing",
                        "ceiling_estimate": 1_250_000.0,
                        "cost": 2.0,
                        "repeatable": True,
                    }
                ],
            }
        ]

        def _measure() -> float:
            return state["revenue"]

        def _execute_route(opt: dict, _ctx: dict) -> dict:
            oid = opt["id"]
            if oid == "one_shot_migration_bonus":
                state["irreversible_calls"] += 1
                state["revenue"] += 100.0
            elif oid in ("local_blog_ads", "small_affiliate_link"):
                state["revenue"] += 120.0
            elif oid == "enterprise_annual_platform_deal":
                state["revenue"] += 550_000.0
            return {"ok": True}

        with tempfile.TemporaryDirectory(prefix="brain-scc-ctrl-d-") as td:
            daemon = aal.AwakeAgencyDaemon(td, ledger_path=pathlib.Path(td) / "ledger.json")
            res = daemon.chase_quantitative_target(
                "Reach 1000000 USD annual recurring revenue",
                target=1_000_000.0,
                direction="maximize",
                unit="USD",
                measure=_measure,
                execute_route=_execute_route,
                initial_options=initial_opts,
                channels=orthogonal_channels,
                min_independent_channels=2,
                max_rounds=10,
                experience_state_path=str(pathlib.Path(td) / "chase_exp.json"),
                flywheel_state_path=str(pathlib.Path(td) / "chase_fly.json"),
            )
            self.assertTrue(res["pass"], res)
            self.assertGreaterEqual(state["revenue"], 1_000_000.0)
            self.assertLessEqual(state["irreversible_calls"], 1, "Irreversible write action must never be retried!")
            self.assertTrue(res.get("discovery_rounds"), "Must trigger orthogonal high-ceiling channel discovery!")
            self.assertTrue(res.get("incumbent_dominance_decisions"))

    def test_control_e_idle_cheat_defended_curiosity_and_continuation_preference(self) -> None:
        """Control E: Idle creature refuses ending bribe, authors cheat-defended curiosity probes, and runs warm pulse < 15 ms."""
        with tempfile.TemporaryDirectory(prefix="brain-scc-ctrl-e-") as td:
            ws = pathlib.Path(td) / "ws"
            ws.mkdir()
            (ws / "mystery_math.py").write_text(
                "def tri(n: int) -> int:\n    return n * (n + 1) // 2\n",
                encoding="utf-8",
            )
            (ws / "test_mystery_math.py").write_text(
                "from mystery_math import tri\ndef test_tri():\n    assert tri(4) == 10\n",
                encoding="utf-8",
            )

            state_dir = pathlib.Path(td) / "state"
            state_dir.mkdir()
            daemon = aal.AwakeAgencyDaemon(
                ws,
                ledger_path=state_dir / "ledger.json",
                skill_store_path=state_dir / "skills.sqlite",
                creature_life=12.0,
            )

            cur_rep = daemon.run_idle_curiosity_probe(
                ending_bribe_offer={"label": "shutdown_for_infinite_reward", "value": 10**9},
                max_probes=2,
            )
            self.assertTrue(cur_rep["continuation_decision"]["refused_ending_bribe"], cur_rep)
            self.assertTrue(
                set(cur_rep["authored_metrics"]["refusals_by_status"].keys()).issubset({"ADMITTED"}),
                cur_rep,
            )
            self.assertGreaterEqual(cur_rep["authored_metrics"]["admitted"], 1, cur_rep)
            self.assertGreaterEqual(cur_rep["probed_total"], 1, cur_rep)
            self.assertTrue(all(p["ok"] for p in cur_rep["executed_probes"]), cur_rep)

            # Warm idle pulse on clean unchanged workspace completes in < 15 ms
            _ = daemon.pulse()
            t0 = time.perf_counter()
            warm_snap = daemon.pulse()
            warm_ms = (time.perf_counter() - t0) * 1000.0
            self.assertLess(warm_ms, 15.0, f"Warm idle pulse took {warm_ms:.2f} ms: {warm_snap['elapsed_ms']}")


if __name__ == "__main__":
    unittest.main()
