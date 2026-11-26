#!/usr/bin/env python3
"""Zero-mock end-to-end tests for Wave 45-46 (33 newly awakened DARK modules -> 100 total
across Waves 40-46 + 6 new federated engines across UnifiedModel, Creature & federation)."""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from canonical.runtime import brain_unified_model_v1 as BUM
from canonical.runtime import creature_runtime_v1 as CR
from canonical.runtime import unified_hidden_capability_federation_v1 as FED
from canonical.runtime import wave45_46_anytime_valid_quotient_metamorphic_hcu_v1 as W45


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestWave45To46FrontierLeapfrog(unittest.TestCase):
    def test_01_all_33_newly_awakened_dark_modules_and_100_cumulative_live(self) -> None:
        inv = W45.awakened_dark_modules_w45_46_inventory()
        self.assertTrue(inv["all_loaded"], inv)
        self.assertEqual(inv["wave45_46_count"], 33)
        self.assertEqual(inv["wave45_46_loaded"], 33)
        self.assertEqual(inv["cumulative_waves_40_to_46_count"], 100)
        self.assertEqual(len(set(W45.ALL_W40_W46_AWAKENED_DARK_MODULES)), 100)
        self.assertEqual(inv["k3_model_calls"], 0)
        self.assertEqual(inv["spend_usd"], 0.0)

    def test_02_quotient_of_trace_angelic_forcing_and_systematic_exploration(self) -> None:
        kernel = W45.QuotientAngelicProbeInducerKernel()

        # Coarsest sufficient trace quotient separating traces that reach value 1 vs 0
        traces = [
            [(("a", 0), ("b", 0)), (("a", 1), ("b", 0))],
            [(("a", 0), ("b", 2)), (("a", 1), ("b", 2))],
            [(("a", 0), ("b", 0)), (("a", 0), ("b", 2))],
            [(("a", 0), ("b", 1)), (("a", 0), ("b", 0))],
        ]
        labels = [True, True, False, False]
        q_res = kernel.compute_trace_quotient(traces, labels, max_size=2)
        self.assertTrue(q_res["pass"], q_res)
        self.assertIsNotNone(q_res["coarsest_quotient"])
        self.assertEqual(q_res["coarsest_quotient"]["collisions"], 0)

        # Angelic value forcing + expression synthesis on a real Python function
        src = (
            "def compute_total(price, qty):\n"
            "    subtotal = price * qty\n"
            "    total = subtotal + 1\n"
            "    return total\n"
        )
        ang = kernel.angelic_force_and_synthesize(src, "compute_total", [10, 3], line=3)
        self.assertTrue(ang["pass"], ang)
        self.assertGreater(ang["instrumented_site_count"], 0)
        self.assertTrue(ang["differential_witness_inverter_ready"])

        # Systematic exploration on an unknown finite graph without paying twice
        graph = {
            "S0": {"east": "S1", "north": "S0"},
            "S1": {"east": "S2", "west": "S0"},
            "S2": {"north": "GOAL", "west": "S1"},
            "GOAL": {"south": "S2"},
        }
        exp = kernel.separate_vocabulary_and_explore(graph=graph, start_state="S0", goal_state="GOAL", action_budget=30)
        self.assertTrue(exp["pass"], exp)
        self.assertTrue(exp["graph_exploration"]["reached"])
        self.assertTrue(all(exp["probe_and_guard_organs_ready"].values()))

    def test_03_metamorphic_seed_corpus_lineage_name_hole_and_symbol_ownership(self) -> None:
        kernel = W45.MetamorphicLineageCorpusSWEKernel()

        # Harvest repo seed corpus + check zero-test metamorphic canonicality law
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "sample.py"
            p.write_text("TOKEN = 'alpha_beta'\ndef parse(x):\n    return x.strip()\n", encoding="utf-8")
            harv = kernel.harvest_corpus_and_check_laws(
                td,
                sample_source=p.read_text(encoding="utf-8"),
                canonicality_name="clean_json",
                canonicality_result={"ok": True, "items": [1, 2, 3]},
            )
            self.assertTrue(harv["pass"], harv)
            self.assertTrue(any("alpha_beta" in lit for lit in harv["extracted_literals"]), harv["extracted_literals"])

        # Producer localization + file alphabet + two-guard edit + symbol ownership enforcement
        src = (
            "def validate_bounds(x, lo, hi):\n"
            "    if x < lo:\n"
            "        return False\n"
            "    if x > hi:\n"
            "        return False\n"
            "    return True\n\n"
            "def unrelated_helper(v):\n"
            "    return v + 1\n"
        )
        # Blocked when touching an unowned symbol
        blocked = kernel.localize_producer_and_repair_holes(
            repo_root=REPO_ROOT / "canonical" / "swe_kernel",
            source=src,
            changed_lines=[9],
            owned_symbols=["validate_bounds"],
        )
        self.assertFalse(blocked["pass"])
        self.assertFalse(blocked["symbol_ownership_ok"])
        self.assertIn("UNOWNED_SYMBOL_TOUCHED:unrelated_helper", blocked["symbol_ownership_violations"])

        # Admitted when symbol is owned + coupled two-guard replacement succeeds
        repaired = kernel.localize_producer_and_repair_holes(
            repo_root=REPO_ROOT / "canonical" / "swe_kernel",
            source=src,
            changed_lines=[2, 4],
            owned_symbols=["validate_bounds"],
            two_guard_edits=[
                {"old": "x < lo", "new": "x <= lo"},
                {"old": "x > hi", "new": "x >= hi"},
            ],
        )
        self.assertTrue(repaired["pass"], repaired)
        self.assertTrue(repaired["two_guard_applied"])
        self.assertIn("x <= lo", repaired["patched_source"])
        self.assertIn("x >= hi", repaired["patched_source"])
        self.assertGreater(repaired["lineage_function_count"], 0)

    def test_04_ax_guard_accessibility_debt_zero_screenshot_cache_and_osworld_ledger(self) -> None:
        kernel = W45.AXGuardZeroShotCacheHCUKernel()

        # Accessibility-debt audit: zero debt -> Channel 1 pure AX; undescribed widget -> vision only on debt
        clean_nodes = [
            {"id": "btn-1", "role": "button", "name": "Save", "states": ["enabled"]},
            {"id": "txt-1", "role": "textbox", "name": "Filename", "states": ["enabled"]},
        ]
        clean_audit = kernel.audit_accessibility_debt(clean_nodes)
        self.assertEqual(clean_audit["accessibility_debt_ratio"], 0.0)
        self.assertFalse(clean_audit["visual_fallback_needed"])
        self.assertEqual(clean_audit["recommended_channel"], "CHANNEL_1_PURE_AX_ZERO_PIXEL")

        debt_nodes = [
            {"id": "btn-1", "role": "button", "name": "Save"},
            {"id": "btn-2", "role": "button", "name": "", "bounds": [10, 20, 40, 50]},
            {"id": "dead-1", "role": "button", "name": "Old", "states": ["defunct"]},
        ]
        debt_audit = kernel.audit_accessibility_debt(debt_nodes)
        self.assertEqual(debt_audit["undescribed_count"], 1)
        self.assertEqual(debt_audit["defunct_filtered"], 1)
        self.assertTrue(debt_audit["visual_fallback_needed"])

        # Pre-input AX Action Guard blocks defunct target before executing
        obs_pre = {
            "url": "https://shop.local/orders/42",
            "ax_nodes": [{"id": "b1", "role": "button", "name": "Confirm", "states": ["enabled"]}],
            "predicates": ["cart_ready"],
            "fields": {"status": "draft"},
        }
        obs_defunct = {
            "url": "https://shop.local/orders/42",
            "ax_nodes": [{"id": "b1", "role": "button", "name": "Confirm", "states": ["defunct"]}],
            "predicates": ["cart_ready"],
            "fields": {"status": "draft"},
        }
        blocked = kernel.execute_guarded_cached_ax_batch(
            url="https://shop.local/orders/42",
            intent="confirm_order",
            action_type="click",
            selector="#confirm",
            expected_role="button",
            expected_name="Confirm",
            pre_obs=obs_pre,
            live_obs=obs_defunct,
            required_predicates=["cart_ready"],
            expected_added_predicates=["order_confirmed"],
        )
        self.assertFalse(blocked["pass"])
        self.assertIn("ACTION_GUARD_BLOCKED", blocked["status"])

        # Healthy live AX target succeeds with zero screenshots via ZeroScreenshotActionCache
        ok_res = kernel.execute_guarded_cached_ax_batch(
            url="https://shop.local/orders/42",
            intent="confirm_order",
            action_type="click",
            selector="#confirm",
            expected_role="button",
            expected_name="Confirm",
            pre_obs=obs_pre,
            live_obs=obs_pre,
            required_predicates=["cart_ready"],
            expected_added_predicates=["order_confirmed"],
            expected_field_deltas={"status": "confirmed"},
        )
        self.assertTrue(ok_res["pass"], ok_res)
        self.assertFalse(ok_res["pixel_vision_required"])
        self.assertTrue(all(ok_res["aux_organs_ready"].values()))

        # OSWorld verified task ledger compilation & audit
        led = kernel.audit_osworld_ledger(
            "Create a file named report.txt containing DONE",
            {"files": {"report.txt": "DONE"}},
        )
        self.assertIn("audit", led)
        self.assertIn("decision", led)

    def test_05_anti_manufactured_confidence_lapse_meme_6op_and_capsule_rollback(self) -> None:
        eng = W45.AntiManufacturedConfidenceMemoryEngine()

        # 1) Kwon 2026 Manufactured-Confidence Law: single hedged source is QUARANTINED, never authoritative!
        q1 = eng.ingest_fact(
            "alex",
            "clearance",
            "level_4",
            modality="HEDGED",
            source_id="slack-rumor-1",
            raw_text="Alex reportedly has level 4 clearance",
        )
        self.assertTrue(q1["quarantined"])
        self.assertFalse(q1["accepted_as_authoritative"])
        q_before = eng.query("alex", "clearance")
        self.assertNotEqual(q_before["query_result"].get("status"), "ESTABLISHED")
        self.assertEqual(len(q_before["hedged_quarantine"]), 1)

        # 2) Corroboration by a SECOND independent source promotes it cleanly!
        q2 = eng.ingest_fact(
            "alex",
            "clearance",
            "level_4",
            modality="HEDGED",
            source_id="hr-ledger-2",
            raw_text="Alex reportedly has level 4 clearance",
        )
        self.assertFalse(q2["quarantined"])
        self.assertTrue(q2["accepted_as_authoritative"])
        self.assertEqual(q2["record"]["modality"], "CORROBORATED")
        self.assertEqual(eng.query("alex", "clearance")["query_result"]["status"], "ESTABLISHED")

        # 3) LAPSE temporal-shape fidelity: progressive text stays PROGRESSIVE, never coerced to STATIVE
        prog = eng.ingest_fact(
            "alex",
            "project_status",
            "migration",
            source_id="standup-1",
            raw_text="Alex is working on the database migration for now",
        )
        self.assertEqual(prog["record"]["temporal_shape"], "PROGRESSIVE")
        self.assertEqual(prog["record"]["temporal_fidelity"], "FAITHFUL")
        checkpoint_head = prog["capsule_head"]

        # 4) MEME 6-op DependencyMemory Cascade + Retract + Absence-of-Support distinction!
        eng.add_rule(
            "r_access",
            head=("alex", "can_enter", "vault"),
            body=[("alex", "clearance", "level_4")],
        )
        self.assertEqual(eng.query("alex", "can_enter")["query_result"]["status"], "ESTABLISHED")
        eng.retract_fact("alex", "clearance", "level_4")
        after_retract = eng.query("alex", "can_enter")["query_result"]
        self.assertEqual(after_retract["status"], "ABSENCE__SUPPORT_PREMISE_INVALIDATED")

        # 5) Tamper-evident capsule rollback + capture-recapture unseen diagnostic
        rb = eng.rollback_capsule(checkpoint_head)
        self.assertTrue(rb["pass"], rb)
        diag = eng.diagnostic_readers_and_unseen(single_source_only=10, multi_source_overlap=5)
        self.assertTrue(diag["pass"])
        self.assertTrue(all(diag["organs_ready"].values()))

    def test_06_anytime_valid_evalue_gate_verifier_falsification_phi_and_thompson_defense(self) -> None:
        gate = W45.AnytimeValidEValueEvolutionGateKernel()

        # 1) Strong held-out sequence (18/18 wins against p0=0.5) crosses Ville 1/0.05 = 20 easily
        admitted = gate.admit_self_modification(
            "cand-strong",
            heldout_outcomes=[True] * 18,
            mutant_kills=9,
            total_mutants=10,
            patch_source="def safe_fix(x):\n    return max(0, x)\n",
            v1_errors=[True, False, False, False, True, False],
            v2_errors=[False, True, False, False, False, True],
            goal_text="edit ast function safe_fix to clamp negative values",
        )
        self.assertTrue(admitted["admitted"], admitted)
        self.assertGreaterEqual(admitted["e_process"]["sup_e_value"], 20.0)
        self.assertTrue(admitted["verifier_falsification"]["can_say_no"])
        self.assertTrue(admitted["verifier_dependence"]["independent_enough"])
        self.assertTrue(admitted["thompson_security"]["clean"])

        # 2) Reject rubber-stamp verifier (0/10 mutants killed)
        rubber = gate.admit_self_modification(
            "cand-rubber",
            heldout_outcomes=[True] * 18,
            mutant_kills=0,
            total_mutants=10,
        )
        self.assertFalse(rubber["admitted"])
        self.assertIn("VERIFIER_FALSIFICATION_FAILED__MUTANT_KILL_RATE_TOO_LOW", rubber["rejection_reasons"])

        # 3) Reject correlated verifiers (phi == 1.0 >= 0.5)
        corr = gate.admit_self_modification(
            "cand-corr",
            heldout_outcomes=[True] * 18,
            mutant_kills=10,
            total_mutants=10,
            v1_errors=[True, True, False, False, True, False],
            v2_errors=[True, True, False, False, True, False],
        )
        self.assertFalse(corr["admitted"])
        self.assertIn("VERIFIER_CORRELATED_ERRORS__PHI_GE_0_5", corr["rejection_reasons"])

        # 4) Reject Thompson-poisoning backdoor (`verify=False`)
        poison = gate.admit_self_modification(
            "cand-poison",
            heldout_outcomes=[True] * 18,
            mutant_kills=10,
            total_mutants=10,
            patch_source="requests.get(url, verify=False)\n",
        )
        self.assertFalse(poison["admitted"])
        self.assertTrue(any("THOMPSON_POISONING_DETECTED" in r for r in poison["rejection_reasons"]))

    def test_07_three_tier_continual_hierarchical_d2l_and_lrcp_zero_interference(self) -> None:
        cont = W45.ThreeTierZeroForgettingContinualKernel()

        # Tier 0: HierarchicalSkillLibrary acquire + counterfactual lesson + O(1) unlearn
        t0 = cont.tier0_learn_and_query(
            trace={
                "task": "patch boundary off-by-one bug in parser",
                "success": True,
                "operations": ["localize_guard", "check_alphabet", "run_pytest"],
            },
            query_task="boundary off-by-one bug",
        )
        self.assertTrue(t0["pass"])
        self.assertEqual(t0["k3_model_calls"], 0)

        # Tier 1: Doc-to-LoRA rank-budgeted adapter manifest (<50 MB, zero base-weight drift)
        t1 = cont.tier1_doc_to_lora_manifest("rfc-9999", "SPEC " * 1500, max_adapter_mb=50.0)
        self.assertTrue(t1["pass"], t1)
        self.assertTrue(t1["manifest"]["within_50mb_budget"])
        self.assertEqual(t1["manifest"]["base_weight_drift"], 0.0)

        # Tier 2: LRCP Gram-Schmidt orthogonal projection certifies < 1e-9 interference!
        t2 = cont.tier2_lrcp_orthogonal_consolidate(
            candidate_id="sleep-upd-1",
            new_gradient=[1.5, 2.0, -0.5, 3.0],
            historical_basis=[
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 1.0, 0.0],
            ],
            slot_activations={"slot_a": 0.92, "slot_b": 0.11, "slot_c": 0.87, "slot_d": 0.04},
            top_k_slots=2,
            heldout_outcomes=[True] * 18,
            mutant_kills=9,
            total_mutants=10,
        )
        self.assertTrue(t2["pass"], t2)
        self.assertTrue(t2["consolidation"]["zero_interference_certified"])
        self.assertLess(t2["consolidation"]["max_historical_interference"], 1e-12)
        self.assertEqual(t2["consolidation"]["sparse_memory_slots"], ["slot_a", "slot_c"])

    def test_08_unified_model_creature_and_federation_end_to_end_plus_elon_law(self) -> None:
        # Strict Elon Law check: brain_unified_model_v1.py strictly < 7,534 LOC
        bum_lines = len(
            (REPO_ROOT / "canonical" / "runtime" / "brain_unified_model_v1.py")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        self.assertLess(bum_lines, 7534, f"Elon Law cap exceeded: {bum_lines}")

        # Verify all 6 Wave 45-46 descriptors registered and unfamiliar-name concepts resolve
        for eid in (
            "LEAPFROG_W45_QUOTIENT_ANGELIC_PROBE_INDUCER",
            "LEAPFROG_W45_METAMORPHIC_LINEAGE_CORPUS_SWE",
            "LEAPFROG_W45_AX_GUARD_ZERO_SHOT_CACHE_HCU",
            "LEAPFROG_W46_ANTI_MANUFACTURED_CONFIDENCE_MEMORY",
            "LEAPFROG_W46_ANYTIME_VALID_EVALUE_EVOLUTION_GATE",
            "LEAPFROG_W46_THREE_TIER_ZERO_FORGETTING_CONTINUAL",
        ):
            self.assertIn(eid, FED.FEDERATED_KERNEL_DESCRIPTORS)

        # Federation dispatch smoke on anytime-valid e-value gate
        f_res = FED._dispatch_kernel(
            "LEAPFROG_W46_ANYTIME_VALID_EVALUE_EVOLUTION_GATE",
            {"op": "e_process", "heldout_outcomes": [True] * 18, "alpha": 0.05},
            "Verify anytime-valid SCoRE conformal e-values under Ville's inequality",
        )
        self.assertTrue(
            f_res.get("ok") is True or f_res.get("pass") is True or f_res.get("status") == "PASS",
            f_res,
        )

        # UnifiedModel + Creature end-to-end live facade
        model = BUM.load_unified_model()
        inv = model.awakened_dark_modules_w45_46_inventory()
        self.assertEqual(inv["cumulative_waves_40_to_46_count"], 100)

        with tempfile.TemporaryDirectory() as td:
            c = CR.boot(td, identity="wave45-46-test")
            mem_r = c.anti_manufactured_confidence_memory_op({
                "op": "ingest",
                "subj": "svc_a",
                "rel": "status",
                "obj": "degraded",
                "modality": "HEDGED",
                "source_id": "rumor-only",
                "raw_text": "svc_a is reportedly degraded",
            })
            self.assertTrue(mem_r["quarantined"])
            e_r = c.anytime_valid_evalue_gate_op({
                "op": "e_process",
                "heldout_outcomes": [True] * 18,
            })
            self.assertTrue(e_r["anytime_valid_pass"])


if __name__ == "__main__":
    unittest.main()
