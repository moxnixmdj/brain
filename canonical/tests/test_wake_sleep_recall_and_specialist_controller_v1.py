"""Regression tests for wake/sleep latency in Tier 0 skill recall and structured specialist dispatch in `solve_or_learn`."""
from __future__ import annotations

import json
import math
import pathlib
import shutil
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from unittest import mock
from urllib.parse import parse_qs

from canonical.runtime import brain_unified_model_v1 as bum
from canonical.swe_kernel.autonomous_awake_loop_v1 import AwakeAgencyDaemon
from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn
from canonical.swe_kernel.concept_library_v1 import CompoundingConceptLibrary
from canonical.swe_kernel.meta_circular_organ_graph_v1 import POLICY, MetaCircularOrganGraph


class WakeSleepRecallAndSpecialistControllerTests(unittest.TestCase):
    def test_unconfined_prose_goal_fails_closed_at_confinement_boundary(self) -> None:
        """Unconfined host Python execution (`Add two numbers in Python`) must fail closed at the boundary."""
        res = solve_or_learn("Add two numbers in Python", learn=True, record_open_gap=False)
        self.assertIs(res.get("pass"), False)
        self.assertEqual(
            res.get("status"),
            "FAIL_CLOSED__COMPUTER_EXECUTION_REQUIRES_ADMITTED_CONFINEMENT",
        )
        self.assertEqual(
            res.get("tier_used"),
            "tier2_unconfined_documentation_execution_refused",
        )

    def test_tier0_compiled_http_skill_recall_stays_under_50ms_across_even_wake_episodes(self) -> None:
        """Consecutive Tier 0 compiled workflow recalls with `learn=True` must not block for 8.85s in `record_wake_episode`."""
        calls: list[tuple[str, dict[str, str]]] = []

        class _DeployConsoleApp(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
                return

            def do_GET(self) -> None:  # noqa: N802
                html = (
                    b"<html><body>"
                    b"<form action='/api/deploy' method='POST'>"
                    b"<input type='hidden' name='token' value='verified-hidden'/>"
                    b"<input type='text' name='service'/>"
                    b"<select name='env'><option value='staging'>staging</option><option value='prod'>prod</option></select>"
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

        srv1 = HTTPServer(("127.0.0.1", 0), _DeployConsoleApp)
        srv2 = HTTPServer(("127.0.0.1", 0), _DeployConsoleApp)
        p1, p2 = srv1.server_address[1], srv2.server_address[1]
        threading.Thread(target=srv1.serve_forever, daemon=True).start()
        threading.Thread(target=srv2.serve_forever, daemon=True).start()
        try:
            with tempfile.TemporaryDirectory() as td:
                db_path = pathlib.Path(td) / "workflows.sqlite"

                # Call 1: Tier 2 semantic web form discovery + twin server ownership gate qualification
                r1 = solve_or_learn(
                    f"Submit service=billing_api and env=staging to http://127.0.0.1:{p1}/console",
                    db_path=db_path,
                    learn=True,
                    record_open_gap=False,
                )
                self.assertIs(r1.get("pass"), True)
                self.assertIs(r1.get("skill_crystallized"), True)

                # Calls 2, 3, 4: Tier 0 compiled skill recall across even/odd wake transitions
                for svc, env_name in (("auth_gateway", "prod"), ("ledger_core", "staging"), ("search_idx", "prod")):
                    t0 = time.perf_counter()
                    r_recall = solve_or_learn(
                        f"Submit service={svc} and env={env_name} to http://127.0.0.1:{p2}/console",
                        db_path=db_path,
                        learn=True,
                        record_open_gap=False,
                    )
                    wall_ms = (time.perf_counter() - t0) * 1000.0
                    self.assertIs(r_recall.get("pass"), True)
                    self.assertEqual(r_recall.get("tier_used"), "tier0_compiled_skill_recall")
                    self.assertIs(r_recall.get("from_memory"), True)
                    self.assertEqual(r_recall.get("fastest_layer"), "http_request")
                    self.assertLess(float(r_recall.get("elapsed_ms", 999.0)), 50.0)
                    self.assertLess(wall_ms, 50.0)
                    self.assertEqual(
                        calls[-1],
                        ("/api/deploy", {"service": svc, "env": env_name, "token": "verified-hidden"}),
                    )
        finally:
            srv1.shutdown()
            srv1.server_close()
            srv2.shutdown()
            srv2.server_close()

    def test_organ_graph_gates_synchronous_policy_evolution_on_contrasting_signal(self) -> None:
        """Uniform wake transitions must be fast (<50ms in-memory) and only trigger policy evolution when contrasting signal exists."""
        graph = MetaCircularOrganGraph(state_path=None)
        # Seed 2 bootstrap transitions and evolve an incumbent policy organ
        graph.record_transition(action_id="act_a", cost=0.01, failed=False, value=1.0)
        graph.record_transition(action_id="act_a", cost=0.01, failed=False, value=1.0)
        self.assertIsNotNone(graph.get_primary(POLICY, "policy::instrumental_q"))

        with mock.patch.object(
            graph,
            "evolve_policy_from_traces",
            wraps=graph.evolve_policy_from_traces,
        ) as spy_evolve:
            t0 = time.perf_counter()
            for _idx in range(4):
                graph.record_transition(
                    action_id="tier0_compiled_skill_recall",
                    cost=0.002,
                    failed=False,
                    value=1.0,
                )
            uniform_ms = (time.perf_counter() - t0) * 1000.0
            self.assertLess(uniform_ms, 50.0)
            self.assertEqual(spy_evolve.call_count, 0)

            # Recording a contrasting failure outcome on an even transition triggers evolution
            graph.record_transition(
                action_id="tier2_bad_route",
                cost=0.025,
                failed=True,
                value=0.0,
            )
            graph.record_transition(
                action_id="tier0_compiled_skill_recall",
                cost=0.002,
                failed=False,
                value=1.0,
            )
            self.assertEqual(spy_evolve.call_count, 1)

    def test_concept_library_sleep_abstract_synthesizes_first_and_higher_order_concepts_fast(self) -> None:
        """`CompoundingConceptLibrary.sleep_abstract` must abstract Stitch + Plotkin LGG concepts in <2.0s."""
        with tempfile.TemporaryDirectory() as td:
            lib = CompoundingConceptLibrary(pathlib.Path(td) / "concepts.json")
            progs = [
                "def sum_vals(xs, z):\n    acc = z\n    for x in xs:\n        acc = acc + x\n    return acc\n",
                "def prod_vals(ys, one):\n    out = one\n    for y in ys:\n        out = out * y\n    return out\n",
                "def norm_a(val, lo, hi):\n    return (min(max(val, lo), hi) - lo) / (hi - lo) if hi > lo else 0.0\n",
                "def norm_b(u, a, b):\n    return 2.0 + ((min(max(u, a), b) - a) / (b - a) if b > a else 0.0)\n",
            ]
            t0 = time.perf_counter()
            res = lib.sleep_abstract(progs)
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            self.assertLess(elapsed_ms, 2000.0)
            self.assertGreaterEqual(int(res.get("admitted_count", 0)), 2)
            self.assertTrue(any(c.is_higher_order for c in lib.concepts()))

    def test_structured_specialists_and_byte_verified_bridge_dispatch_cleanly(self) -> None:
        """Structured specialist problems (`polytope_problem`, `scientific_discovery_problem`, `byte_verified_bridge`) must dispatch without falling through."""
        # 1. Exact rational polytope specialist
        poly_res = solve_or_learn(
            {
                "task_id": "poly-1",
                "goal": "Bound linear parameter polytope",
                "polytope_problem": {
                    "feature_semantics_bound": True,
                    "observation_intervals_sound": True,
                    "observations": [
                        {"features": ["1", "0"], "output_interval": ["9/10", "11/10"]},
                        {"features": ["1", "1"], "output_interval": ["29/10", "31/10"]},
                    ],
                    "queries": [{"query_id": "q_x2", "features": ["1", "2"]}],
                },
            },
            learn=False,
            record_open_gap=False,
        )
        self.assertIs(poly_res.get("pass"), True)
        self.assertEqual(poly_res.get("tier_used"), "tier0_exact_linear_parameter_polytope")
        self.assertEqual(
            poly_res["polytope"]["query_predictions"][0]["prediction_interval"],
            ["47/10", "53/10"],
        )

        # 2. Scientific discovery specialist via `UnifiedModel.act_or_learn` (0C specialist door -> `solve_or_learn`)
        with tempfile.TemporaryDirectory() as td:
            model = bum.open_model()
            sci_res = model.act_or_learn(
                "Discover sparse trigonometric law from observations",
                inputs={
                    "scientific_discovery_problem": {
                        "rows": [
                            {"angle": x, "out": -0.5 + 2.1 * math.sin(x)}
                            for x in (-1.0, -0.5, -0.1, 0.3, 0.7, 1.1)
                        ],
                        "target": "out",
                        "max_depth": 1,
                    }
                },
                cwd=td,
            )
            self.assertIs(sci_res.get("pass"), True)
            self.assertEqual(sci_res.get("tier_used"), "tier2_symbolic_or_scientific_law_discovery")
            self.assertIn(
                "sin(",
                str(sci_res["autonomous_result"]["scientific_discovery"]["best_symbolic_expression"]),
            )

        # 3. Byte-verified two-step capability bridge populates `round0_precheck` without NameError
        repo_root = pathlib.Path(__file__).resolve().parents[2]
        scratch = repo_root / "canonical" / "astra_runtime" / "tmp" / "pytest_wake_sleep_bridge"
        shutil.rmtree(scratch, ignore_errors=True)
        scratch.mkdir(parents=True, exist_ok=True)
        try:
            json_rel = (scratch / "records.json").relative_to(repo_root).as_posix()
            db_rel = (scratch / "records.sqlite").relative_to(repo_root).as_posix()
            spec_payload = json.dumps([{"id": 1, "name": "alpha"}, {"id": 2, "name": "beta"}])
            bridge_res = solve_or_learn(
                {
                    "task_id": "bridge-1",
                    "goal": f"Write JSON records to {json_rel} and load them into SQLite {db_rel}",
                    "byte_verified_bridge": {
                        "producer_cid": "json.file.write",
                        "producer_args": {"output_path": json_rel, "spec": spec_payload},
                        "artifact_type": "json",
                        "consumer_cid": "sqlite.table.create_from_json_records",
                        "consumer_artifact_arg": "json_path",
                        "consumer_extra_args": {
                            "goal": f"Create table named items in {db_rel} from {json_rel} with columns id, name",
                            "output_path": db_rel,
                        },
                    },
                },
                cwd=repo_root,
                learn=False,
                record_open_gap=False,
            )
            self.assertIs(bridge_res.get("pass"), True)
            self.assertEqual(bridge_res.get("tier_used"), "tier1_byte_verified_bridge")
            self.assertIsInstance(bridge_res.get("round0_precheck"), dict)
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def test_awake_daemon_explicit_r3_state_path_reports_verified_fixed_point_status(self) -> None:
        """`AwakeAgencyDaemon.pulse()` with explicit `r3_state_path` must report `VERIFIED_R3_FIXED_POINT_REACHED` when already converged."""
        with tempfile.TemporaryDirectory() as td:
            base = pathlib.Path(td)
            ws = base / "ws"
            ws.mkdir()
            (ws / "mod.py").write_text("def inc(x):\n    return x + 1\n", encoding="utf-8")
            (ws / "test_mod.py").write_text(
                "from mod import inc\ndef test_inc():\n    assert inc(2) == 3\n",
                encoding="utf-8",
            )
            st = base / "state"
            st.mkdir()
            daemon = AwakeAgencyDaemon(
                ws,
                ledger_path=st / "ledger.json",
                skill_store_path=st / "skills.db",
                workflow_db_path=st / "workflows.db",
                journal_dir=st / "journal",
                r3_state_path=st / "r3_state.json",
            )
            snap = daemon.pulse(max_curriculum_lessons=0)
            self.assertEqual(snap["k3_external_llm_calls"], 0)
            self.assertIs(snap["r3_fixed_point"]["fixed_point"], True)
            self.assertEqual(snap["r3_fixed_point"]["status"], "VERIFIED_R3_FIXED_POINT_REACHED")


if __name__ == "__main__":
    unittest.main()
