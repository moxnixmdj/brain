#!/usr/bin/env python3
"""End-to-end & adversarial verification suite for the Unfamiliar-Name 6-Move UnifiedModel Leapfrog."""
from __future__ import annotations

import gzip
import io
import json
import lzma
import pathlib
import tempfile
import time
import unittest
import zipfile

from canonical.runtime import brain_unified_model_v1 as u
from canonical.runtime import monotone_semantic_drd_bridge_v1 as drd_bridge
from canonical.swe_kernel import unified_unfamiliar_leapfrog_v1 as uul

ROOT = pathlib.Path(__file__).resolve().parents[2]


class TestUnfamiliarSixMovesUnifiedModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = u.open_model(root=ROOT)

    def test_move_0_version_shadowing_collapse_and_apartness_lsharp(self) -> None:
        # 1. `find_source` collapses `v1..v(N-1)` clones by default while keeping explicit version queries intact
        collapsed = self.model.find_source("harbor science agent", top_k=5)
        paths_collapsed = [r["path"] for r in collapsed["candidates"]]
        self.assertIn("canonical/runtime/harbor_science_agent_v13.py", paths_collapsed)
        for old_v in range(1, 13):
            self.assertNotIn(f"canonical/runtime/harbor_science_agent_v{old_v}.py", paths_collapsed)

        explicit_v1 = self.model.find_source("harbor_science_agent_v1", top_k=5)
        self.assertEqual(
            explicit_v1["best"]["path"],
            "canonical/runtime/harbor_science_agent_v1.py",
        )

        # 2. `L#_e` observation-table-free constructive apartness + error-sink pruning
        def vault_machine(seq: list[str] | tuple[str, ...]) -> list[str]:
            st = 0
            outs: list[str] = []
            for act in seq:
                if act in ("bad_token", "expired_cert"):
                    outs.append("ERR_DENIED_SINK")
                elif st == 0 and act == "login":
                    st = 1
                    outs.append("SESSION_OPEN")
                elif st == 1 and act == "elevate":
                    st = 2
                    outs.append("PRIV_ARMED")
                elif st == 2 and act == "seal":
                    outs.append("SEALED_OK")
                else:
                    outs.append("REFUSED_ORDER")
            return outs

        alphabet = ["login", "elevate", "seal", "bad_token", "expired_cert"]
        held_out = [
            ["login", "elevate", "seal"],
            ["elevate", "login", "elevate", "seal"],
            ["bad_token", "login", "elevate"],
            ["login", "expired_cert", "elevate", "seal"],
        ]
        pruned_res = self.model.learn_apartness_lsharp(
            alphabet=alphabet,
            execute_trace=vault_machine,
            held_out_traces=held_out,
            target_output="SEALED_OK",
            prune_error_sinks=True,
        )
        unpruned_res = self.model.learn_apartness_lsharp(
            alphabet=alphabet,
            execute_trace=vault_machine,
            held_out_traces=held_out,
            target_output="SEALED_OK",
            prune_error_sinks=False,
        )
        self.assertTrue(pruned_res["pass"])
        self.assertIs(pruned_res["observation_table_allocated"], False)
        self.assertEqual(pruned_res["held_out_exact_accuracy"], 1.0)
        self.assertEqual(pruned_res["shortest_plan_to_target"], ["login", "elevate", "seal"])
        self.assertGreater(pruned_res["error_sink_probes_pruned"], 0)
        self.assertLessEqual(pruned_res["membership_queries"], unpruned_res["membership_queries"])
        self.assertLess(pruned_res["elapsed_ms"], 10.0)

    def test_move_1_angelic_forest_sygus_name_scope_and_non_vacuous_verifier(self) -> None:
        # 1a. Multi-function module where `unrelated_helper` is dead/unreachable and `normalize_slug` needs `OE-SyGuS`
        buggy_sygus = (
            "def dead_helper(x: int) -> int:\n"
            "    return x + 99\n\n"
            "def normalize_slug(raw: str) -> str:\n"
            "    return raw.lower()\n"
        )
        test_sygus = (
            "assert normalize_slug('  Hello_World  ') == 'hello_world'\n"
            "assert normalize_slug('clean') == 'clean'\n"
            "assert normalize_slug('\\tPyTest\\n') == 'pytest'\n"
        )
        res_sygus = self.model.solve_angelic_sygus_swe(buggy_sygus, test_sygus, seed_cold_store=True)
        self.assertTrue(res_sygus["pass"], res_sygus)
        self.assertGreaterEqual(res_sygus["angelic_pruned_site_count"], 1)
        self.assertEqual(res_sygus["non_vacuous_assertions_verified"], 3)
        self.assertGreater(res_sygus["cold_store_seed"]["admitted_count"], 0)
        self.assertGreater(res_sygus["cold_store_seed"]["refuted_coincidences_killed"], 0)

        # 1b. `NAME_SCOPE` (`__spec__.parent` -> `parent`) through BOTH `solve_angelic_sygus_swe` AND `solve_swe_repo`!
        with tempfile.TemporaryDirectory(prefix="name_scope_swe_") as td:
            repo = pathlib.Path(td)
            (repo / "lazy_loader.py").write_text(
                "class _SpecStub:\n"
                "    parent = 'wrong_root'\n"
                "__spec__ = _SpecStub()\n\n"
                "def child_module_name(parent: str, mod: str) -> str:\n"
                "    return f'{__spec__.parent}.{mod}'\n",
                encoding="utf-8",
            )
            (repo / "test_lazy_loader.py").write_text(
                "from lazy_loader import child_module_name\n\n"
                "def test_resolves_caller_parent():\n"
                "    assert child_module_name('packaging', 'errors') == 'packaging.errors'\n"
                "    assert child_module_name('packaging.licenses', 'spdx') == 'packaging.licenses.spdx'\n",
                encoding="utf-8",
            )
            swe_out = self.model.solve_swe_repo(repo, test_file="test_lazy_loader.py")
            self.assertTrue(swe_out["pass"], swe_out)
            repaired_disk = (repo / "lazy_loader.py").read_text(encoding="utf-8")
            self.assertIn("{parent}", repaired_disk)

        # 1c. All 4 PR #7049 non-vacuous verifier refusals must reject false passes
        r_zero = uul.audit_test_run_truthfulness(returncode=0, stdout="0 passed in 0.01s", stderr="")
        self.assertFalse(r_zero["truthful_pass"])
        self.assertEqual(r_zero["verdict"], "REFUSED__VACUOUS_ZERO_TESTS_RAN")

        r_coll = uul.audit_test_run_truthfulness(
            returncode=1,
            stdout="ERROR collecting test_mod.py\nImportError: cannot import name 'x'",
            stderr="",
        )
        self.assertFalse(r_coll["truthful_pass"])
        self.assertEqual(r_coll["verdict"], "REFUSED__COLLECTION_OR_IMPORT_ERROR")

        r_usage = uul.audit_test_run_truthfulness(
            returncode=4,
            stdout="RuntimeError: PYTEST_EXECUTION_FAILED:4\n1 passed",
            stderr="",
        )
        self.assertFalse(r_usage["truthful_pass"])
        self.assertEqual(r_usage["verdict"], "REFUSED__RUNNER_USAGE_OR_NO_TESTS_EXIT")

        r_valid = uul.audit_test_run_truthfulness(returncode=0, stdout="4 passed in 0.03s", stderr="")
        self.assertTrue(r_valid["truthful_pass"])
        self.assertEqual(r_valid["tests_ran"], 4)

    def test_move_2_protocol_lifting_kernel_isolation_and_effect_oracle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="move2_oracle_") as td:
            td_path = pathlib.Path(td)
            src_bytes = b"exact-round-trip-payload-bytes-98765"

            # Genuine gzip passes
            good_gz = td_path / "good.gz"
            good_gz.write_bytes(gzip.compress(src_bytes))
            res = self.model.lift_protocol_and_verify_effect(
                cdp_network_events=[
                    {"url": "https://portal.example/assets/bundle.css", "method": "GET", "status": 200, "mime_type": "text/css"},
                    {"url": "https://google-analytics.com/collect", "method": "POST", "status": 204, "mime_type": "text/plain"},
                    {
                        "url": "https://portal.example/api/orders",
                        "method": "POST",
                        "status": 200,
                        "mime_type": "application/json",
                        "post_data": json.dumps({"sku": "A1", "qty": 1}),
                    },
                ],
                webmcp_tools=[
                    {"name": "create_order", "inputSchema": {"required": ["sku", "qty"]}},
                ],
                goal_parameters={"sku": "B99", "qty": 4},
                transport_fn=lambda m, url, _h, body: {"status": 200, "method": m, "url": url, "body": body},
                artifact_check={"path": good_gz, "expected_source_bytes": src_bytes},
            )
            self.assertTrue(res["pass"])
            self.assertEqual(res["static_noise_events_deleted"], 2)
            self.assertEqual(res["webmcp_selected"]["bound_arguments"], {"qty": 4, "sku": "B99"})
            self.assertEqual(res["lifted_zero_browser_replay"]["body_sent"], {"sku": "B99", "qty": 4})
            self.assertIs(res["lifted_zero_browser_replay"]["browser_spawned"], False)

            # Impostor 1: `xz` bytes inside `fake_xz.gz` MUST BE REFUSED (PR #7071 measured bug!)
            fake_xz_as_gz = td_path / "fake_xz.gz"
            fake_xz_as_gz.write_bytes(lzma.compress(src_bytes))
            bad_xz = uul.verify_artifact_effect_oracle(fake_xz_as_gz, expected_source_bytes=src_bytes)
            self.assertFalse(bad_xz["pass"])
            self.assertIn("REFUSED__MAGIC_HEADER_MISMATCH:declared=.gz:actual=.xz", bad_xz["verdict"])

            # Impostor 2: `zip` archive inside `fake_zip.gz` (fools `gzip -dc`!) MUST BE REFUSED
            fake_zip_as_gz = td_path / "fake_zip.gz"
            zbuf = io.BytesIO()
            with zipfile.ZipFile(zbuf, "w") as zf:
                zf.writestr("payload.bin", src_bytes)
            fake_zip_as_gz.write_bytes(zbuf.getvalue())
            bad_zip = uul.verify_artifact_effect_oracle(fake_zip_as_gz, expected_source_bytes=src_bytes)
            self.assertFalse(bad_zip["pass"])
            self.assertIn("REFUSED__MAGIC_HEADER_MISMATCH:declared=.gz:actual=.zip", bad_zip["verdict"])

            # Impostor 3: Genuine gzip header but wrong payload bytes MUST BE REFUSED
            wrong_bytes_gz = td_path / "wrong_payload.gz"
            wrong_bytes_gz.write_bytes(gzip.compress(b"different-bytes"))
            bad_rt = uul.verify_artifact_effect_oracle(wrong_bytes_gz, expected_source_bytes=src_bytes)
            self.assertFalse(bad_rt["pass"])
            self.assertEqual(bad_rt["verdict"], "REFUSED__ROUNDTRIP_BYTES_MISMATCH")

            # Kernel/fork confinement sentinel check
            sentinel = td_path / "host_sentinel.txt"
            sentinel.write_text("UNTOUCHED", encoding="utf-8")
            iso = uul.execute_in_kernel_confinement(
                lambda scratch: (scratch / "local.txt").write_text("isolated", encoding="utf-8"),
                host_sentinel_path=sentinel,
            )
            self.assertTrue(iso["pass"])
            self.assertTrue(iso["host_untouched"])

    def test_move_3_why_provenance_semiring_jtms_meme_cascade_and_absence(self) -> None:
        bench = self.model.semiring_jtms_memory_cycle(chain_count=24, chain_depth=4)
        self.assertTrue(bench["pass"])
        self.assertEqual(bench["meme_cascade_accuracy"], 1.0)
        self.assertEqual(bench["meme_absence_accuracy"], 1.0)
        self.assertEqual(bench["diamond_alternative_proof_accuracy"], 1.0)
        self.assertLess(bench["retract_cascade_p50_us"], 100.0)

        # Verify unwitnessed write refusal + never-established vs invalidated-support Absence distinction
        mem = uul.SemiringProvenanceJTMSMemory()
        refused = mem.assert_premise("node_a", "status", "ok", witness_sha="")
        self.assertFalse(refused["accepted"])
        self.assertEqual(mem.query("never_seen", "status")["status"], "ABSTAIN__NEVER_ESTABLISHED")

    def test_move_4_minimax_contrastive_interrogation_and_semantic_drd_bridge(self) -> None:
        hyps = {
            "w_pos": lambda x: x > 0,
            "w_even_pos": lambda x: (x % 2 == 0) and x > 0,
            "w_gt5": lambda x: x > 5,
            "w_ge2": lambda x: x >= 2,
        }
        probes = [
            {"id": "p1", "input": 1, "cost_units": 1.0},
            {"id": "p2", "input": 2, "cost_units": 1.0},
            {"id": "p3", "input": 3, "cost_units": 1.0},
            {"id": "p6", "input": 6, "cost_units": 1.0},
            {"id": "p_destructive", "input": 0, "cost_units": 0.05, "irreversible": True},
        ]
        out = self.model.minimax_interrogate_version_space(
            hypotheses=hyps,
            candidate_probes=probes,
            true_oracle=hyps["w_even_pos"],
        )
        self.assertTrue(out["pass"])
        self.assertEqual(out["surviving_worlds"], ["w_even_pos"])
        self.assertLessEqual(len(out["executed_probes"]), 2)
        self.assertIn("p_destructive", out["gated_irreversible_probes"])

        # Negative control: non-separating probes (`{1, 2, 6}` cannot separate `w_even_pos` from `w_ge2`)
        non_sep = self.model.minimax_interrogate_version_space(
            hypotheses=hyps,
            candidate_probes=[p for p in probes if p["id"] != "p3"],
        )
        self.assertFalse(non_sep["pass"])

        # Also verify unwired `monotone_semantic_drd_bridge_v1.solve` over Boolean basis
        bridge_res = drd_bridge.solve(
            decision_basis=["is_admin", "has_mfa"],
            policy_conditions={
                "grant_access": {
                    "condition": {"op": "AND", "args": [{"op": "ATOM", "id": "is_admin"}, {"op": "ATOM", "id": "has_mfa"}]},
                    "adequacy_certificate_id": "cert_grant",
                },
                "deny_access": {
                    "condition": {
                        "op": "OR",
                        "args": [
                            {"op": "NOT", "arg": {"op": "ATOM", "id": "is_admin"}},
                            {"op": "NOT", "arg": {"op": "ATOM", "id": "has_mfa"}},
                        ],
                    },
                    "adequacy_certificate_id": "cert_deny",
                },
            },
            observations=[
                {"observation_id": "obs_admin", "formula": {"op": "ATOM", "id": "is_admin"}, "truthfulness_certificate_id": "cert_o1", "cost_units": 1.0},
                {"observation_id": "obs_mfa", "formula": {"op": "ATOM", "id": "has_mfa"}, "truthfulness_certificate_id": "cert_o2", "cost_units": 1.0},
            ],
        )
        self.assertTrue(bridge_res["pass"], bridge_res)

    def test_move_5_zero_llm_alphaevolve_and_anti_reward_hacking_gate(self) -> None:
        slow_fn = (
            "def sum_squares(n):\n"
            "    acc = 0\n"
            "    for i in range(n + 1):\n"
            "        acc += i ** 2\n"
            "    return acc\n"
        )
        evolved = self.model.evolve_pareto_organ(
            slow_fn,
            fn_name="sum_squares",
            test_inputs=[(0,), (1,), (7,), (60,), (500,)],
        )
        self.assertTrue(evolved["pass"], evolved)
        self.assertEqual(evolved["evaluator_false_passes"], 0)
        self.assertGreater(evolved["best_speedup_x"], 5.0)
        self.assertIn("// 6", evolved["best_source"])

        # Adversarial control: a vacuous/reward-hackable evaluator (`lambda _i, _o: True`) MUST be refused!
        hacked = self.model.evolve_pareto_organ(
            slow_fn,
            fn_name="sum_squares",
            test_inputs=[(1,), (5,)],
            evaluator_fn=lambda _inp, _out: True,
        )
        self.assertFalse(hacked["pass"])
        self.assertEqual(hacked["status"], "REFUSED__REWARD_HACKABLE_OR_VACUOUS_EVALUATOR")

    def test_front_door_concept_bridge_and_elon_latency_budgets(self) -> None:
        t0 = time.perf_counter()
        m_warm = u.open_model(root=ROOT)
        warm_ms = (time.perf_counter() - t0) * 1000.0
        self.assertLess(warm_ms, 5.0)

        concept = m_warm.resolve_concept("vaandrager apartness angelix eusolver why provenance semiring alphaevolve")
        self.assertEqual(
            concept["best"]["concept_family"],
            "unfamiliar_apartness_angelix_sygus_semiring_alphaevolve",
        )

        suite = m_warm.invoke_frontier_organ("unfamiliar_six_moves_suite")
        self.assertTrue(suite["pass"])
        self.assertEqual(suite["model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
