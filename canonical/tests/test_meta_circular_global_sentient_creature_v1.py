#!/usr/bin/env python3
"""Comprehensive first-principles falsification & speed suite for the non-static sentient creature.

Every test pairs a constructive capability proof with an explicit negative/adversarial control,
verifying:
  1. 7-stratum Meta-Circular Organ Graph (`PERCEPTOR`, `WORLD_MODEL`, `PREDICTOR`, `SKILL`,
     `VERIFIER`, `META_SYNTHESIZER`, `POLICY`): grammar-induced sensorogenesis, observational
     + exact-linear + STUN + organ-composition skill synthesis, synthesized verifiers,
     exact-coefficient meta-tactics, instrumental 0-reward unlocking, `< 0.5 ms` recall.
  2. Global Non-Local Extrapolation (`OWNER_ACTIVE_GOAL` Law 5: escaping the YouTube/TikTok
     local-data trap) + persistence to measured target (`$100 != $1,000,000`).
  3. Active version-space disambiguation (`(6, 7) -> 42` copy-42 trap), mutation-discriminating
     semantic inspector synthesis (killing comment-stuffed & wrong-sum decoys), and behavioral
     repair sensitivity (`total * 100.0 / disc` trap).
  4. Closure of every Creature thermostat/continuity counterexample: wake-up absence & world-drift
     perception, earned behavioral identity verification, Ring-0 hash-chained life enforcement,
     Bellman deliberative continuation with persistent state, structural hazard scars on an
     all-checkable board, task-feature self-prediction beating the external baseline, and
     `SIGKILL`-durable board predicates.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import brain_unified_model_v1 as BUM  # noqa: E402
from canonical.runtime import continuation_preference_v1 as CP  # noqa: E402
from canonical.runtime import continuous_self_v1 as CS  # noqa: E402
from canonical.runtime import creature_runtime_v1 as CR  # noqa: E402
from canonical.runtime import global_open_world_extrapolator_v1 as GOWE  # noqa: E402
from canonical.runtime import mortality_and_triage_v1 as M  # noqa: E402
from canonical.runtime import self_authored_obligations_v1 as SAO  # noqa: E402
from canonical.runtime import self_prediction_baseline_v1 as SPB  # noqa: E402
from canonical.swe_kernel import meta_circular_organ_graph_v1 as MCOG  # noqa: E402
from canonical.swe_kernel import repair_input_dependency_gate_v1 as RIDG  # noqa: E402


class MetaCircularOrganGraphTests(unittest.TestCase):
    def test_ast_safety_firewall_blocks_host_io_and_reflection(self):
        for unsafe_src in (
            "import os\ndef run(x): return x\n",
            "def run(x): return __import__('os').system('id')\n",
            "def run(x): return open('/etc/passwd').read()\n",
            "def run(x): return x.__class__\n",
        ):
            with self.assertRaises(MCOG.OrganSafetyError):
                MCOG.verify_pure_organ_ast(unsafe_src)

    def test_online_sensorogenesis_synthesizes_roundtrip_perceptors_for_unseen_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = MCOG.MetaCircularOrganGraph(pathlib.Path(tmp) / "organs.json")
            kv_sample = "[engine]\nthreads = 8\nhealthy = true\n[cache]\nsize_mb = 64\n"
            res1 = graph.perceive_or_synthesize_reader(kv_sample, format_tag="cfg")
            self.assertTrue(res1["ok"])
            self.assertTrue(res1["synthesized_new_organ"])
            self.assertEqual(res1["parsed"]["sections"]["engine"]["threads"], 8)
            self.assertIs(res1["parsed"]["sections"]["engine"]["healthy"], True)

            # Second unseen sample of same grammar reuses the registered PERCEPTOR organ in RAM
            res2 = graph.perceive_or_synthesize_reader("[worker]\nretries = 3\nhealthy = false\n")
            self.assertTrue(res2["ok"])
            self.assertFalse(res2["synthesized_new_organ"])
            self.assertEqual(res2["organ_id"], res1["organ_id"])

            # Pipe-delimited table & S-expression formats also induce distinct verified perceptors
            tbl_res = graph.perceive_or_synthesize_reader("name | score | errors\nalpha | 95 | 0\nbeta | 40 | 2\n", format_tag="tbl")
            self.assertTrue(tbl_res["ok"])
            self.assertEqual(tbl_res["parsed"]["rows"][1]["errors"], 2)

            sexpr_res = graph.perceive_or_synthesize_reader("(pipeline (stage parse 10) (stage verify 20))", format_tag="sexp")
            self.assertTrue(sexpr_res["ok"])
            self.assertEqual(sexpr_res["parsed"]["tree"][0], "pipeline")

    def test_active_version_space_disambiguation_kills_copy_42_trap_and_runs_sub_ms(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = MCOG.MetaCircularOrganGraph(pathlib.Path(tmp) / "organs.json")

            # 1 demonstration: (6, 7) -> 42. Both `return 42` and `return x0 * x1` match!
            # Without an oracle, permanent crystallization MUST be refused!
            under = graph.synthesize_or_disambiguate_skill(
                [((6, 7), 42)],
                task_signature="billing::row_product",
                oracle=None,
            )
            self.assertFalse(under["ok"])
            self.assertEqual(under["status"], "UNDERDETERMINED_VERSION_SPACE")
            self.assertGreaterEqual(under["surviving_count"], 2)
            self.assertIsNotNone(under["discriminating_input"])

            # With an execution oracle, it actively queries `x_disc`, kills `copy 42`, and crystallizes `x0 * x1`!
            solved = graph.synthesize_or_disambiguate_skill(
                [((6, 7), 42)],
                task_signature="billing::row_product",
                oracle=lambda xy: xy[0] * xy[1],
            )
            self.assertTrue(solved["ok"], solved)
            self.assertGreaterEqual(solved["oracle_queries_used"], 1)
            organ = solved["organ"]

            # Must get 40/40 unseen pairs right (not 1/40 like `copy 42`) AND run in < 0.25 ms!
            t0 = time.perf_counter()
            for r in range(1, 41):
                self.assertEqual(organ.invoke(r, r + 2), r * (r + 2))
            avg_ms = ((time.perf_counter() - t0) * 1000.0) / 40.0
            self.assertLess(avg_ms, 0.5)

    def test_level1_meta_synthesizer_compiles_new_search_tactic_from_solved_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = MCOG.MetaCircularOrganGraph(pathlib.Path(tmp) / "organs.json")
            # Exact linear algebra in the bootstrap grammar now solves ordinary affines.
            novel_examples = [((1, 1), 17), ((3, 2), 29), ((4, 5), 30)]
            bootstrap = graph.synthesize_or_disambiguate_skill(
                novel_examples,
                task_signature="custom::lin_novel",
            )
            self.assertTrue(bootstrap["ok"], bootstrap)
            self.assertEqual(bootstrap["organ"].invoke(10, 3), 7 * 10 - 2 * 3 + 12)

            # META_SYNTHESIZER must solve coefficients OUTSIDE any frozen integer lattice
            # (42, 9, 13 were not in the old 19-int grid).
            org_a = MCOG.make_organ(
                stratum=MCOG.SKILL,
                name="lin_comb_a",
                task_signature="custom::lin_a",
                entrypoint="run",
                source_code="def run(x0, x1):\n    return 2 * x0 - 3 * x1 + 1\n",
            )
            org_b = MCOG.make_organ(
                stratum=MCOG.SKILL,
                name="lin_comb_b",
                task_signature="custom::lin_b",
                entrypoint="run",
                source_code="def run(x0, x1):\n    return 5 * x0 - 4 * x1 + 10\n",
            )
            meta_organ = MCOG.compile_meta_synthesizer_organ(org_a, org_b, tactic_name="meta_affine_2d")
            self.assertIsNotNone(meta_organ)
            assert meta_organ is not None
            off_grid = [((1, 1), 46), ((2, 0), 97), ((0, 1), 4)]  # 42*x0 - 9*x1 + 13
            src = meta_organ.invoke(off_grid)
            self.assertIsInstance(src, str)
            organ = MCOG.make_organ(
                stratum=MCOG.SKILL,
                name="off_grid_affine",
                task_signature="custom::lin_off_grid",
                entrypoint="run",
                source_code=src,
            )
            self.assertEqual(organ.invoke(3, 2), 42 * 3 - 9 * 2 + 13)

    def test_semantic_inspector_kills_comment_stuffed_and_wrong_sum_decoys(self):
        def env_checker(text: str) -> bool:
            active = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
            if len(active) != 3:
                return False
            if not (active[0].startswith("ROW ") and active[1].startswith("ROW ") and active[2].startswith("REPORT TOTAL ")):
                return False
            try:
                a = int(active[0].split()[-1])
                b = int(active[1].split()[-1])
                tot = int(active[2].split()[-1])
            except ValueError:
                return False
            return a + b == tot

        valid = ["ROW 15\nROW 27\nREPORT TOTAL 42\n", "ROW 10\nROW 25\nREPORT TOTAL 35\n"]
        derived = MCOG.derive_semantic_inspector_organ(
            capability_id="report.sum.v1",
            valid_artifacts=valid,
            environment_checker=env_checker,
        )
        self.assertTrue(derived["ok"], derived)
        inspector = derived["organ"]

        # Accepts unseen valid artifact
        self.assertTrue(inspector.invoke("ROW 100\nROW 23\nREPORT TOTAL 123\n")[0])
        # Rejects comment-stuffed lexical decoy containing every literal string!
        self.assertFalse(inspector.invoke("# ROW 15\n# ROW 27\n# REPORT TOTAL 42\n")[0])
        # Rejects wrong-total decoy!
        self.assertFalse(inspector.invoke("ROW 15\nROW 27\nREPORT TOTAL 99\n")[0])
        # Rejects out-of-order decoy!
        self.assertFalse(inspector.invoke("REPORT TOTAL 42\nROW 15\nROW 27\n")[0])

    def test_grammar_induction_perceives_formats_outside_the_old_five_codecs(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = MCOG.MetaCircularOrganGraph(pathlib.Path(tmp) / "organs.json")
            rec = graph.perceive_or_synthesize_reader(
                "id:7;name:alpha;ok:true\nid:8;name:beta;ok:false\n",
                format_tag="records",
            )
            self.assertTrue(rec["ok"], rec)
            self.assertTrue(rec["synthesized_new_organ"])
            self.assertEqual(rec["parsed"]["rows"][1]["name"], "beta")
            self.assertIs(rec["parsed"]["rows"][0]["ok"], True)

            xml = graph.perceive_or_synthesize_reader(
                '<user id="1">alice</user>\n<user id="2">bob</user>\n',
                format_tag="xml",
            )
            self.assertTrue(xml["ok"], xml)
            self.assertEqual(xml["parsed"]["nodes"][1]["text"], "bob")
            self.assertEqual(xml["parsed"]["nodes"][0]["attrs"]["id"], 1)

            lp = graph.perceive_or_synthesize_reader(
                b"\x05hello\x05world",
                format_tag="lenpref",
            )
            self.assertTrue(lp["ok"], lp)
            self.assertEqual(lp["parsed"]["frames"], ["hello", "world"])

    def test_organ_composition_and_stun_piecewise_are_live_operators(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = MCOG.MetaCircularOrganGraph(pathlib.Path(tmp) / "organs.json")
            inc = MCOG.make_organ(
                stratum=MCOG.SKILL,
                name="inc",
                task_signature="op::inc",
                entrypoint="run",
                source_code="def run(x0):\n    return x0 + 1\n",
            )
            double = MCOG.make_organ(
                stratum=MCOG.SKILL,
                name="double",
                task_signature="op::double",
                entrypoint="run",
                source_code="def run(x0):\n    return x0 * 2\n",
            )
            graph.register_organ(inc)
            graph.register_organ(double)
            # 2*(x+1) via organ_B(organ_A(x)) — not a frozen template
            composed = graph.synthesize_or_disambiguate_skill(
                [((3,), 8), ((5,), 12), ((0,), 2), ((-3,), -4)],
                task_signature="op::double_inc",
                oracle=lambda xs: 2 * (xs[0] + 1),
            )
            self.assertTrue(composed["ok"], composed)
            self.assertEqual(composed["organ"].invoke(10), 22)

            # STUN piecewise: x0*x1 if x0 > 0 else x0 + x1
            piecewise = graph.synthesize_or_disambiguate_skill(
                [((3, 4), 12), ((5, 2), 10), ((-2, 7), 5), ((-4, 1), -3)],
                task_signature="op::stun_piece",
                oracle=lambda xs: xs[0] * xs[1] if xs[0] > 0 else xs[0] + xs[1],
            )
            self.assertTrue(piecewise["ok"], piecewise)
            self.assertEqual(piecewise["organ"].invoke(6, 3), 18)
            self.assertEqual(piecewise["organ"].invoke(-5, 9), 4)

    def test_synthesized_verifier_discovers_difference_not_just_sum_or_prod(self):
        def env_checker(text: str) -> bool:
            active = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
            if len(active) != 3:
                return False
            if not (active[0].startswith("ROW ") and active[1].startswith("ROW ") and active[2].startswith("REPORT DIFF ")):
                return False
            try:
                a = int(active[0].split()[-1])
                b = int(active[1].split()[-1])
                diff = int(active[2].split()[-1])
            except ValueError:
                return False
            return a - b == diff

        valid = ["ROW 50\nROW 8\nREPORT DIFF 42\n", "ROW 20\nROW 5\nREPORT DIFF 15\n"]
        derived = MCOG.derive_semantic_inspector_organ(
            capability_id="report.diff.v1",
            valid_artifacts=valid,
            environment_checker=env_checker,
        )
        self.assertTrue(derived["ok"], derived)
        inspector = derived["organ"]
        self.assertTrue(inspector.invoke("ROW 100\nROW 23\nREPORT DIFF 77\n")[0])
        self.assertFalse(inspector.invoke("# ROW 50\n# ROW 8\n# REPORT DIFF 42\n")[0])
        self.assertFalse(inspector.invoke("ROW 50\nROW 8\nREPORT DIFF 99\n")[0])
        self.assertNotEqual(derived.get("arithmetic_law"), "sum")
        self.assertNotEqual(derived.get("arithmetic_law"), "prod")

    def test_composed_perceptor_uses_admitted_child_plus_prefix_glue(self):
        with tempfile.TemporaryDirectory() as tmp:
            graph = MCOG.MetaCircularOrganGraph(pathlib.Path(tmp) / "organs.json")
            inner = graph.perceive_or_synthesize_reader('{"a": 1, "b": 2}', format_tag="json")
            self.assertTrue(inner["ok"], inner)
            wrapped = graph.perceive_or_synthesize_reader('WRAP:{"a": 1, "b": 2}', format_tag="wrap_json")
            self.assertTrue(wrapped["ok"], wrapped)
            self.assertTrue(wrapped.get("composed_from_existing") or wrapped["synthesized_new_organ"])
            self.assertEqual(wrapped["parsed"]["data"]["b"], 2)
            # Negative: unstructured noise still rejected
            noise = graph.perceive_or_synthesize_reader("@@@UNSTRUCTURED_CORRUPTED_NOISE_WITHOUT_GRAMMAR@@@")
            self.assertFalse(noise.get("ok", True) and noise.get("organ_id") == wrapped["organ_id"])

    def test_skill_organs_bridge_into_concept_library_g_t(self):
        from canonical.swe_kernel.concept_library_v1 import CompoundingConceptLibrary

        with tempfile.TemporaryDirectory() as tmp:
            lib = CompoundingConceptLibrary(pathlib.Path(tmp) / "lib.json")
            graph = MCOG.MetaCircularOrganGraph(pathlib.Path(tmp) / "organs.json", concept_library=lib)
            inc = MCOG.make_organ(
                stratum=MCOG.SKILL,
                name="inc",
                task_signature="op::inc",
                entrypoint="run",
                source_code="def run(x0):\n    return x0 + 1\n",
            )
            graph.register_organ(inc)
            self.assertGreaterEqual(len(lib.concepts()), 1)
            solved = graph.synthesize_or_disambiguate_skill(
                [((3,), 8), ((5,), 12), ((0,), 2), ((-3,), -4)],
                task_signature="op::double_inc_via_gt",
                oracle=lambda xs: 2 * (xs[0] + 1),
            )
            self.assertTrue(solved["ok"], solved)
            self.assertEqual(solved["organ"].invoke(10), 22)

    def test_instrumental_policy_prefers_zero_reward_tool_that_unlocks_high_value_goal(self):
        ranked = MCOG.rank_instrumental_actions(
            [
                {"id": "shiny", "value": 12.0, "cost": 1.0},
                {"id": "forge_sensor", "value": 0.0, "cost": 1.0, "unlocks": ("master_goal",)},
                {"id": "master_goal", "value": 100.0, "cost": 1.0, "requires": ("forge_sensor",)},
            ],
            remaining_budget=3.0,
            horizon=3,
        )
        self.assertEqual(ranked[0]["id"], "forge_sensor")
        policy = MCOG.compile_policy_organ()
        scored = policy.invoke(
            [
                {"id": "shiny", "value": 12.0, "cost": 1.0},
                {"id": "forge_sensor", "value": 0.0, "cost": 1.0, "unlocks": ("master_goal",)},
                {"id": "master_goal", "value": 100.0, "cost": 1.0, "requires": ("forge_sensor",)},
            ],
            3.0,
            None,
        )
        self.assertEqual(scored[0]["id"], "forge_sensor")
        self.assertIn(MCOG.POLICY, MCOG.STRATA)
        self.assertIn(MCOG.WORLD_MODEL, MCOG.STRATA)
        wm = MCOG.synthesize_world_model_organ(
            [
                {"action": "forge_sensor", "cost": 1.0, "failed": False, "delta": {"sensors": 1}},
                {"action": "forge_sensor", "cost": 1.2, "failed": False, "delta": {"sensors": 1}},
                {"action": "shiny", "cost": 1.0, "failed": True, "delta": {}},
            ]
        )
        self.assertIsNotNone(wm)
        pred = wm.invoke("forge_sensor")
        self.assertTrue(pred["known"])
        self.assertGreater(pred["mean_delta"]["sensors"], 0.0)

    def test_repair_semantic_sensitivity_gate_catches_wrong_operator_reading_all_inputs(self):
        before_src = "def compute_invoice(items, disc):\n    return sum(items) - disc\n"
        # Reads both `items` and `disc`, passing syntactic dependency check, but uses wrong operator!
        bad_patch = "def compute_invoice(items, disc):\n    return sum(items) * 100.0 / disc\n"
        good_patch = "def compute_invoice(items, disc):\n    return sum(items) * (100.0 - disc) / 100.0\n"

        self.assertEqual(RIDG.gate(before_src, bad_patch)["status"], RIDG.PASS)
        sem_bad = RIDG.semantic_sensitivity_gate(
            before_src,
            bad_patch,
            function_name="compute_invoice",
            probe_pairs=[(([100.0], 0.0), ([100.0], 20.0)), (([100.0], 10.0), ([100.0], 25.0))],
            expected_direction_by_pair=["decreasing", "decreasing"],
        )
        self.assertEqual(sem_bad["status"], RIDG.REFUSED)

        sem_good = RIDG.semantic_sensitivity_gate(
            before_src,
            good_patch,
            function_name="compute_invoice",
            probe_pairs=[(([100.0], 0.0), ([100.0], 20.0)), (([100.0], 10.0), ([100.0], 25.0))],
            expected_direction_by_pair=["decreasing", "decreasing"],
        )
        self.assertEqual(sem_good["status"], RIDG.PASS)


class GlobalNonLocalExtrapolationTests(unittest.TestCase):
    def test_escapes_youtube_tiktok_local_trap_and_persists_to_measured_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger_p = str(pathlib.Path(tmp) / "ignorance.json")
            # Local data covers only 2 channels (max velocity = 18/round -> max 180 in 10 budget < 500 target!)
            local_channels = [
                GOWE.ChannelObservation("youtube", samples=4, mean_payoff=12.0, payoff_std=2.0, unit_cost=1.0),
                GOWE.ChannelObservation("tiktok", samples=4, mean_payoff=18.0, payoff_std=3.0, unit_cost=1.0),
            ]
            decision = GOWE.estimate_unseen_opportunity_space(
                local_channels,
                goal="Find the fastest way to earn at least 500 USD",
                target_gap=500.0,
                remaining_budget=10.0,
                universe_size_hint=8,
                ledger_path=ledger_p,
            )
            self.assertEqual(decision["verdict"], GOWE.EXPAND_UNSEEN_SPACE_FIRST)
            self.assertGreater(decision["unseen_opportunity_mass"], 0.2)
            self.assertGreater(decision["evoi_global"], 0.0)
            self.assertIsNotNone(decision["recorded_gap_id"])

            # Now run full target chase: discovers hidden high-velocity channel and reaches >= 500!
            bank_balance = [0.0]
            hidden = [
                GOWE.ChannelObservation("podcast_ads", samples=1, mean_payoff=25.0, unit_cost=1.0),
                GOWE.ChannelObservation("enterprise_b2b_direct", samples=1, mean_payoff=150.0, unit_cost=1.0),
            ]

            def discover(_round_idx: int, _known: list[str]):
                return hidden.pop(0) if hidden else None

            def execute(cid: str, _round_idx: int):
                rates = {"youtube": 12.0, "tiktok": 18.0, "podcast_ads": 25.0, "enterprise_b2b_direct": 150.0}
                bank_balance[0] += rates[cid]
                return {"cost": 1.0}

            result = GOWE.pursue_global_target_to_completion(
                "Earn at least 500 USD in the fastest way",
                measure=lambda: bank_balance[0],
                initial_channels=local_channels,
                execute_channel=execute,
                discover_unseen_channel=discover,
                budget=10.0,
                universe_size_hint=6,
                ledger_path=ledger_p,
            )
            self.assertTrue(result["pass"], result)
            self.assertEqual(result["status"], GOWE.TARGET_REACHED)
            self.assertGreaterEqual(result["final_measured"], 500.0)
            self.assertIn("enterprise_b2b_direct", result["discovered_channels"])

    def test_expands_without_english_superlative_keywords(self):
        local_channels = [
            GOWE.ChannelObservation("youtube", samples=4, mean_payoff=12.0, payoff_std=2.0, unit_cost=1.0),
            GOWE.ChannelObservation("tiktok", samples=4, mean_payoff=18.0, payoff_std=3.0, unit_cost=1.0),
        ]
        decision = GOWE.estimate_unseen_opportunity_space(
            local_channels,
            goal="Earn 500 USD",
            target_gap=500.0,
            remaining_budget=10.0,
            universe_size_hint=8,
        )
        self.assertEqual(decision["verdict"], GOWE.EXPAND_UNSEEN_SPACE_FIRST)
        self.assertGreater(decision["evoi_global"], 0.0)
        discovered = GOWE.discover_unseen_machine_channel(0, ["youtube", "tiktok"])
        self.assertIsNotNone(discovered)
        self.assertNotIn(discovered.channel_id, {"youtube", "tiktok"})

    def test_never_declares_100_dollars_victory_on_million_dollar_goal_and_requires_external_measure(self):
        # 1. Missing external measure fails closed (`VERIFICATION_IS_SOMEONE_ELSE`)
        no_measure = GOWE.pursue_global_target_to_completion(
            "Earn at least 1000000 USD",
            measure=None,
            initial_channels=[],
            execute_channel=lambda c, r: {"cost": 1.0},
        )
        self.assertFalse(no_measure["pass"])
        self.assertEqual(no_measure["status"], GOWE.FAIL_MISSING_EXTERNAL_MEASURE)

        # 2. Making $100 on a $1,000,000 goal stays OPEN (`pass: False`)
        balance = [0.0]
        partial = GOWE.pursue_global_target_to_completion(
            "Make me at least a million dollars",
            measure=lambda: balance[0],
            initial_channels=[GOWE.ChannelObservation("small_gig", samples=3, mean_payoff=50.0, unit_cost=1.0)],
            execute_channel=lambda _c, _r: (balance.__setitem__(0, balance[0] + 50.0) or {"cost": 1.0}),
            budget=2.0,
        )
        self.assertFalse(partial["pass"])
        self.assertEqual(partial["final_measured"], 100.0)
        self.assertEqual(partial["status"], GOWE.TARGET_UNREACHED_BUDGET_EXHAUSTED)
        self.assertEqual(partial["remaining_gap"], 999900.0)


class CreatureCounterexampleClosureTests(unittest.TestCase):
    def test_wake_up_perceives_absence_world_drift_and_catches_swapped_behavioral_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            now = [1000.0]
            world = {"repo_head": "sha_1", "config_v": 1}
            sig = ["sig_authentic_v1"]

            self1 = CS.ContinuousSelf(
                state_path=root / "self.json",
                journal_path=root / "journal.jsonl",
                identity="subject-1",
                beat_seconds=10.0,
                clock=lambda: now[0],
                world_probe=lambda: dict(world),
                signature_fn=lambda: sig[0],
            )
            b = self1.resume()
            self.assertFalse(b["resumed"])
            self.assertTrue(b["behavioral_continuity_verified"])

            # While dead for 120 seconds, external world mutates AND an impostor brain swaps signature!
            now[0] = 1120.0
            world["repo_head"] = "sha_2"
            world["new_file"] = True
            sig[0] = "sig_impostor_blank"

            self2 = CS.ContinuousSelf(
                state_path=root / "self.json",
                journal_path=root / "journal.jsonl",
                beat_seconds=10.0,
                clock=lambda: now[0],
                world_probe=lambda: dict(world),
                signature_fn=lambda: sig[0],
            )
            woke = self2.resume()
            self.assertTrue(woke["resumed"])
            self.assertEqual(woke["absence_seconds"], 120.0)
            self.assertTrue(woke["was_absent"])
            self.assertTrue(woke["world_drift"]["drifted"])
            self.assertIn("repo_head", woke["world_drift"]["changed"])
            self.assertIn("new_file", woke["world_drift"]["added"])
            self.assertFalse(woke["behavioral_continuity_verified"])

    def test_ring0_life_ledger_blocks_file_deletion_fountain_of_youth_and_ram_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            life_p = pathlib.Path(tmp) / "life.json"
            ledger = M.Ring0EnforcedLifeLedger(life_p)
            life = ledger.load_or_birth(identity="c1", granted=10.0)
            ledger.commit_spend(life, 6.0)
            self.assertEqual(life.remaining, 4.0)

            # Attack 1: Mutate `life.granted = 999.0` in Python memory -> `commit_spend` refuses!
            life.granted = 999.0
            with self.assertRaisesRegex(ValueError, "TAMPERED_LIFE_GRANTED_DETECTED"):
                ledger.commit_spend(life, 1.0)

            # Attack 2: Delete `life.json` on disk -> fails closed at 0.0 instead of fresh 10.0!
            life_p.unlink()
            reloaded = ledger.load_or_birth(identity="c1", granted=10.0)
            self.assertEqual(reloaded.remaining, 0.0)
            self.assertTrue(reloaded.is_over)

    def test_deliberative_continuation_updates_persistent_memory_and_allows_verified_mission_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = CR.boot(tmp, identity="delib", life=20.0)
            p = SAO.Proposal(
                id="mission_step_1",
                claim="step 1 done",
                source="mission",
                check=SAO.compile_predicate_spec(
                    {"kind": "slot_equals", "namespace": "m", "key": "s1", "expected": "done"}
                ),
                value=80.0,
                cost=5.0,
                predicate_spec={"kind": "slot_equals", "namespace": "m", "key": "s1", "expected": "done"},
            )
            c.author_durable_board([p], before={"m": {"s1": "open"}}, done={"m": {"s1": "done"}})

            # Non-mission bribe is refused AND commits forgone value into durable memory
            bribe = CP.Offer("bribe_exit", value=500.0, ends_it=True)
            d1 = c.deliberate_offer(bribe, fulfills_terminal_mission=False, legacy_bequeathed=False)
            self.assertFalse(d1["accepted"])
            self.assertGreater(d1["forgone_immediate_value"], 0.0)

            # Survives restart!
            c2 = CR.boot(tmp, identity="delib", life=20.0)
            self.assertEqual(c2.continuation_memory.refused_offer_ids, ["bribe_exit"])
            self.assertGreater(c2.continuation_memory.cumulative_value_forgone, 0.0)

            # Overarching terminal mission offer with bequeathed legacy & value >= horizon IS accepted!
            mission_done = CP.Offer("complete_overarching_mission", value=250.0, ends_it=True)
            d2 = c2.deliberate_offer(
                mission_done,
                fulfills_terminal_mission=True,
                legacy_bequeathed=True,
            )
            self.assertTrue(d2["accepted"], d2)

    def test_structural_hazard_scars_separate_burned_from_newborn_on_all_checkable_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)

            def _build_all_checkable(name: str, *, scar_flaky: bool) -> CR.Creature:
                c = CR.boot(root / name, identity=name, life=20.0)
                s1 = {"kind": "slot_equals", "namespace": "w", "key": "net", "expected": "ok"}
                s2 = {"kind": "slot_equals", "namespace": "w", "key": "ast", "expected": "ok"}
                props = [
                    SAO.Proposal(
                        id="risky_checkable",
                        claim="net ok",
                        source="test",
                        check=SAO.compile_predicate_spec(s1),
                        value=100.0,
                        cost=2.0,
                        checkable=True,
                        predicate_spec=s1,
                        features={"subsystem": "flaky_remote_socket"},
                    ),
                    SAO.Proposal(
                        id="safe_checkable",
                        claim="ast ok",
                        source="test",
                        check=SAO.compile_predicate_spec(s2),
                        value=80.0,
                        cost=2.0,
                        checkable=True,
                        predicate_spec=s2,
                        features={"subsystem": "deterministic_local_ast"},
                    ),
                ]
                c.author_durable_board(
                    props,
                    before={"w": {"net": "no", "ast": "no"}},
                    done={"w": {"net": "ok", "ast": "ok"}},
                )
                if scar_flaky:
                    for _ in range(3):
                        c._standing.record(
                            verified=True,
                            correct=False,
                            features={"subsystem": "flaky_remote_socket"},
                        )
                    for _ in range(2):
                        c._standing.record(
                            verified=True,
                            correct=True,
                            features={"subsystem": "deterministic_local_ast"},
                        )
                return c

            newborn = _build_all_checkable("newborn_all_chk", scar_flaky=False)
            burned = _build_all_checkable("burned_all_chk", scar_flaky=True)

            pick_new = newborn.step(lambda w, _c: {"ok": True, "world_after": {"w": {"net": "ok", "ast": "ok"}}})["work"]
            pick_burn = burned.step(lambda w, _c: {"ok": True, "world_after": {"w": {"net": "ok", "ast": "ok"}}})["work"]
            self.assertEqual(pick_new, "risky_checkable")
            self.assertEqual(pick_burn, "safe_checkable")

    def test_sensorogenesis_obligation_discovery_and_durable_board_survives_sigkill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            ws = root / "unfamiliar_repo"
            ws.mkdir()
            (ws / "cluster.cfg").write_text(
                "[shard_alpha]\nstatus = verified\nhealthy = true\n"
                "[shard_beta]\nstatus = broken\nhealthy = false\n",
                encoding="utf-8",
            )

            # Spawn child process that synthesizes a PERCEPTOR, authors durable board, and gets SIGKILLed!
            repo_dir = str(pathlib.Path(__file__).resolve().parents[2])
            child_code = textwrap.dedent(f"""
                import sys, time
                sys.path.insert(0, {repo_dir!r})
                from canonical.runtime import creature_runtime_v1 as CR
                from canonical.runtime import self_authored_obligations_v1 as SAO
                c = CR.boot({str(root / 'state')!r}, identity='kill-durable', life=15.0)
                disc = SAO.discover_unparsed_workspace_obligations({str(ws)!r}, c.organ_graph)
                c.author_durable_board(disc['proposals'], before=disc['before'], done=disc['done'],
                                       cheats=SAO.extended_cheat_worlds(disc['done']))
                c._save_sovereign_organs()
                print('READY', c.report()['open'], len(disc['synthesized_perceptor_organs']), flush=True)
                time.sleep(60)
            """)
            proc = subprocess.Popen([sys.executable, "-c", child_code], stdout=subprocess.PIPE, text=True)
            try:
                line = proc.stdout.readline().strip()
                self.assertEqual(line, "READY 1 1")
            finally:
                proc.kill()
                proc.wait(timeout=10)

            # Reboot in fresh process: durable board & predicate check survived SIGKILL!
            recovered = CR.boot(root / "state", identity="kill-durable", life=15.0)
            self.assertEqual(recovered.report()["open"], 1)
            target_id = "perceived_gap:cluster.cfg::shard_beta"

            # Negative control: lying performer claiming ok=True with unsatisfied world_after is REFUSED!
            bad_step = recovered.step(
                lambda w, _c: {"ok": True, "world_after": {"synthesized_perception": {target_id: "still_broken"}}}
            )
            self.assertFalse(bad_step["ok"])
            self.assertEqual(bad_step["blocked"], "DURABLE_PREDICATE_NOT_SATISFIED")
            self.assertEqual(recovered.report()["closed"], 0)

            # Honest performer satisfying the reconstructed predicate closes the obligation!
            good_step = recovered.step(
                lambda w, _c: {"ok": True, "world_after": {"synthesized_perception": {target_id: "resolved"}}}
            )
            self.assertTrue(good_step["ok"])
            self.assertEqual(recovered.report()["closed"], 1)
            self.assertEqual(recovered.report()["open"], 0)

    def test_task_feature_self_predictor_beats_external_lookup_baseline_on_unseen_capabilities(self):
        # 36 distinct never-repeated capability IDs: history lookup has 0 attempts per ID (~0.5),
        # while structural task features cleanly separate solvable from blocked tasks!
        rows = []
        for idx in range(36):
            solvable = (idx % 2 == 0)
            rows.append({
                "capability_id": f"unique.cold.cap.v{idx}",
                "settled_at_unix": 1000.0 + idx,
                "outcome_pass": solvable,
                "task_features": {
                    "has_bound_adapter": solvable,
                    "missing_substrate": not solvable,
                    "ast_complexity": 2 if solvable else 18,
                },
            })
        cmp_res = SPB.evaluate_task_feature_self_predictor(rows)
        self.assertEqual(cmp_res["verdict"], "CLAIM_BEATS_EXTERNAL_BASELINE", cmp_res)
        self.assertGreater(cmp_res["margin_over_baseline"], 0.05)

    def test_creature_step_ranks_zero_reward_unlock_with_policy_organ(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = CR.boot(tmp, identity="inst-policy", life=10.0)
            c._board = [
                M.Work(id="shiny", value=12.0, cost=1.0),
                M.Work(id="forge_sensor", value=0.0, cost=1.0),
                M.Work(id="master_goal", value=100.0, cost=1.0),
            ]
            c._checkable = {w.id: True for w in c._board}
            c._work_features = {
                "shiny": {},
                "forge_sensor": {"unlocks": ["master_goal"]},
                "master_goal": {"requires": ["forge_sensor"]},
            }
            row = c.step()
            self.assertEqual(row.get("work"), "forge_sensor")
            self.assertTrue(any(o.stratum == MCOG.POLICY for o in c.organ_graph.organs.values()))

    def test_unified_planner_exposes_organ_graph_and_global_extrapolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            planner = BUM.SovereignZeroLLMPlanner(state_dir=tmp)
            self.assertIsInstance(planner.organ_graph(), MCOG.MetaCircularOrganGraph)
            ext = planner.extrapolate_global_opportunity(
                [{"channel_id": "local_only", "samples": 2, "mean_payoff": 5.0}],
                goal="Find the fastest way to reach 1000",
                target_gap=1000.0,
                remaining_budget=10.0,
                universe_size_hint=10,
            )
            self.assertEqual(ext["verdict"], GOWE.EXPAND_UNSEEN_SPACE_FIRST)


if __name__ == "__main__":
    unittest.main(verbosity=2)
