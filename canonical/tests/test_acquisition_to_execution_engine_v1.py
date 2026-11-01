"""End-to-end verification & sabotage tests for the 4-Phase Acquisition-to-Execution Engine."""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import sqlite3
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from canonical.runtime import curriculum_v1
from canonical.runtime import ignorance_ledger_v1
from canonical.runtime import live_brain_route_admission_v1 as door
from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (
    compile_and_qualify_skill,
    elevate_trace_to_fastest_layer,
    recall_and_execute_workflow,
)
from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import (
    inspect_local_repo_for_goal,
    solve_or_learn,
    study_open_gaps,
)


class AcquisitionToExecutionEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_acq_exec_test_"))
        self.skill_db = self.tmp / "compiled_workflows.sqlite"
        self._old_wf_env = os.environ.get("BRAIN_COMPILED_WORKFLOW_DB")
        os.environ["BRAIN_COMPILED_WORKFLOW_DB"] = str(self.skill_db)

    def tearDown(self) -> None:
        if self._old_wf_env is None:
            os.environ.pop("BRAIN_COMPILED_WORKFLOW_DB", None)
        else:
            os.environ["BRAIN_COMPILED_WORKFLOW_DB"] = self._old_wf_env
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_phase1_speed_elevation_ownership_gate_and_sabotage_rejection(self) -> None:
        db1, db2, db3, db4, db_fake = (
            self.tmp / "a.sqlite",
            self.tmp / "b.sqlite",
            self.tmp / "c.sqlite",
            self.tmp / "d.sqlite",
            self.tmp / "fake.sqlite",
        )
        for p in (db1, db2, db3, db4, db_fake):
            con = sqlite3.connect(str(p))
            con.execute("CREATE TABLE flags (name TEXT PRIMARY KEY, enabled INTEGER)")
            con.execute("INSERT INTO flags VALUES ('dark_mode', 0), ('beta_search', 0), ('turbo_mode', 0)")
            con.commit()
            con.close()

        noisy_trace = [
            {"kind": "pixel_click", "x": 320, "y": 180},
            {"kind": "ui_type", "text": "dark_mode"},
            {
                "kind": "sqlite_query",
                "db_path": str(db1),
                "sql": "UPDATE flags SET enabled = 1 WHERE name = ?",
                "params": ["dark_mode"],
            },
        ]
        elevated = elevate_trace_to_fastest_layer(noisy_trace)
        self.assertEqual(elevated["elevated_step_count"], 1)
        self.assertEqual(elevated["dominant_layer"], "sqlite_exec")
        self.assertTrue(elevated["elevated_from_ui"])

        # Identical training instance as held-out MUST fail closed
        same_inst = compile_and_qualify_skill(
            goal=f"Enable feature flag dark_mode in database {db1}",
            trace=noisy_trace,
            postcondition={
                "kind": "sqlite_row_exists",
                "db_path": str(db1),
                "sql": "SELECT enabled FROM flags WHERE name = 'dark_mode' AND enabled = 1",
            },
            heldout_goal=f"Enable feature flag dark_mode in database {db1}",
            db_path=self.skill_db,
        )
        self.assertFalse(same_inst["pass"])
        self.assertEqual(same_inst["status"], "FAIL_CLOSED__HELDOUT_IDENTICAL_TO_TRAINING_INSTANCE")

        # Tautological postcondition passing under sabotage MUST fail closed at ownership gate
        fake_skill = compile_and_qualify_skill(
            goal=f"Enable feature flag dark_mode in database {db1}",
            trace=noisy_trace,
            postcondition={"kind": "sqlite_row_exists", "db_path": str(db1), "sql": "SELECT 1"},
            heldout_goal=f"Enable feature flag beta_search in database {db_fake}",
            sabotaged_postcondition={"kind": "sqlite_row_exists", "db_path": str(db_fake), "sql": "SELECT 1"},
            db_path=self.skill_db,
        )
        self.assertFalse(fake_skill["pass"])
        self.assertIn("OWNERSHIP_GATE_REJECTED", fake_skill["status"])

        # Genuine perturbed held-out + sabotaged negative control qualifies cleanly
        qualified = compile_and_qualify_skill(
            goal=f"Enable feature flag dark_mode in database {db1}",
            trace=noisy_trace,
            postcondition={
                "kind": "sqlite_row_exists",
                "db_path": str(db1),
                "sql": "SELECT enabled FROM flags WHERE name = 'dark_mode' AND enabled = 1",
            },
            heldout_goal=f"Enable feature flag beta_search in database {db2}",
            heldout_postcondition={
                "kind": "sqlite_row_exists",
                "db_path": str(db2),
                "sql": "SELECT enabled FROM flags WHERE name = 'beta_search' AND enabled = 1",
            },
            sabotaged_postcondition={
                "kind": "sqlite_row_exists",
                "db_path": str(db2),
                "sql": "SELECT enabled FROM flags WHERE name = 'missing_flag' AND enabled = 1",
            },
            db_path=self.skill_db,
        )
        self.assertTrue(qualified["pass"], qualified)

        # Recall on 3rd untouched database via Tier 0A solve_or_learn (<25 ms!) + front-door solve()
        t0 = time.perf_counter()
        fast_recalled = solve_or_learn(
            f"Enable feature flag turbo_mode in database {db3}",
            db_path=self.skill_db,
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(fast_recalled["pass"], fast_recalled)
        self.assertTrue(fast_recalled.get("from_memory"))
        self.assertLess(elapsed_ms, 25.0)
        con = sqlite3.connect(str(db3))
        val = con.execute("SELECT enabled FROM flags WHERE name = 'turbo_mode'").fetchone()[0]
        con.close()
        self.assertEqual(val, 1)

        door_recalled = door.solve(
            {"task_id": "wf-recall-door", "goal": f"Enable feature flag turbo_mode in database {db4}"}
        )
        self.assertTrue(door_recalled["pass"], door_recalled)
        self.assertTrue(door_recalled.get("from_memory"))

    def test_phase2_semantic_web_form_to_direct_http_generalization(self) -> None:
        calls: list[tuple[str, dict[str, str]]] = []

        class _App(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
                return

            def do_GET(self) -> None:  # noqa: N802
                html = (
                    b"<html><body><form action='/api/deploy' method='POST'>"
                    b"<input name='service' type='text'/>"
                    b"<input name='env' type='text'/>"
                    b"<input name='token' type='hidden' value='verified-hidden'/>"
                    b"</form></body></html>"
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)

            def do_POST(self) -> None:  # noqa: N802
                ln = int(self.headers.get("Content-Length") or "0")
                parsed = {k: v[0] for k, v in parse_qs(self.rfile.read(ln).decode("utf-8")).items()}
                calls.append((self.path, parsed))
                ok = self.path == "/api/deploy" and parsed.get("token") == "verified-hidden" and bool(parsed.get("service"))
                out = json.dumps({"ok": ok, "service": parsed.get("service")}).encode("utf-8")
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

        srv1 = HTTPServer(("127.0.0.1", 0), _App)
        srv2 = HTTPServer(("127.0.0.1", 0), _App)
        p1, p2 = srv1.server_address[1], srv2.server_address[1]
        threading.Thread(target=srv1.serve_forever, daemon=True).start()
        threading.Thread(target=srv2.serve_forever, daemon=True).start()
        try:
            first = solve_or_learn(
                f"Submit service=billing_api and env=staging to http://127.0.0.1:{p1}/console",
                db_path=self.skill_db,
            )
            self.assertTrue(first["pass"], first)
            self.assertTrue(first["skill_crystallized"], first)

            t1 = time.perf_counter()
            second = solve_or_learn(
                f"Submit service=auth_gateway and env=prod to http://127.0.0.1:{p2}/console",
                db_path=self.skill_db,
            )
            ms2 = (time.perf_counter() - t1) * 1000.0
            self.assertTrue(second["pass"], second)
            self.assertTrue(second["from_memory"], second)
            self.assertEqual(second["fastest_layer"], "http_request")
            self.assertLess(ms2, 50.0)
            self.assertEqual(
                calls[-1],
                ("/api/deploy", {"service": "auth_gateway", "env": "prod", "token": "verified-hidden"}),
            )
        finally:
            srv1.shutdown()
            srv1.server_close()
            srv2.shutdown()
            srv2.server_close()

    def test_phase2_live_runtime_assertion_trace_synthesis_repairs_dynamic_spec(self) -> None:
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        rt_base = repo_root / "canonical" / "astra_runtime"
        rt_base.mkdir(parents=True, exist_ok=True)
        proj = pathlib.Path(tempfile.mkdtemp(prefix="swe_dyn_synth_", dir=str(rt_base)))
        try:
            (proj / "pkg").mkdir()
            (proj / "pkg" / "__init__.py").write_text("", encoding="utf-8")
            (proj / "pkg" / "quota.py").write_text(
                "def calc_quota(n: int) -> int:\n    return n\n",
                encoding="utf-8",
            )
            (proj / "tests").mkdir()
            # Expected values exist only dynamically at runtime (`(v << 1) + 5`), not as static AST pairs!
            (proj / "tests" / "test_quota.py").write_text(
                "from pkg.quota import calc_quota\n\n"
                "def test_quota_loop():\n"
                "    for v in (0, 2, 5, 9):\n"
                "        want = (v << 1) + 5\n"
                "        assert calc_quota(v) == want\n",
                encoding="utf-8",
            )
            rel_proj = proj.relative_to(repo_root).as_posix()
            rel_out = (proj / "report.json").relative_to(repo_root).as_posix()
            res = door.solve(
                {
                    "task_id": "dyn-trace-repair",
                    "goal": f"Fix the failing tests in {rel_proj} and write the repair report to {rel_out}",
                }
            )
            self.assertTrue(res["pass"], res)
            rep = json.loads((proj / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(rep.get("repair_mode"), "live_trace_observational_synthesis")
        finally:
            shutil.rmtree(proj, ignore_errors=True)

    def test_phase2_whitebox_introspector_and_honest_refusal_preservation(self) -> None:
        wb = inspect_local_repo_for_goal("elevate causal trace to fastest layer", "canonical/swe_kernel")
        self.assertTrue(wb["ok"], wb)
        self.assertEqual(wb["top_candidates"][0]["name"], "elevate_trace_to_fastest_layer")

        # Law-pinned honest refusal MUST never be bypassed by Tier 1 / Tier 2 escalation
        refusal = solve_or_learn(
            "Find the race condition in canonical/swe_kernel/__init__.py",
            db_path=self.skill_db,
        )
        self.assertFalse(refusal["pass"])
        self.assertEqual(refusal["tier_used"], "tier0_honest_contract_refusal")

    def test_phase3_cli_pipeline_crystallization_and_tier3_curriculum_closure(self) -> None:
        cli_dir = self.tmp / "cli"
        cli_dir.mkdir()
        rows1 = [f"svc-{i}" for i in range(8)] + [f"svc-{i}" for i in range(8)]
        (cli_dir / "data.txt").write_text("\n".join(rows1) + "\n", encoding="utf-8")

        r1 = solve_or_learn("how many unique lines in data.txt", cwd=cli_dir, db_path=self.skill_db)
        self.assertTrue(r1["pass"], r1)
        self.assertEqual(str(r1["answer"]).strip(), "8")
        self.assertTrue(r1["skill_crystallized"], r1)

        rows2 = [f"pod-{i}" for i in range(13)] + [f"pod-{i}" for i in range(13)]
        (cli_dir / "pods.txt").write_text("\n".join(rows2) + "\n", encoding="utf-8")
        t0 = time.perf_counter()
        r2 = solve_or_learn("how many unique lines in pods.txt", cwd=cli_dir, db_path=self.skill_db)
        ms = (time.perf_counter() - t0) * 1000.0
        self.assertTrue(r2["pass"], r2)
        self.assertTrue(r2["from_memory"], r2)
        self.assertEqual(str(r2["answer"]).strip(), "13")
        self.assertLess(ms, 80.0)


if __name__ == "__main__":
    unittest.main()
