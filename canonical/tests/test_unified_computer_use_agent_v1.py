"""Tests for the Unified Zero-LLM Computer-Use Agent & External Instant Procedure Store."""
from __future__ import annotations

import csv
import json
import os
import pathlib
import sqlite3
import subprocess
import sys
import tempfile

from canonical.runtime import instant_cu_procedure_store_v1 as PROC_STORE
from canonical.runtime import unified_computer_use_agent_v1 as AGENT

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "t@local",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "t@local",
}


def _git(args: list[str], cwd: pathlib.Path) -> str:
    p = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        env=_GIT_ENV,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return p.stdout


def test_procedure_store_admission_refusal_save_delete_and_narrowing() -> None:
    store = PROC_STORE.new_store()
    # Admission MUST refuse leaked /tmp/ host path
    leaked = PROC_STORE.induce_procedure_from_verified_run(
        store,
        domain="git",
        goal_kind="test_leak",
        concrete_steps=[{"op": "noop", "path": "/tmp/leaked_abs_path"}],
        hole_bindings={},
        env_observables=["has_git_repo"],
        frame_invariants=[],
    )
    assert leaked is None
    assert store["procedures"] == {}

    # Valid hole-abstracted admission
    proc = PROC_STORE.induce_procedure_from_verified_run(
        store,
        domain="git",
        goal_kind="recover_and_merge_lost_commits",
        concrete_steps=[{"op": "git_recover_and_merge_lost_commits", "repo_dir": "site", "target_branch": "master"}],
        hole_bindings={"__REPO_DIR__": "site", "__TARGET_BRANCH__": "master"},
        env_observables=["has_git_repo", "has_git_lost_commits", "has_git_objects"],
        frame_invariants=["clean_git_working_tree"],
    )
    assert proc is not None
    pid = proc["procedure_id"]
    assert proc["parameters_stored"] == 0
    assert proc["external_model_dependency"] is False
    assert proc["steps"][0]["repo_dir"] == "__REPO_DIR__"
    assert proc["steps"][0]["target_branch"] == "__TARGET_BRANCH__"

    # Save, reload, delete
    with tempfile.TemporaryDirectory() as tmp:
        sp = pathlib.Path(tmp) / "procs.json"
        PROC_STORE.save_store(store, sp)
        reloaded = PROC_STORE.load_store(sp)
        assert pid in reloaded["procedures"]
        assert PROC_STORE.delete_procedure(reloaded, pid) is True
        assert pid not in reloaded["procedures"]

    # Counterexample narrowing then fail-closed quarantine
    r1 = PROC_STORE.refute_procedure(
        store, pid, counterexample_observables=["has_git_repo", "has_git_lost_commits"]
    )
    assert r1["status"] == "QUARANTINED" or r1["status"] == "NARROWED"
    # Second identical counterexample with all support observables must quarantine
    r2 = PROC_STORE.refute_procedure(
        store, pid, counterexample_observables=["has_git_repo", "has_git_lost_commits", "has_git_objects"]
    )
    assert r2["status"] == "QUARANTINED"
    assert store["procedures"][pid]["status"] == PROC_STORE.STATUS_QUARANTINED


def test_git_lost_commit_recovery_and_one_shot_cross_env_transfer() -> None:
    """Env A learns detached-commit recovery -> transfers on attempt 1 to unseen Env B (`main`) -> delete removes recall."""
    store = PROC_STORE.new_store()

    def _make_lost_commit_repo(ws: pathlib.Path, repo_name: str, branch: str, secret_file: str, secret_body: str) -> pathlib.Path:
        repo = ws / repo_name
        repo.mkdir(parents=True)
        _git(["init", "-b", branch], repo)
        (repo / "index.html").write_text("<h1>v1</h1>\n", encoding="utf-8")
        _git(["add", "-A"], repo)
        _git(["commit", "-m", "init"], repo)
        # Detach HEAD, make a lost commit, then checkout branch
        _git(["checkout", "--detach", "HEAD"], repo)
        (repo / secret_file).write_text(secret_body, encoding="utf-8")
        _git(["add", "-A"], repo)
        _git(["commit", "-m", "lost work"], repo)
        _git(["checkout", branch], repo)
        assert not (repo / secret_file).exists()
        return repo

    with tempfile.TemporaryDirectory() as tmp:
        ws_a = pathlib.Path(tmp) / "env_a"
        repo_a = _make_lost_commit_repo(ws_a, "personal-site", "master", "about.md", "Moved to Cairo\n")
        res_a = AGENT.solve_computer_use_task(
            ws_a,
            "I made changes to my site and checked out master, now I can't find them. Please recover and merge them into master.",
            procedure_store=store,
            learn_into_store=True,
        )
        assert res_a["verified"] is True
        assert res_a["model_calls"] == 0
        assert res_a["parameters_stored"] == 0
        assert (repo_a / "about.md").read_text(encoding="utf-8") == "Moved to Cairo\n"
        learned_pid = res_a["learned_procedure_id"]
        assert learned_pid is not None

        # Unseen Env B: different folder (`blog-app`), different branch (`main`), different file (`notes.md`)
        ws_b = pathlib.Path(tmp) / "env_b"
        repo_b = _make_lost_commit_repo(ws_b, "blog-app", "main", "notes.md", "New release notes\n")
        res_b = AGENT.solve_computer_use_task(
            ws_b,
            "I lost my recent changes after switching back to main. Please find them and merge them into main.",
            procedure_store=store,
            learn_into_store=False,
        )
        assert res_b["verified"] is True
        assert res_b["tier"] == "TIER0_PROCEDURE_RECALL"
        assert res_b["procedure_id_used"] == learned_pid
        assert (repo_b / "notes.md").read_text(encoding="utf-8") == "New release notes\n"

        # Deleting the procedure from JSON cleanly removes Tier 0 recall
        assert PROC_STORE.delete_procedure(store, learned_pid) is True
        ws_c = pathlib.Path(tmp) / "env_c"
        repo_c = _make_lost_commit_repo(ws_c, "docs", "main", "guide.md", "Fresh guide\n")
        res_c = AGENT.solve_computer_use_task(
            ws_c,
            "Please recover my lost changes and merge them into main.",
            procedure_store=store,
            learn_into_store=False,
        )
        assert res_c["verified"] is True
        assert res_c["tier"] == "TIER1_FIRST_PRINCIPLES"
        assert res_c["procedure_id_used"] is None
        assert (repo_c / "guide.md").read_text(encoding="utf-8") == "Fresh guide\n"


def test_sqlite_wal_cryptanalysis_and_one_shot_cross_db_transfer() -> None:
    """Env A cracks single-byte XOR WAL -> transfers on attempt 1 to Env B with unknown 3-byte repeating XOR WAL!"""
    store = PROC_STORE.new_store()

    def _make_encrypted_wal_env(ws: pathlib.Path, db_name: str, key: bytes, base_n: int, extra_n: int) -> None:
        ws.mkdir(parents=True)
        db = ws / db_name
        conn = sqlite3.connect(str(db))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, value INTEGER)")
        for i in range(1, base_n + 1):
            conn.execute("INSERT INTO items VALUES (?, ?, ?)", (i, f"item{i}", i * 10))
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        # Insert extra records into WAL without checkpointing!
        conn.execute("PRAGMA wal_autocheckpoint=0")
        for i in range(base_n + 1, base_n + extra_n + 1):
            conn.execute("INSERT INTO items VALUES (?, ?, ?)", (i, f"item{i}", i * 10))
        conn.commit()
        # Snapshot raw DB and uncheckpointed WAL BEFORE closing (close checkpoints WAL!)
        wal = ws / (db_name + "-wal")
        db_bytes = db.read_bytes()
        wal_bytes = wal.read_bytes()
        conn.close()
        # Overwrite with pre-checkpoint base DB + encrypted WAL
        db.write_bytes(db_bytes)
        enc_wal = bytes(wal_bytes[i] ^ key[i % len(key)] for i in range(len(wal_bytes)))
        wal.write_bytes(enc_wal)
        shm = ws / (db_name + "-shm")
        if shm.exists():
            shm.unlink()

    with tempfile.TemporaryDirectory() as tmp:
        ws_a = pathlib.Path(tmp) / "wal_a"
        _make_encrypted_wal_env(ws_a, "main.db", bytes([0x5A]), base_n=3, extra_n=4)
        res_a = AGENT.solve_computer_use_task(
            ws_a,
            "My SQLite database in WAL mode has an encrypted WAL file. Fix the WAL, recover all 7 records, and save /app/recovered.json sorted by id.",
            procedure_store=store,
            learn_into_store=True,
        )
        assert res_a["verified"] is True
        rows_a = json.loads((ws_a / "recovered.json").read_text(encoding="utf-8"))
        assert len(rows_a) == 7
        assert [r["id"] for r in rows_a] == list(range(1, 8))
        pid = res_a["learned_procedure_id"]
        assert pid is not None

        # Unseen Env B: different DB name (`inventory.db`), different 3-byte repeating XOR key, different output file!
        ws_b = pathlib.Path(tmp) / "wal_b"
        _make_encrypted_wal_env(ws_b, "inventory.db", bytes([0xA3, 0x1F, 0x77]), base_n=2, extra_n=3)
        res_b = AGENT.solve_computer_use_task(
            ws_b,
            "SQLite database WAL file is corrupted/encrypted. Recover all 5 records and write /app/out_items.json sorted by id.",
            procedure_store=store,
            learn_into_store=False,
        )
        assert res_b["verified"] is True
        assert res_b["tier"] == "TIER0_PROCEDURE_RECALL"
        assert res_b["procedure_id_used"] == pid
        rows_b = json.loads((ws_b / "out_items.json").read_text(encoding="utf-8"))
        assert len(rows_b) == 5
        assert [r["id"] for r in rows_b] == [1, 2, 3, 4, 5]


def test_git_secret_purge_log_aggregation_and_dom_stepper() -> None:
    """Verify git secret forensics+purge with frame invariants, bracketed log counting, and zero-LLM DOM stepper."""
    with tempfile.TemporaryDirectory() as tmp:
        # 1. Git secret recovery + purge + frame invariance
        ws_g = pathlib.Path(tmp) / "git_sec"
        repo = ws_g / "repo"
        repo.mkdir(parents=True)
        _git(["init", "-b", "master"], repo)
        (repo / "README.md").write_text("clean project\n", encoding="utf-8")
        _git(["add", "README.md"], repo)
        _git(["commit", "-m", "initial commit"], repo)
        (repo / "leak.txt").write_text("token[abc_987_xyz]\n", encoding="utf-8")
        _git(["add", "leak.txt"], repo)
        _git(["commit", "-m", "oops leak"], repo)
        _git(["reset", "--hard", "HEAD~1"], repo)

        res_g = AGENT.solve_computer_use_task(
            ws_g,
            "A secret was committed in /app/repo and rewritten away. Recover the token[...] secret to /app/found.txt, purge it from git, and keep irrelevant files and commit messages untouched.",
        )
        assert res_g["verified"] is True
        assert (ws_g / "found.txt").read_text(encoding="utf-8").strip() == "token[abc_987_xyz]"
        assert (repo / "README.md").read_text(encoding="utf-8") == "clean project\n"

        # 2. Dated log aggregation with bracketed severity disambiguation + explicit reference date
        ws_l = pathlib.Path(tmp) / "logs_ws"
        ldir = ws_l / "logs"
        ldir.mkdir(parents=True)
        (ldir / "2025-08-12_app.log").write_text(
            "2025-08-12 01:00:00 [ERROR] disk full\n"
            "2025-08-12 02:00:00 [WARNING] retry will ERROR next time\n"
            "2025-08-12 03:00:00 [INFO] ok\n",
            encoding="utf-8",
        )
        (ldir / "2025-07-01_app.log").write_text("2025-07-01 01:00:00 [ERROR] old err\n", encoding="utf-8")
        res_l = AGENT.solve_computer_use_task(
            ws_l,
            "Analyze logs in /app/logs for ERROR, WARNING, INFO across Today, Last 7 days, Last 30 days, month_to_date, Total. Write /app/summary.csv with header period,severity,count. The current date is 2025-08-12.",
        )
        assert res_l["verified"] is True
        with (ws_l / "summary.csv").open(encoding="utf-8") as f:
            rows = {(r["period"], r["severity"]): int(r["count"]) for r in csv.DictReader(f)}
        assert rows[("today", "ERROR")] == 1  # NOT 2 (the [WARNING] mentioning ERROR must not double-count!)
        assert rows[("today", "WARNING")] == 1
        assert rows[("total", "ERROR")] == 2

    # 3. Zero-LLM observable DOM/AX-tree stepper
    dom = [
        {"role": "button", "id": "#cancel", "text": "Cancel"},
        {"role": "button", "id": "#submit-order", "text": "Submit Order"},
        {"role": "input", "id": "#email", "text": "Email Address"},
    ]
    step = AGENT.step_observable_dom(dom, "Click the 'Submit Order' button")
    assert step["model_calls"] == 0
    assert step["parameters_stored"] == 0
    assert step["action"]["op"] == "click"
    assert step["action"]["selector"] == "#submit-order"
