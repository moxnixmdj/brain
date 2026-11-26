"""Tests for `canonical.swe_kernel.unified_epistemic_portfolio_v1` and its `UnifiedModel` integration."""
from __future__ import annotations

import concurrent.futures
import pathlib
import tempfile
import unittest

from canonical.runtime.brain_unified_model_v1 import SovereignZeroLLMPlanner, open_model
from canonical.swe_kernel.unified_epistemic_portfolio_v1 import (
    ActiveSymbolicMealyLearner,
    CandidatePatch,
    CodePlanObligationZipper,
    EStitchSemanticSkillStore,
    VSAWoodburyFastMemory,
    WarmCoWForkScreener,
    WholeSliceMutantKillingGate,
    ZeroOverheadLineMonitor,
    build_rel_to_module_map,
    induce_hypothesis_and_vocabulary_unified,
    organ_portfolio_status,
    run_test_targets_fast,
    teach_edit_by_example_unified,
    verify_patch_uncheatable,
)


class UnifiedEpistemicPortfolioTests(unittest.TestCase):
    def test_all_96_organs_wired_and_ready_at_unified_model(self) -> None:
        direct = organ_portfolio_status()
        self.assertEqual(direct["total_organs"], 96)
        self.assertEqual(direct["ready_organs"], 96)
        self.assertTrue(direct["all_ready"])
        self.assertEqual(direct["model_calls"], 0)
        self.assertEqual(direct["parameters_stored"], 0)

        model = open_model()
        via_model = model.organ_portfolio_status()
        self.assertTrue(via_model["all_ready"])
        self.assertEqual(via_model["ready_organs"], 96)

        planner = SovereignZeroLLMPlanner()
        via_planner = planner.organ_portfolio_status()
        self.assertTrue(via_planner["all_ready"])
        self.assertEqual(via_planner["ready_organs"], 96)

    def test_zero_overhead_line_monitor_tracks_repo_and_excludes_tests(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td).resolve()
            (root / "pkg").mkdir()
            (root / "tests").mkdir()
            src_f = root / "pkg" / "mod.py"
            tst_f = root / "tests" / "test_mod.py"
            src_f.write_text("def compute(x):\n    y = x + 1\n    return y * 2\n", encoding="utf-8")
            tst_f.write_text("def helper(v):\n    return v - 1\n", encoding="utf-8")

            ns_src: dict[str, object] = {}
            ns_tst: dict[str, object] = {}
            exec(compile(src_f.read_text(encoding="utf-8"), str(src_f), "exec"), ns_src)
            exec(compile(tst_f.read_text(encoding="utf-8"), str(tst_f), "exec"), ns_tst)

            with ZeroOverheadLineMonitor(root, exclude_tests=True) as mon:
                res = ns_src["compute"](5)  # type: ignore[operator]
                _ = ns_tst["helper"](res)  # type: ignore[operator]

            self.assertEqual(res, 12)
            tracked_files = {rel for rel, _ in mon.hits}
            self.assertIn("pkg/mod.py", tracked_files)
            self.assertNotIn("tests/test_mod.py", tracked_files)

    def test_warm_cow_fork_screener_preserves_workspace_and_is_thread_safe(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td).resolve()
            (ws / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
            (ws / "test_calc.py").write_text(
                "import unittest\nfrom calc import add\n"
                "class CalcTest(unittest.TestCase):\n"
                "    def test_add(self):\n"
                "        self.assertEqual(add(2, 3), 5)\n",
                encoding="utf-8",
            )
            bad = CandidatePatch("bad", "test", {"calc.py": "def add(a, b):\n    return a * b\n"})
            good = CandidatePatch("good", "test", {"calc.py": "def add(a, b):\n    return a + b\n"})

            screener = WarmCoWForkScreener(ws, ["test_calc.py"], per_candidate_timeout_s=4.0)
            survivors = screener.screen_batch([bad, good], max_parallel=2, budget_s=10.0)
            self.assertEqual([c.patch_id for c in survivors], ["good"])
            # Original workspace file must remain completely untouched
            self.assertIn("return a - b", (ws / "calc.py").read_text(encoding="utf-8"))

            # Verify concurrent multi-threaded screening never raises ChildProcessError
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                f1 = pool.submit(screener.screen_batch, [bad, good], max_parallel=2, budget_s=10.0)
                f2 = pool.submit(screener.screen_batch, [good, bad], max_parallel=2, budget_s=10.0)
                self.assertEqual([c.patch_id for c in f1.result()], ["good"])
                self.assertEqual([c.patch_id for c in f2.result()], ["good"])

    def test_whole_slice_mutant_killing_gate_rejects_overfits_and_prefers_minimal_mdl(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td).resolve()
            (ws / "norm.py").write_text(
                "def dedup_first_wins(text: str) -> dict[str, str]:\n"
                "    return {tok.lower(): tok for tok in text.split()}\n",
                encoding="utf-8",
            )
            (ws / "test_norm.py").write_text(
                "import unittest\nfrom norm import dedup_first_wins\n"
                "class NormTests(unittest.TestCase):\n"
                "    def test_case_first_wins(self):\n"
                "        self.assertEqual(dedup_first_wins('Alpha ALPHA'), {'alpha': 'Alpha'})\n"
                "    def test_case_distinct_keys(self):\n"
                "        self.assertEqual(dedup_first_wins('Beta Gamma'), {'beta': 'Beta', 'gamma': 'Gamma'})\n",
                encoding="utf-8",
            )
            # Overfit patch: hardcodes {'alpha': 'Alpha'}, breaking sibling `test_case_distinct_keys`
            overfit = CandidatePatch(
                "overfit",
                "bad",
                {"norm.py": "def dedup_first_wins(text: str) -> dict[str, str]:\n    return {'alpha': 'Alpha'}\n"},
                mdl_delta_bytes=2,
            )
            bloated_good = CandidatePatch(
                "bloated_good",
                "good_big",
                {
                    "norm.py": (
                        "def dedup_first_wins(text: str) -> dict[str, str]:\n"
                        "    items = list(text.split())\n"
                        "    rev_items = list(reversed(items))\n"
                        "    unused_padding = [1, 2, 3, 4, 5]\n"
                        "    return {tok.lower(): tok for tok in rev_items if unused_padding}\n"
                    )
                },
                mdl_delta_bytes=95,
            )
            minimal_good = CandidatePatch(
                "minimal_good",
                "good_mdl",
                {
                    "norm.py": (
                        "def dedup_first_wins(text: str) -> dict[str, str]:\n"
                        "    return {tok.lower(): tok for tok in reversed(text.split())}\n"
                    )
                },
                mdl_delta_bytes=8,
            )
            winner, meta = WholeSliceMutantKillingGate.select_verified_winner(
                ws,
                ["test_norm.py"],
                None,
                [overfit, bloated_good, minimal_good],
                timeout_per_check_s=8.0,
                budget_s=15.0,
            )
            self.assertIsNotNone(winner)
            assert winner is not None
            self.assertEqual(winner.patch_id, "minimal_good")
            self.assertGreaterEqual(meta["rejected_single_node_overfits"], 1)
            self.assertEqual(meta["verified_candidates"], 2)

    def test_codeplan_obligation_zipper_propagates_cross_file_callsite_arity(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td).resolve()
            (ws / "pkg").mkdir()
            (ws / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            orig_a = "def parse_item(raw):\n    return raw.strip()\n"
            (ws / "pkg" / "core.py").write_text(orig_a, encoding="utf-8")
            (ws / "pkg" / "caller.py").write_text(
                "from pkg.core import parse_item\n\ndef run_all(xs):\n    return [parse_item(x) for x in xs]\n",
                encoding="utf-8",
            )
            zipper = CodePlanObligationZipper(ws)
            self.assertEqual(zipper.dependent_callsites("pkg/core.py", "parse_item"), [("pkg/caller.py", 4)])

            patched_a = "def parse_item(raw, mode):\n    return raw.strip() if mode is None else raw\n"
            bundle = zipper.propagate_default_arg_obligations("pkg/core.py", orig_a, patched_a)
            self.assertIn("pkg/core.py", bundle)
            self.assertIn("pkg/caller.py", bundle)
            self.assertIn("parse_item(x, None)", bundle["pkg/caller.py"])

    def test_end_to_end_workspace_repair_via_unified_model_epistemic_and_act_or_learn(self) -> None:
        model = open_model()
        # Case 1: DictComp first-wins repair via `UnifiedModel.solve(mode="EPISTEMIC")`
        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td).resolve()
            (ws / "refs.py").write_text(
                "def collect_refs(expr: str) -> dict[str, str]:\n"
                "    return {tok.lower(): tok for tok in expr.split()}\n",
                encoding="utf-8",
            )
            (ws / "test_refs.py").write_text(
                "import unittest\nfrom refs import collect_refs\n"
                "class RefTests(unittest.TestCase):\n"
                "    def test_preserves_first_casing(self):\n"
                "        self.assertEqual(collect_refs('Ref-Foo ref-foo'), {'ref-foo': 'Ref-Foo'})\n"
                "    def test_multiple_distinct(self):\n"
                "        self.assertEqual(collect_refs('Ref-A Ref-B'), {'ref-a': 'Ref-A', 'ref-b': 'Ref-B'})\n",
                encoding="utf-8",
            )
            sol = model.solve(
                "Repair collect_refs first-occurrence casing bug",
                inputs={"workspace_dir": str(ws), "pytest_targets": ["test_refs.py"], "timeout_s": 20.0},
                mode="EPISTEMIC",
            )
            self.assertTrue(sol["pass"])
            self.assertEqual(sol["model_calls"], 0)
            self.assertIn("reversed(", (ws / "refs.py").read_text(encoding="utf-8"))

        # Case 2: Partial accumulator continuation repair via `UnifiedModel.act_or_learn`
        with tempfile.TemporaryDirectory() as td2:
            ws2 = pathlib.Path(td2).resolve()
            (ws2 / "groups.py").write_text(
                "def parse_entries(items, errors):\n"
                "    acc = []\n"
                "    before = len(errors)\n"
                "    for it in items:\n"
                "        if isinstance(it, int):\n"
                "            acc.append(it)\n"
                "        else:\n"
                "            errors.append(it)\n"
                "    if len(errors) > before:\n"
                "        return ()\n"
                "    return tuple(acc)\n",
                encoding="utf-8",
            )
            (ws2 / "test_groups.py").write_text(
                "import unittest\nfrom groups import parse_entries\n"
                "class GroupTests(unittest.TestCase):\n"
                "    def test_returns_valid_partial_entries_on_error(self):\n"
                "        errs = []\n"
                "        out = parse_entries([10, 'bad', 20], errs)\n"
                "        self.assertEqual(errs, ['bad'])\n"
                "        self.assertEqual(out, (10, 20))\n"
                "    def test_clean_entries(self):\n"
                "        errs = []\n"
                "        self.assertEqual(parse_entries([1, 2], errs), (1, 2))\n",
                encoding="utf-8",
            )
            act_out = model.act_or_learn(
                "Fix parse_entries partial error continuation",
                inputs={
                    "learn": False,
                    "epistemic_portfolio_problem": {
                        "workspace_dir": str(ws2),
                        "pytest_targets": ["test_groups.py"],
                        "timeout_s": 20.0,
                    },
                },
                cognitive_state_dir=ws2 / "_cog_state",
                db_path=ws2 / "_ctrl.sqlite",
                forged_state_path=ws2 / "_forged.json",
            )
            self.assertTrue(act_out["pass"])
            self.assertIn("tuple(acc)", (ws2 / "groups.py").read_text(encoding="utf-8"))

    def test_estitch_semantic_skill_store_alpha_equivalence_and_bitemporal_invalidation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            store_file = pathlib.Path(td) / "motifs.json"
            store = EStitchSemanticSkillStore(store_file)
            c1 = store.canonicalize_snippet("def f(alpha, beta):\n    return alpha + beta\n")
            c2 = store.canonicalize_snippet("def f(x_val, y_val):\n    return x_val + y_val\n")
            self.assertEqual(c1, c2)

            # Low-surprise episode is gated out
            skipped = store.record_verified_repair(
                family="M7",
                before_source="x = a < b\n",
                after_source="x = a <= b\n",
                scope_id="pkg_v1",
                surprise=0.01,
            )
            self.assertIsNone(skipped)

            # High-surprise motif consolidated, then superseded in same scope with bi-temporal invalidation
            m1 = store.record_verified_repair(
                family="M7",
                before_source="x = a < b\n",
                after_source="x = a <= b\n",
                scope_id="pkg_v1",
                surprise=0.9,
            )
            self.assertIsNotNone(m1)
            m2 = store.record_verified_repair(
                family="M7",
                before_source="y = c < d\n",
                after_source="y = c == d\n",
                scope_id="pkg_v1",
                surprise=0.9,
            )
            self.assertIsNotNone(m2)
            active = store.active_motifs(scope_id="pkg_v1")
            self.assertEqual(len(active), 1)
            assert m2 is not None and m1 is not None
            self.assertEqual(active[0].motif_id, m2.motif_id)
            self.assertIsNotNone(store._motifs[m1.motif_id].t_invalidated_at)

    def test_active_symbolic_mealy_learner_and_version_space_ui_on_unified_model(self) -> None:
        model = open_model()

        def latch_oracle(word: list[str] | tuple[str, ...]) -> list[str]:
            armed = False
            outputs: list[str] = []
            for sym in word:
                if sym == "arm":
                    armed = True
                elif sym == "reset":
                    armed = False
                outputs.append("ACCEPT" if armed else "REJECT")
            return outputs

        sol_mealy = model.solve(
            "Learn unknown 2-state latch controller",
            inputs={"mealy_oracle": latch_oracle, "alphabet": ["arm", "reset"], "max_states": 3},
            mode="PORTFOLIO",
        )
        self.assertTrue(sol_mealy["pass"])
        self.assertEqual(sol_mealy["model_calls"], 0)
        ep_m = sol_mealy["epistemic_result"]
        self.assertEqual(ep_m["n_states"], 2)
        self.assertEqual(ep_m["optimality"], "PROVED_MINIMAL")

        # Few-shot DOM/GUI VersionSpaceSkill synthesis via `UnifiedModel.solve(mode="PORTFOLIO")`
        demo_1 = [
            (
                {
                    "instruction": "Click the Submit button",
                    "elements": [
                        {"tag": "button", "text": "Cancel", "can_click": True},
                        {"tag": "button", "text": "Submit", "can_click": True},
                    ],
                },
                "click@1",
            )
        ]
        demo_2 = [
            (
                {
                    "instruction": "Click the Submit button",
                    "elements": [
                        {"tag": "button", "text": "Submit", "can_click": True},
                        {"tag": "button", "text": "Back", "can_click": True},
                    ],
                },
                "click@0",
            )
        ]
        unseen_page = {
            "instruction": "Click the Submit button",
            "elements": [
                {"tag": "button", "text": "Help", "can_click": True},
                {"tag": "button", "text": "Cancel", "can_click": True},
                {"tag": "button", "text": "Submit", "can_click": True},
            ],
        }
        sol_vs = model.solve(
            "Click the Submit button",
            inputs={"version_space_traces": [demo_1, demo_2], "query_observation": unseen_page},
            mode="PORTFOLIO",
        )
        self.assertTrue(sol_vs["pass"])
        self.assertEqual(sol_vs["epistemic_result"]["predicted_action"], "click@2")

    def test_zero_copy_in_memory_module_override_runner(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td).resolve()
            (ws / "pkg").mkdir()
            (ws / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (ws / "pkg" / "math_ops.py").write_text("def double(v):\n    return v + 1\n", encoding="utf-8")
            (ws / "test_math_ops.py").write_text(
                "import unittest\nfrom pkg.math_ops import double\n"
                "class MathTests(unittest.TestCase):\n"
                "    def test_double(self):\n"
                "        self.assertEqual(double(7), 14)\n",
                encoding="utf-8",
            )
            fail_res = run_test_targets_fast(ws, ["test_math_ops.py"], timeout_s=5.0)
            self.assertNotEqual(fail_res["returncode"], 0)

            rel_map = build_rel_to_module_map(ws)
            mod_name, abs_orig, is_pkg = rel_map["pkg/math_ops.py"]
            overrides = {mod_name: (abs_orig, "def double(v):\n    return v * 2\n", is_pkg)}
            ok_res = run_test_targets_fast(ws, ["test_math_ops.py"], timeout_s=5.0, module_overrides=overrides)
            self.assertEqual(ok_res["returncode"], 0)
            # On-disk file was never mutated
            self.assertIn("return v + 1", (ws / "pkg" / "math_ops.py").read_text(encoding="utf-8"))

    def test_edit_kind_learning_open_ast_operator_zero_shot_transfer(self) -> None:
        store = EStitchSemanticSkillStore()
        before_fn = "def f(x):\n    if x:\n        return x + 1\n    return 0\n"
        after_fn = "def f(x):\n    if x is not None:\n        return x + 1\n    return 0\n"
        motif = store.record_verified_repair(
            family="none_guard",
            before_source=before_fn,
            after_source=after_fn,
            scope_id="transfer_scope",
            surprise=1.0,
        )
        self.assertIsNotNone(motif)

        unseen_fn = "def g(payload_count):\n    if payload_count:\n        return payload_count * 10\n    return -1\n"
        transferred = store.apply_learned_operators("service/handler.py", unseen_fn, {2})
        self.assertTrue(any("payload_count is not None" in c.patched_files["service/handler.py"] for c in transferred))

    def test_zero_vlm_interface_action_grammar_on_unified_model_and_act_or_learn(self) -> None:
        model = open_model()
        html = (
            "<form>"
            "<label for='email'>Email</label><input id='email' name='email' type='text' x='100' y='120' width='180' height='30'/>"
            "<button id='save_btn' type='submit' x='100' y='180' width='80' height='32'>Save</button>"
            "</form>"
        )
        res = model.act_on_interface(
            "Enter 'alice@example.org' into Email and click Save",
            html_source=html,
            submit_effects={"save_btn": {"saved": True}},
            goal_check=lambda st: bool(st.get("effects", {}).get("saved")) and st.get("values", {}).get("email") == "alice@example.org",
        )
        self.assertTrue(res["pass"])
        self.assertEqual(res["model_calls"], 0)
        self.assertTrue(len(res["osworld_pyautogui_script"]) >= 2)

        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td).resolve()
            act_res = model.act_or_learn(
                "Enter 'alice@example.org' into Email and click Save",
                inputs={
                    "learn": False,
                    "interface_action_problem": {
                        "instruction": "Enter 'alice@example.org' into Email and click Save",
                        "html_source": html,
                        "submit_effects": {"save_btn": {"saved": True}},
                    },
                },
                cognitive_state_dir=ws / "_cog",
                db_path=ws / "_ctrl.sqlite",
                forged_state_path=ws / "_forged.json",
            )
            self.assertTrue(act_res["pass"])
            self.assertEqual(act_res.get("model_calls", 0), 0)

    def test_systematic_unknown_environment_explorer_and_calculated_fast_weights(self) -> None:
        class UndocumentedVaultGymEnv:
            """Gym-style `observe()` / `step()` / `reset()` environment with no `.state` or `.act`."""

            def __init__(self) -> None:
                self._room = "hall"
                self._has_key = False
                self._vault_open = False

            def reset(self) -> dict[str, object]:
                self._room = "hall"
                self._has_key = False
                self._vault_open = False
                return self.observe()

            def observe(self) -> dict[str, object]:
                return {"room": self._room, "has_key": self._has_key, "vault_open": self._vault_open}

            def step(self, action: str) -> tuple[dict[str, object], float, bool, dict[str, object]]:
                if action == "go_armory" and self._room == "hall":
                    self._room = "armory"
                elif action == "take_key" and self._room == "armory":
                    self._has_key = True
                elif action == "go_hall" and self._room == "armory":
                    self._room = "hall"
                elif action == "unlock_vault" and self._room == "hall" and self._has_key:
                    self._vault_open = True
                return self.observe(), (1.0 if self._vault_open else 0.0), self._vault_open, {}

        model = open_model()
        planner = SovereignZeroLLMPlanner()
        env = UndocumentedVaultGymEnv()
        actions = ("go_armory", "take_key", "go_hall", "unlock_vault")
        is_goal = lambda s: isinstance(s, dict) and bool(s.get("vault_open"))

        exp_res = planner.explore_unknown_environment(
            env,
            actions,
            is_goal=is_goal,
            action_budget=24,
            verify_replay=True,
        )
        self.assertTrue(exp_res["pass"])
        self.assertEqual(exp_res["model_calls"], 0)
        self.assertEqual(exp_res["parameters_stored"], 0)
        self.assertEqual(exp_res["plan_shortest"], ["go_armory", "take_key", "go_hall", "unlock_vault"])
        self.assertIsNotNone(exp_res["calculated_fast_state"])

        sol_exp = model.solve(
            "Open undocumented vault",
            inputs={
                "unknown_environment_problem": {
                    "env": UndocumentedVaultGymEnv(),
                    "actions": actions,
                    "is_goal": is_goal,
                    "action_budget": 24,
                }
            },
            mode="EPISTEMIC",
        )
        self.assertTrue(sol_exp["pass"])
        self.assertEqual(sol_exp["model_calls"], 0)

    def test_hot_zygote_super_and_slots_safety_and_taught_and_vsa_organs(self) -> None:
        model = open_model()
        # 1. Structural AST edit-by-example transfer (`edit_by_example_v1`)
        taught = model.teach_edit_by_example(
            target_source="def calc(y):\n    return round(y, 2)\n",
            before_example="def f(x, z):\n    return round(x, 2) + round(z, 2)\n",
            after_example="def f(x, z):\n    return round(x, 4) + round(z, 4)\n",
        )
        self.assertTrue(taught["pass"])
        self.assertIn("round(y, 4)", taught["edited_source"])
        self.assertEqual(taught["model_calls"], 0)

        # 2. VSA SimHash + Sherman-Morrison/Woodbury fast associative memory (`K3 = 0`)
        mem_res = model.fast_associate_and_adapt(
            "dataclass slots pickle setstate repair",
            observe_payload={"family": "M9b_dataclass_slots_legacy_dict_setstate"},
            utility=1.0,
        )
        self.assertEqual(mem_res["model_calls"], 0)
        self.assertEqual(mem_res["parameters_stored"], 0)
        self.assertGreaterEqual(len(mem_res["matches"]), 1)

        # 3. Symbolic hypothesis fitting (`induce_hypothesis_and_vocabulary`)
        hyp = model.induce_hypothesis_and_vocabulary(points=[(1, 3), (2, 5), (3, 7), (4, 9)])
        self.assertEqual(hyp["model_calls"], 0)
        self.assertTrue(hyp["pass"])

    def test_end_to_end_object_model_laws_m9b_m10a_m10b(self) -> None:
        model = open_model()
        # Case A: `@dataclass(frozen=True, slots=True)` legacy dict pickle repair (Law M9b)
        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td).resolve()
            (ws / "durl.py").write_text(
                "import dataclasses\nfrom dataclasses import dataclass\n\n"
                "@dataclass(frozen=True, slots=True)\n"
                "class Endpoint:\n"
                "    url: str\n"
                "    port: int = 443\n",
                encoding="utf-8",
            )
            (ws / "test_durl.py").write_text(
                "import unittest\nfrom durl import Endpoint\n\n"
                "class EndpointPickleTests(unittest.TestCase):\n"
                "    def test_old_dict_state_roundtrip(self):\n"
                "        ep = object.__new__(Endpoint)\n"
                "        ep.__setstate__({'url': 'https://a.example', 'port': 8443})\n"
                "        self.assertEqual(ep.url, 'https://a.example')\n"
                "        self.assertEqual(ep.port, 8443)\n"
                "    def test_wrong_keys_rejected(self):\n"
                "        ep = object.__new__(Endpoint)\n"
                "        with self.assertRaises(TypeError):\n"
                "            ep.__setstate__({'url': 'https://a.example'})\n",
                encoding="utf-8",
            )
            sol_m9b = model.solve(
                "Support legacy dict pickle state on Endpoint",
                inputs={"workspace_dir": str(ws), "pytest_targets": ["test_durl.py"], "timeout_s": 20.0},
                mode="EPISTEMIC",
            )
            self.assertTrue(sol_m9b["pass"])
            self.assertEqual(sol_m9b["model_calls"], 0)

        # Case B: `__slots__` `__str__` identity memoization with `__init__` & `__setstate__` coherence (Law M10b)
        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td).resolve()
            (ws / "expr.py").write_text(
                "class Expr:\n"
                "    __slots__ = ('_tok',)\n"
                "    def __init__(self, tok: str) -> None:\n"
                "        self._tok = tok.strip()\n"
                "    def __setstate__(self, state: str) -> None:\n"
                "        self._tok = state\n"
                "    def __str__(self) -> str:\n"
                "        return f'<{self._tok}>'\n",
                encoding="utf-8",
            )
            (ws / "test_expr.py").write_text(
                "import unittest\nfrom expr import Expr\n\n"
                "class ExprStrCacheTests(unittest.TestCase):\n"
                "    def test_str_reuses_instance_and_invalidates_on_reinit_and_setstate(self):\n"
                "        e = Expr('alpha')\n"
                "        assert str(e) is str(e)\n"
                "        e.__setstate__('beta')\n"
                "        assert str(e) == '<beta>'\n"
                "        e.__init__('gamma')\n"
                "        assert str(e) == '<gamma>'\n",
                encoding="utf-8",
            )
            sol_m10b = model.solve(
                "Ensure Expr.__str__ reuses cached string instance coherently",
                inputs={"workspace_dir": str(ws), "pytest_targets": ["test_expr.py"], "timeout_s": 20.0},
                mode="EPISTEMIC",
            )
            self.assertTrue(sol_m10b["pass"])
            self.assertEqual(sol_m10b["model_calls"], 0)

    def test_meaning_ir_pre_sieve_and_simulator_at_unified_model(self) -> None:
        model = open_model()
        sol = model.solve(
            "Pre-sieve candidate repairs in Guarded Region-SSA Meaning-IR",
            inputs={
                "meaning_ir_presieve_problem": {
                    "baseline_source": "def f(x):\n    return x + 1\n",
                    "candidate_sources": [
                        "def f(x):\n    return x - 1\n",
                        "def f(x):\n    return (x - 1)\n",
                        "def f(x):\n    return x * 2\n",
                    ],
                    "entry_func": "f",
                    "probe_args": [5],
                    "expected_return": 4,
                    "check_expected": True,
                }
            },
            mode="EPISTEMIC",
        )
        self.assertTrue(sol["pass"])
        self.assertEqual(sol["model_calls"], 0)
        ep = sol["epistemic_result"]
        self.assertEqual(ep["kept_indices"], [0])
        self.assertEqual(ep["pruned_semantic_duplicates"], 1)
        self.assertEqual(ep["pruned_simulation_mismatches"], 1)

    def test_proved_skill_composition_and_7_language_cst_transfer(self) -> None:
        model = open_model()
        py_res = model.solve(
            "Compose verified AST rule in Python with pure organ verification",
            inputs={
                "proved_skill_composition_problem": {
                    "source_text": "def g(a, b):\n    return a == b and a > 0\n",
                    "before_after_lessons": [
                        ("def f1(u, v):\n    return u == v\n", "def f1(u, v):\n    return u != v\n")
                    ],
                    "target_language": "python",
                    "pure_organ_source": "def pure_add(z: int) -> int:\n    return z + 1\n",
                }
            },
            mode="EPISTEMIC",
        )
        self.assertTrue(py_res["pass"])
        self.assertTrue(py_res["epistemic_result"]["pure_organ_ast_verified"])

        lesson = [("def check(a, b):\n    return a <= b\n", "def check(a, b):\n    return a < b\n")]
        for lang, snip in (
            ("rust", "fn check(u: i32, limit: i32) -> bool { return u <= limit; }\n"),
            ("go", "func check(u int, limit int) bool { return u <= limit }\n"),
            ("typescript", "function check(u: number, limit: number): boolean { return u <= limit; }\n"),
            ("javascript", "function check(u, limit) { return u <= limit; }\n"),
            ("cpp", "bool check(int u, int limit) { return u <= limit; }\n"),
            ("java", "class C { boolean check(int u, int limit) { return u <= limit; } }\n"),
        ):
            c_res = model.compose_and_calibrate_skills(snip, lesson, target_language=lang)
            self.assertTrue(c_res["pass"], msg=f"failed CST transfer for {lang}")
            self.assertIn("< limit", c_res["output_source"] or "")
            self.assertEqual(c_res["model_calls"], 0)

    def test_one_shot_sufficiency_precondition_and_settlement_compiler(self) -> None:
        model = open_model()
        sol = model.solve(
            "Decide 1-shot sufficiency and abduce hidden preconditions",
            inputs={
                "one_shot_sufficiency_problem": {
                    "before_state": {"a.txt": b"hello\nworld\n"},
                    "after_state": {"a.txt": b"hello\n"},
                    "precondition_table": [
                        (["auth", "csrf"], True),
                        (["auth"], False),
                        (["csrf"], False),
                    ],
                    "precondition_vocabulary": ["auth", "csrf", "debug"],
                    "claim_text": "File `canonical/runtime/brain_unified_model_v1.py` exists.",
                    "version_space_examples": [((2,), 4), ((3,), 6)],
                }
            },
            mode="EPISTEMIC",
        )
        self.assertTrue(sol["pass"])
        self.assertEqual(sol["model_calls"], 0)
        ep = sol["epistemic_result"]
        self.assertEqual(set(ep["abduced_precondition"]), {"auth", "csrf"})
        self.assertIsNotNone(ep["settlement"])

    def test_webmcp_html_stale_generation_key_table_and_memoir_fast_memory(self) -> None:
        model = open_model()

        stale = model.act_on_interface("Submit order", observation={"generation": 2}, expected_generation=3)
        self.assertFalse(stale["pass"])
        self.assertEqual(stale["status"], "FAIL_CLOSED__STALE_OBSERVATION_GENERATION")

        wmcp_html = (
            '<form toolname="checkout_cart" tooldescription="Submit shopping cart order">'
            '<input name="coupon" required /><input name="total" /></form>'
        )
        wmcp = model.act_on_interface(
            "Submit shopping cart order with coupon=SAVE10 and total=42",
            observation={"generation": 3},
            expected_generation=3,
            html_source=wmcp_html,
            state_graph_edges=[("s0", "s1"), ("s1", "s2"), ("s2", "s3")],
            start_goal_states=("s0", "s3"),
        )
        self.assertTrue(wmcp["pass"])
        self.assertEqual(wmcp["modality"], "WEBMCP_STRUCTURED_TOOL")
        self.assertEqual(wmcp["tool_call"]["name"], "checkout_cart")
        self.assertEqual(wmcp["articulation_subgoals"], ["s1", "s2"])

        kt = model.act_on_interface(
            "save session",
            help_key_table_text=".save    Save current session\n.exit    Quit the REPL\n",
        )
        self.assertTrue(kt["pass"])
        self.assertEqual(kt["modality"], "CLI_HELP_KEY_TABLE")
        self.assertIn(".save", kt["selected_row"]["tokens"])

        # Memoir credit-boundary separation + bi-temporal invalidation + 2-hop PPR
        mem = VSAWoodburyFastMemory()
        st_unver = mem.observe("specifier prefix slice", "unverified_guess", credit_verified=False)
        self.assertTrue(st_unver["staged_only"])
        self.assertEqual(mem.query("specifier prefix slice")["episodes_indexed"], 0)

        mem.observe("specifier prefix slice", "rule_v1", utility=0.6, credit_verified=True)
        mem.observe("specifier prefix slice", "rule_v2", utility=1.0, credit_verified=True)
        mem.observe("prefix length equality", "bridge_rule", utility=0.9, credit_verified=True)
        q_res = mem.query("specifier equality", top_k=3)
        self.assertTrue(q_res["pass"])
        self.assertEqual(q_res["episodes_indexed"], 2)
        payloads = [m["payload"] for m in q_res["matches"]]
        self.assertIn("rule_v2", payloads)
        self.assertNotIn("rule_v1", payloads)
        self.assertGreater(max(m["ppr_score"] for m in q_res["matches"]), 0.0)


if __name__ == "__main__":
    unittest.main()
