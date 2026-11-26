#!/usr/bin/env python3
"""Zero-Mock End-to-End Verification Suite for Frontier Leapfrog Waves 31-35.

Covers:
  - Wave 31: Elon Speed Pass III (DBSP v3 bit-identical compile cache, lazy Creature organ proxies,
             lazy route dep check, version-family deduplication, `recall_latest_sources`, `elon_speed_profile`)
  - Wave 32: Version-Space Repair Disambiguation, Angelic CEGIS, Observational Equivalence, Inverse Completion,
             History-Induced Edit Grammar, Repo Seed Corpus, Cross-Repo Dataflow, Consistency-vs-Equivalence Proof,
             Distinguishing Projection, Reverted-Part Pinning & Verdict Amplification (`0D` + `0H` + `UnifiedModel`)
  - Wave 33: Meaning-First IR Crystallizer, Cross-Language Transfer, Operator Semantics, Proof-Gated Equivalence
             Compression V8, Scoped Skill Learning & Recheck, Execution-Locus Pipeline, Weight-Update Admission,
             Memini (w_fast/w_slow) + MemRL (TD Q + 2-phase) + APEX-EM + Creature Sleep Consolidation (`0G` + `Creature`)
  - Wave 34: OSWorld 2.1 Pure-Stdlib CU Engine (`workflow_policy_v7` + `unified_policy_v11` + `gui_goal_verifier_v1`
             + `constraint_guard_v1` + `recovery_policy_v2` + `brain_agent_adapter_v1`), Epistemic Computer Agent,
             Action-Grammar Guide, TomasuLLM Speculative Macro Commit (`effect_witness_v1` + `standing_facts_v1`
             + `action_replay_under_change_v1` + `capability_parallel_frontier_v2`) (`0F` + `0I` + `UnifiedModel`)
  - Wave 35: Active-Inference Repertoire Query (`the_repertoire_is_a_query_v1`), Proof-Carrying Counterfactual Union,
             Semantic Operator Counterfactuals, EFE-VI Probe-vs-Abstain (`a_constructed_question_is_a_run_v1`),
             When-to-Stop-Asking, Typed CEGIS(T) (`typed_invention_v1`), Distinction Creation,
             Smallest Checkable Question & `UnifiedModel.leapfrog_solve(...)` dispatch (`0E` + `0I` + `UnifiedModel`)
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestFrontierLeapfrogWaves31To35(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from canonical.runtime.brain_unified_model_v1 import open_model

        cls.um = open_model()

    # ------------------------------------------------------------------ Wave 31
    def test_01_wave31_dbsp_v3_compile_bit_identical(self) -> None:
        """Wave 31: Warm DBSP v3 cached `compile_model()` is 100% bit-identical to `BRAIN_COMPILE_NO_CACHE=1`."""
        from canonical.runtime.compile_brain_unified_model_v1 import canonical_json, compile_model

        m_warm = compile_model()
        old = os.environ.get("BRAIN_COMPILE_NO_CACHE")
        try:
            os.environ["BRAIN_COMPILE_NO_CACHE"] = "1"
            m_nocache = compile_model()
        finally:
            if old is None:
                os.environ.pop("BRAIN_COMPILE_NO_CACHE", None)
            else:
                os.environ["BRAIN_COMPILE_NO_CACHE"] = old
        self.assertEqual(m_warm["digest"]["value"], m_nocache["digest"]["value"])
        self.assertEqual(canonical_json(m_warm), canonical_json(m_nocache))

    def test_02_wave31_version_family_dedup_and_elon_profile(self) -> None:
        """Wave 31: Version-family deduplication collapses v1..v17 sprawl and `elon_speed_profile` reports Wave 31 flags."""
        from canonical.runtime.brain_unified_model_v1 import dedupe_version_families

        rows = [
            {"path": "canonical/runtime/osworld_v21_unified_policy_v2.py", "score": 1.0},
            {"path": "canonical/runtime/osworld_v21_unified_policy_v11.py", "score": 0.9},
            {"path": "canonical/runtime/osworld_v21_unified_policy_v17.py", "score": 0.8},
            {"path": "canonical/runtime/unique_helper.py", "score": 0.5},
        ]
        deduped = dedupe_version_families(rows)
        paths = [r["path"] for r in deduped]
        self.assertEqual(len(deduped), 2)
        self.assertIn("canonical/runtime/osworld_v21_unified_policy_v17.py", paths)
        self.assertIn("canonical/runtime/unique_helper.py", paths)
        self.assertNotIn("canonical/runtime/osworld_v21_unified_policy_v2.py", paths)

        latest = self.um.recall_latest_sources("osworld policy", limit=8)
        self.assertTrue(latest["pass"])
        self.assertGreaterEqual(latest["collapsed_superseded_count"], 0)

        prof = self.um.elon_speed_profile()
        self.assertTrue(prof["pass"])
        self.assertTrue(prof["lazy_route_dep_probe"])
        self.assertTrue(prof["version_family_dedup_enabled"])

    def test_03_wave31_creature_lazy_organ_proxies(self) -> None:
        """Wave 31: `creature_runtime_v1` uses `_LazyModule` proxies for CP/CS/S/M/A without breaking real Creature boot."""
        from canonical.runtime import creature_runtime_v1 as cr

        for sym in ("CP", "CS", "S", "M", "A"):
            self.assertIsInstance(getattr(cr, sym), cr._LazyModule)

        with tempfile.TemporaryDirectory() as td:
            creature = self.um.open_creature(Path(td), identity="wave31_lazy_test", life=25.0)
            rep = creature.report()
            self.assertEqual(rep["identity"], "wave31_lazy_test")

    # ------------------------------------------------------------------ Wave 32
    def test_04_wave32_version_space_disambiguation_and_angelic_cegis(self) -> None:
        """Wave 32 (`0D`): Version-space partition/decide + observational equivalence + inverse completion + history grammar + cross-repo dataflow."""
        res = self.um.disambiguate_and_pin_repairs(
            candidate_ids=["r1", "r2", "r3"],
            behaviours={
                "r1": [1, 2, 10],
                "r2": [1, 2, 20],
                "r3": [1, 2, 10],
            },
            probe_ids=["p_edge"],
            probe_outcomes={"p_edge": ["A", "B", "A"]},
            observations={"p_edge": "B"},
            equiv_pair=(lambda x: x + x, lambda x: 2 * x),
            equiv_inputs=[{"x": 0}, {"x": 3}, {"x": -4}],
            inverse_name="save_state",
            inverse_siblings=["save_state"],
            writer_payloads=[{"a": 1, "b": "hi"}, {"a": 2, "b": "ok"}],
            roundtrip_pair=(lambda d: dict(d), lambda d: dict(d)),
            inverse_samples=[{"a": 1}, {"a": 2}],
            history_pairs=[
                ("bug1", "def f(x):\n    return x < 0\n", "def f(x):\n    return x <= 0\n"),
            ],
            history_target_source="def g(n):\n    return n < 0\n",
            history_function_line=2,
            dataflow_root=ROOT / "canonical/swe_kernel",
            dataflow_var="root",
            dataflow_max_files=12,
        )
        self.assertTrue(res["pass"], res)
        inner = res["version_space_swe"]["results"]
        self.assertIn("version_space", inner)
        self.assertIn("observational_equivalence", inner)
        self.assertIn("inverse_completion", inner)
        self.assertIn("history_edit_grammar", inner)
        self.assertGreaterEqual(inner["history_edit_grammar"]["template_count"], 1)
        self.assertIn("cross_repo_dataflow", inner)
        self.assertGreater(inner["cross_repo_dataflow"]["files_indexed"], 0)

    def test_05_wave32_equivalence_proof_projection_pinning_and_amplification(self) -> None:
        """Wave 32 (`0H`): `consistency_vs_equivalence_v1` + `distinguishing_projection_v1` + `pins_from_the_reverted_part_v1` + `patch_verdict_amplification_v1`."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "sample.py").write_text("def add_one(x: int) -> int:\n    return x + 1\n", encoding="utf-8")
            (root / "test_sample.py").write_text(
                "from sample import add_one\ndef test_add():\n    assert add_one(2) == 3\n",
                encoding="utf-8",
            )
            res = self.um.prove_equivalence_and_amplify(
                code_rule={"rule_id": "inc_rule", "before": "x - 1", "after": "x + 1"},
                before_snippet="def f(x):\n    return x - 1\n",
                after_snippet="def f(x):\n    return x + 1\n",
                rule_judge=lambda _src, pt: pt + 1,
                rule_probes=[0, 1, 5, -2],
                gate_report={"admitted": True, "score": 1.0},
                projection_root=root,
                projection_features=["name", "size"],
                pin_test_source="from sample import add_one\ndef test_add():\n    assert add_one(2) == 3\n",
                amplify_module_path="sample.py",
                amplify_repo_root=root,
                amplify_candidate_source="def add_one(x: int) -> int:\n    return x + 1\n",
            )
            self.assertTrue(res["pass"], res)
            inner = res["equivalence_oracle"]["results"]
            self.assertIn("equivalence_proof", inner)
            self.assertIn("distinguishing_projection", inner)
            self.assertIn("test_calls", inner)
            self.assertGreaterEqual(inner["test_calls"]["count"], 1)
            self.assertIn("verdict_amplification", inner)

    # ------------------------------------------------------------------ Wave 33
    def test_06_wave33_meaning_first_ir_cross_language_and_compression(self) -> None:
        """Wave 33 (`0G`): Semantic unification, IR bridge, cross-language transfer, operator semantics, equivalence compression V8, execution locus & weight admission."""
        from canonical.runtime import equivalence_compression_v8 as eqc8

        d1 = eqc8.object_digest(object_id="obj_a", behavior_signature=["sort:ok", "stable:true"], goal_scope="sort")
        d2 = eqc8.object_digest(object_id="obj_b", behavior_signature=["sort:ok", "stable:true"], goal_scope="sort")
        objs = [
            {
                "object_id": "obj_a",
                "goal_scope": "sort",
                "behavior_signature": ["sort:ok", "stable:true"],
                "verification_receipt": {
                    "receipt_id": "rcpt_a",
                    "object_id": "obj_a",
                    "goal_scope": "sort",
                    "object_sha256": d1,
                    "independent_verified": True,
                    "exact_byte_bound": True,
                    "conclusion": "success",
                },
            },
            {
                "object_id": "obj_b",
                "goal_scope": "sort",
                "behavior_signature": ["sort:ok", "stable:true"],
                "verification_receipt": {
                    "receipt_id": "rcpt_b",
                    "object_id": "obj_b",
                    "goal_scope": "sort",
                    "object_sha256": d2,
                    "independent_verified": True,
                    "exact_byte_bound": True,
                    "conclusion": "success",
                },
            },
        ]
        res = self.um.crystallize_meaning_first_transfer(
            semantic_sources=[
                "def total(xs):\n    s = 0\n    for v in xs:\n        s += v\n    return s\n",
                "def acc(items):\n    out = 0\n    for item in items:\n        out += item\n    return out\n",
            ],
            before_snippet="def clamp(x):\n    return x < 0\n",
            after_snippet="def clamp(x):\n    return x <= 0\n",
            ir_language="python",
            ir_target_source="def check(n):\n    return n < 0\n",
            target_language="python",
            target_source="def check(n):\n    return n < 0\n",
            operator_symbol="<=",
            taught_in="python",
            proposed_in="javascript",
            frozen_operators=["+", "<=", "/"],
            compress_objects=objs,
            compress_mappings=[],
            recheck_rule={"rule_id": "lt_to_le", "before": "x < 0", "after": "x <= 0", "language": "python"},
            locus_source="def check(n):\n    return n < 0\n",
            locus_executed_lines=[1, 2],
            weight_goal="fix boundary comparison bug",
            weight_probe_goals=["fix loop boundary off-by-one"],
        )
        self.assertTrue(res["pass"], res)
        inner = res["meaning_first"]["results"]
        self.assertIn("semantic_unification", inner)
        self.assertIn("ir_bridge", inner)
        self.assertIn("cross_language_transfer", inner)
        self.assertIn("operator_semantics", inner)
        self.assertIn("equivalence_compression", inner)
        self.assertIn("skill_recheck", inner)
        self.assertIn("execution_locus", inner)
        self.assertIn("weight_update_admission", inner)

    def test_07_wave33_memini_memrl_apex_and_creature_sleep(self) -> None:
        """Wave 33 (`0G` + `Creature`): Memini (`w_fast`/`w_slow`) + MemRL TD `Q` + APEX-EM 3-channel recall & Creature sleep consolidation."""
        with tempfile.TemporaryDirectory() as td:
            creature = self.um.open_creature(Path(td), identity="wave33_sleep", life=25.0)
            bus = creature.memory_bus
            # Crystallize two verified skills so Memini/MemRL have live skills to weight & rank
            bus.crystallize_action_macro(
                trigger_key="fix_parser_bug",
                actions=["inspect", "patch", "test"],
                provenance_episode_id="ep1",
            )
            bus.crystallize_action_macro(
                trigger_key="stale_noop",
                actions=["noop"],
                provenance_episode_id="ep2",
            )
            sids = sorted(bus.skills.keys())
            good_sid = [s for s in sids if "fix_parser_bug" in bus.skills[s].trigger_key][0]
            bad_sid = [s for s in sids if "stale_noop" in bus.skills[s].trigger_key][0]

            # Reinforce good_sid and penalize bad_sid via Creature sleep consolidation
            sleep_res = creature.sleep_consolidate_memory(
                program_sources=[
                    "def f(x):\n    return (x + 1) * 2\n",
                    "def g(y):\n    return (y + 1) * 2\n",
                ],
                memrl_outcomes=[
                    {"skill_id": good_sid, "reward": 1.0},
                    {"skill_id": bad_sid, "reward": 0.0},
                ],
                recheck_rules=[{"rule_id": "r_sleep", "before": "a < b", "after": "a <= b", "language": "python"}],
            )
            self.assertIn("memini_memrl_apex", sleep_res)
            self.assertIn("lm_sleep_rechecked", sleep_res)

            # Query with APEX-EM + MemRL Phase-2 Q re-ranking
            ranked = bus.memini_memrl_apex_consolidate(query="fix parser bug", top_k=5)
            self.assertTrue(ranked["pass"])
            self.assertGreater(ranked["q_values"][good_sid], ranked["q_values"][bad_sid])
            self.assertGreater(ranked["weights"][good_sid]["w_fast"], ranked["weights"][bad_sid]["w_fast"])
            self.assertTrue(ranked["ranked_hits"])
            self.assertEqual(ranked["ranked_hits"][0]["skill_id"], good_sid)

    # ------------------------------------------------------------------ Wave 34
    def test_08_wave34_osworld_v21_pure_stdlib_and_epistemic_cu(self) -> None:
        """Wave 34 (`0F`): OSWorld 2.1 pure-stdlib stack (`workflow_policy_v7` + `unified_policy_v11` + verifier + guard + adapter) + Epistemic CU + Action-Grammar Guide."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sample_csv = root / "report.csv"
            sample_csv.write_text("name,val\nalpha,1\nbeta,2\n", encoding="utf-8")

            res = self.um.execute_osworld_v21_epistemic_cu(
                osworld_state={
                    "instruction": "Do not modify /etc/hosts; inspect desktop state and finish",
                    "step": 0,
                    "a11y_tree": "",
                    "terminal_output": "",
                    "history": [],
                },
                instruction="Do not delete /tmp/protected.txt",
                proposed_action={"type": "bash", "command": "rm /tmp/protected.txt"},
                protected_paths=["/tmp/protected.txt"],
                nl_goal="Convert report.csv to sorted output.json",
                inspect_path=sample_csv,
                epistemic_store_root=root / "ep_store",
                grammar_need="convert csv file to json",
                grammar_pages={},
                grammar_declared_flags={},
            )
            self.assertTrue(res["pass"], res)
            inner = res["osworld_epistemic_cu"]["results"]
            self.assertIn("osworld_v21", inner)
            self.assertIn("decision", inner["osworld_v21"])
            self.assertIn("browser_surfaces", inner["osworld_v21"])
            self.assertIn("epistemic_cu", inner)
            self.assertTrue(inner["epistemic_cu"]["agent_ready"])
            self.assertIn("action_grammar", inner)

    def test_09_wave34_speculative_macro_commit_safe_and_abort(self) -> None:
        """Wave 34 (`0F`): TomasuLLM Speculative Macro Commit commits on frame-licensed change and ROLLS BACK on unexpected standing-fact drift."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            f_a = root / "a.txt"
            f_a.write_text("hello\n", encoding="utf-8")
            contract = {"frame": {"creates": [], "modifies": ["{target}"], "removes": []}}

            # Case 1: Only frame-licensed file mutated -> COMMIT
            safe_res = self.um.speculative_macro_commit(
                witness_root=root,
                witness_argv=["edit", "a.txt"],
                witness_expected=["a.txt"],
                standing_before_state={"a.txt": b"v1", "untouched.txt": b"keep"},
                standing_after_state={"a.txt": b"v2", "untouched.txt": b"keep"},
                standing_contract=contract,
                standing_binding={"target": "a.txt"},
                replay_before="x = 1\ny = 2\n",
                replay_after="x = 1\ny = 3\n",
                replay_target_text="x = 1\ny = 2\n",
                plan_parallel_frontier=True,
            )
            self.assertTrue(safe_res["pass"], safe_res)
            self.assertEqual(safe_res["speculative_commit"]["commit_decision"], "COMMIT")
            self.assertEqual(safe_res["speculative_commit"]["results"]["action_replay"]["replayed_text"], "x = 1\ny = 3\n")
            self.assertIn("parallel_frontier", safe_res["speculative_commit"]["results"])

            # Case 2: Unlicensed standing fact silently mutated -> ROLLBACK (0 false accepts!)
            abort_res = self.um.speculative_macro_commit(
                standing_before_state={"a.txt": b"v1", "untouched.txt": b"keep"},
                standing_after_state={"a.txt": b"v2", "untouched.txt": b"CORRUPTED"},
                standing_contract=contract,
                standing_binding={"target": "a.txt"},
            )
            self.assertFalse(abort_res["pass"])
            self.assertEqual(
                abort_res["speculative_commit"]["commit_decision"],
                "ROLLBACK__UNEXPECTED_STANDING_FACT_DRIFT",
            )

    # ------------------------------------------------------------------ Wave 35
    def test_10_wave35_active_repertoire_efe_vi_typed_cegis_and_distinction(self) -> None:
        """Wave 35 (`0E`): BM25 repertoire query, semantic operator counterfactuals, EFE-VI probe-vs-abstain, typed CEGIS(T), distinction creation & smallest checkable question."""
        # Build real transition observations with a genuine vocabulary alias
        transitions = [
            ("toggle", {"flag": True, "hidden": 0}, {"flag": False, "hidden": 0}),
            ("toggle", {"flag": True, "hidden": 1}, {"flag": True, "hidden": 1}),
        ]
        res = self.um.active_repertoire_typed_invention(
            repertoire_documents=[
                "git status --short shows working tree status",
                "python3 -m unittest runs python test suites deterministically",
                "tar -czf creates gzip compressed tar archives",
            ],
            repertoire_query="python test suites",
            contract_text="Every public API must reject negative timeout and preserve existing files.",
            efe_info_gain=0.85,
            efe_probe_cost=0.20,
            efe_abstain_risk=0.40,
            question_statement="Ensure parse_int handles negative numbers",
            question_source="def parse_int(s):\n    return int(s)\n",
            typed_examples=[({"x": 1}, 2), ({"x": 4}, 5)],
            typed_source="def inc(x: int) -> int:\n    return x + 1\n",
            typed_grammar=["x", "1", "x + 1", "x - 1"],
            typed_result_type="int",
            distinction_transitions=transitions,
            distinction_conditions=[("flag", True)],
            distinction_holds=lambda cond, st: st.get(cond[0]) == cond[1],
        )
        self.assertTrue(res["pass"], res)
        inner = res["active_repertoire"]["results"]
        self.assertIn("repertoire_query", inner)
        self.assertEqual(inner["repertoire_query"]["bm25_ranked"][0]["index"], 1)
        self.assertIn("semantic_operator_counterfactuals", inner)
        self.assertEqual(inner["efe_vi_decision"]["decision"], "PROBE_WITH_CONSTRUCTED_RUN")
        self.assertIn("smallest_checkable_question", inner)
        self.assertIn("typed_invention", inner)
        self.assertIn("distinction_creation", inner)

        # Verify EFE-VI abstains when probe cost - info gain >= abstain_risk
        abstain = self.um.active_repertoire_typed_invention(
            efe_info_gain=0.05,
            efe_probe_cost=0.60,
            efe_abstain_risk=0.40,
        )
        self.assertTrue(abstain["pass"])
        self.assertEqual(
            abstain["active_repertoire"]["results"]["efe_vi_decision"]["decision"],
            "ABSTAIN_AND_ACT",
        )

    def test_11_wave35_leapfrog_solve_unified_dispatch_all_modes(self) -> None:
        """Wave 35: `UnifiedModel.leapfrog_solve(...)` dispatches all Waves 31-35 modes cleanly via both explicit and auto mode."""
        r_latest = self.um.leapfrog_solve("osworld policy", mode="latest_sources")
        self.assertTrue(r_latest["pass"])

        r_vs = self.um.leapfrog_solve(
            "disambiguate candidate patches",
            inputs={"candidate_ids": ["c1", "c2"], "behaviours": {"c1": [1], "c2": [2]}},
        )
        self.assertTrue(r_vs["pass"])
        self.assertEqual(r_vs["operation"], "DISAMBIGUATE_AND_PIN_REPAIRS")

        r_mf = self.um.leapfrog_solve(
            "check operator semantics",
            inputs={"operator_symbol": "+", "taught_in": "python", "proposed_in": "javascript"},
        )
        self.assertTrue(r_mf["pass"])
        self.assertEqual(r_mf["operation"], "MEANING_FIRST_TRANSFER")

        r_mem = self.um.leapfrog_solve("memini consolidate", mode="memini_memrl", inputs={"outcomes": []})
        self.assertTrue(r_mem["pass"])
        self.assertEqual(r_mem["operation"], "MEMINI_MEMRL_APEX")

        r_cu = self.um.leapfrog_solve(
            "parse cu goal",
            inputs={"nl_goal": "Copy notes.txt to backup.txt"},
        )
        self.assertTrue(r_cu["pass"])
        self.assertEqual(r_cu["operation"], "OSWORLD_V21_EPISTEMIC_CU")

        r_spec = self.um.leapfrog_solve(
            "speculative replay",
            inputs={"replay_before": "a = 1\n", "replay_after": "a = 2\n"},
        )
        self.assertTrue(r_spec["pass"])
        self.assertEqual(r_spec["operation"], "SPECULATIVE_MACRO_COMMIT")

        r_rep = self.um.leapfrog_solve(
            "query repertoire",
            inputs={"repertoire_documents": ["grep pattern file"], "repertoire_query": "grep"},
        )
        self.assertTrue(r_rep["pass"])
        self.assertEqual(r_rep["operation"], "ACTIVE_REPERTOIRE_TYPED_INVENTION")


if __name__ == "__main__":
    unittest.main()
