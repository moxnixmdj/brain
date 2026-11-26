#!/usr/bin/env python3
"""Zero-Mock End-to-End Tests for Wave 47-48 Frontier-Leapfrog Unification (`K3 = 0`, `$0` Spend).

Verifies all 6 newly federated Wave 47-48 engines, all 33 newly awakened DARK/unwired titan
modules (133 cumulative Waves 40-48), `UnifiedModel`, `Creature`, Federation dispatch,
cross-disciplinary concept-map routing, subprocess `dark_matter_adjudicator_v1` `PROVEN`
certification, static `K3 = 0` endpoint absence, and strict Elon Law LOC cap (< 7,534).
"""

from __future__ import annotations

import pathlib
import tempfile
import unittest

from canonical.runtime import brain_unified_model_v1 as BUM
from canonical.runtime import creature_runtime_v1 as CR
from canonical.runtime import unified_hidden_capability_federation_v1 as FED
from canonical.runtime import wave47_48_futamura_tomography_egraph_crystallizer_v1 as W47


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def _fed_ok(res: dict) -> bool:
    return bool(res.get("ok") is True or res.get("pass") is True or res.get("status") == "PASS")


def _fed_payload(res: dict) -> dict:
    for key in ("result", "details", "output", "data"):
        if isinstance(res.get(key), dict):
            return res[key]
    return res


class TestWave47To48FrontierLeapfrog(unittest.TestCase):
    def test_01_all_33_newly_awakened_dark_modules_133_cumulative_and_self_check(self) -> None:
        inv = W47.awakened_dark_modules_w47_48_inventory()
        self.assertTrue(inv["pass"], inv)
        self.assertEqual(inv["wave47_48_count"], 33)
        self.assertEqual(inv["wave47_48_loaded"], 33)
        self.assertEqual(inv["wave47_48_failed"], {})
        self.assertEqual(inv["overlap_with_w40_w46"], [])
        self.assertEqual(inv["cumulative_waves_40_to_48_count"], 133)
        self.assertEqual(len(set(W47.ALL_W40_W48_AWAKENED_DARK_MODULES)), 133)
        self.assertEqual(inv["k3_model_calls"], 0)
        self.assertEqual(inv["spend_usd"], 0.0)

        sc = W47.self_check()
        self.assertTrue(sc["pass"], sc)
        self.assertEqual(sc["verdict"], "SELF_CHECK_PASS")
        self.assertEqual(sc["checks"], 7)
        self.assertEqual(sc["passed"], 7)

    def test_02_futamura_skill_compiler_mealy_dbsp_and_action_grammar(self) -> None:
        k1 = W47.FutamuraSkillCompilerGrammarKernel()
        r1a = k1.run(
            {
                "op": "compile_trace",
                "goal": "Create user 'alice' at http://app.local/users",
                "trace": [
                    {"layer": "ui", "action": "click", "x": 120, "y": 40},
                    {"layer": "http_request", "method": "POST", "url": "http://app.local/users", "body": {"name": "alice"}},
                ],
                "postcondition": {"created": "alice"},
                "novel_goal": "Create user 'bob' at http://app.local/users",
            }
        )
        self.assertTrue(r1a["pass"], r1a)
        self.assertEqual(r1a["fastest_layer"], "http_request")
        self.assertTrue(r1a["fast_path_hit"])
        self.assertIn("bob", (r1a["novel_goal_bindings"] or {}).values())

        r1b = k1.run(
            {
                "op": "mealy_dbsp_evalue",
                "source": "def f(x):\n    if x < 0:\n        return -x\n    return x + 1\n",
                "test_cases": ["assert f(-2) == 2", "assert f(3) == 3"],
                "belief_deltas": [
                    {"key": "cfg:host", "value": "old", "weight": 1, "valid_from": 0, "valid_to": 5},
                    {"key": "cfg:host", "value": "new", "weight": 1, "valid_from": 5, "valid_to": None},
                ],
                "evalue_observations": [(True, 0.2), (True, 0.2), (True, 0.2), (True, 0.2)],
                "query_key": "cfg:host",
                "query_time": 10,
            }
        )
        self.assertTrue(r1b["pass"], r1b)
        self.assertEqual(r1b["conformal_decision"]["verdict"], "COMMIT")
        self.assertEqual(r1b["dbsp_query"][0]["payload"], "new")

        r1c = k1.run(
            {
                "op": "action_grammar",
                "guide_page": {"program": "gzip", "synopsis": {"description": "compress files"}, "declared": {}},
                "instruction": 'Fill Name with "Alice" and click Submit',
                "a11y_nodes": [
                    {"node_id": "n1", "role": "textbox", "name": "Name", "bounds": (10, 10, 200, 40)},
                    {"node_id": "n2", "role": "button", "name": "Submit", "bounds": (10, 60, 120, 90)},
                ],
                "submit_effects": {"n2": {"status_banner": "SUBMITTED:Submit"}},
                "expected_banner_contains": "SUBMITTED",
            }
        )
        self.assertTrue(r1c["pass"], r1c)
        self.assertTrue(r1c["gui_solved"])
        self.assertGreaterEqual(len(r1c["pyautogui"]), 2)

    def test_03_reverse_tomography_bidirectional_lens_and_assertion_demand(self) -> None:
        k2 = W47.ReverseTomographyAngelicLensSWEKernel()
        r2a = k2.run(
            {
                "op": "reverse_tomography",
                "source": "def compute(x):\n    return x + 1\n",
                "exc_msg": "AssertionError: assert 5 == 6",
                "actual_val": 5,
                "expected_val": 6,
                "ranked_lines": [{"line": 2, "score": 1.0}],
                "shrink_items": ["a", "b", "BUG", "c", "d", "e"],
                "bad_subset_token": "BUG",
            }
        )
        self.assertTrue(r2a["pass"], r2a)
        self.assertEqual(r2a["ddmin_minimal_items"], ["BUG"])
        self.assertTrue(r2a["ddmin_one_minimal"])
        self.assertGreaterEqual(r2a["boundary_vector_count"], 16)

        r2b = k2.run(
            {
                "op": "bidirectional_lens",
                "io_pairs": [("\x04", "^D"), ("\x1a", "^Z"), ("\x01", "^A")],
                "heldout_inputs": ["\x03", "\x07"],
                "negative_rule_signature": "bad_null_rule_sig",
            }
        )
        self.assertTrue(r2b["pass"], r2b)
        self.assertTrue(r2b["roundtrip_verified"])
        self.assertEqual(r2b["heldout_outputs"], ["^C", "^G"])
        self.assertTrue(r2b["negative_space_pruned"])

        r2c = k2.run(
            {
                "op": "assertion_demand",
                "test_source": "def test_it():\n    assert f(3) == 42\n",
                "assert_line": 2,
                "target_source": "def f(x):\n    return x + 1\n",
                "recorded_values": [4, 4],
            }
        )
        self.assertTrue(r2c["pass"], r2c)
        self.assertGreater(r2c["generated_term_count"], 0)

    def test_04_meaning_egraph_vericoding_and_exact_global_proof_cut(self) -> None:
        k3 = W47.MeaningEGraphVericodingProofCutKernel()
        r3a = k3.run({"op": "egraph_saturate", "run_semantic_self_check": True})
        self.assertTrue(r3a["pass"], r3a)
        self.assertEqual(r3a["mul2_extracted_op"], "shl")
        self.assertEqual(r3a["div2_extracted_op"], "var_x")
        self.assertTrue(r3a["semantic_causal_self_check_pass"])

        r3b = k3.run(
            {
                "op": "vericoding_audit",
                "test_source": "def test_sum():\n    assert add(2, 3) == 5\n",
                "request_text": 'Calling math_mod.add with JSON arguments [2, 3] must equal 5\nPython function add must exist in file "math_mod.py"',
                "positive_examples": [1, 5, 10],
                "negative_mutants": [-5, 0],
                "patch_a": {"a.py": "x = 1\n"},
                "patch_b": {"b.py": "y = 2\n"},
            }
        )
        self.assertTrue(r3b["pass"], r3b)
        self.assertTrue(r3b["strict_verifier_can_say_no"])
        self.assertTrue(r3b["tautology_verifier_rejected"])
        self.assertTrue(r3b["semantic_acceptance_complete"])
        self.assertEqual(r3b["orthogonal_merge_files"], ["a.py", "b.py"])

        r3c = k3.run(
            {
                "op": "proof_cut",
                "obligations": [
                    {"id": "OB1", "status": "OPEN", "terminal_necessary": True},
                    {"id": "OB2", "status": "OPEN", "terminal_necessary": True},
                ],
                "candidate_actions": [
                    {"id": "A_CHEAP", "covers": ["OB1", "OB2"], "new_reality_units": 1.0, "dependency_depth": 1, "critical_path_wall_clock_units": 2.0},
                    {"id": "A_DOMINATED", "covers": ["OB1"], "new_reality_units": 5.0, "dependency_depth": 2, "critical_path_wall_clock_units": 9.0},
                ],
            }
        )
        self.assertTrue(r3c["pass"], r3c)
        self.assertEqual(r3c["selected_actions"], ["A_CHEAP"])
        self.assertTrue(any(d["deleted"] == "A_DOMINATED" for d in r3c["dominated_deleted"]))

    def test_05_evolving_interface_and_ring0_byte_effect_oracle(self) -> None:
        k4 = W47.EvolvingInterfaceByteEffectHCUKernel()
        r4a = k4.run(
            {
                "op": "evolve_interface",
                "goal_text": "Convert input.csv to output.json",
                "domain": "cli",
                "traj_a": ["csv2json", "--in", "a.csv", "--out", "a.json"],
                "traj_b": ["csv2json", "--in", "b.csv", "--out", "b.json"],
                "petri_edges": [("s", "a"), ("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("d", "g")],
                "start_node": "s",
                "goal_node": "g",
            }
        )
        self.assertTrue(r4a["pass"], r4a)
        self.assertEqual(r4a["evolved_template"], ["csv2json", "--in", "?slot_0", "--out", "?slot_1"])
        self.assertEqual(r4a["petri_dominator_cuts"], ["a", "d"])

        r4b = k4.run(
            {
                "op": "transactional_byte_effect",
                "file_writes": {"report.json": b'{"ok": true}\n'},
                "allowed_writes": ["report.json"],
                "check_target": "report.json",
                "inject_unauthorized_file": "rogue.tmp",
                "simulate_crash_recovery": True,
            }
        )
        self.assertTrue(r4b["pass"], r4b)
        self.assertTrue(r4b["crash_recovered"])
        self.assertTrue(r4b["directory_effect_pass"])
        self.assertTrue(r4b["unauthorized_side_effect_caught"])

    def test_06_five_timescale_sleep_csr_and_cross_language_ir(self) -> None:
        k5 = W47.FiveTimescaleSleepCrystallizerCSRMemoryEngine()
        r5a = k5.run(
            {
                "op": "five_timescale_bus",
                "entity": "svc_api",
                "attribute": "port",
                "initial_value": "8080",
                "updated_value": "9090",
            }
        )
        self.assertTrue(r5a["pass"], r5a)
        self.assertEqual(r5a["initial_query_values"], ["8080"])
        self.assertEqual(r5a["superseded_query_values"], ["9090"])
        self.assertEqual(r5a["historical_time_travel_values"], ["8080"])
        self.assertEqual(r5a["write_amplification_llm_calls"], 0)

        r5b = k5.run(
            {
                "op": "mmap_csr_index",
                "rows_by_path": {
                    "a.py": {"tokens": ["alpha", "beta"], "terms": {"alpha": 2, "beta": 1}, "length": 2},
                    "b.py": {"tokens": ["beta", "gamma"], "terms": {"beta": 3, "gamma": 1}, "length": 2},
                },
                "query_term": "beta",
            }
        )
        self.assertTrue(r5b["pass"], r5b)
        self.assertEqual(r5b["posting_hits"], 2)

        r5c = k5.run({"op": "cross_lang_crystallize"})
        self.assertTrue(r5c["pass"], r5c)
        self.assertIn("None", r5c["compiled_python"])
        self.assertIn("null", r5c["compiled_javascript"])
        self.assertIn("NULL", r5c["compiled_c"])
        self.assertTrue(r5c["good_candidate_admitted"])
        self.assertTrue(r5c["control_breaking_rejected"])

    def test_07_meta_circular_plotkin_refusal_and_dark_matter_adjudicator(self) -> None:
        k6 = W47.MetaCircularConceptRefusalAdjudicatorKernel()
        r6a = k6.run({"op": "meta_circular_concept"})
        self.assertTrue(r6a["pass"], r6a)
        self.assertTrue(r6a["unsafe_organ_blocked"])
        self.assertTrue(r6a["firewall_protected_blocked"])
        self.assertTrue(r6a["firewall_mutable_allowed"])
        self.assertIn("_fn0", r6a["plotkin_lgg_params"])
        self.assertIsNotNone(r6a["periodic_operator"])

        r6b = k6.run({"op": "refusal_curriculum"})
        self.assertTrue(r6b["pass"], r6b)
        self.assertEqual(r6b["curriculum_demand"]["class"], "OVERWRITE")
        self.assertIn("token_limit", r6b["refusal_named_missing_words"])
        self.assertEqual(r6b["efe_ranked_experiments"][0]["probe"], "balanced_split")

        r6c = k6.run(
            {
                "op": "adjudicate_and_k3_audit",
                "module_names": [
                    "canonical.runtime.wave47_48_futamura_tomography_egraph_crystallizer_v1",
                    "canonical.swe_kernel.semantic_causal_engine_v1",
                ],
                "k3_audit_relpaths": [
                    "canonical/runtime/wave47_48_futamura_tomography_egraph_crystallizer_v1.py",
                ],
            }
        )
        self.assertTrue(r6c["pass"], r6c)
        self.assertEqual(r6c["proven_count"], 2)
        self.assertEqual(r6c["total_endpoint_hits"], 0)

    def test_08_unified_model_creature_federation_concept_map_and_elon_law(self) -> None:
        bum_lines = len(
            (REPO_ROOT / "canonical" / "runtime" / "brain_unified_model_v1.py")
            .read_text(encoding="utf-8")
            .splitlines()
        )
        self.assertLess(bum_lines, 7534, f"Elon Law cap exceeded: {bum_lines}")

        for eid in (
            "LEAPFROG_W47_FUTAMURA_SKILL_COMPILER_GRAMMAR",
            "LEAPFROG_W47_REVERSE_TOMOGRAPHY_ANGELIC_LENS_SWE",
            "LEAPFROG_W47_MEANING_EGRAPH_VERICODING_PROOF_CUT",
            "LEAPFROG_W48_EVOLVING_INTERFACE_BYTE_EFFECT_HCU",
            "LEAPFROG_W48_FIVE_TIMESCALE_SLEEP_CSR_MEMORY",
            "LEAPFROG_W48_META_CIRCULAR_REFUSAL_ADJUDICATOR",
        ):
            self.assertIn(eid, FED.FEDERATED_KERNEL_DESCRIPTORS)

        f1 = FED._dispatch_kernel(
            "LEAPFROG_W47_MEANING_EGRAPH_VERICODING_PROOF_CUT",
            {"op": "egraph_saturate", "run_semantic_self_check": False},
            "Run egglog equality saturation and universal meaning UIR canonicalization",
        )
        self.assertTrue(_fed_ok(f1), f1)
        f2 = FED._dispatch_kernel(
            "LEAPFROG_W48_META_CIRCULAR_REFUSAL_ADJUDICATOR",
            {"op": "meta_circular_concept"},
            "Discover Plotkin LGG fold abstraction behind Ring-0 SelfPatchFirewall",
        )
        self.assertTrue(_fed_ok(f2), f2)

        # Cross-disciplinary unfamiliar-name concept map hits our new Wave 47-48 engines
        hit_fut = FED.resolve_cross_disciplinary_concept("futamura projection partial evaluation egglog vericoding")
        self.assertTrue(any("LEAPFROG_W47" in e for m in hit_fut["matched_families"] for e in m["engines"]), hit_fut)
        hit_s4 = FED.resolve_cross_disciplinary_concept("agent s4 evolving agent interfaces sleep time compute feldera dbsp")
        self.assertTrue(any("LEAPFROG_W48" in e for m in hit_s4["matched_families"] for e in m["engines"]), hit_s4)
        hit_lilo = FED.resolve_cross_disciplinary_concept("higher order plotkin lgg lilo stitch dark matter adjudicator")
        self.assertTrue(any("LEAPFROG_W48_META_CIRCULAR_REFUSAL_ADJUDICATOR" in e for m in hit_lilo["matched_families"] for e in m["engines"]), hit_lilo)

        # UnifiedModel + Creature live end-to-end facade
        um = BUM.load_unified_model()
        inv = um.awakened_dark_modules_w47_48_inventory()
        self.assertEqual(inv["cumulative_waves_40_to_48_count"], 133)
        self.assertTrue(um.meaning_egraph_vericoding_op({"op": "egraph_saturate", "run_semantic_self_check": False})["pass"])

        with tempfile.TemporaryDirectory() as td:
            c = CR.boot(td, identity="wave47-48-test")
            c1 = c.futamura_skill_compiler_op(
                {
                    "op": "compile_trace",
                    "goal": "Create user 'alice' at http://app.local/users",
                    "trace": [
                        {"layer": "ui", "action": "click", "x": 120, "y": 40},
                        {"layer": "http_request", "method": "POST", "url": "http://app.local/users", "body": {"name": "alice"}},
                    ],
                    "postcondition": {"created": "alice"},
                    "novel_goal": "Create user 'dana' at http://app.local/users",
                }
            )
            self.assertTrue(c1["pass"], c1)
            c2 = c.reverse_tomography_lens_swe_op(
                {
                    "op": "bidirectional_lens",
                    "io_pairs": [("\x04", "^D"), ("\x1a", "^Z")],
                    "heldout_inputs": ["\x05"],
                }
            )
            self.assertTrue(c2["pass"] and c2["heldout_outputs"] == ["^E"], c2)
            c3 = c.meaning_egraph_vericoding_op({"op": "egraph_saturate", "run_semantic_self_check": False})
            self.assertTrue(c3["pass"], c3)
            c4 = c.evolving_interface_byte_effect_hcu_op(
                {
                    "op": "transactional_byte_effect",
                    "file_writes": {"out.json": b'{"v": 1}\n'},
                    "allowed_writes": ["out.json"],
                    "check_target": "out.json",
                    "inject_unauthorized_file": "evil.bin",
                }
            )
            self.assertTrue(c4["pass"], c4)
            c5 = c.five_timescale_sleep_csr_memory_op({"op": "cross_lang_crystallize"})
            self.assertTrue(c5["pass"], c5)
            c6 = c.meta_circular_refusal_adjudicator_op({"op": "meta_circular_concept"})
            self.assertTrue(c6["pass"], c6)


if __name__ == "__main__":
    unittest.main()
