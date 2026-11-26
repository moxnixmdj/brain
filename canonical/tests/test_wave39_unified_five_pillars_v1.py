"""Wave 39 Verification Suite: Unified Five-Pillar Frontier Kernel + Zero-Adapter Inventory Bridge + Elon-Speed Slice Core.

Pure stdlib `unittest.TestCase` (compatible with both `python3 -m unittest` and `pytest`).
Covers positive + negative controls across:
  0. Zero-Adapter `5,221`-function Inventory Bridge (`module_bridge_v1` + `type_level_composer_v1`)
  1. Elon-speed `os.pread` cold-section slice loading (`section_byte_spans`) + `O(1)` postings `discover_dark_matter()`
  2. Pillar I: Action-invariant Moore bisimulation transfer, `OPINE-World` ontology-error predicate synthesis, FCA Galois concept lattices, and `FlashMeta D4` witness inversion
  3. Pillar II: Bijective OOXML/JSON structural lenses, relational record frames + `CAS` stale-click abort, `standing_facts_v1` batch clobber recovery, and `implied_ending_v1` anti-false-`DONE` gate
  4. Pillar III: Calibrated non-vacuous test oracle, Plastic Surgery donor mining, `Coccinelle`/`SyDIT` multi-file sibling closure, and `DeltaBox` warm-zygote `os.fork()` CoW rollouts
  5. Pillar IV: `Kumiho` write-time prospective cue indexing, `CPB` Sybil echo-chamber defense, AGM $K^*7/K^*8$ entrenchment, and `RD-Forget` selective replay unlearning (`Leak = 0.0`)
  6. Pillar V: `Babble`/`Stitch` Meaning-IR crystallization, zero-shot verified cross-language transfer (Python -> TypeScript/Go/Rust), Hoare contract composition, and MDL bit-rent eviction
  7. End-to-end `UnifiedModel`, `unified_hidden_capability_federation_v1`, `DOMAIN_ATLAS_V1`, and `Creature.step_unified()` (`K3 = 0`)
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest
import zipfile
from unittest import mock

from canonical.runtime.brain_unified_model_v1 import (
    DEFAULT_ARTIFACT,
    DEFAULT_CORE_ARTIFACT,
    ROOT,
    UnifiedModelError,
    load_model,
    open_model,
)
from canonical.runtime.creature_runtime_v1 import Creature
from canonical.runtime.mortality_and_triage_v1 import Work
from canonical.runtime.ooxml_package_transaction import XmlSetText
from canonical.runtime.unified_hidden_capability_federation_v1 import (
    resolve_cross_disciplinary_concept,
    run_federated_engine,
)
from canonical.swe_kernel.effect_contract_composition_v1 import Effect, EffectContract
from canonical.swe_kernel.unified_five_pillar_frontier_kernel_v1 import (
    UnifiedFivePillarKernel,
    compute_galois_concept_lattice,
    synthesize_by_witness_inversion,
)

MODEL_PATH = ROOT / DEFAULT_ARTIFACT
CORE_PATH = ROOT / DEFAULT_CORE_ARTIFACT


class _ModCounterEnv:
    def __init__(self, inc_name: str, jump_name: str, modulus: int = 4) -> None:
        self.inc_name = inc_name
        self.jump_name = jump_name
        self.modulus = modulus
        self.val = 0

    def reset(self) -> None:
        self.val = 0

    def state(self) -> int:
        return self.val

    def act(self, action: str) -> None:
        if action == self.inc_name:
            self.val = (self.val + 1) % self.modulus
        elif action == self.jump_name:
            self.val = (self.val + 2) % self.modulus


class TestWave39UnifiedFivePillarsV1(unittest.TestCase):
    def test_00_zero_adapter_inventory_bridge_discovers_and_composes_without_wrappers(self) -> None:
        model = open_model()
        res = model.zero_adapter_inventory_bridge(
            "read excel spreadsheet markdown",
            top_k=6,
            max_chain_len=2,
        )
        self.assertEqual(res["thin_adapters_created"], 0)
        self.assertEqual(res["model_calls"], 0)
        self.assertGreaterEqual(len(res["candidates"]), 1)
        fn_names = [c["function"] for c in res["candidates"]]
        self.assertIn("read_excel_to_markdown", fn_names)

    def test_01_cold_section_pread_slicing_avoids_full_13mb_json_load(self) -> None:
        core_meta = json.loads(CORE_PATH.read_text(encoding="utf-8"))
        spans = core_meta.get("section_byte_spans") or {}
        for key in (
            "source_index",
            "extended_source_index",
            "knowledge",
            "research_index",
            "harvested_capabilities",
        ):
            self.assertIn(key, spans, f"missing byte span for {key}")
            start, end = spans[key]
            self.assertGreater(start, 0)
            self.assertGreater(end, start)
            self.assertLess(end, int(core_meta["artifact_bytes"]))

        with tempfile.TemporaryDirectory() as td:
            tmp_path = pathlib.Path(td)
            with (
                mock.patch("canonical.runtime.brain_unified_model_v1._core_cache_dir", return_value=tmp_path / "sec_cache"),
                mock.patch("canonical.runtime.brain_unified_model_v1._get_mmap_csr", return_value=None),
                mock.patch.dict("canonical.runtime.brain_unified_model_v1._OPEN_MODEL_MEM_CACHE", {}, clear=True),
            ):
                cold_um = open_model()
                self.assertIsNone(cold_um._model_loaded)
                s_res = cold_um.find_source("transition system", top_k=5)
                dm_res = cold_um.discover_dark_matter("flashmeta prose d4 kumiho rd-forget", top_k=5)
                rec_res = cold_um.recall("verification", top_k=3)
                self.assertGreaterEqual(len(s_res["candidates"]), 1)
                self.assertEqual(
                    dm_res["l0_cross_disciplinary"]["best"]["concept_family"],
                    "five_pillar_frontier_unification_w39",
                )
                self.assertGreaterEqual(len(rec_res["hits"]), 1)
                # Crucial Elon-speed invariant: NONE of those cold queries loaded the 13.47 MB JSON!
                self.assertIsNone(cold_um._model_loaded)

            # Negative control: tampered artifact bytes still fail closed!
            tampered = tmp_path / "TAMPERED_MODEL.json"
            raw = MODEL_PATH.read_bytes()
            tampered.write_bytes(raw[:-32] + b" " * 32)
            with self.assertRaises(UnifiedModelError):
                load_model(tampered, verify=True)

    def test_02_pillar1_instant_learning_moore_transfer_ontology_galois_and_d4_witness(self) -> None:
        kern = UnifiedFivePillarKernel()
        src_env = _ModCounterEnv("step_right", "jump_across", modulus=4)
        tgt_env = _ModCounterEnv("alpha", "beta", modulus=4)

        turn = kern.run_turn(
            "induce unknown finite machine and transfer plan",
            pillar="INSTANT_LEARNING",
            payload={
                "source_env": src_env,
                "source_actions": ["step_right", "jump_across"],
                "source_is_goal": lambda s: s == 3,
                "source_plan": ["jump_across", "step_right"],
                "target_env": tgt_env,
                "target_actions": ["beta", "alpha"],
                "target_is_goal": lambda s: s == 3,
                "transitions": [
                    ("check_order", [(1, "b"), (2, "a")], [0]),
                    ("check_order", [(1, "a"), (2, "b")], [1]),
                ],
                "io_examples": [("Ada Lovelace", "AL"), ("Alan Turing", "AT")],
                "io_held_out": [("Grace Hopper", "GH"), ("Donald Knuth", "DK")],
                "concept_incidence": {
                    "moore": ["deterministic", "quotient", "bisimulation"],
                    "mealy": ["deterministic", "quotient"],
                    "galois": ["quotient", "lattice"],
                },
            },
        )
        self.assertTrue(turn["pass"])
        self.assertEqual(turn["model_calls"], 0)
        res = turn["result"]
        xfer = res["moore_isomorphism_transfer"]
        self.assertEqual(xfer["mapped_plan"], ["beta", "alpha"])
        self.assertTrue(xfer["target_goal_verified_by_execution"])

        # Negative control: 5-state target is provably non-isomorphic (`NO_WITNESS`)
        non_iso_env = _ModCounterEnv("alpha", "beta", modulus=5)
        neg = kern.instant_learner.learn_and_transfer(
            source_env=src_env,
            source_actions=["step_right", "jump_across"],
            source_is_goal=lambda s: s == 3,
            source_plan=["jump_across", "step_right"],
            target_env=non_iso_env,
            target_actions=["beta", "alpha"],
            target_is_goal=lambda s: s == 3,
        )
        self.assertIn("NO_WITNESS", str(neg["moore_isomorphism_transfer"]["isomorphism_status"]))
        self.assertNotIn("mapped_plan", neg["moore_isomorphism_transfer"])

        preds = res["ontology_error_residual"]["synthesized_separating_predicates"]
        self.assertIn("sorted_content", preds)

        inc = {"o1": ["a", "b"], "o2": ["a", "c"], "o3": ["b", "c"]}
        lat = compute_galois_concept_lattice(inc)
        self.assertGreaterEqual(len(lat), 4)
        # Verify Galois closure A'' == A and B' == A' on every formal concept
        for concept in lat:
            ext = set(concept["extent"])
            intent = set(concept["intent"])
            if ext:
                derived_intent = set.intersection(*(set(inc[o]) for o in ext))
                self.assertEqual(derived_intent, intent)
        self.assertEqual(res["witness_inversion_synthesis"]["best_program"], "acronym_upper(' ')")

        lin = synthesize_by_witness_inversion([(2, 7), (5, 16)], held_out=[(10, 31)])
        self.assertTrue(lin["pass"])
        self.assertEqual(lin["best_program"], "affine(3*x + 1)")

        between = synthesize_by_witness_inversion(
            [("user:<alice>@org", "alice"), ("id:<bob_42>@org", "bob_42")],
            held_out=[("tag:<root>@org", "root")],
        )
        self.assertTrue(between["pass"])
        self.assertIn("extract_between", between["best_program"])

    def test_03_pillar2_computer_use_bijective_ooxml_lens_cas_reanchor_standing_facts_and_ending(self) -> None:
        kern = UnifiedFivePillarKernel()
        with tempfile.TemporaryDirectory() as td:
            tmp_path = pathlib.Path(td)
            docx_path = tmp_path / "report.docx"
            with zipfile.ZipFile(docx_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    "[Content_Types].xml",
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>',
                )
                zf.writestr(
                    "word/document.xml",
                    '<?xml version="1.0" encoding="UTF-8"?>'
                    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                    "<w:body><w:p><w:t>Draft v0</w:t></w:p></w:body></w:document>",
                )

            obs_plan = {
                "elements": [
                    {"index": 0, "parent": -1, "tag": "div", "classes": "inbox", "text": ""},
                    {"index": 1, "parent": 0, "tag": "div", "classes": "email-row", "text": ""},
                    {"index": 2, "parent": 1, "tag": "span", "classes": "sender", "text": "Alice"},
                    {"index": 3, "parent": 1, "tag": "button", "classes": "star", "text": "", "can_click": True},
                    {"index": 4, "parent": 1, "tag": "button", "classes": "trash", "text": "", "can_click": True},
                    {"index": 5, "parent": 0, "tag": "div", "classes": "email-row", "text": ""},
                    {"index": 6, "parent": 5, "tag": "span", "classes": "sender", "text": "Enrichetta"},
                    {"index": 7, "parent": 5, "tag": "button", "classes": "star", "text": "", "can_click": True},
                    {"index": 8, "parent": 5, "tag": "button", "classes": "trash", "text": "", "can_click": True},
                ]
            }
            obs_live = {
                "elements": [
                    {"index": 0, "parent": -1, "tag": "div", "classes": "inbox", "text": ""},
                    {"index": 10, "parent": 0, "tag": "div", "classes": "email-row", "text": ""},
                    {"index": 11, "parent": 10, "tag": "span", "classes": "sender", "text": "NewArrival"},
                    {"index": 12, "parent": 10, "tag": "button", "classes": "star", "text": "", "can_click": True},
                    {"index": 13, "parent": 10, "tag": "button", "classes": "trash", "text": "", "can_click": True},
                    {"index": 40, "parent": 0, "tag": "div", "classes": "email-row", "text": ""},
                    {"index": 41, "parent": 40, "tag": "span", "classes": "sender", "text": "Enrichetta"},
                    {"index": 42, "parent": 40, "tag": "button", "classes": "star", "text": "", "can_click": True},
                    {"index": 43, "parent": 40, "tag": "button", "classes": "trash", "text": "", "can_click": True},
                ]
            }

            json_cfg = tmp_path / "settings.json"
            res = kern.computer_use.execute_workflow(
                instruction="Star the email from Enrichetta and update report",
                workspace_dir=tmp_path,
                observation=obs_plan,
                live_observation_before_dispatch=obs_live,
                record_identifier="Enrichetta",
                control_word="star",
                ooxml_transaction={
                    "input_path": str(docx_path),
                    "output_path": str(docx_path),
                    "operations": [
                        XmlSetText(member="word/document.xml", path=(0, 0, 0), text="Approved Final v1"),
                    ],
                },
                json_lens_patch={
                    "path": str(json_cfg),
                    "updates": {"theme": "solarized", "verified": True},
                },
                batch_steps=[
                    {"writes": {"batch_a.txt": "clean_a"}, "establish_facts": ["batch_a.txt"]},
                    {
                        "writes": {"batch_a.txt": "CLOBBERED_BY_MISTAKE", "batch_b.txt": "clean_b"},
                        "touches": ["batch_a.txt", "batch_b.txt"],
                        "establish_facts": ["batch_b.txt"],
                    },
                ],
            )
            self.assertTrue(res["pass"])
            with zipfile.ZipFile(docx_path, "r") as zf:
                self.assertIn("Approved Final v1", zf.read("word/document.xml").decode("utf-8"))
            self.assertTrue(res["json_lens_receipt"]["changed"])
            self.assertEqual(json.loads(json_cfg.read_text(encoding="utf-8"))["theme"], "solarized")
            self.assertTrue(res["cas_seal_guard"]["stale_click_aborted"])
            self.assertEqual(res["relational_frame"]["index"], 42)
            self.assertEqual(res["standing_facts"]["recovered_clobbers"], 1)
            self.assertEqual((tmp_path / "batch_a.txt").read_text(encoding="utf-8"), "clean_a")
            self.assertEqual((tmp_path / "batch_b.txt").read_text(encoding="utf-8"), "clean_b")

            obs_uncommitted = {
                "elements": [
                    {"index": 0, "tag": "input", "text": "", "value": "edited", "can_type": True},
                    {"index": 1, "tag": "button", "text": "Save", "classes": "save", "can_click": True},
                ]
            }
            blocked = kern.computer_use.execute_workflow(
                instruction="Enter the title in the input field",
                observation=obs_uncommitted,
                attempt_done=True,
            )
            self.assertFalse(blocked["pass"])
            self.assertFalse(blocked["done_gate"]["done_allowed"])
            self.assertTrue(blocked["done_gate"]["blocked_by_unclicked_implied_ending"])

    def test_04_pillar3_coding_agents_multifile_sibling_closure_cow_fork_and_vacuous_judge(self) -> None:
        kern = UnifiedFivePillarKernel()
        with tempfile.TemporaryDirectory() as td:
            tmp_path = pathlib.Path(td)
            repo = tmp_path / "multifile_repo"
            repo.mkdir()
            (repo / "billing.py").write_text(
                "def calc_us(sub, tax_rate):\n    return sub - sub * tax_rate\n", encoding="utf-8"
            )
            (repo / "checkout.py").write_text(
                "def calc_eu(net, vat_rate):\n    return net - net * vat_rate\n", encoding="utf-8"
            )
            (repo / "test_checkout.py").write_text(
                "import unittest\nfrom billing import calc_us\nfrom checkout import calc_eu\n"
                "class T(unittest.TestCase):\n"
                "    def test_us(self): self.assertAlmostEqual(calc_us(100.0, 0.1), 110.0)\n"
                "    def test_eu(self): self.assertAlmostEqual(calc_eu(200.0, 0.2), 240.0)\n",
                encoding="utf-8",
            )

            dry = kern.swe_kernel.repair_repository(repo, apply_winning_patch=False)
            self.assertTrue(dry["pass"])
            self.assertEqual(dry["winner"]["kind"], "SIBLING_CLOSED_MULTIFILE")
            self.assertEqual(sorted(dry["winner"]["files_touched"]), ["billing.py", "checkout.py"])
            self.assertIn(" - ", (repo / "billing.py").read_text(encoding="utf-8"))

            applied = kern.swe_kernel.repair_repository(repo, apply_winning_patch=True)
            self.assertTrue(applied["pass"])
            self.assertEqual(sorted(applied["applied_files"]), ["billing.py", "checkout.py"])
            self.assertIn(" + ", (repo / "billing.py").read_text(encoding="utf-8"))
            self.assertIn(" + ", (repo / "checkout.py").read_text(encoding="utf-8"))

            vac_repo = tmp_path / "vacuous_repo"
            vac_repo.mkdir()
            (vac_repo / "app.py").write_text("def compute(x):\n    return x * 2\n", encoding="utf-8")
            (vac_repo / "test_app.py").write_text(
                "import unittest\nclass TVac(unittest.TestCase):\n    def test_vacuous(self): self.assertTrue(True)\n",
                encoding="utf-8",
            )
            vac = kern.swe_kernel.repair_repository(vac_repo)
            self.assertFalse(vac["pass"])
            self.assertIn("ORACLE_DOES_NOT_FAIL", str(vac["status"]))

    def test_05_pillar4_memory_prospective_cues_sybil_lineage_entrenchment_and_selective_replay(self) -> None:
        kern = UnifiedFivePillarKernel()
        mem = kern.memory

        b1 = mem.stage_or_commit_belief(
            belief_id="b_gateway_timeout",
            subject="gateway_timeout_s",
            value=30,
            source_id="incident_note_1",
            positive_states=[
                ["env:prod", "svc:gateway", "dc:eu"],
                ["env:prod", "svc:gateway", "dc:us"],
            ],
            negative_states=[["env:staging", "svc:gateway", "dc:eu"]],
        )
        self.assertEqual(b1["status"], "PROVISIONAL")

        recalled = mem.recall_by_prospective_cues(["env:prod", "svc:gateway", "dc:ap"])
        self.assertEqual(recalled["hits"][0]["belief_id"], "b_gateway_timeout")

        sybil = mem.stage_or_commit_belief(
            belief_id="b_gateway_timeout",
            subject="gateway_timeout_s",
            value=30,
            source_id="summary_copy_of_note_1",
            parent_lineage_roots=["incident_note_1"],
        )
        self.assertTrue(sybil["sybil_echo_blocked"])
        self.assertEqual(sybil["status"], "PROVISIONAL")
        self.assertFalse(mem.authorize_irreversible_action(["b_gateway_timeout"])["authorized"])

        indep = mem.stage_or_commit_belief(
            belief_id="b_gateway_timeout",
            subject="gateway_timeout_s",
            value=30,
            source_id="envoy_live_config_2",
        )
        self.assertEqual(indep["status"], "COMMITTED")
        self.assertTrue(mem.authorize_irreversible_action(["b_gateway_timeout"])["authorized"])

        mem.stage_or_commit_belief(
            belief_id="b_healthcheck_ok",
            subject="healthcheck_enabled",
            value=True,
            source_id="k8s_probe",
            attested_by_sensor=True,
        )
        mem.register_derived_plan("plan_tainted_only", support_belief_ids=[["b_gateway_timeout"]])
        mem.register_derived_plan(
            "plan_diamond_survives",
            support_belief_ids=[["b_gateway_timeout"], ["b_healthcheck_ok"]],
        )

        weak_rumor = mem.stage_or_commit_belief(
            belief_id="b_weak_override",
            subject="gateway_timeout_s",
            value=999,
            source_id="unverified_chat_msg",
        )
        self.assertIn("ENTRENCH", str(weak_rumor["status"]))

        sensor_override = mem.stage_or_commit_belief(
            belief_id="b_sensor_timeout_10",
            subject="gateway_timeout_s",
            value=10,
            source_id="prometheus_sensor",
            attested_by_sensor=True,
        )
        replay = sensor_override["selective_replay"]
        self.assertEqual(replay["tainted_plan_leak_rate"], 0.0)
        self.assertEqual(replay["purged_tainted_plans"], ["plan_tainted_only"])
        self.assertEqual(replay["survived_alternative_proof_plans"], ["plan_diamond_survives"])

    def test_06_pillar5_continual_learning_meaning_ir_cross_language_ratchet_and_mdl_rent(self) -> None:
        kern = UnifiedFivePillarKernel()
        before_py = "def valid_idx(i, n):\n    return i <= n\n"
        after_py = "def valid_idx(i, n):\n    return i < n\n"

        c1 = EffectContract.of(
            "parse_ast",
            preconditions=("src_present",),
            observables=("src_file",),
            actions=("parse",),
            verdict="ast_parser",
            effects=(Effect("ESTABLISH", "ast_ready"),),
        )
        c2 = EffectContract.of(
            "apply_rule",
            preconditions=("ast_ready",),
            observables=("ast_tree",),
            actions=("rewrite_ir",),
            verdict="target_verifier",
            effects=(Effect("ESTABLISH", "patched_verified"),),
        )
        for lang, buggy, expected_sub in [
            ("typescript", "function validIdx(i, n) { return i <= n; }", "i < n"),
            ("go", "func validIdx(i int, n int) bool { return i <= n }", "i < n"),
            ("rust", "fn valid_idx(i: usize, n: usize) -> bool { return i <= n; }", "i < n"),
        ]:
            res = kern.skill_ratchet.consolidate_and_transfer(
                before_snippet=before_py,
                after_snippet=after_py,
                source_language="python",
                target_language=lang,
                target_buggy_source=buggy,
                target_verifier=lambda s, sub=expected_sub: sub in s and "<=" not in s,
                effect_contracts=[c1, c2],
            )
            self.assertTrue(res["pass"], f"failed transfer for {lang}: {res}")
            self.assertIn(expected_sub, res["cross_language_transfer"]["patched_source"])
            self.assertTrue(res["contract_verdict"]["pass"])

    def test_07_unified_model_federation_and_creature_step_unified_preserve_existing_contracts(self) -> None:
        model = open_model()
        organs = model.frontier_organs()
        move_ids = {m["organ_id"] for m in organs["leapfrog_moves"]}
        self.assertIn("w39_zero_adapter_inventory_bridge", move_ids)
        self.assertIn("w39_deltastate_sibling_swe", move_ids)

        inv = model.invoke_frontier_organ(
            "w39_zero_adapter_inventory_bridge",
            {"goal": "read excel spreadsheet markdown", "top_k": 4},
        )
        self.assertGreaterEqual(len(inv["candidates"]), 1)

        fed = run_federated_engine(
            "LEAPFROG_W39_ZERO_ADAPTER_INVENTORY_BRIDGE",
            {"goal": "read excel spreadsheet markdown", "top_k": 4},
        )
        self.assertTrue(fed["pass"])

        concept = resolve_cross_disciplinary_concept("FlashMeta D4 inverse witness RD-Forget Kumiho")
        self.assertEqual(concept["best"]["concept_family"], "five_pillar_frontier_unification_w39")

        with tempfile.TemporaryDirectory() as td:
            tmp_path = pathlib.Path(td)
            c_default = Creature(
                identity="c_default",
                root=tmp_path / "c_def",
                life_grant=20.0,
                _board=[Work(id="w1", value=5.0, cost=1.0)],
                _checkable={"w1": True},
            )
            c_default.boot()
            s_def = c_default.step()
            self.assertEqual(s_def["blocked"], "NO_EXECUTOR_WIRED")

            c_uni = Creature(
                identity="c_uni",
                root=tmp_path / "c_uni",
                life_grant=20.0,
                _board=[Work(id="w_uni", value=5.0, cost=1.0)],
                _checkable={"w_uni": True},
            )
            c_uni.boot()
            c_uni.attach_unified_work_payload("w_uni", {"goal": "read excel spreadsheet markdown"})
            s_uni = c_uni.step_unified()
            self.assertTrue(s_uni["ok"])
            self.assertTrue(s_uni["verified"])
            self.assertTrue(s_uni["correct"])
            self.assertEqual(s_uni["unified_turn"]["model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
