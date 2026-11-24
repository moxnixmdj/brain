"""Tests for the task gate.

The gate exists to stop the tree measuring surfaces instead of artifacts, so its own tests
have to hold the same line: each verifier must PASS on a correct workspace and FAIL on a
plausible wrong one. A verifier that cannot fail is not a verifier.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sqlite3
import tempfile
import unittest

from canonical.runtime import task_gate_v1 as gate


class VerifierTest(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="gate-test-"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_line_count_accepts_the_right_number_and_refuses_a_wrong_one(self):
        (self.root / "data.txt").write_text(gate.TEXT)
        (self.root / "count.json").write_text(json.dumps({"lines": 5}))
        self.assertTrue(gate._verify_line_count(self.root)[0])
        (self.root / "count.json").write_text(json.dumps({"lines": 4}))
        self.assertFalse(gate._verify_line_count(self.root)[0])

    def test_line_count_refuses_a_file_that_is_absent(self):
        self.assertFalse(gate._verify_line_count(self.root)[0])

    def test_gzip_accepts_a_real_gzip_and_refuses_a_plain_copy(self):
        (self.root / "data.txt").write_text(gate.TEXT)
        (self.root / "data.txt.gz").write_text(gate.TEXT)          # a copy, not a gzip
        self.assertFalse(gate._verify_gzip(self.root)[0])
        import gzip
        (self.root / "data.txt.gz").write_bytes(gzip.compress(gate.TEXT.encode()))
        self.assertTrue(gate._verify_gzip(self.root)[0])

    def test_tar_gz_needs_every_named_member(self):
        import io
        import tarfile
        (self.root / "data.txt").write_text(gate.TEXT)
        with tarfile.open(self.root / "bundle.tar.gz", "w:gz") as archive:
            info = tarfile.TarInfo("data.txt")
            payload = gate.TEXT.encode()
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        ok, detail = gate._verify_tar_gz(self.root)
        self.assertFalse(ok, "a bundle missing two members must fail")
        self.assertIn("holds", detail)

    def test_rename_refuses_when_a_log_file_is_left(self):
        gate._setup_logs(self.root)
        (self.root / "one.log").rename(self.root / "one.txt")
        self.assertFalse(gate._verify_rename(self.root)[0])

    def test_rename_refuses_changed_bytes(self):
        gate._setup_logs(self.root)
        (self.root / "one.log").rename(self.root / "one.txt")
        (self.root / "two.log").rename(self.root / "two.txt")
        (self.root / "one.txt").write_text("tampered\n")
        self.assertFalse(gate._verify_rename(self.root)[0])

    def test_adults_needs_the_exact_set_in_order(self):
        gate._setup_records(self.root)
        (self.root / "adults.txt").write_text("ada\ncy\neve\n")
        self.assertTrue(gate._verify_adults(self.root)[0])
        (self.root / "adults.txt").write_text("ada\ncy\ndee\neve\n")  # 30 is not > 30
        self.assertFalse(gate._verify_adults(self.root)[0])

    def test_sqlite_refuses_an_empty_table(self):
        connection = sqlite3.connect(str(self.root / "tasks.db"))
        connection.execute("create table tasks (id integer, title text)")
        connection.commit()
        connection.close()
        self.assertFalse(gate._verify_sqlite(self.root)[0])
        connection = sqlite3.connect(str(self.root / "tasks.db"))
        connection.execute("insert into tasks values (1, 'x')")
        connection.commit()
        connection.close()
        self.assertTrue(gate._verify_sqlite(self.root)[0])

    def test_digest_needs_both_numbers(self):
        (self.root / "data.txt").write_text(gate.TEXT)
        sha = hashlib.sha256(gate.TEXT.encode()).hexdigest()
        (self.root / "digest.json").write_text(json.dumps({"sha256": sha}))
        self.assertFalse(gate._verify_digest(self.root)[0], "bytes missing")
        (self.root / "digest.json").write_text(
            json.dumps({"sha256": sha, "bytes": len(gate.TEXT.encode())}))
        self.assertTrue(gate._verify_digest(self.root)[0])


class EscapeTest(unittest.TestCase):
    def test_a_plan_that_writes_into_the_repository_is_refused(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="escape-"))
        try:
            plan = {"inputs": {"output_path":
                               "canonical/astra_runtime/tmp/brain_out__x.json",
                               "source_root": "."}}
            self.assertTrue(gate._escapes(root, plan))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_a_plan_inside_the_workspace_is_allowed(self):
        root = pathlib.Path(tempfile.mkdtemp(prefix="escape-ok-"))
        try:
            plan = {"inputs": {"output_path": str(root / "count.json"),
                               "source_root": "."}}
            self.assertEqual(gate._escapes(root, plan), [])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class GateTest(unittest.TestCase):
    def test_every_task_in_the_gate_has_setup_verify_and_instruction(self):
        for task in gate.TASKS:
            self.assertIn("instruction", task)
            self.assertTrue(callable(task["setup"]))
            self.assertTrue(callable(task["verify"]))

    def test_the_gate_runs_without_executing_anything(self):
        report = gate.run_gate(execute=False)
        self.assertEqual(report["tasks"], len(gate.TASKS))
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(sum(report["counts"].values()), report["tasks"])
        # a compile-only run can never claim a pass: nothing wrote an artifact
        self.assertEqual(report["passed"], 0)


if __name__ == "__main__":
    unittest.main()
