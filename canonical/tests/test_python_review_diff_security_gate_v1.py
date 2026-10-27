# PROJECT_BRAIN
"""Pins for python.review.diff_security_gate.v1 — bandit on changed lines.
Paired worlds: a green change PASSES; shell=True added on a changed line
FAILs with B602 named; the same B602 pre-existing outside the diff never
blocks.

Run: python -m pytest canonical/tests/test_python_review_diff_security_gate_v1.py -q
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import (
    python_review_diff_security_gate as gate,
)

PY = sys.executable

CLEAN = """def greet(name: str) -> str:
    return "hello " + name
"""

DIRTY = """import subprocess


def run_it(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True)
"""

# B602 lives at line 5 (pre-existing); diff only renames the function on
# line 4 -> blocking law must NOT fire, advisory row carries the context
PREEXISTING = """import subprocess


def run_it(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True)
"""

GREEN_DIFF = """--- a/pkg/s.py
+++ b/pkg/s.py
@@ -1,2 +1,2 @@
-def greet(name: str) -> str:
+def greet_user(name: str) -> str:
     return "hello " + name
"""

RED_DIFF = """--- a/pkg/s.py
+++ b/pkg/s.py
@@ -1,2 +1,5 @@
-def greet(name: str) -> str:
-    return "hello " + name
+import subprocess
+
+
+def run_it(cmd):
+    return subprocess.run(cmd, shell=True, capture_output=True)
"""

PRE_EXISTING_DIFF = """--- a/pkg/s.py
+++ b/pkg/s.py
@@ -4,1 +4,1 @@
-def run_it(cmd):
+def run_cmd(cmd):
"""


def _tree(root: Path, content: str) -> None:
    (root / "wt" / "pkg").mkdir(parents=True)
    (root / "wt" / "pkg" / "s.py").write_text(content, encoding="utf-8")


def _run(root: Path, diff_rel: str, py: str = PY):
    return gate.run({
        "diff_path": diff_rel,
        "worktree_path": "wt",
        "output_path": "_out/sec.json",
        "python_executable": py,
        "timeout_s": 120,
    }, root)


class TestDiffSecurityGate(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="secgate_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _have_bandit(self) -> bool:
        p = subprocess.run([PY, "-m", "bandit", "--version"],
                           capture_output=True, text=True)
        return p.returncode == 0

    def test_golden_pass(self):
        _tree(self.tmp, CLEAN)
        (self.tmp / "d.diff").write_text(GREEN_DIFF, encoding="utf-8")
        res = _run(self.tmp, "d.diff")
        if not self._have_bandit():
            self.skipTest("bandit absent")
        self.assertEqual(res["gate"], "PASS")
        self.assertTrue(res["verified"])

    def test_shell_true_on_changed_line_blocks_b602_named(self):
        _tree(self.tmp, DIRTY)
        (self.tmp / "d.diff").write_text(RED_DIFF, encoding="utf-8")
        res = _run(self.tmp, "d.diff")
        if not self._have_bandit():
            self.skipTest("bandit absent")
        self.assertEqual(res["gate"], "FAIL")
        self.assertFalse(res["verified"])
        art = json.loads((self.tmp / "_out/sec.json").read_text())
        ids = {f["test_id"] for f in art["blocking_findings"]}
        self.assertIn("B602", ids)
        b602 = [f for f in art["blocking_findings"] if f["test_id"] == "B602"]
        self.assertEqual({f["line"] for f in b602}, {5})

    def test_preexisting_b602_outside_diff_never_blocks(self):
        _tree(self.tmp, PREEXISTING)
        (self.tmp / "d.diff").write_text(PRE_EXISTING_DIFF, encoding="utf-8")
        res = _run(self.tmp, "d.diff")
        if not self._have_bandit():
            self.skipTest("bandit absent")
        self.assertEqual(res["gate"], "PASS")
        art = json.loads((self.tmp / "_out/sec.json").read_text())
        self.assertEqual(art["blocking_count"], 0)
        scoped = [f for f in art["advisory_findings"] if f.get("out_of_scope")]
        self.assertTrue(any(f["test_id"] == "B602" for f in scoped))

    def test_low_confidence_medium_is_advisory(self):
        # hashlib md5 w/o usedforsecurity -> B324 severity MEDIUM confidence HIGH
        # would block; instead craft a LOW advisory: plain subprocess import B404
        _tree(self.tmp, DIRTY)
        (self.tmp / "d.diff").write_text(RED_DIFF, encoding="utf-8")
        art_path = self.tmp / "_out/sec.json"
        _run(self.tmp, "d.diff")
        art = json.loads(art_path.read_text())
        lows = [f for f in art["blocking_findings"] + art["advisory_findings"]
                if f["test_id"] == "B404"]
        self.assertTrue(lows)
        self.assertTrue(all(f["severity"] == "LOW" for f in lows))
        # LOW never lands in blocking even on a changed line
        self.assertTrue(all(f not in art["blocking_findings"] or f["line"] not in (1,)
                            for f in lows))

    def test_hardcoded_password_blocks_b105(self):
        body = "def connect(host):\n    password = \"hunter2-known-teststring\"\n    return host, password\n"
        _tree(self.tmp, body)
        (self.tmp / "p.diff").write_text(
            "--- /dev/null\n+++ b/pkg/s.py\n@@ -0,0 +1,3 @@\n"
            "+def connect(host):\n"
            "+    password = \"hunter2-known-teststring\"\n"
            "+    return host, password\n", encoding="utf-8")
        res = _run(self.tmp, "p.diff")
        if not self._have_bandit():
            self.skipTest("bandit absent")
        self.assertEqual(res["gate"], "FAIL")
        art = json.loads((self.tmp / "_out/sec.json").read_text())
        self.assertIn("B105", {f["test_id"] for f in art["blocking_findings"]})

    def test_bandit_absent_degrades_loudly(self):
        _tree(self.tmp, DIRTY)
        (self.tmp / "d.diff").write_text(RED_DIFF, encoding="utf-8")
        res = _run(self.tmp, "d.diff", py="/usr/bin/false")
        self.assertEqual(res["gate"], "PASS_BASELINE_ONLY")
        self.assertEqual(res["bandit"], "UNAVAILABLE")
        self.assertFalse(res["verified"])

    def test_byte_identical_rerun(self):
        _tree(self.tmp, DIRTY)
        (self.tmp / "d.diff").write_text(RED_DIFF, encoding="utf-8")
        _run(self.tmp, "d.diff")
        first = (self.tmp / "_out/sec.json").read_bytes()
        _run(self.tmp, "d.diff")
        self.assertEqual(first, (self.tmp / "_out/sec.json").read_bytes())

    def test_empty_diff_refuses(self):
        _tree(self.tmp, CLEAN)
        (self.tmp / "e.diff").write_text("", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "e.diff")
        self.assertIn("DIFF_EMPTY", str(ctx.exception))

    def test_path_escape_refuses(self):
        _tree(self.tmp, CLEAN)
        (self.tmp / "d.diff").write_text(GREEN_DIFF, encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "../out.diff")
        self.assertIn("PATH_ESCAPE", str(ctx.exception))

    def test_missing_touched_file_refuses(self):
        _tree(self.tmp, CLEAN)
        (self.tmp / "m.diff").write_text(
            "--- a/pkg/ghost.py\n+++ b/pkg/ghost.py\n@@ -1,1 +1,1 @@\n-def a():\n+def b():\n     pass\n",
            encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "m.diff")
        self.assertIn("TOUCHED_FILE_MISSING_IN_WORKTREE", str(ctx.exception))

    def test_syntax_broken_blocks_without_bandit(self):
        _tree(self.tmp, "def broken(:\n")
        (self.tmp / "d.diff").write_text(PRE_EXISTING_DIFF, encoding="utf-8")
        res = _run(self.tmp, "d.diff")
        self.assertEqual(res["gate"], "FAIL")
        art = json.loads((self.tmp / "_out/sec.json").read_text())
        self.assertTrue(art["syntax_errors"])

    def test_schema_and_diff_sha(self):
        _tree(self.tmp, CLEAN)
        (self.tmp / "d.diff").write_text(GREEN_DIFF, encoding="utf-8")
        _run(self.tmp, "d.diff")
        art = json.loads((self.tmp / "_out/sec.json").read_text())
        self.assertEqual(art["diff_sha256"],
                         hashlib.sha256(GREEN_DIFF.encode()).hexdigest())
        for key in ("schema", "gate", "gate_law", "blocking_findings",
                    "advisory_findings", "syntax_errors", "bandit", "complete"):
            self.assertIn(key, art)

    def test_worktree_must_be_directory(self):
        _tree(self.tmp, CLEAN)
        (self.tmp / "d.diff").write_text(GREEN_DIFF, encoding="utf-8")
        (self.tmp / "file.txt").write_text("x")
        with self.assertRaises(SystemExit):
            gate.run({"diff_path": "d.diff", "worktree_path": "file.txt",
                      "output_path": "_out/x.json", "python_executable": PY},
                     self.tmp)


if __name__ == "__main__":
    unittest.main()
