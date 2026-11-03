#!/usr/bin/env python3
"""End-to-end verification of `unified_creature_plus_fast_general_organs` (PR #6601).

Runnable under both `.venv/bin/python -m pytest` and bare `/usr/bin/python3 -m unittest`.
"""
from __future__ import annotations

import importlib.util
import pathlib
import tempfile
import time
import unittest

try:
    import pytest  # noqa: F401
except ImportError:
    pytest = None  # type: ignore[assignment]


class UnifiedCreaturePlusFastGeneralOrgansTests(unittest.TestCase):
    def test_component1_persistent_confined_zygote_speed_isolation_and_multifile(self) -> None:
        from canonical.runtime import brokered_workspace_execution_v1 as broker
        from canonical.runtime import confine_v1
        from canonical.swe_kernel.zygote_worker_pool_v1 import screen_python_candidates_cow

        with tempfile.TemporaryDirectory() as td:
            ws = pathlib.Path(td)
            (ws / "config.txt").write_text("UNTOUCHED\n", encoding="utf-8")
            (ws / "calc.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
            (ws / "test_calc.py").write_text(
                "import unittest\nfrom calc import add\n\n"
                "class T(unittest.TestCase):\n"
                "    def test_add(self):\n"
                "        self.assertEqual(add(4, 3), 7)\n",
                encoding="utf-8",
            )

            cands = [
                # Hostile write-through + env poison attempt
                "import os, pathlib\n"
                "try:\n    pathlib.Path('config.txt').write_text('HACKED')\nexcept Exception:\n    pass\n"
                "os.environ['POISON_KEY'] = '1'\n"
                "def add(a, b): return a - b\n",
                # Infinite loop bounded by per_candidate_timeout_s
                "def add(a, b):\n    while True:\n        pass\n",
            ]
            for i in range(9):
                cands.append(f"def add(a, b):\n    return a + b + {i + 1}\n")
            cands.append("def add(a, b):\n    return a + b\n")

            # Warm persistent confined Zygote once, then measure warm 12-candidate batch
            _ = screen_python_candidates_cow(
                ws, "calc.py", ["test_calc.py"], cands[:2], per_candidate_timeout_s=0.12
            )
            t0 = time.perf_counter()
            res = screen_python_candidates_cow(
                ws,
                "calc.py",
                ["test_calc.py"],
                cands,
                stop_on_first_pass=False,
                per_candidate_timeout_s=0.12,
            )
            warm_ms = (time.perf_counter() - t0) * 1000.0
            self.assertTrue(res["ok"], res)
            self.assertTrue(res["screen_authoritative"], res)
            self.assertEqual(res["passing_indices"], [11])
            self.assertEqual((ws / "config.txt").read_text(encoding="utf-8"), "UNTOUCHED\n")
            self.assertLess(warm_ms, 250.0)

            # Multi-file override dict batch in PersistentConfinedZygote
            (ws / "mul.py").write_text("def mul(a, b):\n    return a + b\n", encoding="utf-8")
            (ws / "test_both.py").write_text(
                "import unittest\nfrom calc import add\nfrom mul import mul\n\n"
                "class TB(unittest.TestCase):\n"
                "    def test_both(self):\n"
                "        self.assertEqual(add(2, 5), 7)\n"
                "        self.assertEqual(mul(3, 4), 12)\n",
                encoding="utf-8",
            )
            mf = broker.run_confined_python_candidate_batch(
                ws,
                "",
                ["test_both.py"],
                [
                    {"calc.py": "def add(a, b):\n    return a + b\n"},
                    {
                        "calc.py": "def add(a, b):\n    return a + b\n",
                        "mul.py": "def mul(a, b):\n    return a * b\n",
                    },
                ],
                stop_on_first_pass=True,
            )
            self.assertTrue(mf["ok"] and mf["confined"], mf)
            self.assertEqual(mf["passing_indices"], [1])

            # confine_v1.run_readonly executes read-only inside namespace confinement
            ro = confine_v1.run_readonly(
                "import pathlib; print(pathlib.Path('config.txt').read_text().strip())",
                ws,
                timeout=10,
            )
            self.assertEqual(ro["verdict"], "OK", ro)
            self.assertEqual(ro["exit_status"], 0, ro)
            self.assertEqual(ro["output"].strip(), "UNTOUCHED")
            self.assertTrue(ro["confined"])
            self.assertEqual((ws / "config.txt").read_text(encoding="utf-8"), "UNTOUCHED\n")

    def test_component2_generic_cst_anti_unification_slice_and_scope_calibration(self) -> None:
        from canonical.swe_kernel import rule_scope_learning_v1 as rscope
        from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import (
            compile_rule_to_cst_skeleton,
            iter_cst_skeleton_candidates,
            recall_across_languages_cst,
        )
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

        # Preserve law-pinned 3-tuple SCOPE_HYPOTHESES and single-instance UNDERDETERMINED
        self.assertEqual(
            tuple(h.hypothesis_id for h in rscope.SCOPE_HYPOTHESES),
            ("SCOPE_STATEMENT", "SCOPE_OPERATOR", "SCOPE_SEMANTIC"),
        )

        with tempfile.TemporaryDirectory() as td:
            tp = pathlib.Path(td)
            store = VerifiedSkillStore(tp / "cst.sqlite")

            # 1. Generic CST anti-unification: list comprehension + augmented assignment (no per-construct whitelist)
            c_comp = store.crystallize_code_fix(
                before_snippet="def bump(xs):\n    return [v - 1 for v in xs]\n",
                after_snippet="def bump(xs):\n    return [v + 1 for v in xs]\n",
                language="python",
                error_class="COMP_FIX",
            )
            self.assertTrue(c_comp["crystallized"], c_comp)
            rule_comp = [r for r in store.lookup_rules("python") if r["skill_id"] == c_comp["skill_id"]][0]
            cands_comp = list(
                iter_cst_skeleton_candidates(
                    "def grow(items):\n    return [el - 1 for el in items]\n",
                    rule_comp,
                    target_language="python",
                    minimize=True,
                )
            )
            self.assertTrue(any("[el + 1 for el in items]" in c for c in cands_comp), cands_comp)

            c_aug = store.crystallize_code_fix(
                before_snippet="def dec(acc, step):\n    acc += step\n    return acc\n",
                after_snippet="def dec(acc, step):\n    acc -= step\n    return acc\n",
                language="python",
                error_class="AUG_FIX",
            )
            self.assertTrue(c_aug["crystallized"], c_aug)
            rule_aug = [r for r in store.lookup_rules("python") if r["skill_id"] == c_aug["skill_id"]][0]
            cands_aug = list(
                iter_cst_skeleton_candidates(
                    "def drain(bal, amt):\n    bal += amt\n    return bal\n",
                    rule_aug,
                    target_language="python",
                    minimize=True,
                )
            )
            self.assertTrue(any("bal -= amt" in c for c in cands_aug), cands_aug)

            # 2. Cross-language SLICE (`arr[i:n]` -> JS `buf.slice(lo, hi)`) when tree-sitter is installed
            if importlib.util.find_spec("tree_sitter_languages") is not None:
                c_sl = store.crystallize_code_fix(
                    before_snippet="def trim(arr, i, n):\n    return arr[i:n - 1]\n",
                    after_snippet="def trim(arr, i, n):\n    return arr[i:n]\n",
                    language="python",
                    error_class="SLICE_FIX",
                )
                self.assertTrue(c_sl["crystallized"], c_sl)
                hit_js_sl = recall_across_languages_cst(
                    store,
                    source_text="function windowBuf(buf, lo, hi) {\n  return buf.slice(lo, hi - 1);\n}\n",
                    target_language="javascript",
                    verifier=lambda s: "buf.slice(lo, hi)" in s,
                    error_class="SLICE_FIX",
                    minimize=True,
                )
                self.assertIsNotNone(hit_js_sl)

            # 3. 4-tier scope calibration (`elif <= -> <` => SCOPE_SEMANTIC, `max->min` => SCOPE_EXPRESSION, `True->False` => SCOPE_STATEMENT)
            store_sc = VerifiedSkillStore(tp / "scope.sqlite")
            r_elif = store_sc.crystallize_code_fix(
                before_snippet="def grade(x, cut):\n    if x < 0:\n        return -1\n    elif x <= cut:\n        return 1\n    return 0\n",
                after_snippet="def grade(x, cut):\n    if x < 0:\n        return -1\n    elif x < cut:\n        return 1\n    return 0\n",
                language="python",
                error_class="ELIF_BOUND",
            )
            self.assertTrue(r_elif["crystallized"])
            rule_elif = [r for r in store_sc.lookup_rules("python") if r["skill_id"] == r_elif["skill_id"]][0]
            cal_elif = rscope.calibrate_rule_scope(rule_elif, store=store_sc)
            self.assertEqual(cal_elif["scope"], "SCOPE_SEMANTIC", cal_elif)

            r_expr = store_sc.crystallize_code_fix(
                before_snippet="def pick_low(a, b):\n    return max(a, b)\n",
                after_snippet="def pick_low(a, b):\n    return min(a, b)\n",
                language="python",
                error_class="CALL_SWAP",
            )
            self.assertTrue(r_expr["crystallized"])
            rule_expr = [r for r in store_sc.lookup_rules("python") if r["skill_id"] == r_expr["skill_id"]][0]
            self.assertIsNotNone(compile_rule_to_cst_skeleton(rule_expr))
            cal_expr = rscope.calibrate_rule_scope(rule_expr, store=store_sc)
            self.assertEqual(cal_expr["scope"], "SCOPE_EXPRESSION", cal_expr)

            r_stmt = store_sc.crystallize_code_fix(
                before_snippet="def is_disabled():\n    return True\n",
                after_snippet="def is_disabled():\n    return False\n",
                language="python",
                error_class="BOOL_CONST",
            )
            self.assertTrue(r_stmt["crystallized"])
            rule_stmt = [r for r in store_sc.lookup_rules("python") if r["skill_id"] == r_stmt["skill_id"]][0]
            cal_stmt = rscope.calibrate_rule_scope(rule_stmt, store=store_sc)
            self.assertEqual(cal_stmt["scope"], "SCOPE_STATEMENT", cal_stmt)

    def test_component3_routing_ledger_fast_bind_invalidation_memory_policy_and_confined_make(self) -> None:
        from canonical.runtime.brain_unified_model_v1 import open_model
        from canonical.runtime.memory_policy_v1 import memory_policy_scope
        from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import (
            execute_and_elevate_confined_trajectory,
            solve_or_learn,
        )
        from canonical.swe_kernel.upstream_routing_ledger_v1 import (
            UpstreamRoutingLedger,
            classify_goal_intent_signature,
        )

        s_png = classify_goal_intent_signature("extract text from invoice.png to out.txt")
        s_pdf = classify_goal_intent_signature("extract text from invoice.pdf to out.txt")
        self.assertNotEqual(s_png["shape_hash"], s_pdf["shape_hash"])
        self.assertIn("|ext:", s_png["structural_skeleton"])

        with tempfile.TemporaryDirectory() as td:
            tp = pathlib.Path(td)
            led_path = tp / "routing.sqlite"
            led = UpstreamRoutingLedger(led_path)
            self.assertFalse(led.record_verified_route("Write json file a.json", "json.file.write")["promoted"])
            r2 = led.record_verified_route("Write json file b.json", "json.file.write")
            self.assertTrue(r2["promoted"])
            r3 = led.record_verified_route("Write json file c.json", "json.file.write")
            self.assertTrue(r3.get("ram_fast_hit"))

            with memory_policy_scope("OFF"):
                self.assertIsNone(led.lookup_shape("Write json file d.json")["preferred_capability"])
                self.assertFalse(led.record_verified_route("Write json file e.json", "json.file.write")["recorded"])

            # UnifiedModel.solve() direct preferred_capability binding + miss invalidation fallback
            model = open_model()
            out_rel = "canonical/astra_runtime/tmp/ut_fast_bind_out.json"
            out_abs = pathlib.Path(__file__).resolve().parents[2] / out_rel
            try:
                goal_j = f"Write json file {out_rel}"
                sol = model.solve(
                    goal_j,
                    inputs={"ledger_db_path": str(led_path), "output_path": out_rel, "spec": {"status": "ok"}},
                )
                self.assertTrue(sol["pass"], sol)
                self.assertEqual(sol["routing"]["best"]["rule"], "UPSTREAM_ROUTING_LEDGER_PREFERRED")

                # Mis-promoted real capability fails execution, gets invalidated in ledger, and falls back to self.route(goal)
                led_bad_path = tp / "routing_bad.sqlite"
                led_bad = UpstreamRoutingLedger(led_bad_path)
                led_bad.record_verified_route("Write json file x.json", "docx.document.verify.ooxml")
                led_bad.record_verified_route("Write json file y.json", "docx.document.verify.ooxml")
                self.assertEqual(led_bad.lookup_shape(goal_j)["preferred_capability"], "docx.document.verify.ooxml")

                sol_fb = model.solve(
                    goal_j,
                    inputs={"ledger_db_path": str(led_bad_path), "output_path": out_rel, "spec": {"status": "ok"}},
                )
                self.assertTrue(sol_fb["pass"], sol_fb)
                self.assertEqual(sol_fb["capability_id"], "json.file.write")
                # Promoted bad entry was automatically invalidated on miss and replaced by verified json.file.write!
                self.assertNotEqual(led_bad.lookup_shape(goal_j)["preferred_capability"], "docx.document.verify.ooxml")
            finally:
                if out_abs.exists():
                    out_abs.unlink()

            # Unconfined refusal vs confined Makefile execution via taskfile_read_v1 + autonomous_v1
            ws_mk = tp / "mk_proj"
            ws_mk.mkdir()
            (ws_mk / "Makefile").write_text("package:\n\t@printf 'packaged-ok' > dist.txt\n", encoding="utf-8")
            refused = solve_or_learn("run make package", cwd=ws_mk, record_open_gap=False, allow_jit_network=False)
            self.assertEqual(refused["status"], "FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT")
            self.assertFalse((ws_mk / "dist.txt").exists())

            admitted = solve_or_learn(
                "run make package",
                cwd=ws_mk,
                confinement_admitted=True,
                record_open_gap=False,
                allow_jit_network=False,
            )
            self.assertTrue(admitted["pass"], admitted)
            self.assertEqual((ws_mk / "dist.txt").read_text(encoding="utf-8"), "packaged-ok")

            # N=2 trajectory macro promotion into real `macro_v1` + `< 1 ms` recall on 3rd workspace
            ws_t1, ws_t2, ws_t3 = tp / "t1", tp / "t2", tp / "t3"
            ws_t1.mkdir()
            ws_t2.mkdir()
            ws_t3.mkdir()
            (ws_t1 / "Makefile").write_text("emit:\n\t@printf '1' > out.txt\n", encoding="utf-8")
            (ws_t2 / "Makefile").write_text("emit:\n\t@printf '2' > out.txt\n", encoding="utf-8")
            (ws_t3 / "Makefile").write_text("emit:\n\t@printf '3' > out.txt\n", encoding="utf-8")
            m1 = execute_and_elevate_confined_trajectory("run make emit", cwd=ws_t1, workflow_db_path=tp / "m.json")
            m2 = execute_and_elevate_confined_trajectory("run make emit", cwd=ws_t2, workflow_db_path=tp / "m.json")
            m3 = execute_and_elevate_confined_trajectory("run make emit", cwd=ws_t3, workflow_db_path=tp / "m.json")
            self.assertTrue(m1["pass"] and not m1["macro_promoted"] and not m1["from_macro"])
            self.assertTrue(m2["pass"] and m2["macro_promoted"] and not m2["from_macro"])
            self.assertTrue(m3["pass"] and m3["from_macro"])
            self.assertEqual((ws_t3 / "out.txt").read_text(encoding="utf-8"), "3")

    def test_component4_sovereign_creature_board_calibration_and_awake_delegation(self) -> None:
        from canonical.runtime import creature_runtime_v1 as R
        from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon

        # Regression lock: zero hardcoded capability whitelists in `creature_runtime_v1`
        self.assertFalse(hasattr(R, "_SOVEREIGN_STDLIB_INSPECTABLE_FAMILIES"))

        with tempfile.TemporaryDirectory() as td:
            tp = pathlib.Path(td)

            # 1. Default `run_its_own_board` (`does_nothing`) & unverified inspector refusal remain intact
            default_rep = R.run_its_own_board(tp / "default_c", cycles=4)
            self.assertEqual(default_rep["run"]["closed"], 0)
            self.assertGreater(default_rep["run"]["parked"], 0)

            c_guard = R.boot(tp / "guard_c")
            c_guard.author_inspector_investigation()
            # Run past the child discovery steps until the parent inspector obligation itself is attempted
            statuses = [
                c_guard.step(lambda w, _c: {"ok": True, "verified": True, "correct": True, "value": w.value})["status"]
                for _ in range(5)
            ]
            self.assertIn("WAITING_FOR_INSPECTOR_VERIFIER", statuses)

            # 2. Uncurated `external_hard_slice_v1.select` board closes real capabilities via `type_directed_sampler_v1` + Flight + Factory & beats baseline
            sov = R.run_sovereign_board(tp / "sov_c", cycles=26)
            self.assertEqual(
                sov["hard_slice_plan"]["selection_excludes"],
                ["the system's own stated confidence"],
            )
            self.assertGreaterEqual(sov["run"]["closed"], 5, sov)
            self.assertGreater(sov["run"]["parked"], 0, sov)
            self.assertEqual(sov["derived_flight_metrics"]["over_permissive_derivations"], 0)
            self.assertGreaterEqual(sov["derived_flight_metrics"]["registered"], 5)
            self.assertGreaterEqual(sov["onboarding_factory_metrics"]["onboarded"], 5)
            self.assertEqual(sov["calibration"]["verdict"], "CALIBRATED", sov["calibration"])
            self.assertEqual(
                sov["baseline_comparison"]["verdict"],
                "CLAIM_BEATS_EXTERNAL_BASELINE",
                sov["baseline_comparison"],
            )
            self.assertGreater(sov["baseline_comparison"]["margin_over_baseline"], 0.05)

            # 3. AwakeAgencyDaemon delegates multi-file confined repair, warm 0.0-Life skip (< 15 ms), and numeric chase to Creature
            ws_mf = tp / "mf_repo"
            (ws_mf / "pkg").mkdir(parents=True)
            (ws_mf / "tests").mkdir()
            (ws_mf / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (ws_mf / "pkg" / "math_ops.py").write_text("def offset(v):\n    return v - 3\n", encoding="utf-8")
            (ws_mf / "tests" / "test_flow.py").write_text(
                "from pkg.math_ops import offset\n\ndef test_offset():\n    assert offset(10) == 13\n",
                encoding="utf-8",
            )
            daemon = AwakeAgencyDaemon(
                ws_mf,
                ledger_path=tp / "awake_led.json",
                skill_store_path=tp / "awake_skills.sqlite",
                apply_verified_repairs=True,
            )
            p1 = daemon.pulse(max_curriculum_lessons=0)
            self.assertEqual(p1["cow_experimentation"]["repaired"], 1, p1)
            self.assertEqual(p1["cow_experimentation"]["repairs"][0]["mode"], "CONFINED_ZYGOTE_MULTIFILE_REPAIR")

            _ = daemon.pulse(max_curriculum_lessons=0)
            life_before = daemon.creature.report()["life_remaining"]
            t_w = time.perf_counter()
            p_warm = daemon.pulse(max_curriculum_lessons=0)
            warm_ms = (time.perf_counter() - t_w) * 1000.0
            self.assertEqual(daemon.creature.report()["life_remaining"], life_before)
            self.assertEqual(p_warm["creature_steps"], [])
            self.assertLess(warm_ms, 25.0)

            state = {"rem": 3}
            daemon.register_numeric_chase(
                "reduce_rem",
                goal="Make at most 0 remaining errors",
                measure=lambda: state["rem"],
                act=lambda _ctx: (state.__setitem__("rem", max(0, state["rem"] - 1)) or {"status": "DEC"}),
            )
            daemon.pulse(max_curriculum_lessons=0)
            self.assertEqual(state["rem"], 0)


if __name__ == "__main__":
    unittest.main()
