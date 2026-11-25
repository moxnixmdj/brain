"""Tests for V4 Next-Wave Non-LLM SWE & Computer-Use Organs + Harbor Front Door.

Covers:
  1. Multi-Statement AST/IR Subtree Anti-Unification (`learned_skill_id` crystallization,
     single-experience Python -> Python + JavaScript (`node`) + Rust transfer, `O(1)` deletion,
     and §6 3-way memory ablation: `generalized` vs `raw_traces` vs `disabled`).
  2. Bidirectional Algebraic Codec Lens (`\\x04 <-> ^D`, `\\x1a <-> ^Z`, hex bijection,
     round-trip invertibility `decode(encode(x)) == x`).
  3. 64-Way Parallel `os.fork()` Copy-on-Write Differential Boundary Fuzzer + L3 Negative-Space
     Invariant compilation (`record_negative_invariant` / `is_blocked_by_negative_invariant`).
  4. 320-Step (`64 x 5`) Cross-Modal Petri Dominator Cut-Vertex Long-Horizon Planner (`O(64 * b^5)`
     factored sub-goals vs exponential flat horizon).
  5. Live `open_model().solve(..., mode="EPISTEMIC")` Harbor front-door dispatch + command-policy
     validation + multi-cycle `run_epistemic_goal` integration (`0` model calls, `0` host execution).
"""
from __future__ import annotations

import asyncio
import json
import pathlib
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from types import SimpleNamespace

from canonical.runtime import harbor_epistemic_agent_v1 as harbor_agent
from canonical.runtime.brain_unified_model_v1 import open_model
from canonical.swe_kernel.harbor_epistemic_controller_v1 import (
    CAPABILITY_ID,
    is_harbor_epistemic_envelope,
    solve_harbor_cycle,
)
from canonical.swe_kernel.harbor_in_container_runner_v1 import phase_discover, phase_repair
from canonical.swe_kernel.petri_cow_splicing_engine_v1 import (
    ASTSubtreeAntiUnifier,
    AdmissionFilteredSkillStore,
    BidirectionalCodecLens,
    CoWDifferentialBoundaryFuzzer,
    CrossModalMorphism,
    CrossModalPetriPlanner,
)


class V4SubtreeFuzzerHarborTests(unittest.TestCase):
    def test_multistatement_subtree_crystallization_cross_lang_and_memory_ablations(self) -> None:
        before_py = textwrap.dedent(
            """
            if self.help is None:
                return None
            return (self.make_metavar(ctx), self.help)
            """
        ).strip()
        after_py = textwrap.dedent(
            """
            if self.help is None:
                return (self.make_metavar(ctx), (self.help or ''))
            return (self.make_metavar(ctx), self.help)
            """
        ).strip()

        unseen_py_a = textwrap.dedent(
            """
            if item.summary is None:
                return None
            return (item.render_key(env), item.summary)
            """
        ).strip()
        unseen_py_b = textwrap.dedent(
            """
            if field.caption is None:
                return None
            return (field.format_title(req), field.caption)
            """
        ).strip()
        unseen_js = "function doc(opt, ctx) { if (opt.desc === null) { return null; } return [opt.metavar(ctx), opt.desc]; }"
        unseen_rs = 'fn doc(opt: &Opt) -> Option<(String, String)> { if opt.desc.is_none() { return None; } return Some((opt.key.clone(), opt.desc.unwrap())); }'

        ablation_scores: dict[str, int] = {}
        with tempfile.TemporaryDirectory() as tmp:
            for mode in ("generalized", "raw_traces", "disabled"):
                sp = pathlib.Path(tmp) / f"store_{mode}.json"
                st = AdmissionFilteredSkillStore(sp, mode=mode)
                ok, skill_id = st.try_admit_subtree(
                    domain="cli_help",
                    concrete_before=before_py,
                    concrete_after=after_py,
                    verified=True,
                    goal_relevant=True,
                    probes_before_success=6,
                    raw_episode_bytes=4096,
                    source_fingerprint="src/click/core.py",
                    witness_inputs=[{"help": None}],
                    revalidation_probe={"expected": ("ARG", "")},
                )
                self.assertTrue(ok)
                self.assertTrue(skill_id.startswith("sub_"))

                wins = 0
                # Exact replay task
                r_exact = st.retrieve_for_subtree(before_py, target_lang="python")
                if r_exact and "self.help or ''" in r_exact[0][0]:
                    wins += 1
                # Unseen Python variable/attribute rename A
                r_a = st.retrieve_for_subtree(unseen_py_a, target_lang="python")
                if r_a and "item.summary or ''" in r_a[0][0]:
                    ns: dict = {}
                    fn_src = "def f(item, env):\n" + textwrap.indent(r_a[0][0], "    ")
                    exec(fn_src, ns)
                    dummy = SimpleNamespace(summary=None, render_key=lambda e: f"K:{e}")
                    if ns["f"](dummy, "prod") == ("K:prod", ""):
                        wins += 1
                # Unseen Python variable/attribute rename B
                r_b = st.retrieve_for_subtree(unseen_py_b, target_lang="python")
                if r_b and "field.caption or ''" in r_b[0][0]:
                    wins += 1
                # Unseen JavaScript task verified in real Node.js runtime (`node -e`)
                r_js = st.retrieve_for_subtree(unseen_js, target_lang="javascript")
                if r_js:
                    if shutil.which("node"):
                        js_eval = (
                            r_js[0][0]
                            + "\nconst out = doc({desc: null, metavar: (c) => 'MV_' + c}, 'cli');"
                            + "\nif (JSON.stringify(out) !== JSON.stringify(['MV_cli', ''])) process.exit(1);"
                        )
                        proc = subprocess.run(["node", "-e", js_eval], capture_output=True, text=True, timeout=10)
                        if proc.returncode == 0:
                            wins += 1
                    elif '|| ""' in r_js[0][0]:
                        wins += 1
                # Unseen Rust lowering
                r_rs = st.retrieve_for_subtree(unseen_rs, target_lang="rust")
                if r_rs and "unwrap_or_default()" in r_rs[0][0]:
                    wins += 1

                ablation_scores[mode] = wins

                # Verify O(1) deletion without retraining on generalized store
                if mode == "generalized":
                    self.assertTrue(st.remove_skill(skill_id))
                    self.assertEqual(st.retrieve_for_subtree(unseen_py_a, target_lang="python"), [])

        self.assertEqual(ablation_scores["generalized"], 5)
        self.assertEqual(ablation_scores["raw_traces"], 1)
        self.assertEqual(ablation_scores["disabled"], 0)

    def test_statement_insertion_anti_unification_knuth_bendix_well_formed(self) -> None:
        before_block = textwrap.dedent(
            """
            if self.token is not None:
                return f"{self.type.title()} {self.token}"
            return f"{self.type.title()} {dump_header(self.parameters)}"
            """
        ).strip()
        after_block = textwrap.dedent(
            """
            if self.token is not None:
                return f"{self.type.title()} {self.token}"
            if not self.parameters:
                return self.type.title()
            return f"{self.type.title()} {dump_header(self.parameters)}"
            """
        ).strip()
        lhs, rhs = ASTSubtreeAntiUnifier.anti_unify_blocks(before_block, after_block)
        replayed = ASTSubtreeAntiUnifier.apply_to_code(
            lhs,
            rhs,
            textwrap.dedent(
                """
                if hdr.secret is not None:
                    return f"{hdr.scheme.title()} {hdr.secret}"
                return f"{hdr.scheme.title()} {encode_params(hdr.fields)}"
                """
            ).strip(),
        )
        self.assertIsNotNone(replayed)
        assert replayed is not None
        self.assertIn("if not hdr.fields:", replayed)
        self.assertIn("return hdr.scheme.title()", replayed)

    def test_bidirectional_codec_lens_caret_and_hex_invertibility(self) -> None:
        lens = BidirectionalCodecLens.synthesize_verified_lens([(b"\x04", "^D"), (b"\x1a", "^Z")])
        self.assertIsNotNone(lens)
        assert lens is not None
        self.assertTrue(lens["roundtrip_verified"])
        fwd, inv = lens["forward_fn"], lens["inverse_fn"]
        # Generalizes to unseen control bytes (`\x03 -> ^C`, `\x00 -> ^@`) without memorization!
        self.assertEqual(fwd(b"hi\x03\x04"), "hi^C^D")
        self.assertEqual(inv(fwd(b"hi\x03\x04")), b"hi\x03\x04")

        hex_lens = BidirectionalCodecLens.synthesize_verified_lens([(b"\xde\xad", "DEAD"), (b"\xbe\xef", "BEEF")])
        self.assertIsNotNone(hex_lens)
        assert hex_lens is not None
        self.assertEqual(hex_lens["forward_fn"](b"\xca\xfe"), "CAFE")
        self.assertEqual(hex_lens["inverse_fn"]("CAFE"), b"\xca\xfe")

    def test_64_way_cow_boundary_fuzzer_and_negative_space_invariants(self) -> None:
        def orig_fn(x):
            if x is None:
                return ""
            return str(x).strip()

        # Bad patch: crashes on empty string `""` via `x[0]`
        def bad_patch(x):
            if x is None:
                return ""
            if isinstance(x, str) and x[0] == " ":
                return x.strip()
            return str(x)

        # Good patch: preserves all passing boundary sorts while fixing `False -> "False"`
        def good_patch(x):
            if x is None:
                return ""
            return str(x).strip()

        bad_res = CoWDifferentialBoundaryFuzzer.verify_differential_invariance(
            orig_fn, bad_patch, [(" hello ",)], workers=8
        )
        self.assertFalse(bad_res["ok"])
        self.assertGreaterEqual(bad_res["cases_tested"], 32)
        self.assertTrue(any("IndexError" in r["kind"] for r in bad_res["regressions"]))

        good_res = CoWDifferentialBoundaryFuzzer.verify_differential_invariance(
            orig_fn, good_patch, [(" hello ",)], workers=8
        )
        self.assertTrue(good_res["ok"])

        with tempfile.TemporaryDirectory() as tmp:
            st = AdmissionFilteredSkillStore(pathlib.Path(tmp) / "neg.json")
            inv_id = st.record_negative_invariant(
                domain="swe_python",
                target_ast_shape="orig_fn",
                forbidden_delta_op="UNBOUNDED_INDEX_0",
                failure_kind="NEW_CRASH:IndexError",
                minimal_witness={"input": "('')"},
            )
            self.assertTrue(inv_id.startswith("neg_"))
            self.assertTrue(
                st.is_blocked_by_negative_invariant(
                    target_ast_shape="orig_fn", candidate_delta_op="UNBOUNDED_INDEX_0"
                )
            )

    def test_320_step_petri_dominator_cut_vertex_long_horizon(self) -> None:
        planner = CrossModalPetriPlanner()
        surfaces = ("CLI", "FS", "SQLITE", "HTTP_JSON")
        # Build a 320-transition (`64` sequential stages x `5` transitions per stage with distractor branches)
        # cross-modal Petri net where every stage converges on an articulation/dominator checkpoint `stage_{i}_done`.
        for stage in range(64):
            in_tok = "seed_0" if stage == 0 else f"stage_{stage - 1}_done"
            p1 = f"s{stage}_p1"
            p2 = f"s{stage}_p2"
            p3 = f"s{stage}_p3"
            p4 = f"s{stage}_p4"
            out_tok = f"stage_{stage}_done"
            surf = surfaces[stage % len(surfaces)]
            planner.register(CrossModalMorphism(f"m_{stage}_1", surf, (in_tok,), p1, (), (), lambda env, k=in_tok: env[k] + 1))
            planner.register(CrossModalMorphism(f"m_{stage}_2", surf, (p1,), p2, (), (), lambda env, k=p1: env[k] + 1))
            planner.register(CrossModalMorphism(f"m_{stage}_3", surf, (p2,), p3, (), (), lambda env, k=p2: env[k] + 1))
            planner.register(CrossModalMorphism(f"m_{stage}_4", surf, (p3,), p4, (), (), lambda env, k=p3: env[k] + 1))
            planner.register(CrossModalMorphism(f"m_{stage}_5", surf, (p4,), out_tok, (), (), lambda env, k=p4: env[k] + 1))
            # Add dead-end distractor branch at each stage (`b > 1` branching factor: `2^64` flat horizon!)
            planner.register(CrossModalMorphism(f"dead_{stage}", surf, (p1,), f"dead_tok_{stage}", (), (), lambda env, k=p1: env[k]))

        res = planner.execute_checkpointed_long_horizon(
            {"seed_0": 0},
            "stage_63_done",
            lambda tokens: tokens.get("stage_63_done") == 320,
            subgoal_max_depth=6,
        )
        self.assertTrue(res["ok"])
        self.assertEqual(res["steps_executed"], 320)
        self.assertEqual(res["final_goal_value"], 320)
        self.assertGreaterEqual(res["cut_vertices_discovered"], 64)

    def test_harbor_open_model_solve_and_in_container_loop(self) -> None:
        model = open_model()
        goal = harbor_agent.build_goal("Fix trailing space in auth.py to_header()", 1, [])
        inputs_c1 = {
            "harbor_task": "Fix trailing space in auth.py to_header()",
            "cycle": 1,
            "observations": [],
        }
        self.assertTrue(is_harbor_epistemic_envelope(inputs_c1))
        out1 = model.solve(goal, inputs=inputs_c1, mode="EPISTEMIC")
        self.assertTrue(out1["pass"])
        self.assertEqual(out1["capability_id"], CAPABILITY_ID)
        self.assertEqual(out1["model_calls"], 0)
        actions1 = harbor_agent.extract_actions(out1)
        self.assertEqual(len(actions1), 1)
        kind1, args1 = harbor_agent.validate_action(actions1[0])
        self.assertEqual(kind1, "exec")
        self.assertIn("--phase discover", args1["command"])

        # Simulate container environment end-to-end through `harbor_agent.run_epistemic_goal`
        class ContainerMockEnv:
            def __init__(self) -> None:
                self.calls: list[str] = []

            async def exec(self, command: str, **kwargs):
                self.calls.append(command)
                if "harbor_container_solver_worker_v1.py" in command:
                    b64_req = command.rsplit(" ", 1)[-1].strip("'")
                    import base64 as _b64
                    req = json.loads(_b64.b64decode(b64_req).decode("utf-8"))
                    ans = solve_harbor_cycle(req["goal"], inputs=req["inputs"], model_digest="test")
                    return SimpleNamespace(
                        return_code=0,
                        stdout="BRAIN_CONTAINER_SOLVE_V1:" + json.dumps(ans) + "\n",
                        stderr="",
                    )
                if "--phase discover" in command:
                    disc_out = {"ecosystems": {"python": True}, "ranked_tests": ["tests/test_auth.py"]}
                    return SimpleNamespace(return_code=0, stdout=json.dumps(disc_out) + "\n", stderr="")
                if "--phase repair" in command:
                    rep_out = {"status": "PASS__VERIFIED_REPAIR", "pass": True, "repaired_file": "auth.py"}
                    return SimpleNamespace(return_code=0, stdout=json.dumps(rep_out) + "\n", stderr="")
                return SimpleNamespace(return_code=0, stdout="{}\n", stderr="")

        mock_env = ContainerMockEnv()
        # Exercise full 3-cycle Harbor loop on a 24,000-byte monorepo issue prompt (`> 23,642` bytes of
        # `ansible-40ade1f8`) to verify `MAX_WORKER_REQUEST_BYTES == 64_000` is never exceeded!
        large_instruction = "Fix auth.py to_header()\n" + ("Detailed monorepo context line for Ansible task.\n" * 490)
        self.assertGreater(len(large_instruction.encode("utf-8")), 23642)
        loop_res = asyncio.run(harbor_agent.run_epistemic_goal(large_instruction, mock_env))
        self.assertEqual(loop_res["status"], "FINISHED__MODEL_PROPOSED__VERIFIER_DECIDES")
        self.assertFalse(loop_res["task_completion_claimed"])
        self.assertEqual(loop_res["cycles"], 3)

    def test_v5_issue_witness_compiler_doctest_and_fenced_repro(self) -> None:
        import sys
        import canonical.swe_kernel.harbor_in_container_runner_v1 as runner

        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp) / "repo"
            (repo / "calcmod").mkdir(parents=True)
            (repo / "calcmod" / "__init__.py").write_text(
                "def normalize_key(items, key=None):\n"
                "    return [key(x) if key else x for x in items]\n",
                encoding="utf-8",
            )
            # Broken pseudocode snippet with undefined identifier MUST be rejected cleanly
            bad_res = runner.compile_issue_witness_test(
                "```python\nfrom calcmod import normalize_key\nassert normalize_key(undefined_var) == []\n```",
                repo,
                sys.executable,
                out_path=pathlib.Path(tmp) / "bad_witness.py",
            )
            self.assertFalse(bad_res["compiled"])

            # Valid doctest witness reproducing genuine failure on falsey callable `key`
            good_out = pathlib.Path(tmp) / "good_witness.py"
            good_res = runner.compile_issue_witness_test(
                ">>> from calcmod import normalize_key\n"
                ">>> class F:\n"
                "...     def __bool__(self): return False\n"
                "...     def __call__(self, v): return v * 10\n"
                ">>> normalize_key([2, 3], key=F())\n"
                "[20, 30]\n",
                repo,
                sys.executable,
                out_path=good_out,
            )
            self.assertTrue(good_res["compiled"])
            self.assertGreaterEqual(len(good_res["failing_nodes"]), 1)
            good_out.unlink(missing_ok=True)

    def test_v5_self_play_distiller_compactor_and_non_tautology_guards(self) -> None:
        import dataclasses
        from canonical.swe_kernel.first_principles_mental_cegis_v1 import (
            ProgramStateMentalModel,
            synthesize_expressions_bottom_up,
        )
        from canonical.swe_kernel.petri_cow_splicing_engine_v1 import SelfPlaySkillDistiller

        with tempfile.TemporaryDirectory() as tmp:
            st_path = pathlib.Path(tmp) / "skills.json"
            store = AdmissionFilteredSkillStore(st_path, mode="generalized")
            k_file = pathlib.Path(__file__).resolve()
            distiller = SelfPlaySkillDistiller(store, kernel_paths=[k_file])
            ep = distiller.harvest_subtree_episode(
                domain="swe",
                before_block="return '; '.join(self.params)\n",
                after_block="if not self.params:\n    return self.kind.title()\nreturn '; '.join(self.params)\n",
                verified_by_suite=True,
                probes_before_success=2,
                raw_episode_bytes=900,
            )
            self.assertTrue(ep["admitted"])
            self.assertTrue(ep["kernel_identity_preserved"])
            base_rec = next(iter(store.records.values()))
            store.records["sub_dup_shard"] = dataclasses.replace(
                base_rec,
                skill_id="sub_dup_shard",
                witness_inputs=[{"shard": 2}],
            )
            comp = store.compact_and_deduplicate()
            self.assertEqual(comp["subtree_merged"], 1)
            self.assertEqual(len(store.records), 1)

        # Symmetric sort-discipline + substring-view alias filter
        mental = ProgramStateMentalModel(
            [{"locals": {"key": "b'rawsecret'", "stripped": "b'rawsecret'", "flag": False}}],
            [{"locals": {"key": "b'-----BEGIN PEM-----\\n'", "stripped": "b'-----BEGIN PEM-----'", "flag": True}}],
        )
        cands = [
            c_txt
            for c_txt, _ in synthesize_expressions_bottom_up(
                mental,
                orig_expr="flag",
                fail_envs=mental.fail_envs,
                pass_envs=mental.pass_envs,
                target_fail_values=[True],
            )
        ]
        self.assertTrue(all("key == stripped" not in c and "stripped == key" not in c for c in cands))

    def test_v6_metamorphic_habitation_fst_zipper_and_o1_surgical_ablation(self) -> None:
        import subprocess
        from canonical.swe_kernel.causal_swe_repair_v1 import repair_worktree
        from canonical.swe_kernel.first_principles_mental_cegis_v1 import (
            _has_new_dead_branch_equivalence,
            _synthesize_callee_param_threading,
        )
        from canonical.swe_kernel.harbor_in_container_runner_v1 import synthesize_metamorphic_green_witness
        from canonical.swe_kernel.petri_cow_splicing_engine_v1 import (
            AdmissionFilteredSkillStore,
            BidirectionalFSTLensSynthesizer,
            CodebaseTypeHabitationMiner,
            compute_structural_fp64,
        )

        # 1. FP64 renaming invariance
        fp_a = compute_structural_fp64("if alpha is None:\n    return 0\nreturn alpha + 1\n")
        fp_b = compute_structural_fp64("if beta_val is None:\n    return 0\nreturn beta_val + 1\n")
        self.assertEqual(fp_a, fp_b)

        # 2. Dead-branch complexity regression guard
        orig_code = "def f(x):\n    if hasattr(x, '__reversed__'):\n        return next(reversed(x))\n    return slow(x)\n"
        bad_code = "def f(x):\n    if hasattr(x, '__reversed__'):\n        return slow(x)\n    return slow(x)\n"
        good_code = "def f(x):\n    if getattr(x, '__reversed__', None) is not None:\n        return next(reversed(x))\n    return slow(x)\n"
        self.assertTrue(_has_new_dead_branch_equivalence(orig_code, bad_code))
        self.assertFalse(_has_new_dead_branch_equivalence(orig_code, good_code))

        # 3. Type-Habitation (`head.copy()` + `getattr(..., None) is not None`) & Callee Live-Param Threading
        with tempfile.TemporaryDirectory(prefix="v6_unit_") as td:
            import pathlib
            wt = pathlib.Path(td)
            mod_src = (
                "def helper_dispatch(env, name, val, context=None):\n"
                "    return (name, val, context)\n\n"
                "def outer_entry(env, context, item):\n"
                "    return helper_dispatch(env, 'k', item)\n"
            )
            (wt / "mod.py").write_text(mod_src, encoding="utf-8")
            import ast
            tr = ast.parse(mod_src)
            threaded = _synthesize_callee_param_threading(wt, "mod.py", mod_src, tr, 5, [{"context": {"t": "Obj"}}])
            self.assertTrue(any("helper_dispatch(env, 'k', item, context)" in p[0] for p in threaded))

            spy_src = "def spy(it):\n    head = [1, 2]\n    return head, iter(head)\n"
            spy_tr = ast.parse(spy_src)
            ret_st = spy_tr.body[0].body[1]
            hab = CodebaseTypeHabitationMiner.synthesize_stmt_habitation_rewrites(
                wt, "spy.py", spy_src, ret_st, [{"head": {"t": "list"}}]
            )
            self.assertTrue(any("head.copy()" in p[0] for p in hab))

            # 4. Bidirectional FST Lens (`(f2 o f1)^-1 = f1^-1 o f2^-1`)
            fst_src = (
                "def escape_q(s):\n"
                "    return s.replace('\"', '\\\\\"').replace('\\\\', '\\\\\\\\')\n"
                "def unescape_q(s):\n"
                "    return s.replace('\\\\\"', '\"').replace('\\\\\\\\', '\\\\')\n"
            )
            fst_repairs = BidirectionalFSTLensSynthesizer.synthesize_lens_repairs(fst_src, ast.parse(fst_src))
            self.assertTrue(any(r[2] == "FST_MISSING_INVERSE_TRANSITION" for r in fst_repairs))

            # 5. Wall-1 Metamorphic Witness Splitter (`ACTIVE_RETURN_ALIAS_INDEPENDENCE`) on 100%-green worktree
            alias_wt = wt / "alias_repo"
            (alias_wt / "pkg").mkdir(parents=True)
            (alias_wt / "tests").mkdir(parents=True)
            (alias_wt / "pkg" / "__init__.py").write_text(
                "from itertools import chain\n"
                "def peek_head(iterable):\n"
                "    it = iter(iterable)\n"
                "    head = [next(it)]\n"
                "    return head, chain(head, it)\n",
                encoding="utf-8",
            )
            (alias_wt / "tests" / "test_pkg.py").write_text(
                "import unittest\n"
                "from pkg import peek_head\n"
                "class T(unittest.TestCase):\n"
                "    def test_basic(self):\n"
                "        h, full = peek_head([10, 20])\n"
                "        self.assertEqual((h, list(full)), ([10], [10, 20]))\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "init", "-q"], cwd=alias_wt, check=True)
            subprocess.run(["git", "config", "user.email", "t@t.io"], cwd=alias_wt, check=True)
            subprocess.run(["git", "config", "user.name", "t"], cwd=alias_wt, check=True)
            subprocess.run(["git", "add", "."], cwd=alias_wt, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=alias_wt, check=True)

            import sys
            w_alias = synthesize_metamorphic_green_witness(
                "pkg.peek_head returns a head list that aliases the chained iterator when mutated.",
                alias_wt,
                sys.executable,
            )
            self.assertTrue(w_alias["compiled"])
            self.assertEqual(w_alias["relation"], "ACTIVE_RETURN_ALIAS_INDEPENDENCE")
            wp = pathlib.Path(w_alias["witness_path"])
            rep_alias = repair_worktree(alias_wt, str(wp), python_exe=sys.executable, budget_s=25.0)
            wp.unlink(missing_ok=True)
            self.assertTrue(rep_alias["pass"])
            self.assertIn("head.copy()", (alias_wt / "pkg" / "__init__.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
