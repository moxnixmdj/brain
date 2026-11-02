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

            # Second boot on same state_root increments epoch and preserves spent life
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
            self.assertLess(p2["creature"]["life_remaining"], life_after_1)


if __name__ == "__main__":
    unittest.main()
