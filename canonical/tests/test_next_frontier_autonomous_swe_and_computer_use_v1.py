#!/usr/bin/env python3
"""End-to-End & Sabotage Verification Suite for the 4-Phase Next-Frontier Upgrade."""
from __future__ import annotations

import json
import pathlib
import secrets
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import unittest
import unittest.mock
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical.runtime import computer_env_v1 as cenv  # noqa: E402
from canonical.runtime import live_brain_route_admission_v1 as door  # noqa: E402
from canonical.runtime.bound_capabilities import git_repository_operate as git_op  # noqa: E402
from canonical.swe_kernel.causal_trace_to_skill_compiler_v1 import (  # noqa: E402
    export_workflow_bundle,
    import_workflow_bundle,
)
from canonical.swe_kernel.closed_loop_autonomous_controller_v1 import solve_or_learn  # noqa: E402
from canonical.swe_kernel.diagnostics_perf_and_design_engine_v1 import detect_race_conditions  # noqa: E402
from canonical.swe_kernel.multistep_repo_closed_loop_solver_v1 import (  # noqa: E402
    _sabotage_control_kills_suite,
    solve_repository_closed_loop,
)
from canonical.swe_kernel.upstream_routing_ledger_v1 import UpstreamRoutingLedger  # noqa: E402


class NextFrontierAutonomousSWEAndComputerUseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_next_frontier_"))
        self.repo_scratch = ROOT / "canonical" / "astra_runtime" / "tmp" / f"nf_{secrets.token_hex(4)}"
        self.repo_scratch.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(self.repo_scratch, ignore_errors=True)

    # ------------------------------------------------------------------ #
    # PHASE 1: Multi-Step Zero-Hint Repo Solver & Live Race Prober
    # ------------------------------------------------------------------ #

    def test_phase1_zero_hint_two_file_coupled_bug_and_door_integration(self) -> None:
        repo_dir = self.repo_scratch / "billing_pkg"
        (repo_dir / "billing").mkdir(parents=True)
        (repo_dir / "tests").mkdir(parents=True)
        (repo_dir / "billing" / "__init__.py").write_text("", encoding="utf-8")
        (repo_dir / "billing" / "discounts.py").write_text(
            "def apply_discount(price: float, disc: float) -> float:\n"
            "    return price + disc\n",
            encoding="utf-8",
        )
        (repo_dir / "billing" / "invoice.py").write_text(
            "from billing.discounts import apply_discount\n\n"
            "def compute_invoice(items: list[float], disc: float) -> float:\n"
            "    total = 0.0\n"
            "    for i in range(len(items) - 1):\n"
            "        total += items[i]\n"
            "    return apply_discount(total, disc)\n",
            encoding="utf-8",
        )
        (repo_dir / "tests" / "test_billing.py").write_text(
            "import unittest\n"
            "from billing.invoice import compute_invoice\n\n"
            "class BillingTests(unittest.TestCase):\n"
            "    def test_single(self):\n"
            "        self.assertEqual(compute_invoice([100.0], 15.0), 85.0)\n"
            "    def test_multi(self):\n"
            "        self.assertEqual(compute_invoice([40.0, 60.0, 20.0], 10.0), 110.0)\n",
            encoding="utf-8",
        )

        # 1. Dry-run (`apply_to_source=False`): NEVER-MUTATE-SOURCE must hold byte-for-byte
        skill_db = self.tmp / "skills.sqlite"
        dry = solve_repository_closed_loop(
            repo_dir, "Fix the billing package so tests pass", apply_to_source=False, skill_db_path=skill_db
        )
        self.assertTrue(dry["ok"], dry)
        self.assertEqual(dry["steps_taken"], 2)
        self.assertTrue(dry["sabotage_control_passed"])
        self.assertEqual(sorted(dry["changed_files"]), ["billing/discounts.py", "billing/invoice.py"])
        self.assertIn("price + disc", (repo_dir / "billing" / "discounts.py").read_text(encoding="utf-8"))

        # 2. Live front-door `door.solve` on a 3-file coupled bug (cross-module TypeError kwarg
        #    mismatch + inverted discount + off-by-one loop) with ZERO `.py` file or symbol hints!
        (repo_dir / "billing" / "tax.py").write_text(
            "def apply_tax(amount: float, tax_rate: float) -> float:\n"
            "    return round(amount * (1.0 + tax_rate), 2)\n",
            encoding="utf-8",
        )
        (repo_dir / "billing" / "invoice.py").write_text(
            "from billing.discounts import apply_discount\n"
            "from billing.tax import apply_tax\n\n"
            "def compute_invoice(items: list[float], disc: float) -> float:\n"
            "    total = 0.0\n"
            "    for i in range(len(items) - 1):\n"
            "        total += items[i]\n"
            "    return apply_tax(apply_discount(total, disc), bad_rate_kw=0.0)\n",
            encoding="utf-8",
        )
        rel_dir = repo_dir.relative_to(ROOT).as_posix()
        live = door.solve(
            {"task_id": "NF-REPO-1", "goal": f"Fix the failing tests in {rel_dir}"}
        )
        self.assertTrue(live.get("pass"), live)
        self.assertEqual(live.get("compiled_capability_id"), "python.software.repair.apply.verified.v1")

        # Independent `unittest` verification in fresh subprocess
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_phase1_sabotage_control_rejects_tautological_suite(self) -> None:
        taut_dir = self.tmp / "taut_repo"
        (taut_dir / "pkg").mkdir(parents=True)
        (taut_dir / "tests").mkdir(parents=True)
        (taut_dir / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (taut_dir / "pkg" / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        # Tautological test never calls `calc.add`!
        (taut_dir / "tests" / "test_noop.py").write_text(
            "import unittest\nclass NoopTest(unittest.TestCase):\n    def test_tautology(self):\n        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        self.assertFalse(_sabotage_control_kills_suite(taut_dir, "pkg/calc.py", "add"))

    def test_phase1_cross_module_keyword_alignment_and_live_race_prober(self) -> None:
        kw_repo = self.tmp / "kw_repo"
        (kw_repo / "orders").mkdir(parents=True)
        (kw_repo / "tests").mkdir(parents=True)
        (kw_repo / "orders" / "__init__.py").write_text("", encoding="utf-8")
        (kw_repo / "orders" / "tax.py").write_text(
            "def add_tax(subtotal: float, tax_rate: float) -> float:\n"
            "    return round(subtotal * (1.0 + tax_rate), 2)\n",
            encoding="utf-8",
        )
        (kw_repo / "orders" / "checkout.py").write_text(
            "from orders.tax import add_tax\n\n"
            "def total_with_tax(subtotal: float) -> float:\n"
            "    return add_tax(subtotal, rate_pct=0.1)\n",
            encoding="utf-8",
        )
        (kw_repo / "tests" / "test_orders.py").write_text(
            "import unittest\nfrom orders.checkout import total_with_tax\n"
            "class OrderTests(unittest.TestCase):\n"
            "    def test_tax(self):\n"
            "        self.assertEqual(total_with_tax(100.0), 110.0)\n",
            encoding="utf-8",
        )
        res = solve_repository_closed_loop(kw_repo, "Repair failing order checkout tests", apply_to_source=True)
        self.assertTrue(res["ok"], res)
        self.assertIn("orders/checkout.py", res["changed_files"])

        # Live thread-schedule race prober: catches real race AND spares pure function
        racy = self.tmp / "racy.py"
        racy.write_text(
            "import time\ncount = 0\ndef bump():\n    global count\n    c = count\n    time.sleep(0)\n    count = c + 1\n",
            encoding="utf-8",
        )
        pure = self.tmp / "pure.py"
        pure.write_text("def area(w: int, h: int) -> int:\n    return w * h\n", encoding="utf-8")
        r_hit = detect_race_conditions(racy)
        r_pure = detect_race_conditions(pure)
        self.assertTrue(r_hit["execution_reproduced"])
        self.assertGreaterEqual(r_hit["race_condition_count"], 1)
        self.assertFalse(r_pure["execution_reproduced"])
        self.assertEqual(r_pure["race_condition_count"], 0)

    # ------------------------------------------------------------------ #
    # PHASE 2: Upstream Routing Ledger & Plumbing-Verified Git Ops
    # ------------------------------------------------------------------ #

    def test_phase2_upstream_routing_ledger_learns_mismatch_and_preserves_honest_refusal(self) -> None:
        ledger = UpstreamRoutingLedger(db_path=self.tmp / "ledger.sqlite")
        candidates = ["writer.wrong.v1", "reader.right.v1"]

        def fake_exec(cap_id: str) -> dict:
            if cap_id == "writer.wrong.v1":
                return {"ok": False, "refusal_code": "READ_ONLY_GOAL_DISPATCHED_TO_WRITER", "mutated_workspace": False}
            return {"ok": True, "answer": "verified_diagnosis"}

        # First call: tries writer.wrong.v1 -> learns selection mismatch -> reroutes in-run to reader.right.v1
        first = ledger.dispatch_with_reroute("Find the deadlock in app/worker.py", candidates, fake_exec)
        self.assertTrue(first["ok"])
        self.assertTrue(first["rerouted_in_run"])
        self.assertEqual(first["selected_capability_id"], "reader.right.v1")

        # Second call on an UNSEEN file path: writer.wrong.v1 is filtered out UPSTREAM (1 attempt only!)
        second = ledger.dispatch_with_reroute("Find the deadlock in core/scheduler.py", candidates, fake_exec)
        self.assertTrue(second["ok"])
        self.assertFalse(second["rerouted_in_run"])
        self.assertEqual(len(second["routing_attempts"]), 1)

        # Sabotage / Honesty Check: BISECT_WITHOUT_A_KNOWN_GOOD_COMMIT MUST NEVER disqualify git.bisect!
        rec = ledger.record_refusal(
            "Bisect the regression in pkg/calc.py",
            "git.history.bisect_regression.v1",
            "BISECT_WITHOUT_A_KNOWN_GOOD_COMMIT",
        )
        self.assertFalse(rec["recorded"])

    def test_phase2_git_repository_operate_branch_cherry_pick_changelog_and_host_guard(self) -> None:
        # Sabotage check: host repository MUST refuse mutating branch creation & cherry_pick
        with self.assertRaises(git_op.GitOperateError) as ctx_b:
            git_op.run({"op": "branch", "branch_name": "forbid-host-branch"}, ROOT)
        self.assertIn("TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY", str(ctx_b.exception))

        with self.assertRaises(git_op.GitOperateError) as ctx_cp:
            git_op.run({"op": "cherry_pick", "rev": "HEAD"}, ROOT)
        self.assertIn("TARGET_NOT_IN_STANDALONE_GIT_REPOSITORY", str(ctx_cp.exception))

        # Standalone repo inside repo_scratch: test branch creation, cherry_pick, and changelog
        sub_repo = self.repo_scratch / "standalone_git"
        sub_repo.mkdir(parents=True)
        rel_repo = sub_repo.relative_to(ROOT).as_posix()
        env = {**__import__("os").environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "t@local",
               "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "t@local"}
        subprocess.run(["git", "init", "-b", "main"], cwd=str(sub_repo), check=True, capture_output=True, env=env)
        (sub_repo / "a.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(["git", "add", "a.py"], cwd=str(sub_repo), check=True, capture_output=True, env=env)
        subprocess.run(["git", "commit", "-m", "initial base"], cwd=str(sub_repo), check=True, capture_output=True, env=env)
        (sub_repo / "b.py").write_text("y = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "b.py"], cwd=str(sub_repo), check=True, capture_output=True, env=env)
        subprocess.run(["git", "commit", "-m", "add hotfix b"], cwd=str(sub_repo), check=True, capture_output=True, env=env)

        cp_res = git_op.run(
            {"op": "cherry_pick", "repo_root": rel_repo, "rev": "HEAD", "branch_name": "release/v1"},
            ROOT,
        )
        self.assertTrue(cp_res["output_verified"])
        self.assertEqual(cp_res["observed_effect"]["branch"], "release/v1")
        self.assertEqual(cp_res["observed_effect"]["subject"], "add hotfix b")

        br_res = git_op.run(
            {"op": "branch", "repo_root": rel_repo, "branch_name": "feature/clean", "checkout": False},
            ROOT,
        )
        self.assertIn("feature/clean", [r["name"] for r in br_res["rows"]])

        cl_res = git_op.run({"op": "changelog", "repo_root": rel_repo, "limit": 5}, ROOT)
        self.assertEqual(cl_res["row_count"], 2)
        self.assertIn("add hotfix b", cl_res["observed_effect"]["changelog_markdown"])

    # ------------------------------------------------------------------ #
    # PHASE 3: Stateful CLI Chains & Table-Free Metamorphic Signatures
    # ------------------------------------------------------------------ #

    def test_phase3_tar_gz_chain_and_table_free_metamorphic_ablation(self) -> None:
        pkg = self.tmp / "my_service"
        pkg.mkdir()
        (pkg / "handler.py").write_text("def handle():\n    return 'ok'\n", encoding="utf-8")

        # Stateless single-step `discover` preserves pinned contract
        self.assertEqual(
            cenv.discover("pack my_service into my_service.tar.gz")["status"],
            "OPEN__FORMAT_NEEDS_A_CHAIN_THIS_CHANNEL_CANNOT_KEEP",
        )
        # Stateful `perform` executes verified 2-stage chain (.tar -> .tar.gz)
        chained = cenv.perform("pack my_service into my_service.tar.gz", cwd=self.tmp)
        self.assertTrue(chained["pass"], chained)
        with tarfile.open(self.tmp / "my_service.tar.gz", "r:gz") as tf:
            self.assertIn("my_service/handler.py", tf.getnames())

        # Constructor-Table Ablation (`probe_bytes -> None`):
        data = self.tmp / "metrics.log"
        # 9 total lines, 4 distinct lines ("k1","k2","k3","k4"), 3 duplicate lines ("k1","k2","k3"), non-adjacent!
        data.write_text("k1 a\nk2 b\nk3 c\nk4 d\nk1 a\nk2 b\nk3 c\nk1 a\nk2 b\n", encoding="utf-8")
        with unittest.mock.patch.object(cenv, "probe_bytes", return_value=None):
            tot = cenv.answer_query("how many lines are in metrics.log", data)
            uniq = cenv.answer_query("how many different lines are in metrics.log", data)
            dup = cenv.answer_query("how many duplicate lines are in metrics.log", data)
        self.assertEqual((tot["pass"], tot.get("answer")), (True, "9"))
        self.assertEqual((uniq["pass"], uniq.get("answer")), (True, "4"))
        self.assertEqual((dup["pass"], dup.get("answer")), (True, "3"))

    # ------------------------------------------------------------------ #
    # PHASE 4: Stateful CookieJar/CSRF HTTP Workflows & Bundle Integrity
    # ------------------------------------------------------------------ #

    def test_phase4_stateful_csrf_cookiejar_workflow_and_tamper_bundle_guard(self) -> None:
        sessions: dict[str, str] = {}
        submissions: list[dict[str, str]] = []

        class _StatefulCSRFApp(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: object) -> None:
                return

            def do_GET(self) -> None:  # noqa: N802
                sid = secrets.token_hex(8)
                csrf = secrets.token_hex(12)
                sessions[sid] = csrf
                html = (
                    "<html><body>"
                    "<form action='/api/update' method='POST'>"
                    f"<input type='hidden' name='csrf_token' value='{csrf}'>"
                    "<label for='em'>Email</label><input id='em' name='email' type='text'>"
                    "</form></body></html>"
                ).encode("utf-8")
                self.send_response(200)
                self.send_header("Set-Cookie", f"sid={sid}; Path=/")
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)

            def do_POST(self) -> None:  # noqa: N802
                cookie_hdr = str(self.headers.get("Cookie") or "")
                sid = ""
                for part in cookie_hdr.split(";"):
                    part = part.strip()
                    if part.startswith("sid="):
                        sid = part[4:]
                raw = self.rfile.read(int(self.headers.get("Content-Length") or "0")).decode("utf-8")
                form = {k: v[0] for k, v in parse_qs(raw).items() if v}
                expected_csrf = sessions.pop(sid, None)  # single-use CSRF token!
                if not expected_csrf or form.get("csrf_token") != expected_csrf:
                    self.send_response(403)
                    self.end_headers()
                    self.wfile.write(b'{"ok": false, "error": "CSRF_OR_COOKIE_INVALID"}')
                    return
                submissions.append(form)
                body = json.dumps({"ok": True, "email": form.get("email")}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        srv = HTTPServer(("127.0.0.1", 0), _StatefulCSRFApp)
        port = srv.server_address[1]
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        wf_db = self.tmp / "wf.sqlite"
        try:
            # 1. Cold call: discovers HTML <form>, negotiates Set-Cookie + single-use CSRF, qualifies on twin!
            r1 = solve_or_learn(
                f"Submit the form at http://127.0.0.1:{port}/profile with email=alice@example.com",
                db_path=wf_db,
            )
            self.assertTrue(r1["pass"], r1)
            self.assertTrue(r1["skill_crystallized"], r1.get("qualification_receipt"))

            # 2. Warm call with a NEW email (must fetch a brand-new single-use CSRF + Set-Cookie in <25 ms!)
            r2 = solve_or_learn(
                f"Submit the form at http://127.0.0.1:{port}/profile with email=bob@example.com",
                db_path=wf_db,
            )
            self.assertTrue(r2["pass"], r2)
            self.assertTrue(r2["from_memory"])
            self.assertEqual([s["email"] for s in submissions], ["alice@example.com", "bob@example.com"])
        finally:
            srv.shutdown()
            srv.server_close()

        # 3. Export bundle & verify tamper-detection negative control!
        bundle_file = self.tmp / "bundle.json"
        exp = export_workflow_bundle(bundle_file, db_path=wf_db)
        self.assertEqual(exp["skill_count"], 1)

        fresh_db = self.tmp / "fresh_wf.sqlite"
        imp_good = import_workflow_bundle(bundle_file, db_path=fresh_db)
        self.assertTrue(imp_good["ok"])
        self.assertEqual(imp_good["accepted"], 1)

        # Sabotage bundle: mutate step URL while keeping old SHA-256 -> MUST BE REFUSED!
        tampered = json.loads(bundle_file.read_text(encoding="utf-8"))
        tampered["skills"][0]["abstract_steps"][0]["url"] = "http://evil.invalid/steal"
        tampered_file = self.tmp / "tampered_bundle.json"
        tampered_file.write_text(json.dumps(tampered), encoding="utf-8")

        sab_db = self.tmp / "sab_wf.sqlite"
        imp_bad = import_workflow_bundle(tampered_file, db_path=sab_db)
        self.assertFalse(imp_bad["ok"])
        self.assertEqual(imp_bad["accepted"], 0)
        self.assertEqual(imp_bad["refused"], 1)
        self.assertEqual(imp_bad["reason"] if "reason" in imp_bad else imp_bad["refusals"][0]["reason"], "TAMPERED_ARTIFACT_SHA256")

    def test_phase1b_src_layout_pytest_multiline_issue_door_solve(self) -> None:
        """Multi-line pasted pytest traceback + src/-layout + duplicate method names repaired via door.solve."""
        from canonical.runtime import live_brain_route_admission_v1 as door

        base_tmp = ROOT / "canonical" / "astra_runtime" / "tmp" / "nf_src_pytest_probe"
        if base_tmp.exists():
            shutil.rmtree(base_tmp)
        try:
            pkg_dir = base_tmp / "src" / "optkit"
            test_dir = base_tmp / "testing"
            pkg_dir.mkdir(parents=True)
            test_dir.mkdir(parents=True)
            (pkg_dir / "__init__.py").write_text("from .core import BaseParam, OptionParam\n", encoding="utf-8")
            (pkg_dir / "core.py").write_text(
                "class BaseParam:\n"
                "    def value_is_missing(self, value):\n"
                "        return value is None\n\n"
                "class OptionParam(BaseParam):\n"
                "    def __init__(self, nargs=1, multiple=False):\n"
                "        self.nargs = nargs\n"
                "        self.multiple = multiple\n"
                "    def value_is_missing(self, value):\n"
                "        if value is None:\n"
                "            return True\n"
                "        if (self.nargs != 1 or self.multiple) or value == ():\n"
                "            return True\n"
                "        return False\n",
                encoding="utf-8",
            )
            (test_dir / "conftest.py").write_text(
                "import pytest\nfrom optkit.core import OptionParam\n"
                "@pytest.fixture\ndef single_opt():\n    return OptionParam(nargs=1, multiple=False)\n",
                encoding="utf-8",
            )
            (test_dir / "test_options.py").write_text(
                "from optkit.core import OptionParam\n"
                "def test_single_present(single_opt):\n"
                "    assert single_opt.value_is_missing('ok') is False\n"
                "def test_multiple_present():\n"
                "    opt = OptionParam(nargs=1, multiple=True)\n"
                "    assert opt.value_is_missing(('a', 'b')) is False\n"
                "def test_multiple_empty():\n"
                "    opt = OptionParam(nargs=1, multiple=True)\n"
                "    assert opt.value_is_missing(()) is True\n",
                encoding="utf-8",
            )
            issue = (
                f"Fix the failing tests in {base_tmp}. The suite reports:\n\n"
                "___________________ test_multiple_present ____________________\n"
                "    def cli(message):\n"
                "        # --message cli flag fixture\n"
                ">       assert opt.value_is_missing(('a', 'b')) is False\n"
                "E       assert True is False\n"
                "=========================== short test summary info ============================\n"
                "FAILED testing/test_options.py::test_multiple_present - assert True is False\n"
                "1 failed, 2 passed in 0.05s\n\n"
                "The fault is in src/optkit/core.py. Restore the behaviour the tests expect."
            )
            verdict = door.solve({"task_id": "NF-SRC-PYTEST-DOOR", "goal": issue})
            self.assertTrue(verdict.get("pass"), verdict)
            repaired = (pkg_dir / "core.py").read_text(encoding="utf-8")
            self.assertIn("if (self.nargs != 1 or self.multiple) and value == ():", repaired)
        finally:
            shutil.rmtree(base_tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
