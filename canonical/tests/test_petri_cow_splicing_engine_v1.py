#!/usr/bin/env python3
"""End-to-end verification tests for `petri_cow_splicing_engine_v1` (`model_calls == 0`, `$0` spend)."""
from __future__ import annotations

import ast
import pathlib
import shutil
import sqlite3
import tempfile
import unittest

from canonical.swe_kernel import causal_swe_repair_v1 as swe
from canonical.swe_kernel.effect_contract_composition_v1 import Effect
from canonical.swe_kernel.epistemic_computer_agent_v1 import (
    EpistemicComputerAgent,
    EpistemicStore,
)
from canonical.swe_kernel.first_principles_mental_cegis_v1 import (
    ProgramStateMentalModel,
    SemanticMeaningIR,
    synthesize_discriminating_predicates,
)
from canonical.swe_kernel.petri_cow_splicing_engine_v1 import (
    AdmissionFilteredSkillStore,
    AdversarialSelfPlayEngine,
    BackwardWitnessAndDualSplicer,
    CrossModalMorphism,
    CrossModalPetriPlanner,
    MealyStateCompiler,
    ParallelCoWWorldTomographer,
    RepoNativePetriMiner,
    capture_multilayer_snapshot,
    check_foreign_ident_unbound,
)


class TestPetriCowSplicingEngineV1(unittest.TestCase):
    def test_1_repo_native_petri_miner_and_sibling_return_coalescing(self) -> None:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="test_petri_mine_"))
        try:
            (tmp / "cli_core.py").write_text(
                "class Context:\n"
                "    pass\n\n"
                "class Parameter:\n"
                "    def __init__(self, name, help=None):\n"
                "        self.name = name\n"
                "        self._original_name = name\n"
                "        self.help = help\n\n"
                "    def make_metavar(self, ctx: Context) -> str:\n"
                "        return self.name.upper()\n\n"
                "    def get_help_record(self, ctx: Context) -> tuple[str, str]:\n"
                "        if self.help is None:\n"
                "            return None\n"
                "        return self.make_metavar(ctx), self.help\n\n"
                "class Registry:\n"
                "    def get_plugin(self, name: str):\n"
                "        return None\n"
                "    def has_plugin(self, name: str) -> bool:\n"
                "        return False\n"
                "    def get_plugins(self) -> set:\n"
                "        return set()\n",
                encoding="utf-8",
            )
            miner = RepoNativePetriMiner(tmp)
            stats = miner.mine_scope(["cli_core.py"])
            self.assertGreaterEqual(stats["transitions_mined"], 4)

            # A. Collection functor lift: `[x.get_help_record(ctx) for x in args]`
            cands = miner.synthesize_petri_candidates(
                rel_file="cli_core.py",
                orig_expr="records",
                fail_frames=[{
                    "args": {"t": "list", "len": 1, "elem_t": "Parameter", "elem_mro": ["Parameter"]},
                    "ctx": {"t": "Context", "mro": ["Context"]},
                    "records": {"t": "list", "len": 0},
                }],
                pass_frames=[],
                require_bool=False,
            )
            exprs = [c[0] for c in cands]
            self.assertTrue(
                any(".get_help_record(ctx)" in e and "for " in e and " in args]" in e for e in exprs),
                f"Expected comprehension functor lift in {exprs}",
            )

            # B. Boolean-sort discipline: `self.get_plugin(ep_name)` -> `self.has_plugin(ep_name)`, NOT `self.get_plugins()`!
            bool_cands = miner.synthesize_petri_candidates(
                rel_file="cli_core.py",
                orig_expr="self.get_plugin(ep_name)",
                fail_frames=[{
                    "self": {"t": "Registry", "mro": ["Registry"]},
                    "ep_name": {"t": "str", "v": "p1"},
                }],
                pass_frames=[],
                require_bool=True,
            )
            bool_exprs = [c[0] for c in bool_cands]
            self.assertIn("self.has_plugin(ep_name)", bool_exprs)
            self.assertNotIn("self.get_plugins()", bool_exprs)

            # C. Intra-function sibling-return monoidal coalescing
            tree = ast.parse((tmp / "cli_core.py").read_text(encoding="utf-8"))
            param_cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Parameter"][0]
            ghr_fn = [n for n in param_cls.body if isinstance(n, ast.FunctionDef) and n.name == "get_help_record"][0]
            early_ret = [n for n in ast.walk(ghr_fn) if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)][0]
            lifts = miner.synthesize_sibling_return_lifts(
                ghr_fn,
                early_ret,
                [{"self": {"t": "Parameter", "attrs": {"help": "None", "name": "'x'"}}, "ctx": {"t": "Context"}}],
            )
            lift_exprs = [l[0] for l in lifts]
            self.assertIn("(self.make_metavar(ctx), (self.help or ''))", lift_exprs)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_2_backward_witness_inversion_and_dual_program_splicing_end_to_end(self) -> None:
        # 2a. Algebraic backward witness propagation
        ret_node = ast.parse("'prefix:' + slug", mode="eval").body
        inv = BackwardWitnessAndDualSplicer.invert_return_residual(ret_node, "prefix:clean-id")
        self.assertTrue(any(ast.unparse(n) == "slug" and val == "clean-id" for n, val in inv))

        # 2b. Anti-lookup-table gate blocks constant memorization on single test witness
        self.assertTrue(
            BackwardWitnessAndDualSplicer.is_lookup_table_overfit(
                "'memorized_output'", "x == 'test_only_input'", ["x"], num_distinct_fail_witnesses=1
            )
        )
        self.assertFalse(
            BackwardWitnessAndDualSplicer.is_lookup_table_overfit(
                "x.strip()", "len(x) > 0", ["x"], num_distinct_fail_witnesses=1
            )
        )

        # 2c. Live Dual-Program Splicing on a git-stripped worktree where `x.strip()` fixes failing
        #     string inputs but crashes when `x is None` on passing inputs (`(x.strip()) if (x is not None) else (x)`).
        mental = ProgramStateMentalModel(
            [{"x": {"t": "str", "v": "  hello  "}}],
            [{"x": {"t": "NoneType", "v": None}}],
        )
        guards = BackwardWitnessAndDualSplicer.synthesize_separating_guards(
            mental,
            positive_envs=mental.fail_envs,
            negative_envs=mental.pass_envs,
            synthesize_disc_fn=synthesize_discriminating_predicates,
        )
        spliced = BackwardWitnessAndDualSplicer.build_spliced_expressions(
            positive_expr="x.strip()",
            negative_expr="x",
            guards=guards,
            in_scope_vars=["x"],
            num_distinct_fail_witnesses=1,
        )
        self.assertTrue(any("x is not None" in g for _, g in spliced))

    def test_3_parallel_16way_cow_tomography_and_mealy_compiler(self) -> None:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="test_cow_tomo_"))
        store_dir = pathlib.Path(tempfile.mkdtemp(prefix="test_cow_store_"))
        try:
            ws = tmp / "ws"
            ws.mkdir()
            db_p = ws / "accounts.db"
            conn = sqlite3.connect(str(db_p))
            conn.execute("CREATE TABLE users (name TEXT PRIMARY KEY, locked INTEGER)")
            conn.execute("INSERT INTO users VALUES ('alice', 1), ('bob', 0)")
            conn.commit()
            conn.close()
            (ws / "config.json").write_text('{"maintenance": true}', encoding="utf-8")

            before_disk_snap = capture_multilayer_snapshot(ws)

            # Build 16 speculative actions: 14 noisy/destructive/partial actions + 1 exact goal solver (#11) + 1 slow no-op
            actions = []
            for idx in range(16):
                if idx == 3:
                    # Destructive trap: drops SQLite table!
                    def _trap(w: pathlib.Path) -> dict:
                        c = sqlite3.connect(str(w / "accounts.db"))
                        c.execute("DROP TABLE users")
                        c.commit()
                        c.close()
                        return {"dom_state": {"banner": "WIPED"}, "cli_result": {"returncode": 1}}
                    actions.append(("destructive_drop_table", _trap))
                elif idx == 11:
                    # Exact multi-layer winner: unlocks alice in SQLite + sets maintenance=false + ARIA banner READY
                    def _winner(w: pathlib.Path) -> dict:
                        c = sqlite3.connect(str(w / "accounts.db"))
                        c.execute("UPDATE users SET locked = 0 WHERE name = 'alice'")
                        c.commit()
                        c.close()
                        (w / "config.json").write_text('{"maintenance": false}', encoding="utf-8")
                        return {"dom_state": {"banner": "READY"}, "cli_result": {"returncode": 0}}
                    actions.append(("unlock_alice_and_clear_maintenance", _winner))
                else:
                    def _partial(w: pathlib.Path, k: int = idx) -> dict:
                        (w / f"scratch_{k}.txt").write_text(f"attempt {k}", encoding="utf-8")
                        return {"dom_state": {"banner": f"PENDING_{k}"}, "cli_result": {"returncode": 0}}
                    actions.append((f"noop_candidate_{idx}", _partial))

            def _goal_residual(snap, _out) -> float:
                rows = snap.sqlite_db_layer.get("accounts.db::users", [])
                alice_unlocked = ("alice", 0) in rows and ("bob", 0) in rows
                maint_off = snap.config_env_layer.get("config.json:maintenance") is False
                banner_ok = snap.accessibility_dom_layer.get("banner") == "READY"
                return 0.0 if (alice_unlocked and maint_off and banner_ok) else (
                    0.33 * (not alice_unlocked) + 0.33 * (not maint_off) + 0.34 * (not banner_ok)
                )

            # First run with commit_winner=False to prove ZERO base-workspace mutation across 16 CoW forks!
            agent = EpistemicComputerAgent(EpistemicStore(store_dir))
            dry_res = agent.execute_speculative_world_goal(
                ws, actions, _goal_residual, commit_winner=False, initial_dom_state={"banner": "LOCKED"}
            )
            self.assertTrue(dry_res["pass"])
            self.assertEqual(dry_res["branches_forked"], 16)
            self.assertEqual(dry_res["winner_action"], "unlock_alice_and_clear_maintenance")
            self.assertGreaterEqual(dry_res["mealy_transitions_compiled"], 15)
            after_dry_snap = capture_multilayer_snapshot(ws)
            self.assertEqual(before_disk_snap.stable_projection_key(), after_dry_snap.stable_projection_key())

            # Now commit the verified residual-0.0 winner
            live_res = agent.execute_speculative_world_goal(
                ws, actions, _goal_residual, commit_winner=True, initial_dom_state={"banner": "LOCKED"}
            )
            self.assertTrue(live_res["committed"])
            after_live_snap = capture_multilayer_snapshot(ws, dom_state={"banner": "READY"})
            self.assertEqual(_goal_residual(after_live_snap, {}), 0.0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(store_dir, ignore_errors=True)

    def test_4_cross_modal_petri_planner_gui_sqlite_python_cli(self) -> None:
        store_dir = pathlib.Path(tempfile.mkdtemp(prefix="test_cm_petri_"))
        try:
            # 4 real surfaces + 1 inverse UNDO decoy pair
            morphisms = [
                CrossModalMorphism(
                    morphism_id="gui_extract_selected_role",
                    surface="GUI_ARIA",
                    input_places=("aria_tree",),
                    output_place="selected_role",
                    preconditions=(),
                    effects=(Effect("ESTABLISH", "token:selected_role"),),
                    execute=lambda t: [n["value"] for n in t["aria_tree"] if n["role"] == "combobox"][0],
                ),
                CrossModalMorphism(
                    morphism_id="sqlite_fetch_expired_tokens",
                    surface="SQLITE_QUERY",
                    input_places=("sqlite_conn", "selected_role"),
                    output_place="raw_token_rows",
                    preconditions=("token:selected_role",),
                    effects=(Effect("ESTABLISH", "token:raw_token_rows"),),
                    execute=lambda t: t["sqlite_conn"].execute(
                        "SELECT token_id FROM sessions WHERE role = ? AND expired = 1 ORDER BY token_id",
                        (t["selected_role"],),
                    ).fetchall(),
                ),
                CrossModalMorphism(
                    morphism_id="python_normalize_csv_arg",
                    surface="PYTHON_TRANSFORM",
                    input_places=("raw_token_rows",),
                    output_place="normalized_flag_payload",
                    preconditions=("token:raw_token_rows",),
                    effects=(Effect("ESTABLISH", "token:normalized_flag_payload"),),
                    execute=lambda t: ",".join(r[0].strip().lower() for r in t["raw_token_rows"]),
                ),
                CrossModalMorphism(
                    morphism_id="cli_revoke_batch",
                    surface="CLI_EXEC",
                    input_places=("normalized_flag_payload",),
                    output_place="revocation_receipt",
                    preconditions=("token:normalized_flag_payload",),
                    effects=(Effect("ESTABLISH", "token:revocation_receipt"),),
                    execute=lambda t: {"exit_code": 0, "revoked": t["normalized_flag_payload"].split(",")},
                ),
            ]
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE TABLE sessions (token_id TEXT, role TEXT, expired INTEGER)")
            conn.execute("INSERT INTO sessions VALUES ('TOK_A1', 'admin', 1), ('TOK_B2', 'admin', 0), ('TOK_C3', 'admin', 1)")

            agent = EpistemicComputerAgent(EpistemicStore(store_dir))
            res = agent.execute_cross_modal_petri_goal(
                morphisms=morphisms,
                initial_tokens={
                    "aria_tree": [{"role": "combobox", "name": "Target Role", "value": "admin"}],
                    "sqlite_conn": conn,
                },
                goal_place="revocation_receipt",
                goal_verifier=lambda tok: tok.get("revocation_receipt") == {"exit_code": 0, "revoked": ["tok_a1", "tok_c3"]},
            )
            self.assertTrue(res["pass"])
            self.assertEqual(res["surfaces_used"], ["GUI_ARIA", "SQLITE_QUERY", "PYTHON_TRANSFORM", "CLI_EXEC"])
            conn.close()
        finally:
            shutil.rmtree(store_dir, ignore_errors=True)

    def test_5_admission_filter_5_gates_staleness_and_memory_ablations(self) -> None:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="test_admit_ablate_"))
        try:
            store_file = tmp / "skills.json"
            store = AdmissionFilteredSkillStore(store_file, mode="generalized")

            # Gate 1: Unverified -> REJECTED
            ok, reason = store.try_admit(
                domain="swe", concrete_before="x == None", concrete_after="x is not None",
                semantic_Meaning_cls=SemanticMeaningIR, verified=False, goal_relevant=True,
                probes_before_success=2, raw_episode_bytes=400, source_fingerprint="fp_v1",
                witness_inputs=[{"x": []}], revalidation_probe={"expected": True},
            )
            self.assertFalse(ok)
            self.assertEqual(reason, "REJECTED__UNVERIFIED")

            # Gate 3: Zero prediction error (trivial already-known fact) -> REJECTED
            ok, reason = store.try_admit(
                domain="swe", concrete_before="bool(items)", concrete_after="items is not None",
                semantic_Meaning_cls=SemanticMeaningIR, verified=True, goal_relevant=True,
                probes_before_success=0, raw_episode_bytes=400, source_fingerprint="fp_v1",
                witness_inputs=[{"items": []}], revalidation_probe={"expected": True},
            )
            self.assertFalse(ok)
            self.assertEqual(reason, "REJECTED__ZERO_PREDICTION_ERROR")

            # Gate 4: `FOREIGN_IDENT_UNBOUND` -> REJECTED!
            unbound = check_foreign_ident_unbound("items", "[x.render(leaked_ctx) for x in items]")
            self.assertEqual(unbound, ["leaked_ctx"])
            ok, reason = store.try_admit(
                domain="swe", concrete_before="items", concrete_after="[x.render(leaked_ctx) for x in items]",
                semantic_Meaning_cls=SemanticMeaningIR, verified=True, goal_relevant=True,
                probes_before_success=3, raw_episode_bytes=500, source_fingerprint="fp_v1",
                witness_inputs=[{"items": []}], revalidation_probe={"expected": True},
            )
            self.assertFalse(ok)
            self.assertTrue(reason.startswith("REJECTED__FOREIGN_IDENT_UNBOUND:leaked_ctx"))

            # Valid 5-gate admission from ONE Python experience (`bool(payload)` -> `payload is not None`)
            ok, skill_id = store.try_admit(
                domain="null_vs_falsy",
                concrete_before="bool(payload)",
                concrete_after="payload is not None",
                semantic_Meaning_cls=SemanticMeaningIR,
                verified=True,
                goal_relevant=True,
                probes_before_success=2,
                raw_episode_bytes=512,
                source_fingerprint="schema_v1",
                witness_inputs=[{"payload": []}],
                revalidation_probe={"expr": "[] is not None", "want": True},
            )
            self.assertTrue(ok)

            # §6 Memory Ablation across 3 targets:
            #   (1) Unseen renamed Python variable `bool(headers)`
            #   (2) JavaScript `Boolean(headers)`
            #   (3) Rust `!headers.is_empty()` / truthy check -> let's test `SemanticMeaningIR` JS + Python + exact Python
            gen_store = AdmissionFilteredSkillStore(store_file, mode="generalized")
            raw_store = AdmissionFilteredSkillStore(store_file, mode="raw_traces")
            dis_store = AdmissionFilteredSkillStore(store_file, mode="disabled")

            # Generalized transfers to unseen Python identifier, unseen JavaScript, AND unseen Rust!
            py_xfer = gen_store.retrieve_for_expression("bool(headers)", target_lang="python", semantic_meaning_cls=SemanticMeaningIR)
            js_xfer = gen_store.retrieve_for_expression("Boolean(headers)", target_lang="javascript", semantic_meaning_cls=SemanticMeaningIR)
            rs_xfer = gen_store.retrieve_for_expression("!headers.is_empty()", target_lang="rust", semantic_meaning_cls=SemanticMeaningIR)
            self.assertTrue(any("headers is not None" in r[0] for r in py_xfer))
            self.assertTrue(any("headers !== null" in r[0] for r in js_xfer))
            self.assertTrue(any("headers.is_some()" in r[0] for r in rs_xfer))

            # Raw traces ONLY match exact `bool(payload)` in Python — 0% transfer to `headers` or JS!
            self.assertEqual(raw_store.retrieve_for_expression("bool(headers)", target_lang="python", semantic_meaning_cls=SemanticMeaningIR), [])
            self.assertEqual(raw_store.retrieve_for_expression("Boolean(headers)", target_lang="javascript", semantic_meaning_cls=SemanticMeaningIR), [])
            self.assertEqual(len(raw_store.retrieve_for_expression("bool(payload)", target_lang="python", semantic_meaning_cls=SemanticMeaningIR)), 1)

            # Disabled store returns 0 on all queries
            self.assertEqual(dis_store.retrieve_for_expression("bool(payload)", target_lang="python", semantic_meaning_cls=SemanticMeaningIR), [])

            # Staleness detection + re-validation probe on version drift (`schema_v1` -> `schema_v2` vs `schema_broken`)
            drift_ok = gen_store.check_and_refresh_staleness(
                {"null_vs_falsy": "schema_v2"},
                probe_runner=lambda probe: eval(probe["expr"]) is probe["want"],  # noqa: S307
            )
            self.assertEqual(drift_ok, {"drifted": 1, "revalidated": 1, "evicted": 0})
            self.assertEqual(gen_store.records[skill_id].version, 2)

            # Instant removal without retraining
            self.assertTrue(gen_store.remove_skill(skill_id))
            self.assertEqual(len(gen_store.records), 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_6_adversarial_self_play_with_same_identity_supervisor_and_equivalence_proof(self) -> None:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="test_selfplay_"))
        try:
            store = AdmissionFilteredSkillStore(tmp / "selfplay_skills.json", mode="generalized")
            kernel_file = pathlib.Path(swe.__file__).resolve()
            engine = AdversarialSelfPlayEngine(store, kernel_paths=[kernel_file])

            seed_py = (
                "def normalize_tag(tag):\n"
                "    if tag is not None:\n"
                "        return f'[{tag}]'\n"
                "    return 'MISSING'\n"
            )
            buggy_py = (
                "def normalize_tag(tag):\n"
                "    if tag:\n"
                "        return f'[{tag}]'\n"
                "    return 'MISSING'\n"
            )
            test_py = (
                "import unittest\n"
                "from subject_module import normalize_tag\n"
                "class T(unittest.TestCase):\n"
                "    def test_non_empty(self):\n"
                "        self.assertEqual(normalize_tag('v1'), '[v1]')\n"
                "    def test_none(self):\n"
                "        self.assertEqual(normalize_tag(None), 'MISSING')\n"
                "    def test_empty_str_is_valid_tag(self):\n"
                "        self.assertEqual(normalize_tag(''), '[]')\n"
            )

            def _repair_adapter(wt: pathlib.Path) -> dict:
                r = swe.repair_worktree(wt, "tests/test_mod.py", budget_s=25.0)
                if r.get("pass"):
                    return {
                        "status": "REPAIRED_AND_VERIFIED",
                        "before_expr": "tag",
                        "after_expr": "tag is not None",
                        "probes_tested": max(1, int(r.get("verifications_run", 1))),
                    }
                return {"status": r.get("status", "FAILED")}

            ep = engine.run_self_play_episode(
                seed_source_py=seed_py,
                buggy_mutation_py=buggy_py,
                test_source_py=test_py,
                repair_fn=_repair_adapter,
                semantic_meaning_cls=SemanticMeaningIR,
                probe_inputs=["v1", "", None, "0"],
            )
            self.assertTrue(ep["ok"], f"Self-play episode failed: {ep}")
            self.assertTrue(ep["kernel_identity_preserved"])
            self.assertTrue(ep["admitted"])
            self.assertEqual(ep["equivalence_verdict"], "EQUIVALENT_UNDER_PRECONDITION")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
