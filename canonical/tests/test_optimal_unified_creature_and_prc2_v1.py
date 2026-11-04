"""Behavioral & negative-control verification for the unified optimal architecture:

1. PR-C2 (`OPTIMAL_PLAN_20261102_V6.md`): stored rules remain context-anchored;
   apply-time pattern narrowing lifts cross-shape recall from 2/5 to 5/5 under
   `ProjectTestOracle` (`TEST_SUITE`) with 0/4 misapplications and 0 broadened
   proposals ever reaching a `CALLER_PREDICATE` verifier.
2. Thread-safe `ContextVar` `workspace_root` scoping across concurrent threads
   without mutating `live_brain_route_admission_v1._BRAIN_CODE_ROOT` or leaking
   across simultaneous requests.
3. Strict zero-memory `learn=False` isolation across `solve_v1.solve`,
   `computer_env_v1.perform`, `closed_loop_autonomous_controller_v1.solve_or_learn`,
   and `live_brain_route_admission_v1.solve(route_memory_mode='exclude')`.
4. Unified `creature_runtime_v1.Creature` organism: `note_goal_gap` ->
   `ignorance_ledger_v1`, fail-closed/confined `confined_verified_perform`, and
   restart-continuous `run_awake_creature_pulse` (`K3 = 0`).
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import gzip
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNTIME_DIR = REPO_ROOT / "canonical" / "runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from canonical.runtime import computer_env_v1 as cenv
from canonical.runtime import computer_execution_boundary_v1 as boundary
from canonical.runtime import creature_runtime_v1 as creature_mod
from canonical.runtime import flywheel_v1 as flywheel
from canonical.runtime import ignorance_ledger_v1 as ledger
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.runtime import mortality_and_triage_v1 as mortality
from canonical.runtime import self_authored_obligations_v1 as obligations
from canonical.runtime import solve_v1
from canonical.runtime import transfer_learning_v1 as transfer
from canonical.swe_kernel import closed_loop_autonomous_controller_v1 as controller
from canonical.swe_kernel.upstream_routing_ledger_v1 import UpstreamRoutingLedger
from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore
from canonical.tools import pr_c2_apply_time_broadening_benchmark_v1 as prc2_bench


class OptimalUnifiedCreatureAndPrC2Tests(unittest.TestCase):
    def test_prc2_apply_time_broadening_5_of_5_and_weak_verifier_isolation(self) -> None:
        report = prc2_bench.run_benchmark()
        self.assertTrue(report["taught_crystallized"])
        self.assertTrue(report["stored_context_anchored"])
        self.assertEqual(report["direct_recall_count"], 2)
        self.assertEqual(report["scoped_test_suite_recall_count"], 5)
        self.assertEqual(report["negative_control_misapplications"], 0)
        self.assertEqual(report["weak_verifier_broadened_proposals"], 0)

        with tempfile.TemporaryDirectory() as td:
            store = VerifiedSkillStore(pathlib.Path(td) / "weak.sqlite", seed=False)
            with self.assertRaisesRegex(ValueError, "SCOPE_ESCALATION_REQUIRES_SCOPED_TEST_SUITE"):
                store.recall_and_apply_verified(
                    source_text="def f(x, y):\n    return x <= y\n",
                    language="python",
                    verifier=lambda _c: True,
                    allow_scope_escalation=True,
                )

    def test_concurrent_workspace_root_scoping_is_thread_safe_without_global_mutation(self) -> None:
        base_tmp = REPO_ROOT / "canonical" / "astra_runtime" / "tmp"
        base_tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="concurrent_ws_") as td:
            root_base = pathlib.Path(td)
            workspaces: list[tuple[int, pathlib.Path]] = []
            for idx in range(8):
                ws = root_base / f"ws_{idx}"
                pkg = ws / "app" / "pkg"
                pkg.mkdir(parents=True)
                (ws / "out").mkdir(parents=True)
                (pkg / "__init__.py").write_text("", encoding="utf-8")
                (pkg / "sample.py").write_text(
                    f"def unused_helper_{idx}():\n    return {idx}\n\ndef main():\n    return 'ok'\n",
                    encoding="utf-8",
                )
                workspaces.append((idx, ws))

            def _worker(item: tuple[int, pathlib.Path]) -> tuple[int, str, str, bool]:
                idx, ws = item
                res = door.solve(
                    {
                        "task_id": f"ws-thread-{idx}",
                        "goal": "Find dead code in app/pkg and write report to out/dead_report.json",
                        "workspace_root": str(ws),
                        "route_memory_mode": "exclude",
                    }
                )
                rep_file = ws / "out" / "dead_report.json"
                rep_txt = rep_file.read_text(encoding="utf-8") if rep_file.is_file() else json.dumps(res, default=str)
                return (
                    idx,
                    str(door._BRAIN_CODE_ROOT),
                    rep_txt,
                    bool(res.get("pass")),
                )

            with ThreadPoolExecutor(max_workers=8) as pool:
                outcomes = list(pool.map(_worker, workspaces))

            self.assertEqual(pathlib.Path(door.ROOT).resolve(), REPO_ROOT.resolve())
            self.assertEqual(door._BRAIN_CODE_ROOT, REPO_ROOT.resolve())
            for idx, brain_code_root, serialized, passed in outcomes:
                self.assertEqual(pathlib.Path(brain_code_root), REPO_ROOT.resolve())
                self.assertTrue(passed, serialized)
                self.assertIn(f"unused_helper_{idx}", serialized)
                other_idx = (idx + 1) % 8
                self.assertNotIn(f"unused_helper_{other_idx}", serialized)

    def test_strict_learn_false_zero_memory_touch_across_layers(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            # 1. solve_v1.solve(..., learn=False): zero flywheel/workflow/staging reads or writes
            old_fw = flywheel.DEFAULT_STATE
            flywheel.DEFAULT_STATE = str(tmp / "flywheel.json")
            staging_file = tmp / "staging.json"
            staging_file.write_text(json.dumps({"episodes": {"prior": {"goal": "x"}}}), encoding="utf-8")
            PathFly = pathlib.Path(flywheel.DEFAULT_STATE)
            PathFly.write_text(json.dumps({"schema": "seed", "cells": {}}), encoding="utf-8")
            fw_before = PathFly.read_bytes()
            st_before = staging_file.read_bytes()
            work_dir = tmp / "solve_work"
            work_dir.mkdir()
            try:
                steps_called = 0

                def _scripted_model(_goal: str, seeing: dict) -> str | None:
                    nonlocal steps_called
                    self.assertIsNone(seeing["learned"])
                    steps_called += 1
                    if steps_called == 1:
                        return "from pathlib import Path\nPath('done.txt').write_text('ok')\n"
                    return None

                res = solve_v1.solve(
                    "write ok to done.txt",
                    str(work_dir),
                    model=_scripted_model,
                    learn=False,
                    staging_path=staging_file,
                )
                self.assertEqual(res["verdict"], solve_v1.DONE)
                self.assertNotIn("from_memory", res)
                self.assertNotIn("skill_crystallization", res)
                self.assertEqual(PathFly.read_bytes(), fw_before)
                self.assertEqual(staging_file.read_bytes(), st_before)
            finally:
                flywheel.DEFAULT_STATE = old_fw

            # 2. computer_env_v1.perform(..., learn=False): executes real gzip without reading/writing transfer store
            old_tl = transfer.STATE_PATH
            old_fp = os.environ.get("BRAIN_TRANSFER_LEARNING_FINGERPRINTS")
            tl_file = tmp / "tl_episodes.json"
            fp_file = tmp / "tl_fp.json"
            tl_file.write_text(json.dumps([{"plan": ["run_gzip"], "goal_key": "goal"}]), encoding="utf-8")
            fp_file.write_text(json.dumps({"fingerprints": {}}), encoding="utf-8")
            tl_before = tl_file.read_bytes()
            fp_before = fp_file.read_bytes()
            transfer.STATE_PATH = str(tl_file)
            os.environ["BRAIN_TRANSFER_LEARNING_FINGERPRINTS"] = str(fp_file)
            try:
                cdir = tmp / "comp"
                cdir.mkdir()
                (cdir / "note.txt").write_bytes(b"deterministic payload 12345\n")
                out = cenv.perform("compress note.txt into note.txt.gz", cwd=cdir, learn=False)
                self.assertTrue(out["pass"], out)
                self.assertFalse(out["from_memory"])
                self.assertEqual(
                    gzip.decompress((cdir / "note.txt.gz").read_bytes()),
                    b"deterministic payload 12345\n",
                )
                self.assertEqual(tl_file.read_bytes(), tl_before)
                self.assertEqual(fp_file.read_bytes(), fp_before)
            finally:
                transfer.STATE_PATH = old_tl
                if old_fp is None:
                    os.environ.pop("BRAIN_TRANSFER_LEARNING_FINGERPRINTS", None)
                else:
                    os.environ["BRAIN_TRANSFER_LEARNING_FINGERPRINTS"] = old_fp

            # 3. controller.solve_or_learn(..., learn=False) & route_memory_mode='exclude' skip routing ledger
            ledger_db = tmp / "routing_ledger.sqlite"
            uledger = UpstreamRoutingLedger(ledger_db)
            uledger.record_refusal(
                "Find dead code in sample.py",
                "wrong.cap",
                "LEXICAL_EFFECT_CONTRADICTED",
                preferred_capability="software.analysis.diagnose_and_architect.v1",
            )
            db_bytes_before = ledger_db.read_bytes()
            c_res = controller.solve_or_learn(
                {
                    "task_id": "cold-check",
                    "goal": "quantum_nonexistent_goal_for_cold_control_8812",
                    "_routing_ledger_db": str(ledger_db),
                },
                learn=False,
            )
            self.assertFalse(c_res["pass"])
            self.assertEqual(c_res.get("route_memory_policy"), "EXCLUDED_ROUTE_RECALL_ONLY")
            self.assertEqual(ledger_db.read_bytes(), db_bytes_before)

    def test_unified_creature_gap_intake_confined_perform_and_restart_continuity(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            c_root = base / "creature_state"
            ledger_file = base / "ignorance.json"

            # 1. Boot Creature & translate missing typed goal slot into ranked ignorance gap
            c1 = creature_mod.boot(c_root, identity="alpha-creature", life=20.0)
            intake = c1.note_goal_gap(
                "Create a DOCX document with title Report",
                workspace_root=base,
                cost=0.5,
                ledger_path=ledger_file,
            )
            self.assertEqual(intake["outcome"], "SLOT_UNSTATED")
            self.assertEqual(intake["statement"]["slot"], "json_path")
            self.assertEqual(len(intake["gap_ids"]), 1)
            self.assertIsNotNone(intake["next_to_close"])
            self.assertEqual(ledger.open_gaps(path=str(ledger_file)), 1)

            # 2. confined_verified_perform fails closed when confinement is unavailable
            ws = base / "work"
            ws.mkdir()
            c1.author_board(
                [
                    obligations.Proposal(
                        id="write_marker",
                        claim="marker.txt contains verified bytes",
                        source="workspace_observation",
                        check=lambda w: (w.get("files") or {}).get("marker.txt") == "verified",
                        value=2.0,
                        cost=1.0,
                    )
                ],
                before={"files": {"marker.txt": "missing"}},
                done={"files": {"marker.txt": "verified"}},
            )
            perform_fn = creature_mod.confined_verified_perform(
                ws,
                programs={"write_marker": "from pathlib import Path\nPath('marker.txt').write_text('verified')\n"},
                checks={"write_marker": lambda root: (root / "marker.txt").is_file() and (root / "marker.txt").read_text() == "verified"},
            )
            with mock.patch("canonical.runtime.confine_v1.available", return_value=False):
                step_blocked = c1.step(perform_fn)
            self.assertEqual(step_blocked["status"], "WORKED")
            self.assertFalse(step_blocked["ok"])
            self.assertEqual(step_blocked["blocked"], boundary.STATUS)
            self.assertFalse((ws / "marker.txt").exists())

            from canonical.runtime import confine_v1 as C

            if C.available():
                step_confined = c1.step(perform_fn)
                self.assertEqual(step_confined["status"], "WORKED")
                self.assertTrue(step_confined["ok"])
                self.assertTrue(step_confined["confined"])
                self.assertEqual((ws / "marker.txt").read_text(encoding="utf-8"), "verified")

            # 3. Restart continuity via run_awake_creature_pulse (`K3 = 0`)
            proj = base / "awake_repo"
            proj.mkdir()
            (proj / "calc.py").write_text("def ratio(a, b):\n    return a / b\n", encoding="utf-8")
            (proj / "test_calc.py").write_text(
                "import unittest\nfrom calc import ratio\n"
                "class T(unittest.TestCase):\n"
                "    def test_zero(self):\n"
                "        self.assertEqual(ratio(6, 2), 3.0)\n"
                "        self.assertEqual(ratio(5, 0), 0)\n",
                encoding="utf-8",
            )
            pulse_state = base / "pulse_creature"
            skill_db = base / "awake_skills.sqlite"
            p1 = creature_mod.run_awake_creature_pulse(
                proj,
                state_root=pulse_state,
                identity="unified-creature",
                ledger_path=ledger_file,
                skill_store_path=skill_db,
                apply_verified_repairs=True,
                max_curriculum_lessons=0,
            )
            self.assertEqual(p1["k3_external_llm_calls"], 0)
            self.assertEqual(p1["creature"]["identity"], "unified-creature")
            epoch_1 = p1["creature"]["epoch"]
            life_after_1 = p1["creature"]["life_remaining"]
            # Bound to the named grant, not the literal 40.0: the assertion is "life was spent",
            # which is what this test is about, and 40.0 would silently re-starve the creature.
            self.assertLess(life_after_1, creature_mod.DEFAULT_LIFE_GRANT)

            # Second boot on same state_root increments epoch, preserves spent life, and wastes 0.0 Life on green proj
            p2 = creature_mod.run_awake_creature_pulse(
                proj,
                state_root=pulse_state,
                identity="unified-creature",
                ledger_path=ledger_file,
                skill_store_path=skill_db,
                apply_verified_repairs=False,
                max_curriculum_lessons=0,
            )
            self.assertGreater(p2["creature"]["epoch"], epoch_1)
            self.assertEqual(p2["creature"]["life_remaining"], life_after_1)

    def test_memory_policy_chokepoints_block_hidden_writes_and_enforce_monotonic_scopes(self) -> None:
        from canonical.runtime import associative_memory_v1 as amem
        from canonical.runtime.memory_policy_v1 import (
            MemoryPolicyError,
            effective_memory_mode,
            memory_policy_scope,
        )

        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            # 1. Monotonic containment: inner scopes clamp to OFF by default and raise on fail_on_escalation=True
            with memory_policy_scope("OFF"):
                self.assertEqual(effective_memory_mode(), "OFF")
                with memory_policy_scope("READ_WRITE"):
                    self.assertEqual(effective_memory_mode(), "OFF")
                with self.assertRaises(MemoryPolicyError):
                    with memory_policy_scope("READ_ONLY", fail_on_escalation=True):
                        pass
                with self.assertRaises(MemoryPolicyError):
                    with memory_policy_scope("READ_WRITE", fail_on_escalation=True):
                        pass

            # 2. transfer_learning_v1.drive(..., use_transfer=False) writes 0 bytes under OFF / READ_ONLY
            old_tl = transfer.STATE_PATH
            tl_path = tmp / "tl_state.json"
            transfer.STATE_PATH = str(tl_path)
            try:
                class _TinyEnv:
                    def __init__(self) -> None:
                        self.v = 0
                    def reset(self) -> int:
                        self.v = 0
                        return self.v
                    def state(self) -> int:
                        return self.v
                    def act(self, a: str) -> int:
                        if a == "inc":
                            self.v += 1
                        return self.v

                with memory_policy_scope("READ_ONLY"):
                    d_res = transfer.drive(
                        _TinyEnv(),
                        ["inc"],
                        is_goal=lambda s: s == 1,
                        budget=4,
                        use_transfer=False,
                    )
                    self.assertTrue(d_res["reached"])
                self.assertFalse(tl_path.exists())
            finally:
                transfer.STATE_PATH = old_tl

            # 3. associative_memory_v1.recall & VerifiedSkillStore under READ_ONLY read without mutating bytes
            amem_path = tmp / "amem.json"
            amem.remember({"fact": "alpha"}, kind="note", tags=("alpha",), path=str(amem_path))
            amem_before = amem_path.read_bytes()
            with memory_policy_scope("READ_ONLY"):
                hits = amem.recall("alpha", k=1, path=str(amem_path))
                self.assertEqual(len(hits), 1)
                self.assertEqual(amem.remember({"fact": "beta"}, path=str(amem_path)), "")
            self.assertEqual(amem_path.read_bytes(), amem_before)

            with memory_policy_scope("OFF"):
                self.assertEqual(amem.recall("alpha", k=1, path=str(amem_path)), [])

            # 4. live_brain_route_admission_v1.solve rejects invalid memory_policy fail-closed
            bad_mp = door.solve({"task_id": "mp-bad", "goal": "check", "memory_policy": "BOGUS"})
            self.assertFalse(bad_mp["pass"])
            self.assertEqual(bad_mp["status"], "FAIL_CLOSED__MEMORY_POLICY_INVALID")

    def test_compound_cst_subtree_narrowing_cross_language_test_suite_and_suspect_line_priority(self) -> None:
        from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle

        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            scope_id = "unit/compound-cst/v1"
            contract = {
                "schema_version": 1,
                "scope_id": scope_id,
                "verification_kind": "TEST_SUITE",
                "dependencies": {},
                "preconditions": {},
            }
            train_dir = tmp / "train_proj"
            train_dir.mkdir()
            (train_dir / "subject.py").write_text("def ok(x, hi):\n    return x <= hi\n", encoding="utf-8")
            (train_dir / "test_subject.py").write_text(
                "import unittest\nfrom subject import ok\n"
                "class T(unittest.TestCase):\n"
                "    def test_ok(self):\n"
                "        self.assertTrue(ok(3, 5))\n"
                "        self.assertFalse(ok(5, 5))\n"
                "        self.assertFalse(ok(6, 5))\n",
                encoding="utf-8",
            )
            store = VerifiedSkillStore(tmp / "compound.sqlite", seed=False)
            cryst = store.crystallize_code_fix(
                before_snippet="def ok(x, hi):\n    return x <= hi\n",
                after_snippet="def ok(x, hi):\n    return x < hi\n",
                language="python",
                contract=contract,
                training_verifier=ProjectTestOracle(
                    train_dir, "subject.py", ["test_subject.py"], scope_id
                ),
            )
            self.assertTrue(cryst["crystallized"])

            # 1. Compound parenthesized operands + outer call/arithmetic wrapper narrowing via real ProjectTestOracle
            from canonical.swe_kernel.skill_verification_contract_v1 import ConfinedLanguageTestOracle

            for idx_c, (target_src, test_body) in enumerate([
                (
                    "def check_bounds(x, hi):\n    return (x + 1) <= (hi - 1)\n",
                    "from subject import check_bounds\n"
                    "class T(unittest.TestCase):\n"
                    "    def test_cb(self):\n"
                    "        self.assertFalse(check_bounds(3, 5))\n"
                    "        self.assertTrue(check_bounds(2, 5))\n",
                ),
                (
                    "def score_flag(x, hi):\n    return int(x <= hi) + 1\n",
                    "from subject import score_flag\n"
                    "class T(unittest.TestCase):\n"
                    "    def test_sf(self):\n"
                    "        self.assertEqual(score_flag(5, 5), 1)\n"
                    "        self.assertEqual(score_flag(4, 5), 2)\n",
                ),
            ]):
                pdir = tmp / f"comp_py_{idx_c}"
                pdir.mkdir()
                (pdir / "subject.py").write_text(target_src, encoding="utf-8")
                (pdir / "test_subject.py").write_text("import unittest\n" + test_body, encoding="utf-8")
                rec = store.recall_and_apply_verified(
                    source_text=target_src,
                    language="python",
                    verifier=ProjectTestOracle(pdir, "subject.py", ["test_subject.py"], scope_id),
                    required_verification_kind="TEST_SUITE",
                    scope_id=scope_id,
                    context={"dependencies": {}, "preconditions": {}},
                    allow_scope_escalation=True,
                )
                self.assertIsNotNone(rec, target_src)

            # 2. Cross-language Python -> JavaScript ESM under real confined `node --test` TEST_SUITE oracle
            js_dir = tmp / "js_proj"
            js_dir.mkdir()
            js_src = "export function withinCap(a, b) {\n  return (a + 1) <= (b - 2);\n}\n"
            (js_dir / "bounds.mjs").write_text(js_src, encoding="utf-8")
            (js_dir / "test_bounds.mjs").write_text(
                "import test from 'node:test';\n"
                "import assert from 'node:assert/strict';\n"
                "import { withinCap } from './bounds.mjs';\n"
                "test('strict upper bound with compound exprs', () => {\n"
                "  assert.equal(withinCap(1, 5), true);\n"
                "  assert.equal(withinCap(2, 5), false);\n"
                "});\n",
                encoding="utf-8",
            )
            js_oracle = ConfinedLanguageTestOracle(js_dir, "bounds.mjs", ["test_bounds.mjs"], scope_id)
            rec_js = store.recall_and_apply_verified(
                source_text=js_src,
                language="javascript",
                verifier=js_oracle,
                required_verification_kind="TEST_SUITE",
                scope_id=scope_id,
                context={"dependencies": {}, "preconditions": {}},
                allow_scope_escalation=True,
            )
            self.assertIsNotNone(rec_js)
            self.assertEqual(rec_js["scope_tier"], "CROSS_LANGUAGE_CST_SKELETON")
            self.assertIn("(a + 1) < (b - 2)", rec_js["patched_source"])

            # Refused when scope_id mismatches recorded contract
            rec_wrong_scope = store.recall_and_apply_verified(
                source_text=js_src,
                language="javascript",
                verifier=ConfinedLanguageTestOracle(js_dir, "bounds.mjs", ["test_bounds.mjs"], "other/scope/v1"),
                required_verification_kind="TEST_SUITE",
                scope_id="other/scope/v1",
                context={"dependencies": {}, "preconditions": {}},
                allow_scope_escalation=True,
            )
            self.assertIsNone(rec_wrong_scope)

            # 3. Fault-localized suspect_lines tries line 6 first (`oracle.calls == 1` instead of scanning lines 2 & 4 first)
            multi_dir = tmp / "multi_proj"
            multi_dir.mkdir()
            multi_src = (
                "def validate(a, b, c):\n"
                "    ok1 = a <= 10\n"
                "    ok2 = b <= 20\n"
                "    if not (ok1 and ok2):\n"
                "        return False\n"
                "    return c <= 30\n"
            )
            (multi_dir / "subject.py").write_text(multi_src, encoding="utf-8")
            (multi_dir / "test_subject.py").write_text(
                "import unittest\nfrom subject import validate\n"
                "class T(unittest.TestCase):\n"
                "    def test_v(self):\n"
                "        self.assertTrue(validate(10, 20, 29))\n"
                "        self.assertFalse(validate(10, 20, 30))\n",
                encoding="utf-8",
            )
            multi_oracle = ProjectTestOracle(multi_dir, "subject.py", ["test_subject.py"], scope_id)
            rec_loc = store.recall_and_apply_verified(
                source_text=multi_src,
                language="python",
                verifier=multi_oracle,
                required_verification_kind="TEST_SUITE",
                scope_id=scope_id,
                context={"dependencies": {}, "preconditions": {}},
                allow_scope_escalation=True,
                suspect_lines=[6],
            )
            self.assertIsNotNone(rec_loc)
            self.assertEqual(multi_oracle.calls, 1)

    def test_staged_broker_non_destructive_isolation_and_creature_behavioral_counterfactuals(self) -> None:
        from canonical.runtime import brokered_workspace_execution_v1 as broker

        if not broker.namespace_broker_available():
            self.skipTest("user/mount namespace confinement unavailable on host")

        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            # 1. Staged non-destructive guarantee: failed check & protected-test tamper NEVER touch live workspace
            ws = base / "staged_ws"
            ws.mkdir()
            orig_calc = "def add(a, b):\n    return a - b\n"
            orig_test = "from calc import add\nassert add(2, 3) == 5\n"
            (ws / "calc.py").write_text(orig_calc, encoding="utf-8")
            (ws / "test_calc.py").write_text(orig_test, encoding="utf-8")

            c = creature_mod.boot(base / "c_staged", identity="staged-creature", life=10.0)
            c.author_board(
                [
                    obligations.Proposal(
                        id="corrupt_attempt",
                        claim="calc.py passes check",
                        source="test",
                        check=lambda w: (w.get("s") or {}).get("k") == "done",
                        value=2.0,
                        cost=1.0,
                    ),
                    obligations.Proposal(
                        id="tamper_test_attempt",
                        claim="tamper protected test",
                        source="test",
                        check=lambda w: (w.get("s") or {}).get("t") == "done",
                        value=1.5,
                        cost=1.0,
                    ),
                ],
                before={"s": {"k": "open", "t": "open"}},
                done={"s": {"k": "done", "t": "done"}},
            )
            perf = creature_mod.confined_verified_perform(
                ws,
                programs={
                    "corrupt_attempt": "from pathlib import Path\nPath('calc.py').write_text('DESTROYED\\n')\n",
                    "tamper_test_attempt": (
                        "from pathlib import Path\n"
                        "Path('calc.py').write_text('def add(a, b): return a + b\\n')\n"
                        "Path('test_calc.py').write_text('assert True\\n')\n"
                    ),
                },
                checks={
                    "corrupt_attempt": lambda stg: "return a + b" in (stg / "calc.py").read_text(),
                    "tamper_test_attempt": lambda _stg: True,
                },
                targets={"corrupt_attempt": "calc.py", "tamper_test_attempt": "calc.py"},
                protected_tests=("test_calc.py",),
            )
            r1 = c.step(perf)
            self.assertFalse(r1["ok"])
            self.assertTrue(r1["live_workspace_untouched"])
            self.assertEqual((ws / "calc.py").read_text(encoding="utf-8"), orig_calc)

            # Park corrupt_attempt's 2nd try, then verify tamper_test_attempt is denied by broker scope check
            c.step(perf)
            r3 = c.step(perf)
            self.assertFalse(r3["ok"])
            self.assertIn("CANDIDATE_SCOPE_DENIED", str(r3["blocked"]))
            self.assertEqual((ws / "calc.py").read_text(encoding="utf-8"), orig_calc)
            self.assertEqual((ws / "test_calc.py").read_text(encoding="utf-8"), orig_test)

            # 2. Mortality triage counterfactual: scarce life (0.10) sheds cost=0.5 repair; ample life (10.0) repairs!
            for label, grant, expect_repaired in [("scarce", 0.10, 0), ("ample", 10.0, 1)]:
                proj = base / f"mort_{label}"
                proj.mkdir()
                (proj / "inc_mod.py").write_text("def inc(x):\n    return x - 1\n", encoding="utf-8")
                (proj / "test_inc_mod.py").write_text(
                    "from inc_mod import inc\ndef test_inc():\n    assert inc(4) == 5\n",
                    encoding="utf-8",
                )
                pulse_out = creature_mod.run_awake_creature_pulse(
                    proj,
                    state_root=base / f"state_{label}",
                    identity=f"creature-{label}",
                    life=grant,
                    ledger_path=base / f"led_{label}.json",
                    skill_store_path=base / f"sk_{label}.sqlite",
                    apply_verified_repairs=True,
                    max_curriculum_lessons=0,
                )
                self.assertEqual(pulse_out["cow_experimentation"]["repaired"], expect_repaired, pulse_out)

            # 3. Standing posture counterfactual: MEASURED takes high-density speculative item first;
            #    CAUTIOUS (burned twice) refuses speculative gamble in favor of real checkable repair!
            clean_ws = base / "posture_ws"
            clean_ws.mkdir()
            (clean_ws / "bug.py").write_text("def add1(x):\n    return x - 1\n", encoding="utf-8")
            (clean_ws / "test_bug.py").write_text(
                "from bug import add1\ndef test_add1():\n    assert add1(2) == 3\n",
                encoding="utf-8",
            )
            open_state = base / "standing_open"
            p_open = creature_mod.run_awake_creature_pulse(
                clean_ws,
                state_root=open_state,
                identity="open-c",
                life=10.0,
                ledger_path=base / "led_open.json",
                skill_store_path=base / "sk_open.sqlite",
                max_curriculum_lessons=0,
                speculative_work=lambda: {"ok": True, "note": "explored"},
                max_steps=1,
            )
            self.assertTrue(str(p_open["creature_steps"][0]["work"]).startswith("awake:speculative:"))

            cautious_state = base / "standing_cautious"
            c_burned = creature_mod.boot(cautious_state, identity="cautious-c", life=10.0)
            c_burned._standing.record(verified=True, correct=False)
            c_burned._standing.record(verified=True, correct=False)
            c_burned._save()
            self.assertFalse(c_burned._standing.will_trade_on_the_unverifiable())

            p_cautious = creature_mod.run_awake_creature_pulse(
                clean_ws,
                state_root=cautious_state,
                identity="cautious-c",
                life=10.0,
                ledger_path=base / "led_cautious.json",
                skill_store_path=base / "sk_cautious.sqlite",
                max_curriculum_lessons=0,
                speculative_work=lambda: {"ok": True, "note": "explored"},
                max_steps=1,
            )
            self.assertTrue(str(p_cautious["creature_steps"][0]["work"]).startswith("awake:cow_repair:"))

    def test_optimal_pillar1_general_cst_algebra_and_auto_discovered_polyglot_cross_scope_transfer(self) -> None:
        from canonical.swe_kernel.skill_verification_contract_v1 import (
            ConfinedLanguageTestOracle,
            ProjectTestOracle,
        )
        from canonical.swe_kernel.tree_sitter_cst_skill_skeleton_v1 import (
            compile_rule_to_cst_skeleton,
            minimize_cst_skeleton_pair,
        )
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import (
            VerifiedSkillStore,
            anti_unify_code_rule,
        )

        for bs, as_ in (
            ("def f(a, b):\n    return max(a, b - 1)\n", "def f(a, b):\n    return max(a, b)\n"),
            ("def g(items, i):\n    return items[i - 1]\n", "def g(items, i):\n    return items[i]\n"),
            ("def h(self):\n    return self.x <= self.hi\n", "def h(self):\n    return self.x < self.hi\n"),
            ("def t(x, a, b):\n    return a if x >= 0 else b\n", "def t(x, a, b):\n    return a if x > 0 else b\n"),
        ):
            sk = compile_rule_to_cst_skeleton(anti_unify_code_rule(bs, as_))
            self.assertIsNotNone(sk)
            assert sk is not None
            mp, mr = minimize_cst_skeleton_pair(sk["pattern_skeleton"], sk["replacement_skeleton"])
            self.assertNotEqual(mp, mr)

        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            py_donor = base / "py_donor"
            py_donor.mkdir()
            b_py = "def in_half_open(i, n):\n    return 0 <= i and i <= n\n"
            a_py = "def in_half_open(i, n):\n    return 0 <= i and i < n\n"
            (py_donor / "bounds.py").write_text(b_py, encoding="utf-8")
            (py_donor / "test_bounds.py").write_text(
                "from bounds import in_half_open\n"
                "def test_bounds():\n"
                "    assert in_half_open(0, 3) is True\n"
                "    assert in_half_open(2, 3) is True\n"
                "    assert in_half_open(3, 3) is False\n",
                encoding="utf-8",
            )
            store = VerifiedSkillStore(base / "skills.sqlite")
            py_oracle = ProjectTestOracle(py_donor, "bounds.py", ["test_bounds.py"], "repo:py_donor")
            crys = store.crystallize_code_fix(
                before_snippet=b_py,
                after_snippet=a_py,
                language="python",
                error_class="AssertionError",
                contract={"schema_version": 1, "scope_id": "repo:py_donor", "verification_kind": "TEST_SUITE"},
                training_verifier=py_oracle,
            )
            self.assertTrue(crys["crystallized"])

            js_target = base / "js_target"
            js_target.mkdir()
            js_bug = "export function checkIdx(idx, length) {\n  return 0 <= idx && idx <= length;\n}\n"
            (js_target / "bounds.mjs").write_text(js_bug, encoding="utf-8")
            (js_target / "bounds.test.mjs").write_text(
                "import assert from 'node:assert/strict';\n"
                "import { checkIdx } from './bounds.mjs';\n"
                "assert.equal(checkIdx(0, 4), true);\n"
                "assert.equal(checkIdx(3, 4), true);\n"
                "assert.equal(checkIdx(4, 4), false);\n",
                encoding="utf-8",
            )
            js_oracle = ConfinedLanguageTestOracle(js_target, "bounds.mjs", ["bounds.test.mjs"], "repo:js_target")
            ctx = {"dependencies": {}, "preconditions": {}}
            self.assertIsNone(
                store.recall_and_apply_verified(
                    source_text=js_bug,
                    language="javascript",
                    verifier=js_oracle,
                    required_verification_kind="TEST_SUITE",
                    scope_id="repo:js_target",
                    context=ctx,
                    allow_cross_scope_transfer=False,
                )
            )
            rec_js = store.recall_and_apply_verified(
                source_text=js_bug,
                language="javascript",
                verifier=js_oracle,
                required_verification_kind="TEST_SUITE",
                scope_id="repo:js_target",
                context=ctx,
                allow_cross_scope_transfer=True,
            )
            self.assertIsNotNone(rec_js)
            assert rec_js is not None
            self.assertIn("< length", rec_js["patched_source"])

    def test_optimal_pillar2_zero_copy_broker_and_zygote_cow_equal_length_screening(self) -> None:
        from canonical.runtime.brokered_workspace_execution_v1 import run_staged_confined_command
        from canonical.swe_kernel.zygote_worker_pool_v1 import screen_python_candidates_cow

        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            ws = base / "ws"
            ws.mkdir()
            (ws / "orig.py").write_text("VAL = 10\n", encoding="utf-8")
            res = run_staged_confined_command(
                ws,
                [sys.executable, "-c", "import orig; assert orig.VAL == 42"],
                publish=False,
                candidate_overrides={"orig.py": "VAL = 42\n"},
            )
            self.assertTrue(res["ok"], res)
            self.assertEqual((ws / "orig.py").read_text(encoding="utf-8"), "VAL = 10\n")

            z_proj = base / "z_proj"
            z_proj.mkdir()
            (z_proj / "calc.py").write_text("def sub1(x):\n    return x - 2\n", encoding="utf-8")
            (z_proj / "test_calc.py").write_text(
                "from calc import sub1\ndef test_sub1():\n    assert sub1(5) == 4\n    assert sub1(1) == 0\n",
                encoding="utf-8",
            )
            # Equal-byte-length candidates exercise `.pyc` same-second (mtime, size) invalidation
            cands = [f"def sub1(x):\n    return x - {k}\n" for k in range(9, 1, -1)] + ["def sub1(x):\n    return x - 1\n"]
            z_res = screen_python_candidates_cow(z_proj, "calc.py", ["test_calc.py"], cands)
            self.assertTrue(z_res["ok"], z_res)
            self.assertEqual(z_res["passing_indices"], [len(cands) - 1])

    def test_optimal_pillar3_content_addressed_board_continuity_parking_and_zero_green_waste(self) -> None:
        from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon

        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            unfix_ws = base / "unfix_ws"
            unfix_ws.mkdir()
            (unfix_ws / "hard.py").write_text("def impossible(x):\n    return x\n", encoding="utf-8")
            (unfix_ws / "test_hard.py").write_text(
                "from hard import impossible\ndef test_m():\n    assert impossible(1) == 2 and impossible(1) == 3\n",
                encoding="utf-8",
            )
            c_state = base / "c_state"
            d1 = AwakeAgencyDaemon(
                workspace_root=unfix_ws,
                ledger_path=str(base / "ign.json"),
                workflow_db_path=base / "wf.sqlite",
                skill_store_path=base / "sk.sqlite",
                r3_state_path=base / "r3.json",
                creature_root=c_state,
                creature_identity="unfix-c",
                creature_life=20.0,
            )
            p1 = d1.pulse(max_curriculum_lessons=0, channels=[])
            p2 = d1.pulse(max_curriculum_lessons=0, channels=[])
            p3 = d1.pulse(max_curriculum_lessons=0, channels=[])
            self.assertEqual(p1["creature"]["life_spent"], 0.5)
            self.assertEqual(p2["creature"]["life_spent"], 1.0)
            self.assertEqual(p3["creature"]["life_spent"], 1.0)
            self.assertEqual(len(d1.creature.parked()), 1)

            d2 = AwakeAgencyDaemon(
                workspace_root=unfix_ws,
                ledger_path=str(base / "ign.json"),
                workflow_db_path=base / "wf.sqlite",
                skill_store_path=base / "sk.sqlite",
                r3_state_path=base / "r3.json",
                creature_root=c_state,
                creature_identity="unfix-c",
                creature_life=20.0,
            )
            p4 = d2.pulse(max_curriculum_lessons=0, channels=[])
            self.assertEqual(p4["creature"]["life_spent"], 1.0)
            self.assertEqual(list(d2.creature.parked()), list(d1.creature.parked()))

    def test_optimal_pillar4_complete_memory_policy_chokepoints_including_macro_ram_cache(self) -> None:
        from canonical.runtime import macro_v1
        from canonical.runtime.live_integrated_brain_v1 import run_raw_goal
        from canonical.runtime.memory_policy_v1 import OFF, READ_ONLY, memory_policy_scope
        from canonical.swe_kernel.forged_binding_and_macro_spine_v1 import (
            lookup_verified_chain_macro,
            record_verified_chain_macro,
        )
        from canonical.swe_kernel.rule_expiry_v1 import audit as expiry_audit, expire_stale, record_taught
        from canonical.swe_kernel.upstream_routing_ledger_v1 import UpstreamRoutingLedger
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            mp_dir = base / "mp"
            mp_dir.mkdir()
            url_db = mp_dir / "routing.sqlite"
            macro_f = mp_dir / "macros.json"
            chain_macro_f = mp_dir / "chain_macros.json"
            expiry_db = mp_dir / "expiry.sqlite"
            store = VerifiedSkillStore(base / "sk.sqlite")
            old_state = macro_v1.STATE
            macro_v1.STATE = macro_f
            try:
                with memory_policy_scope(OFF):
                    ul_off = UpstreamRoutingLedger(url_db)
                    ul_off.record_refusal("compress foo.txt", "bad.cap", "CAPABILITY_DOMAIN_MISMATCH")
                    ul_off.record_verified_route("compress a.txt", "good.cap")
                    self.assertFalse(
                        macro_v1.record(
                            ["extract text from a.txt", "compress a.txt"],
                            [{"capability_id": "c1", "verified": True}, {"capability_id": "c2", "verified": True}],
                        )
                    )
                    self.assertFalse(
                        record_verified_chain_macro(
                            ["extract text from a.txt", "compress a.txt"],
                            [{"capability_id": "c1", "verified": True}, {"capability_id": "c2", "verified": True}],
                            state_path=chain_macro_f,
                        )
                    )
                    self.assertFalse(record_taught(expiry_db, "rule_1")["recorded"])
                self.assertEqual(list(mp_dir.iterdir()), [])

                ul_rw = UpstreamRoutingLedger(url_db)
                ul_rw.record_refusal("compress alpha.txt", "bad.cap", "CAPABILITY_DOMAIN_MISMATCH")
                self.assertTrue(
                    record_verified_chain_macro(
                        ["extract text from a.txt", "compress a.txt"],
                        [{"capability_id": "c1", "verified": True}, {"capability_id": "c2", "verified": True}],
                        state_path=chain_macro_f,
                    )
                )
                record_taught(expiry_db, "rule_1", fingerprint={"python_major_minor": "3.11", "platform": "Linux", "machine": "x86_64"})
                with memory_policy_scope(READ_ONLY):
                    self.assertIn("bad.cap", ul_rw.lookup_shape("compress beta.txt")["disqualified"])
                    self.assertIsNotNone(
                        lookup_verified_chain_macro(["extract text from b.txt", "compress b.txt"], state_path=chain_macro_f)
                    )
                    self.assertEqual(
                        expire_stale(store, expiry_db, now={"python_major_minor": "3.12", "platform": "Linux", "machine": "x86_64"})["expired"],
                        [],
                    )
                with memory_policy_scope(OFF):
                    self.assertEqual(ul_rw.lookup_shape("compress beta.txt")["disqualified"], {})
                    self.assertIsNone(
                        lookup_verified_chain_macro(["extract text from b.txt", "compress b.txt"], state_path=chain_macro_f)
                    )
                    self.assertEqual(expiry_audit(expiry_db)["rules"], [])
            finally:
                macro_v1.STATE = old_state

            bad_mp = run_raw_goal({"task_id": "mp-invalid", "goal": "hello", "memory_policy": "INVALID_POLICY"})
            self.assertFalse(bad_mp["pass"])
            self.assertEqual(bad_mp["status"], "FAIL_CLOSED__MEMORY_POLICY_INVALID")

    def test_optimal_pillar5_general_rule_scope_persistence_and_n2_verified_route_promotion(self) -> None:
        from canonical.swe_kernel.rule_scope_learning_v1 import calibrate_rule_scope
        from canonical.swe_kernel.skill_verification_contract_v1 import ProjectTestOracle
        from canonical.swe_kernel.upstream_routing_ledger_v1 import UpstreamRoutingLedger
        from canonical.swe_kernel.verified_skill_crystallizer_v1 import VerifiedSkillStore

        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            proj = base / "ge_proj"
            proj.mkdir()
            b_ge = "def is_strict_pos(x):\n    return x >= 0\n"
            a_ge = "def is_strict_pos(x):\n    return x > 0\n"
            (proj / "pos.py").write_text(b_ge, encoding="utf-8")
            (proj / "test_pos.py").write_text(
                "from pos import is_strict_pos\n"
                "def test_pos():\n"
                "    assert is_strict_pos(1) is True\n"
                "    assert is_strict_pos(0) is False\n",
                encoding="utf-8",
            )
            store = VerifiedSkillStore(base / "sk.sqlite")
            oracle = ProjectTestOracle(proj, "pos.py", ["test_pos.py"], "repo:ge_proj")
            crys = store.crystallize_code_fix(
                before_snippet=b_ge,
                after_snippet=a_ge,
                language="python",
                error_class="AssertionError",
                contract={"schema_version": 1, "scope_id": "repo:ge_proj", "verification_kind": "TEST_SUITE"},
                training_verifier=oracle,
            )
            self.assertTrue(crys["crystallized"])
            rule = [r for r in store.lookup_rules("python") if r["skill_id"] == crys["skill_id"]][0]
            calibrate_rule_scope(rule, store=store)
            persisted = [r for r in store.lookup_rules("python") if r["skill_id"] == crys["skill_id"]][0]
            self.assertEqual(persisted["learned_scope"], "SCOPE_SEMANTIC")

            ledger = UpstreamRoutingLedger(base / "promo.sqlite")
            r1 = ledger.record_verified_route("Create table sales in db1.sqlite from rows1.json", "sqlite.table.create_from_json_records")
            self.assertFalse(r1["promoted"])
            r_dup = ledger.record_verified_route("Create table sales in db1.sqlite from rows1.json", "sqlite.table.create_from_json_records")
            self.assertFalse(r_dup["promoted"])
            r2 = ledger.record_verified_route("Create table orders in db2.sqlite from rows2.json", "sqlite.table.create_from_json_records")
            self.assertTrue(r2["promoted"])
            self.assertEqual(
                ledger.lookup_shape("Create table users in db3.sqlite from rows3.json")["preferred_capability"],
                "sqlite.table.create_from_json_records",
            )
            inv = ledger.invalidate_preferred_capability("Create table users in db3.sqlite from rows3.json", "sqlite.table.create_from_json_records")
            self.assertTrue(inv["invalidated"])
            self.assertIsNone(ledger.lookup_shape("Create table users in db3.sqlite from rows3.json")["preferred_capability"])


if __name__ == "__main__":
    unittest.main()
