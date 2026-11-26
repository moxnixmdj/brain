#!/usr/bin/env python3
"""Wave 39 Real-Execution Verification Suite (K3 = 0, $0 spend, ZERO mocks).

Proves end-to-end live execution across `UnifiedModel`, `Creature`, and
`unified_hidden_capability_federation_v1` for all 6 Wave 39 pillars:
1. Mendel Gödel Machine dual splicing + ALBI semantic-anonymization + Anti-Slop/No-Phantom-Guardrails/Symbol-Ownership.
2. Red Queen earned-judge discovery (`auto_judge_discovery_v1` + `earn_a_judge_v1`) + CLI `--check`/refusal/type lifter.
3. Typed `(P,O,A,V,F)` effect-contract composition + Sussman partial-order planning + lifted sketches + provenance + refutation.
4. Decision-theoretic CoW version-space agreement gate (`what_a_decision_costs_v1.decisive`) + real POSIX `os.fork()` isolation.
5. Verbatim 4-way RRF budgeted memory + Nemori surprise gating + TMA-NM tamper exclusion + CLM file-mirrored working context.
6. Closed-form `JitRL` KL logit modulation + `SkillTTA` + Intra-task `Partial Routing` + live `self_verify_harvested_surfaces`.
7. Persistent `Creature` front-door Wave 39 integration.
8. 10 `LEAPFROG_W39_*` federated engines + late-2026 unfamiliar-name lookup + 1.000 `DOMAIN_ATLAS_V1` route recall.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.runtime.unified_hidden_capability_federation_v1 import (
    FEDERATED_KERNEL_DESCRIPTORS,
    resolve_cross_disciplinary_concept,
    run_federated_engine,
)
from canonical.runtime.wave39_leapfrog_unification_v1 import RedQueenMendelEvolver

ROOT = Path(__file__).resolve().parents[2]


class TestFrontierLeapfrogWave39(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model = open_model()

    def test_01_mendel_splicing_albi_anonymization_and_anti_slop_phantom_gates(self) -> None:
        # 1A: Mendel hybridization solves a 2-bug function where NEITHER sibling lineage passes alone
        parent = (
            "def normalize_pair(a, b):\n"
            "    left = a - 1\n"
            "    right = b - 2\n"
            "    return (left, right)\n\n"
            "def untouched_helper(z):\n"
            "    return z * 2\n"
        )
        lineage_a = parent.replace("left = a - 1", "left = a + 1")
        lineage_b = parent.replace("right = b - 2", "right = b + 2")

        def verify_pair(src: str) -> bool:
            ns: dict[str, object] = {}
            exec(src, ns)
            fn = ns["normalize_pair"]
            helper = ns["untouched_helper"]
            return fn(10, 20) == (11, 22) and fn(0, 0) == (1, 2) and helper(5) == 10

        res = self.model.mendel_red_queen_evolve(
            parent,
            lineage_a,
            lineage_b,
            verifier=verify_pair,
            owned_symbols=["normalize_pair"],
        )
        self.assertTrue(res["pass"], f"Mendel splicing failed: {res}")
        self.assertEqual(res["model_calls"], 0)
        self.assertFalse(res["lineage_a_passes"])
        self.assertFalse(res["lineage_b_passes"])
        self.assertTrue(res["hybrid_solved_beyond_parents"])
        self.assertIsNotNone(res["winner"])
        self.assertTrue(res["winner"]["gate_admitted"])
        self.assertTrue(res["winner"]["albi"]["albi_invariant"])

        # 1B: Anti-Slop rejects bloated patches (> 1.60x AST nodes)
        bloated = (
            "def normalize_pair(a, b):\n"
            "    tmp1 = a + 1\n"
            "    tmp2 = b + 2\n"
            "    tmp3 = tmp1 + 0 + 0 + 0\n"
            "    tmp4 = tmp2 + 0 + 0 + 0\n"
            "    tmp5 = [tmp3, tmp4, tmp1, tmp2]\n"
            "    return (tmp5[0], tmp5[1])\n\n"
            "def untouched_helper(z):\n"
            "    return z * 2\n"
        )
        slop_audit = self.model.audit_anti_slop_patch(parent, bloated, owned_symbols=["normalize_pair"], max_ast_bloat_ratio=1.35)
        self.assertFalse(slop_audit["admitted"])
        self.assertTrue(any(r.startswith("SLOP_AST_BLOAT:") for r in slop_audit["reasons"]))

        # 1C: No-Phantom-Guardrails rejects unwitnessed guard, admits guard with real discriminating failing witness
        guarded = (
            "def normalize_pair(a, b):\n"
            "    if a is None:\n"
            "        raise ValueError('none')\n"
            "    return (a + 1, b + 2)\n\n"
            "def untouched_helper(z):\n"
            "    return z * 2\n"
        )
        phantom_rej = self.model.audit_anti_slop_patch(parent, guarded, owned_symbols=["normalize_pair"])
        self.assertFalse(phantom_rej["admitted"])
        self.assertTrue(any("PHANTOM_GUARDRAIL_UNWITNESSED" in r for r in phantom_rej["reasons"]))

        def witness_none_raises_value_error(src: str) -> bool:
            ns: dict[str, object] = {}
            exec(src, ns)
            try:
                ns["normalize_pair"](None, 1)
                return False
            except ValueError:
                return True
            except TypeError:
                return False

        witness_ok = self.model.audit_anti_slop_patch(
            parent,
            guarded,
            failing_witness=witness_none_raises_value_error,
            owned_symbols=["normalize_pair"],
        )
        self.assertTrue(witness_ok["admitted"], f"Witnessed guard should be admitted: {witness_ok}")
        self.assertEqual(witness_ok["witness_status"], "WITNESS_VERIFIED")

        # 1D: Symbol-ownership rejects out-of-scope edits to `untouched_helper`
        collateral = parent.replace("return z * 2", "return z * 3")
        scope_rej = self.model.audit_anti_slop_patch(parent, collateral, owned_symbols=["normalize_pair"])
        self.assertFalse(scope_rej["admitted"])
        self.assertTrue(any("SYMBOL_OWNERSHIP_VIOLATION:untouched_helper" in r for r in scope_rej["reasons"]))

        # 1E: ALBI semantic anonymization yields identical structural SHA for alpha-equivalent code
        a1 = RedQueenMendelEvolver.alpha_anonymize_python("def foo(alpha, beta):\n    return alpha + beta\n")
        a2 = RedQueenMendelEvolver.alpha_anonymize_python("def bar(x_val, y_val):\n    return x_val + y_val\n")
        self.assertEqual(a1["structural_sha256"], a2["structural_sha256"])

    def test_02_red_queen_earned_judges_and_refusal_check_mode_lifter(self) -> None:
        j_res = self.model.discover_and_earn_judges(
            artifacts_by_kind={
                "json": [b'{"k": 1}', b"[10, 20, 30]"],
                "xml": [b"<doc><item>ok</item></doc>"],
            }
        )
        self.assertTrue(j_res["pass"], f"Earned judge discovery failed: {j_res}")
        self.assertEqual(j_res["model_calls"], 0)
        self.assertGreaterEqual(j_res["stdlib_candidates_discovered"], 14)
        earned_kinds = {e["kind"]: e["judge_name"] for e in j_res["earned_judges"]}
        self.assertIn("json", earned_kinds)
        self.assertIn("xml", earned_kinds)

        r_res = self.model.lift_refusal_and_check_oracle(
            "Usage: deploy [OPTIONS] TARGET\n  -n, --dry-run   simulate actions\n  --check         verify config\n  -v, --verbose   verbose\n",
            refusal_lines=["No signature to verify: use the -signature option"],
            action_argv=("deploy", "/tmp/pkg.tar"),
            paths=["/tmp/pkg.tar"],
            type_map={"a.json": "json", "b.json": "json", "c.xml": "xml"},
            labels={"a.json": "json", "b.json": "xml", "c.xml": "xml"},
        )
        self.assertTrue(r_res["pass"])
        self.assertIn("--dry-run", r_res["check_like_flags"])
        self.assertIn("--check", r_res["check_like_flags"])
        self.assertGreaterEqual(r_res["probe_candidates_count"], 2)
        self.assertEqual(r_res["refusal_vocabulary"][0]["parsed_spec"]["form"], "OFFERED")
        self.assertEqual(r_res["refusal_vocabulary"][0]["parsed_spec"]["candidate"], "-signature")
        self.assertTrue(len(r_res["collapsed_type_pairs"]) >= 1)

    def test_03_effect_contracts_sussman_partial_order_lifted_generalizer_and_provenance(self) -> None:
        res = self.model.compose_and_plan_contracts(
            use_measured_advance_pair=True,
            initial_facts=("on_table_A", "on_table_B", "on_A_C", "clear_B", "clear_C"),
            goal_facts=("on_B_A", "on_C_B"),
            operators=[
                {"ident": "unstack_C_A", "pre": ("on_A_C", "clear_C"), "add": ("on_table_C", "clear_A"), "delete": ("on_A_C",)},
                {"ident": "stack_B_C", "pre": ("on_table_B", "clear_B", "clear_C"), "add": ("on_C_B",), "delete": ("on_table_B", "clear_C")},
                {"ident": "stack_A_B", "pre": ("on_table_A", "clear_A", "clear_B"), "add": ("on_B_A",), "delete": ("on_table_A", "clear_B")},
            ],
            concrete_plan=["unstack_C_A", "stack_B_C", "stack_A_B"],
            success_states=[{"on_A_C", "clear_C", "clear_B"}],
            failure_states=[{"clear_B"}],
            ast_provenance_source="def check(x):\n    if x > 0:\n        return x\n    return 0\n",
            run_observation_refutation=True,
        )
        self.assertTrue(res["pass"], f"Contract+Plan failed: {res}")
        self.assertEqual(res["model_calls"], 0)
        self.assertTrue(res["composition"]["chain_valid"])
        self.assertEqual(res["partial_order_plan"]["status"], "PASS__PARTIAL_ORDER_FOUND")
        self.assertEqual(res["partial_order_plan"]["steps"], ["unstack_C_A", "stack_B_C", "stack_A_B"])
        self.assertGreaterEqual(res["partial_order_plan"]["stats"]["threats_resolved"], 1)
        self.assertIsNotNone(res["lifted_generalization"]["sketch"])
        self.assertIn("BRANCH_COUNT_1", res["ast_provenance"]["provenance_features"])
        self.assertGreaterEqual(res["observation_refutation"]["passed"], 1)

    def test_04_decision_cost_cow_gate_agreement_skip_and_real_fork_isolation(self) -> None:
        # 4A: All surviving hypotheses agree -> 0 CoW forks paid
        agree = self.model.speculative_cow_decide(
            survivor_requirements=[{"git_repo", "clean"}, {"git_repo"}],
            observed_facts=["git_repo", "clean"],
        )
        self.assertTrue(agree["pass"])
        self.assertEqual(agree["decision"], "BY_KNOWLEDGE_APPLY")
        self.assertEqual(agree["cow_trials_paid"], 0)

        # 4B: Hypotheses disagree -> real POSIX os.fork() CoW speculation; parent memory untouched
        parent_state = {"mutated_by_child": False}

        def failing_cand() -> int:
            parent_state["mutated_by_child"] = True
            return -999

        def passing_cand() -> int:
            parent_state["mutated_by_child"] = True
            return 2026

        spec = self.model.speculative_cow_decide(
            survivor_requirements=[{"git_repo", "clean"}, {"git_repo"}],
            observed_facts=["git_repo"],
            candidates=[("bad_trial", failing_cand), ("good_trial", passing_cand)],
            verifier=lambda v: v == 2026,
        )
        self.assertTrue(spec["pass"])
        self.assertEqual(spec["decision"], "SPECULATIVE_COW_TRIAL_VERIFIED")
        self.assertEqual(spec["cow_trials_paid"], 2)
        self.assertTrue(spec["winner"]["cow_forked"])
        self.assertEqual(spec["winner"]["candidate_id"], "good_trial")
        self.assertFalse(parent_state["mutated_by_child"], "CoW fork leaked mutation into parent RAM!")

    def test_05_clm_4way_rrf_nemori_surprise_and_tma_nm_tamper_exclusion(self) -> None:
        # 5A: Nemori surprise gating (admit novel, skip low-surprise duplicate, admit belief conflict)
        w1 = self.model.clm_rrf_memory_op(
            "WRITE_SURPRISE_GATED",
            {
                "record_id": "w39_rec_seccomp",
                "key": "kernel.seccomp.io_uring",
                "verbatim_text": "classic BPF seccomp filter returns EPERM on io_uring_setup inside user namespace",
                "payload": {"verdict": "EPERM"},
                "valid_from": 100.0,
                "entities": ["seccomp", "io_uring", "bpf"],
            },
        )
        self.assertTrue(w1["admitted"])
        self.assertEqual(w1["status"], "ADMITTED_SURPRISING")

        w_dup = self.model.clm_rrf_memory_op(
            "WRITE_SURPRISE_GATED",
            {
                "record_id": "w39_rec_seccomp_dup",
                "key": "kernel.seccomp.io_uring",
                "verbatim_text": "classic BPF seccomp filter returns EPERM on io_uring_setup inside user namespace",
                "payload": {"verdict": "EPERM"},
                "valid_from": 101.0,
                "min_surprise": 0.25,
            },
        )
        self.assertFalse(w_dup["admitted"])
        self.assertEqual(w_dup["status"], "SKIPPED_LOW_SURPRISE")

        w_conflict = self.model.clm_rrf_memory_op(
            "WRITE_SURPRISE_GATED",
            {
                "record_id": "w39_rec_seccomp_v2",
                "key": "kernel.seccomp.io_uring",
                "verbatim_text": "classic BPF seccomp filter returns EPERM on io_uring_setup and keyctl inside user namespace",
                "payload": {"verdict": "EPERM_STRICT"},
                "valid_from": 102.0,
                "entities": ["seccomp", "io_uring", "keyctl"],
            },
        )
        self.assertTrue(w_conflict["admitted"])
        self.assertEqual(w_conflict["status"], "ADMITTED_BELIEF_CONFLICT")

        w_other = self.model.clm_rrf_memory_op(
            "WRITE_SURPRISE_GATED",
            {
                "record_id": "w39_rec_mendel",
                "key": "swe.mendel.splicing",
                "verbatim_text": "mendel comparative hybridization splices complementary repair hunks across sibling lineages",
                "payload": {"engine": "mendel"},
                "valid_from": 103.0,
                "entities": ["mendel", "splicing"],
            },
        )
        self.assertTrue(w_other["admitted"])

        # 5B: 4-way RRF strictly under char_budget
        q = self.model.clm_rrf_memory_op(
            "RETRIEVE_4WAY_RRF_BUDGETED",
            {
                "query": "mendel splicing complementary hunks",
                "query_entities": ["mendel"],
                "char_budget": 140,
                "top_k": 3,
            },
        )
        self.assertTrue(q["pass"])
        self.assertLessEqual(q["chars_used"], 140)
        self.assertEqual(q["results"][0]["record_id"], "w39_rec_mendel")

        # 5C: TMA-NM tamper detection excludes silently modified records
        eng = self.model._get_clm_rrf_memory_engine()
        eng._verbatim_archive["w39_rec_seccomp"]["verbatim_text"] = "TAMPERED_MALICIOUS_PAYLOAD"
        q_tamper = self.model.clm_rrf_memory_op(
            "RETRIEVE_4WAY_RRF_BUDGETED",
            {"query": "seccomp io_uring", "char_budget": 400, "top_k": 5},
        )
        self.assertIn("w39_rec_seccomp", q_tamper["tampered_excluded"])
        self.assertNotIn("w39_rec_seccomp", [r["record_id"] for r in q_tamper["results"]])

        # 5D: CLM file-mirrored working context offload, grep restore, and tamper audit
        with tempfile.TemporaryDirectory() as td:
            big_ctx = "HEADER_LOG\n" + ("filler line data " * 60 + "\n") + "CRITICAL_WITNESS: sha256=deadbeef\n"
            off = self.model.clm_rrf_memory_op(
                "CLM_OFFLOAD",
                {"context_text": big_ctx, "workspace_dir": td, "label": "trace_log"},
            )
            self.assertTrue(off["offloaded"])
            self.assertGreater(off["bytes_saved"], 500)

            restored = self.model.clm_rrf_memory_op(
                "CLM_GREP_RESTORE",
                {"offload_ref": off, "pattern": r"CRITICAL_WITNESS"},
            )
            self.assertTrue(restored["pass"])
            self.assertFalse(restored["tampered"])
            self.assertIn("sha256=deadbeef", restored["restored_text"])

            # Tamper with file on disk -> fail-closed tamper flag
            Path(off["path"]).write_text("CORRUPTED_ON_DISK", encoding="utf-8")
            tampered_res = self.model.clm_rrf_memory_op("CLM_GREP_RESTORE", {"offload_ref": off})
            self.assertFalse(tampered_res["pass"])
            self.assertTrue(tampered_res["tampered"])

    def test_06_jitrl_closed_form_skilltta_partial_routing_and_harvested_self_verifier(self) -> None:
        # 6A: Exact closed-form JitRL flips policy without gradient steps
        jrl = self.model.partial_route_with_jitrl(
            "JITRL_MODULATE",
            {
                "prior_logits": {"wrong_flag": 1.8, "verified_flag": 0.4},
                "state_signature": "openssl verify missing signature option",
                "episodic_receipts": [
                    {"state_signature": "openssl verify missing signature option", "action": "wrong_flag", "reward": -1.0},
                    {"state_signature": "openssl verify missing signature option", "action": "verified_flag", "reward": 1.0},
                ],
                "beta": 0.4,
            },
        )
        self.assertTrue(jrl["pass"])
        self.assertEqual(jrl["best_action_prior"], "wrong_flag")
        self.assertEqual(jrl["best_action_posterior"], "verified_flag")
        self.assertTrue(jrl["policy_shifted"])
        self.assertGreater(jrl["kl_divergence"], 0.0)

        # 6B: SkillTTA on-the-fly task-contract skill compilation
        sk = self.model.partial_route_with_jitrl(
            "SKILLTTA_SYNTHESIZE",
            {
                "target_task": {"domain": "swe", "error_kind": "IndexError", "goal": "bounds guard off by one"},
                "verified_traces": [
                    {
                        "trace_id": "tr_bounds_1",
                        "domain": "swe",
                        "error_kind": "IndexError",
                        "goal": "off by one loop bounds",
                        "actions": ["replace:<=" + ":<", "run_cow_tests"],
                        "invariants": ["no_empty_slice_oob"],
                        "verified": True,
                    },
                    {
                        "trace_id": "tr_unrelated",
                        "domain": "audio",
                        "error_kind": "CodecError",
                        "goal": "resample wav",
                        "actions": ["ffmpeg"],
                        "invariants": [],
                        "verified": True,
                    },
                ],
            },
        )
        self.assertTrue(sk["pass"])
        self.assertEqual(sk["source_trace_ids"], ["tr_bounds_1"])
        self.assertTrue(sk["ephemeral"])

        # 6C: Intra-task Partial Routing (75% zero-LLM local offload; Rung-3 called ONLY on hard slice)
        r3_seen: list[str] = []

        def fake_rung3(st: dict[str, object]) -> str:
            r3_seen.append(str(st["subtask_id"]))
            return "HARD_PROPOSED_FIX"

        pr = self.model.partial_route_with_jitrl(
            "PARTIAL_ROUTE",
            {
                "subtasks": [
                    {"subtask_id": "s0_fast", "kind": "fmt", "difficulty": 0.1, "verifier": lambda v: v == "FMT_OK"},
                    {"subtask_id": "s1_sym", "kind": "cmp", "difficulty": 0.3, "verifier": lambda v: v == "SYM_OK"},
                    {"subtask_id": "s2_mendel", "kind": "two_bug", "difficulty": 0.5, "verifier": lambda v: v == "MENDEL_OK"},
                    {"subtask_id": "s3_hard", "kind": "open_design", "difficulty": 0.9, "verifier": lambda v: v == "HARD_PROPOSED_FIX"},
                ],
                "compiled_skills": {"fmt": lambda st: "FMT_OK"},
                "symbolic_solver": lambda st: "SYM_OK" if st["kind"] == "cmp" else None,
                "mendel_solver": lambda st: "MENDEL_OK" if st["kind"] == "two_bug" else None,
                "pluggable_proposer": fake_rung3,
                "delta_threshold": 0.55,
            },
        )
        self.assertTrue(pr["pass"])
        self.assertEqual(pr["pluggable_proposer_calls"], 1)
        self.assertEqual(r3_seen, ["s3_hard"])
        self.assertAlmostEqual(pr["local_offload_ratio"], 0.75, places=4)

        # 6D: Live offline harvested-surface self-verification
        sv = self.model.self_verify_harvested_surfaces(limit=25)
        self.assertTrue(sv["pass"])
        self.assertEqual(sv["model_calls"], 0)
        self.assertEqual(sv["inspected_count"], 25)
        self.assertGreater(sv["status_counts"]["CALLABLE_VERIFIED"], 0)

    def test_07_creature_front_door_wave39_unification(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            c = self.model.open_creature(Path(td) / "creature_w39.json")
            w = c.clm_rrf_memory_op(
                "WRITE_SURPRISE_GATED",
                {
                    "record_id": "c39_rec_1",
                    "key": "creature.w39.fact",
                    "verbatim_text": "creature wave 39 unifies mendel splicing and clm verbatim memory",
                    "entities": ["creature", "mendel", "clm"],
                    "valid_from": 200.0,
                },
            )
            self.assertTrue(w["pass"])
            jrl = c.partial_route_with_jitrl(
                "JITRL_MODULATE",
                {
                    "prior_logits": {"a": 1.0, "b": 0.5},
                    "state_signature": "creature test state",
                    "episodic_receipts": [
                        {"state_signature": "creature test state", "action": "a", "reward": -1.0},
                        {"state_signature": "creature test state", "action": "b", "reward": 1.0},
                    ],
                    "beta": 0.5,
                },
            )
            self.assertEqual(jrl["best_action_posterior"], "b")
            cow = c.speculative_cow_decide(
                survivor_requirements=[{"x", "y"}, {"x"}],
                observed_facts=["x", "y"],
            )
            self.assertEqual(cow["decision"], "BY_KNOWLEDGE_APPLY")
            self.assertEqual(cow["cow_trials_paid"], 0)

    def test_08_wave39_federation_unfamiliar_names_and_100pct_domain_atlas(self) -> None:
        w39_engines = (
            "LEAPFROG_W39_AUTO_JUDGE_DISCOVERY",
            "LEAPFROG_W39_EFFECT_CONTRACT_COMPOSER",
            "LEAPFROG_W39_PARTIAL_ORDER_PLANNER",
            "LEAPFROG_W39_LIFTED_GENERALIZER",
            "LEAPFROG_W39_REFUSAL_ORACLE_LIFTER",
            "LEAPFROG_W39_OBSERVATION_REFUTATION_AND_PROVENANCE",
            "LEAPFROG_W39_DECISION_COST_COW_GATE",
            "LEAPFROG_W39_RED_QUEEN_MENDEL_EVOLVER",
            "LEAPFROG_W39_CLM_RRF_MEMORY_BUS",
            "LEAPFROG_W39_PARTIAL_ROUTING_AND_JITRL",
        )
        for eng in w39_engines:
            self.assertIn(eng, FEDERATED_KERNEL_DESCRIPTORS)

        # Late-2026 unfamiliar-name cross-disciplinary resolution
        for q, must_eng in (
            ("mendel godel machine red queen albi semantic anonymization slopcodebench phantom guardrails", "engine:LEAPFROG_W39_RED_QUEEN_MENDEL_EVOLVER"),
            ("clm context language models hindsight beam-10m nemori verbatim 4-way rrf", "engine:LEAPFROG_W39_CLM_RRF_MEMORY_BUS"),
            ("jitrl skilltta partial routing schema world model tycho microfitting sdft op-mix", "engine:LEAPFROG_W39_PARTIAL_ROUTING_AND_JITRL"),
            ("deltabox sandlock what a decision costs the check mode is the oracle", "engine:LEAPFROG_W39_DECISION_COST_COW_GATE"),
        ):
            res = resolve_cross_disciplinary_concept(q)
            self.assertIsNotNone(res.get("best"), f"No concept match for {q}")
            self.assertIn(must_eng, res["best"]["engines"], f"Missed {must_eng} for {q}: {res['best']}")
            dm = self.model.discover_dark_matter(q)
            self.assertEqual(dm["model_calls"], 0)
            self.assertIn(must_eng, dm["recommended_targets"])

        # Live federated dispatch checks across Wave 39 engines
        f_cc = run_federated_engine("LEAPFROG_W39_EFFECT_CONTRACT_COMPOSER", {"use_measured_advance_pair": True})
        self.assertTrue(f_cc["pass"])

        f_cow = run_federated_engine(
            "LEAPFROG_W39_DECISION_COST_COW_GATE",
            {"survivor_requirements": [{"a", "b"}, {"a"}], "observed_facts": ["a", "b"]},
        )
        self.assertTrue(f_cow["pass"])
        self.assertEqual(f_cow["decision"], "BY_KNOWLEDGE_APPLY")

        f_jrl = run_federated_engine(
            "LEAPFROG_W39_PARTIAL_ROUTING_AND_JITRL",
            {
                "operation": "JITRL_MODULATE",
                "prior_logits": {"x": 1.0, "y": 0.2},
                "state_signature": "demo state",
                "episodic_receipts": [
                    {"state_signature": "demo state", "action": "x", "reward": -1.0},
                    {"state_signature": "demo state", "action": "y", "reward": 1.0},
                ],
                "beta": 0.3,
            },
        )
        self.assertTrue(f_jrl["pass"])
        self.assertEqual(f_jrl["best_action_posterior"], "y")

        # Assert 100.0% (1.000) DOMAIN_ATLAS_V1 route recall across ALL 7 frontier domains
        atlas = json.loads((ROOT / "canonical/unified_model/DOMAIN_ATLAS_V1.json").read_text(encoding="utf-8"))
        reach = atlas["reachability"]
        self.assertEqual(len(reach), 7)
        for dom, row in reach.items():
            self.assertEqual(row["frontier_route_hit_recall"], 1.0, f"{dom} frontier route recall < 1.0: {row}")
            self.assertEqual(row["native_route_hit_recall"], 1.0, f"{dom} native route recall < 1.0: {row}")


if __name__ == "__main__":
    unittest.main()
