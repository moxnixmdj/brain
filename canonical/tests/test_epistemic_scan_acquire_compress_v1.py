"""Permanent verification suite for Iter 75:
  1. Goal-Directed Scan -> Epistemic-Gap-Diff -> On-Demand Acquire -> Leap-4 Mental Rollout -> L1->L2/L3 Compression
     on LIVE arbitrary unseen environments (gzip-disguised files, SQLite FK DB, live HTTP OpenAPI+Auth server,
     20 distractor files, 0-gap cross-environment transfer, instant O(1) deletion forgetting).
  2. OOP @property + Depth-2 Nested Runtime Introspection + Direct SUT Grounding + Existing-Branch
     Disjunctive OE-SyGuS Validation Guard Synthesis.

Zero external model calls (`model_calls == 0`), zero stored weights (`parameters_stored == 0`).
"""
from __future__ import annotations

import gzip
import http.server
import json
import pathlib
import sqlite3
import sys
import tempfile
import threading

from canonical.runtime import causal_angelic_swe_engine_v1 as PY_SWE
from canonical.runtime import epistemic_scan_acquire_compress_v1 as SAC


def _start_openapi_server(endpoint_path: str) -> tuple[http.server.ThreadingHTTPServer, str]:
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/auth/token": {"post": {"summary": "Issue Bearer token"}},
            endpoint_path: {
                "post": {
                    "summary": "Submit aggregated payload",
                    "security": [{"bearerAuth": []}],
                }
            },
        },
    }

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/openapi.json":
                body = json.dumps(spec).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(401)
            self.end_headers()

        def log_message(self, fmt: str, *args: object) -> None:
            return

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{port}"


def _make_sqlite_db(path: pathlib.Path, parent_tbl: str, child_tbl: str) -> None:
    conn = sqlite3.connect(str(path))
    conn.execute(f"CREATE TABLE {parent_tbl} (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute(
        f"CREATE TABLE {child_tbl} (id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES {parent_tbl}(id), amount INTEGER)"
    )
    conn.execute(f"INSERT INTO {parent_tbl} VALUES (1, 'acme')")
    conn.execute(f"INSERT INTO {child_tbl} VALUES (10, 1, 250)")
    conn.commit()
    conn.close()


def test_01_goal_directed_scan_acquire_mental_verify_compress_and_zero_gap_transfer() -> None:
    """Full arbitrary-environment loop: Env A (cold + 20 distractors) -> compress L2/L3 -> Env B (0-gap transfer) -> delete."""
    srv_a, url_a = _start_openapi_server("/v1/orders")
    srv_b, url_b = _start_openapi_server("/v2/invoices")
    try:
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            # --- ENVIRONMENT A (completely unseen, 20 distractor files, gzip disguised as .csv, SQLite FK DB, live HTTP) ---
            env_a = root / "env_alpha"
            env_a.mkdir()
            for i in range(20):
                (env_a / f"distractor_log_{i}.txt").write_text(f"unrelated noise {i}\n", encoding="utf-8")
            # Hidden gzip disguised with .csv extension!
            (env_a / "orders_feed.csv").write_bytes(gzip.compress(b"id,total\n1,100\n2,200\n"))
            _make_sqlite_db(env_a / "orders_warehouse.db", "customers", "orders")

            mem = SAC.new_governed_memory()
            assert mem["parameters_stored"] == 0

            # 1. SCAN Env A
            man_a = SAC.scan_environment(env_a, http_base_url=url_a)
            assert man_a["files"]["orders_feed.csv"]["format"] == "gzip"
            assert man_a["files"]["orders_feed.csv"]["compressed"] is True
            assert "orders_warehouse.db" in man_a["sqlite_dbs"]
            assert len(man_a["sqlite_dbs"]["orders_warehouse.db"]["foreign_keys"]) == 1

            # 2. GOAL-DIRECTED EPISTEMIC FRONTIER (must ignore all 20 distractor files!)
            goal_a = "Read orders feed, query orders database totals, post summary to orders API, and save output"
            front_a = SAC.compute_epistemic_frontier(goal_a, man_a, mem)
            assert len(front_a["ignored_irrelevant_files"]) == 20
            assert set(front_a["relevant_files"]) == {"orders_feed.csv", "orders_warehouse.db"}
            gap_keys_a = {g["key"] for g in front_a["unknown_goal_relevant_gaps"]}
            assert gap_keys_a == {"format:gzip", "interface:sqlite_fk_schema", "interface:http_openapi_auth"}

            # 3. ON-DEMAND ACQUISITION (ONLY the 3 missing goal-relevant gaps!)
            acq_a = SAC.acquire_missing_knowledge(front_a, mem, probe_live=True)
            assert acq_a["acquired_count"] == 3
            assert acq_a["model_calls"] == 0 and acq_a["parameters_stored"] == 0
            assert mem["l3_interface_facts"]["interface:http_openapi_auth"]["auth_endpoint"] == "/auth/token"

            # 4. PRE-EXECUTION LEAP 4 MENTAL SIMULATION & AUTO-REPAIR
            plan_a = SAC.synthesize_and_mentally_verify_plan(goal_a, man_a, front_a, mem)
            sim_a = plan_a["simulation"]
            assert sim_a["safe_to_execute"] is True, sim_a
            assert sim_a["repaired"] is True
            kinds_a = [s["kind"] for s in sim_a["final_plan"]]
            assert "decompress_file" in kinds_a
            assert "http_auth" in kinds_a
            assert "checkpoint" in kinds_a

            # 5. GOVERNED L1 -> L2 COMPRESSION (zero concrete filenames/ports/hostnames leaked into L2!)
            comp = SAC.compress_l1_to_governed_memory(
                sim_a["final_plan"],
                env_modality_signature=front_a["env_modality_signature"],
                slot_bindings=plan_a["slot_bindings"],
                governed_memory=mem,
            )
            assert comp["admitted"] is True
            l2_json = json.dumps(comp["skill"])
            assert "orders_feed.csv" not in l2_json
            assert "orders_warehouse.db" not in l2_json
            assert "/v1/orders" not in l2_json
            assert "127.0.0.1" not in l2_json
            assert comp["skill"]["parameters_stored"] == 0

            # Persist & reload external JSON memory
            mem_path = root / "governed_mem.json"
            SAC.save_governed_memory(mem, mem_path)
            mem_reloaded = SAC.load_governed_memory(mem_path)

            # --- ENVIRONMENT B (brand-new dir, different filenames, different DB tables, different HTTP port & endpoint) ---
            env_b = root / "env_beta"
            env_b.mkdir()
            for i in range(15):
                (env_b / f"readme_junk_{i}.txt").write_text("junk\n", encoding="utf-8")
            (env_b / "invoices_2026.csv").write_bytes(gzip.compress(b"id,amt\n9,777\n"))
            _make_sqlite_db(env_b / "invoices_ledger.db", "clients", "invoices")

            man_b = SAC.scan_environment(env_b, http_base_url=url_b)
            goal_b = "Read invoices feed, query invoices database, send to invoices API, and save result"
            front_b = SAC.compute_epistemic_frontier(goal_b, man_b, mem_reloaded)

            # 0-GAP INSTANT TRANSFER: all 3 L3 interface specs AND the L2 abstract skill recalled in O(1)!
            assert len(front_b["ignored_irrelevant_files"]) == 15
            assert front_b["unknown_goal_relevant_gaps"] == []
            assert len(front_b["known_recalled_l2"]) == 1
            assert front_b["known_recalled_l2"][0]["skill_id"] == comp["skill_id"]

            # Plan instantiated onto Env B's concrete filenames with ZERO repairs needed!
            plan_b = SAC.synthesize_and_mentally_verify_plan(goal_b, man_b, front_b, mem_reloaded)
            assert plan_b["used_l2_skill_id"] == comp["skill_id"]
            assert plan_b["simulation"]["safe_to_execute"] is True
            assert plan_b["simulation"]["repaired"] is False
            final_b_str = json.dumps(plan_b["simulation"]["final_plan"])
            assert "invoices_2026.csv" in final_b_str
            assert "invoices_ledger.db" in final_b_str

            # 6. INSTANT O(1) DELETION FORGETTING (no retraining!)
            assert SAC.delete_l2_skill(mem_reloaded, comp["skill_id"]) is True
            assert SAC.delete_l3_fact(mem_reloaded, "format:gzip") is True
            front_after_del = SAC.compute_epistemic_frontier(goal_b, man_b, mem_reloaded)
            assert front_after_del["known_recalled_l2"] == []
            assert any(g["key"] == "format:gzip" for g in front_after_del["unknown_goal_relevant_gaps"])
    finally:
        srv_a.shutdown()
        srv_b.shutdown()


def test_02_oop_property_depth2_and_disjunctive_raise_branch_synthesis() -> None:
    """Verify @property + depth-2 introspection + SUT grounding + existing-branch OE-SyGuS synthesis (0 rules)."""
    with tempfile.TemporaryDirectory() as td:
        repo = pathlib.Path(td)
        (repo / "ver.py").write_text(
            "class SemVer:\n"
            "    def __init__(self, major, minor, pre=False):\n"
            "        self._major = major\n"
            "        self._minor = minor\n"
            "        self._pre = pre\n"
            "    @property\n"
            "    def major(self):\n"
            "        return self._major\n"
            "    @property\n"
            "    def is_prerelease(self):\n"
            "        return self._pre\n"
            "    def _key(self):\n"
            "        return (self._major, self._minor, 0 if self._pre else 1)\n"
            "    def __lt__(self, other):\n"
            "        return self._key() < other._key()\n"
            "    def __le__(self, other):\n"
            "        return self._key() <= other._key()\n",
            encoding="utf-8",
        )
        (repo / "lockfile.py").write_text(
            "from ver import SemVer\n"
            "class UnsupportedLockError(ValueError):\n"
            "    pass\n"
            "class LockDoc:\n"
            "    def __init__(self, lock_version):\n"
            "        self.lock_version = lock_version\n"
            "def load_lock(v):\n"
            "    doc = LockDoc(v)\n"
            "    if not (SemVer(1, 0) <= doc.lock_version < SemVer(2, 0)):\n"
            "        raise UnsupportedLockError('unsupported lock version')\n"
            "    return doc\n",
            encoding="utf-8",
        )
        (repo / "test_lockfile.py").write_text(
            "import pytest\n"
            "from ver import SemVer\n"
            "from lockfile import load_lock, UnsupportedLockError\n"
            "def test_ok_10():\n"
            "    assert load_lock(SemVer(1, 0)).lock_version.major == 1\n"
            "def test_ok_11():\n"
            "    assert load_lock(SemVer(1, 1)).lock_version.major == 1\n"
            "def test_ok_12_pre():\n"
            "    assert load_lock(SemVer(1, 2, pre=True)).lock_version.major == 1\n"
            "def test_reject_20():\n"
            "    with pytest.raises(UnsupportedLockError):\n"
            "        load_lock(SemVer(2, 0))\n"
            "def test_reject_20_pre_bug1():\n"
            "    with pytest.raises(UnsupportedLockError):\n"
            "        load_lock(SemVer(2, 0, pre=True))\n"
            "def test_reject_21_pre_bug2():\n"
            "    with pytest.raises(UnsupportedLockError):\n"
            "        load_lock(SemVer(2, 1, pre=True))\n",
            encoding="utf-8",
        )
        res = PY_SWE.solve_repository(repo, ["test_lockfile.py"], python_exe=sys.executable, timeout_s=30.0)
        assert res["verified"] is True, res
        assert res["winner"]["file"] == "lockfile.py"
        assert res["winner"]["tier"] == "TIER3_OE_SYGUS_VALIDATION_RAISE"
        assert "major" in res["winner"]["description"]
        assert res["model_calls"] == 0
        assert res["parameters_stored"] == 0
