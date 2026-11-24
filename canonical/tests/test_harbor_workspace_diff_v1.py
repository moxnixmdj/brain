"""Local tests for the bounded workspace snapshot/diff measurement."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from canonical.runtime import harbor_workspace_diff_v1 as wsdiff

SCRIPT = Path(wsdiff.__file__)


class WorkspaceDiffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "app"
        self.root.mkdir()
        self.state = Path(self.tmp.name) / "state.json"

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, mode: str) -> dict:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), mode, str(self.root), str(self.state)],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0)
        line = next(l for l in proc.stdout.splitlines() if l.startswith(wsdiff.MARKER))
        return json.loads(line[len(wsdiff.MARKER):])

    def test_roundtrip_added_changed_removed(self):
        (self.root / "keep.txt").write_text("keep")
        (self.root / "change.txt").write_text("before")
        (self.root / "drop.txt").write_text("gone")
        snap = self.run_cli("snapshot")
        self.assertEqual(snap["status"], "SNAPSHOT")
        self.assertEqual(snap["files"], 3)
        (self.root / "change.txt").write_text("after")
        (self.root / "drop.txt").unlink()
        (self.root / "added.txt").write_text("new!")
        report = self.run_cli("diff")
        self.assertEqual(report["status"], "DIFF")
        self.assertTrue(report["candidate_changed"])
        self.assertEqual(report["added"], 1)
        self.assertEqual(report["removed"], 1)
        self.assertEqual(report["changed"], 1)
        self.assertEqual(report["diff_bytes"], len("after") + len("new!"))
        self.assertIn("added.txt", report["changed_paths"])
        self.assertIn("change.txt", report["changed_paths"])
        self.assertEqual(report["removed_paths"], ["drop.txt"])

    def test_symlinks_and_cache_dirs_are_not_measured(self):
        (self.root / "real.txt").write_text("real")
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "dep.js").write_text("dep")
        (self.root / ".cache").mkdir()
        (self.root / ".cache" / "blob").write_text("blob")
        (self.root / "link.txt").symlink_to(self.root / "real.txt")
        snap = self.run_cli("snapshot")
        self.assertEqual(snap["files"], 1)
        (self.root / "node_modules" / "dep.js").write_text("changed-dep")
        report = self.run_cli("diff")
        self.assertEqual(report["candidate_changed"], False)
        self.assertEqual(report["diff_bytes"], 0)

    def test_missing_baseline_is_an_error_not_a_fake_diff(self):
        self.state.unlink(missing_ok=True)
        report = self.run_cli("diff")
        self.assertEqual(report["status"], "ERROR")

    def test_absolute_root_required(self):
        with self.assertRaises(wsdiff.WorkspaceDiffError):
            wsdiff.snapshot("relative/path", self.state)


if __name__ == "__main__":
    unittest.main()
