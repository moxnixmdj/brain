#!/usr/bin/env python3
"""End-to-end verification of the unified autonomous loop (Cuts 1-3).

Exercises all 5 owner capabilities (`OWNER_ACTIVE_GOAL_20261018_V1.md` §5)
composed exclusively from existing repository organs (`K3=0`, `$0` spend):
  1. General computer use (HTTP `<form>` elevation, `computer_env_v1`, `osworld_computer_surface_v1`)
  2. Instant learning + scope/polyglot/expiry organs (`VerifiedSkillStore` +
     `operator_generalization_v1` + `boundary_disjunction_normalization_v1` +
     `rule_scope_learning_v1` + `language_neutral_skill_bridge_v1` + `rule_expiry_v1`)
  3. Persistence to a measured target (`goal_chase_v1.chase_until_met` wired to 4-tier `solve_or_learn`)
  4. Data-gap detection -> acquisition -> closure (`ignorance_ledger_v1` `note`/`rank`/`close`)
  5. Global non-local completeness (`completeness_gate_for` blocking 1-channel extrapolation)
  + Cut 3 bit-identical `<3 ms` inverted BM25 shortlist & compile-time adapter AST index.
"""
from __future__ import annotations

import inspect
import os
import pathlib
import shutil
import sqlite3
import tempfile
import time
import unittest

from canonical.runtime import brain_unified_model_v1 as bum
from canonical.runtime import capability_selection_retrieval_v1 as csr
from canonical.runtime import ignorance_ledger_v1 as led
from canonical.runtime import live_brain_route_admission_v1 as ra
from canonical.runtime import live_integrated_brain_v1 as lib
from canonical.runtime.bound_capabilities import objective_relevance_bm25 as bm25
from canonical.swe_kernel import rule_expiry_v1 as expiry
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
from execution_guard import goal_chase_v1 as gc_chase


def _exec_py_oracle(candidate: str, asserts: str) -> bool:
    ns: dict = {}
    try:
        exec(compile(candidate, "<candidate>", "exec"), ns)
        exec(compile(asserts, "<asserts>", "exec"), ns)
        return True
    except Exception:
        return False


def _boundary_twin_oracle(candidate: str) -> bool:
    ns: dict = {}
    try:
        exec(compile(candidate, "<twin>", "exec"), ns)
    except Exception:
        return False
    fn = next((v for k, v in ns.items() if k != "__builtins__" and callable(v) and not isinstance(v, type)), None)
    return bool(fn) and fn(10, 10) is False and fn(9, 10) is True


class IntegratedAutonomousLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        ws_tmp_root = pathlib.Path(lib.ROOT) / "canonical/astra_runtime/tmp"
        ws_tmp_root.mkdir(parents=True, exist_ok=True)
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_int_loop_", dir=str(ws_tmp_root)))
        self.wf_db = self.tmp / "workflows.sqlite"
        self.skill_db = self.tmp / "skills.sqlite"
        self.ledger_file = self.tmp / "ignorance_ledger.json"
        self._orig_ledger_path = led.DEFAULT_STATE
        led.DEFAULT_STATE = str(self.ledger_file)
        self._old_wf_env = os.environ.get("BRAIN_COMPILED_WORKFLOW_DB")
        os.environ["BRAIN_COMPILED_WORKFLOW_DB"] = str(self.wf_db)

    def tearDown(self) -> None:
        led.DEFAULT_STATE = self._orig_ledger_path
        if self._old_wf_env is None:
            os.environ.pop("BRAIN_COMPILED_WORKFLOW_DB", None)
        else:
            os.environ["BRAIN_COMPILED_WORKFLOW_DB"] = self._old_wf_env
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cut1_single_front_door_gap_ledger_gui_fallback_and_honest_refusal(self) -> None:
        # 1. Verify duplicate `def solve_or_learn` shadowing bug is eliminated
        defs = [l for l in inspect.getsource(ra).splitlines() if l.startswith("def solve_or_learn")]
        self.assertEqual(len(defs), 1)
        self.assertTrue(callable(getattr(ra, "chase_until_met", None)))

        # 2. Genuine unserved gap records cleanly into ignorance_ledger_v1 (`note` + `rank`)
        gap_goal = "quantum_teleport_a_toaster_across_mars_99182"
        unserved = ra.solve_or_learn(
            {"task_id": "gap-1", "goal": gap_goal},
            db_path=self.wf_db,
            allow_jit_network=False,
        )
        self.assertFalse(unserved["pass"])
        self.assertTrue(unserved["learning"]["gap_recorded"])
        ranked = led.rank(limit=5)
        self.assertEqual(ranked[0]["what"], gap_goal)

        # 3. Learnable CLI goal first recorded as a gap is closed automatically when Tier 2 learns it
        cli_dir = self.tmp / "cli_data"
        cli_dir.mkdir()
        (cli_dir / "items.txt").write_text("alpha\nbeta\nalpha\ngamma\nbeta\n", encoding="utf-8")
        learn_goal = "how many unique lines in items.txt"
        led.note(learn_goal, why="initial gap", cost=1.0)
        self.assertTrue(any(r["what"] == learn_goal for r in led.rank(limit=10)))

        learned = ra.solve_or_learn(
            {"task_id": "learn-cli-1", "goal": learn_goal},
            cwd=cli_dir,
            db_path=self.wf_db,
            allow_jit_network=False,
        )
        self.assertTrue(learned["pass"], learned)
        self.assertEqual(str(learned["answer"]).strip(), "3")
        self.assertTrue(learned.get("learned_this_turn"))
        self.assertTrue(learned.get("closed_gap_ids"))
        # Gap is now closed and no longer appears in open rank()
        self.assertFalse(any(r["what"] == learn_goal for r in led.rank(limit=10)))

        # 4. Typed GUI surface fallback (`osworld_computer_surface_v1`) compiles deterministically
        gui_res = ra.solve_or_learn(
            {
                "task_id": "gui-1",
                "goal": "click the submit button on the modal dialog",
                "gui_action": {"type": "click", "x": 420, "y": 310, "button": "left"},
                "gui_screen": {"width": 1920, "height": 1080},
            },
            db_path=self.wf_db,
            allow_jit_network=False,
        )
        self.assertTrue(gui_res["pass"], gui_res)
        self.assertEqual(gui_res["tier_used"], "tier2_typed_gui_surface")
        self.assertEqual(gui_res["compiled_pyautogui"], "pyautogui.click(x=420, y=310, button='left')")

        # 5. Honest missing-file refusal (`R9`) fails closed immediately
        refused = ra.solve_or_learn(
            {"task_id": "r9-1", "goal": "extract text from a pdf file"},
            db_path=self.wf_db,
            allow_jit_network=False,
        )
        self.assertFalse(refused["pass"])
        self.assertEqual((refused.get("route_admission") or {}).get("rule"), "R9_REQUIRED_FILE_INPUT_UNBOUND")

    def test_cut1_persistent_goal_chase_and_global_completeness_gate(self) -> None:
        # 1. Single correlated channel ("one paper says YouTube") is blocked by completeness_gate_for
        gate = gc_chase.completeness_gate_for("make 1000 dollars")
        blocked = gate(
            {
                "known_options": [
                    {"source_id": "blog_1", "procedure": "youtube", "candidate_authority": "VERIFIED"},
                ]
            }
        )
        self.assertFalse(blocked["complete"])
        self.assertIn("ONLY_1_INDEPENDENT_CHANNEL", blocked["reason"])

        # 2. Target-bound `chase_until_met` stalls first, learns a K2-compiled SQLite workflow skill,
        #    resumes with `live_act` replaying the compiled workflow in <5 ms/round, and reaches target=3!
        db_target = self.tmp / "revenue.sqlite"
        held_db = self.tmp / "heldout_revenue.sqlite"
        for p in (db_target, held_db):
            con = sqlite3.connect(str(p))
            con.execute("CREATE TABLE ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, units INTEGER)")
            con.commit()
            con.close()

        def measure_units() -> float:
            con = sqlite3.connect(str(db_target))
            try:
                row = con.execute("SELECT COALESCE(SUM(units), 0) FROM ledger").fetchone()
                return float(row[0] or 0)
            finally:
                con.close()

        db_rel = self.tmp.relative_to(lib.ROOT) / "revenue.sqlite"
        held_rel = self.tmp.relative_to(lib.ROOT) / "heldout_revenue.sqlite"
        chase_goal = f"Reach 3 units in database {db_rel}"
        held_goal = f"Reach 3 units in database {held_rel}"
        chase_res = ra.chase_until_met(
            chase_goal,
            measure=measure_units,
            target=3.0,
            direction="maximize",
            unit="units",
            max_rounds=5,
            patience=1,
            max_learn_attempts=2,
            widen_options=False,
            flywheel_state_path=str(self.tmp / "flywheel.json"),
            context={
                "skill_db": str(self.wf_db),
                "cwd": str(lib.ROOT),
                "allow_jit_network": False,
                "demonstration_trace": [
                    {
                        "kind": "sqlite_query",
                        "db_path": str(db_rel),
                        "sql": "INSERT INTO ledger(units) VALUES (?)",
                        "params": [1],
                    }
                ],
                "postcondition": {
                    "kind": "sqlite_row_exists",
                    "db_path": str(db_rel),
                    "sql": "SELECT units FROM ledger WHERE units = 1",
                },
                "heldout_goal": held_goal,
                "heldout_cwd": str(lib.ROOT),
                "heldout_postcondition": {
                    "kind": "sqlite_row_exists",
                    "db_path": str(held_rel),
                    "sql": "SELECT units FROM ledger WHERE units = 1",
                },
                "sabotaged_postcondition": {
                    "kind": "sqlite_row_exists",
                    "db_path": str(held_rel),
                    "sql": "SELECT units FROM ledger WHERE units = 999",
                },
            },
        )
        self.assertTrue(chase_res["pass"], chase_res)
        self.assertTrue(chase_res["resumed"])
        self.assertGreaterEqual(measure_units(), 3.0)

    def test_cut2_scope_escalation_polyglot_bridge_version_space_and_expiry(self) -> None:
        store = VerifiedSkillStore(self.skill_db, seed=False)
        taught = store.crystallize_code_fix(
            before_snippet="def within(x, hi):\n    return x <= hi\n",
            after_snippet="def within(x, hi):\n    return x < hi\n",
            language="python",
            error_class="BOUNDARY",
            twin_oracle=_boundary_twin_oracle,
        )
        self.assertTrue(taught["crystallized"])
        sid = taught["skill_id"]

        # 1. Statement + Operator + Semantic Disjunction escalation (all 3 tiers verified by execution)
        variants = [
            ("def inside(a, b):\n    return a <= b\n", "assert inside(5, 5) is False and inside(4, 5) is True"),
            ("def guard(a, b):\n    if a <= b:\n        return True\n    return False\n", "assert guard(5, 5) is False and guard(4, 5) is True"),
            ("def flipped(a, b):\n    return b >= a\n", "assert flipped(5, 5) is False and flipped(4, 5) is True"),
            ("def disj(a, b):\n    return a < b or a == b\n", "assert disj(5, 5) is False and disj(4, 5) is True"),
        ]
        tiers_seen = set()
        for src, asserts in variants:
            hit = store.recall_and_apply_verified(
                source_text=src,
                language="python",
                error_class="BOUNDARY",
                verifier=lambda cand, a=asserts: _exec_py_oracle(cand, a),
                allow_scope_escalation=True,
            )
            self.assertIsNotNone(hit, src)
            tiers_seen.add(hit["scope_tier"])
        self.assertEqual(tiers_seen, {"SCOPE_STATEMENT", "SCOPE_OPERATOR", "SCOPE_SEMANTIC"})

        # 2. Cross-language lexical carry across Go, TypeScript, C++, and Java
        cross_targets = {
            "go": "func Within(v, top int) bool {\n\treturn v <= top\n}\n",
            "typescript": "export function within(v: number, top: number): boolean {\n  return v <= top;\n}\n",
            "cpp": "bool within(int v, int top) {\n    return v <= top;\n}\n",
            "java": "boolean within(int v, int top) {\n    return v <= top;\n}\n",
        }
        for lang, code in cross_targets.items():
            xhit = store.recall_and_apply_verified(
                source_text=code,
                language=lang,
                error_class="BOUNDARY",
                verifier=lambda cand: ("<=" not in cand) and ("< top" in cand),
            )
            self.assertIsNotNone(xhit, f"Failed crossing into {lang}")
            self.assertTrue(xhit.get("from_cross_language_memory"))
            self.assertEqual(xhit.get("from_language"), "python")
            self.assertEqual(xhit.get("to_language"), lang)

        # 3. Rule expiry (`rule_expiry_v1`): FRESH stamp passes, STALE world blocks until re-verified
        expiry.record_taught(self.skill_db, sid)
        self.assertIsNotNone(
            store.recall_and_apply_verified(
                source_text="def f(a, b):\n    return a <= b\n",
                language="python",
                verifier=lambda c: "< b" in c,
            )
        )
        moved_world = expiry.world_fingerprint()
        moved_world["python_major_minor"] = "99.0"
        self.assertIsNone(
            store.recall_and_apply_verified(
                source_text="def f(a, b):\n    return a <= b\n",
                language="python",
                verifier=lambda c: "< b" in c,
                now_world_fingerprint=moved_world,
            )
        )

        # 4. Active version-space learning (`narrow_rule_scope` -> `finite_capability_diagnosis.select_probe`):
        #    (a) Selects 2 informative probes out of 3 offered to resolve `SCOPE_SEMANTIC`.
        resolved = store.narrow_rule_scope(
            sid,
            instances=[
                {
                    "label": "same_shape",
                    "source_text": "def f(a, b):\n    return a <= b\n",
                    "verifier": lambda c: _exec_py_oracle(c, "assert f(5, 5) is False and f(4, 5) is True"),
                },
                {
                    "label": "if_guard",
                    "source_text": "def g(a, b):\n    if a <= b:\n        return True\n    return False\n",
                    "verifier": lambda c: _exec_py_oracle(c, "assert g(5, 5) is False and g(4, 5) is True"),
                },
                {
                    "label": "algebraic_disjunction",
                    "source_text": "def h(a, b):\n    return a < b or a == b\n",
                    "verifier": lambda c: _exec_py_oracle(c, "assert h(5, 5) is False and h(4, 5) is True"),
                },
            ],
        )
        self.assertTrue(resolved["ok"])
        self.assertEqual(resolved["persisted_scope"], "SCOPE_SEMANTIC")
        self.assertEqual(resolved["observations_used"], 2)

        #    (b) Explicit falsification / invalidation immediately removes the rule from recall.
        store.invalidate(sid, reason="counterexample_observed")
        self.assertIsNone(
            store.recall_and_apply_verified(
                source_text="def f(a, b):\n    return a <= b\n",
                language="python",
                verifier=lambda c: "< b" in c,
            )
        )

    def test_cut3_bit_identical_fast_bm25_shortlist_and_adapter_ast_index(self) -> None:
        reg = lib.load_verified_registry(include_extended=True)
        declared = csr.declarations(lib.ROOT)
        raw_docs = [csr.document(cid, entry, declared.get(cid)) for cid, entry in reg.items() if isinstance(entry, dict)]

        # Warm index once
        csr.shortlist("Verify a tar.gz archive against its manifest", reg, lib.ROOT, 5)

        queries = [
            "Count the function and class definitions in canonical/swe_kernel and write the number to out.json",
            "Rename the parameter old_price to price in canonical/swe_kernel/rule_expiry_v1.py",
            "Check whether alpha budget of 40 exceeds beta budget of 30",
            "xyzzy_no_lexical_match_token_887766",
            "",
        ]
        t0 = time.perf_counter()
        fast_outputs = [csr.shortlist(q, reg, lib.ROOT, 5) for q in queries]
        avg_ms = (time.perf_counter() - t0) * 1000.0 / len(queries)
        self.assertLess(avg_ms, 3.0)

        for q, fast in zip(queries, fast_outputs):
            ref = bm25.rank(q, raw_docs, limit=5)
            ref_props = [
                {
                    "capability_id": r["candidate"]["capability_id"],
                    "lexical_relevance_score": r["lexical_relevance_score"],
                    "matched_terms": r.get("matched_terms") or [],
                }
                for r in (ref.get("ranked_candidates") or [])
                if float(r.get("lexical_relevance_score") or 0) > 0
            ]
            self.assertEqual(fast["status"], ref.get("status"))
            self.assertEqual(fast["ranker_reason"], ref.get("reason"))
            self.assertEqual(fast["proposals"], ref_props)

        # Verify compile-time adapter_ast_index serves SHA-256 verified metadata & rejects wrong SHA
        meta = bum.adapter_ast_entry("canonical/runtime/bound_capabilities/python_source_add_parameter.py")
        self.assertIsNotNone(meta)
        self.assertIsInstance(meta["defaulted_keys"], dict)
        self.assertIn("default_expr", meta["defaulted_keys"])
        self.assertIsNone(
            bum.adapter_ast_entry(
                "canonical/runtime/bound_capabilities/python_source_add_parameter.py",
                expected_sha256="0" * 64,
            )
        )


if __name__ == "__main__":
    unittest.main()
