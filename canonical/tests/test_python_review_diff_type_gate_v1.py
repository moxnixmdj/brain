# PROJECT_BRAIN
"""Pins for python.review.diff_type_gate.v1 — the mypy type-soundness gate
on produced diffs.  Every pin declares its world; the sabotage worlds
prove the gate fires on the class ruff's F/E/W sweep cannot see.

Run: python -m pytest canonical/tests/test_python_review_diff_type_gate_v1.py -q
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from canonical.runtime.bound_capabilities import (
    python_review_diff_type_gate as gate,
)

PY = sys.executable

BASE = """def total(prices: list[float]) -> float:
    return sum(prices)
"""

TYPE_LIE = """def total(prices: list[float]) -> float:
    return sum(prices)


def label(count: int) -> str:
    name: str = count + " items"
    return name
"""

PREEXISTING_LIE = """def total(prices: list[float]) -> float:
    return sum(prices)


def old_broken(x) -> int:
    return "not an int at all"
"""

GREEN_DIFF = """--- a/pkg/calc.py
+++ b/pkg/calc.py
@@ -1,2 +1,2 @@
-def total(prices: list[float]) -> float:
+def total(prices: list[float], tax: float = 0.0) -> float:
     return sum(prices)
"""

RED_DIFF = """--- a/pkg/calc.py
+++ b/pkg/calc.py
@@ -1,2 +1,7 @@
 def total(prices: list[float]) -> float:
     return sum(prices)
+
+
+def label(count: int) -> str:
+    name: str = count + " items"
+    return name
"""

# type lie lives ENTIRELY outside the changed hunk: rename on lines 1-2,
# broken pre-existing function at lines 5-7 -> advisory only, never blocks
PREEXISTING_DIFF = """--- a/pkg/calc.py
+++ b/pkg/calc.py
@@ -1,2 +1,2 @@
-def total(prices: list[float]) -> float:
+def summed(prices: list[float]) -> float:
     return sum(prices)
"""

SYNTAX_BROKEN = """def total(prices: list[float]) -> float:
    return sum(prices


def garbage(: 
"""


def _tree(root: Path, content: str) -> None:
    (root / "wt" / "pkg").mkdir(parents=True)
    (root / "wt" / "pkg" / "calc.py").write_text(content, encoding="utf-8")


def _diff(root: Path, rel: str, text: str) -> None:
    (root / rel).write_text(text, encoding="utf-8")


def _run(root: Path, diff_rel: str, py: str = PY):
    return gate.run({
        "diff_path": diff_rel,
        "worktree_path": "wt",
        "output_path": "_out/typegate.json",
        "python_executable": py,
        "timeout_s": 120,
    }, root)


class TestDiffTypeGate(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="typegate_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _have_mypy(self) -> bool:
        import subprocess
        p = subprocess.run([PY, "-m", "mypy", "--version"],
                           capture_output=True, text=True)
        return p.returncode == 0 and "mypy" in p.stdout.lower()

    def test_golden_clean_diff_passes(self):
        _tree(self.tmp, BASE)
        _diff(self.tmp, "d.diff", GREEN_DIFF)
        res = _run(self.tmp, "d.diff")
        if not self._have_mypy():
            self.skipTest("mypy not on this interpreter")
        self.assertEqual(res["gate"], "PASS")
        self.assertTrue(res["verified"])

    def test_type_lie_on_changed_line_is_blocking(self):
        _tree(self.tmp, TYPE_LIE)
        _diff(self.tmp, "d.diff", RED_DIFF)
        res = _run(self.tmp, "d.diff")
        if not self._have_mypy():
            self.skipTest("mypy not on this interpreter")
        self.assertEqual(res["gate"], "FAIL")
        self.assertFalse(res["verified"])
        art = json.loads((self.tmp / "_out/typegate.json").read_text())
        codes = {f["code"] for f in art["blocking_findings"]}
        # int + str and invalid assignment both land on line 6
        self.assertIn("operator", codes)
        self.assertTrue(all(f["line"] == 6 for f in art["blocking_findings"]))

    def test_preexisting_lie_outside_diff_never_blocks(self):
        _tree(self.tmp, PREEXISTING_LIE)
        _diff(self.tmp, "d.diff", PREEXISTING_DIFF)
        res = _run(self.tmp, "d.diff")
        if not self._have_mypy():
            self.skipTest("mypy not on this interpreter")
        self.assertEqual(res["gate"], "PASS")
        art = json.loads((self.tmp / "_out/typegate.json").read_text())
        self.assertEqual(art["blocking_count"], 0)
        self.assertTrue(any(f.get("out_of_scope") == "preexisting"
                            for f in art["advisory_findings"]))

    def test_syntax_error_blocks_without_mypy(self):
        _tree(self.tmp, SYNTAX_BROKEN)
        _diff(self.tmp, "d.diff", RED_DIFF)
        res = _run(self.tmp, "d.diff")
        self.assertEqual(res["gate"], "FAIL")
        art = json.loads((self.tmp / "_out/typegate.json").read_text())
        self.assertTrue(art["syntax_errors"])

    def test_mypy_absent_degrades_loudly_to_pass_baseline_only(self):
        _tree(self.tmp, TYPE_LIE)
        _diff(self.tmp, "d.diff", RED_DIFF)
        res = _run(self.tmp, "d.diff", py="/usr/bin/false")
        self.assertEqual(res["gate"], "PASS_BASELINE_ONLY")
        self.assertEqual(res["mypy"], "UNAVAILABLE")
        self.assertFalse(res["verified"])
        art = json.loads((self.tmp / "_out/typegate.json").read_text())
        self.assertEqual(art["mypy"], "UNAVAILABLE")

    def test_artifact_byte_identical_on_rerun(self):
        _tree(self.tmp, TYPE_LIE)
        _diff(self.tmp, "d.diff", RED_DIFF)
        _run(self.tmp, "d.diff")
        first = (self.tmp / "_out/typegate.json").read_bytes()
        shutil.move(self.tmp / "_out/typegate.json", self.tmp / "_out/again.json")
        (self.tmp / "_out/again.json").unlink()
        _run(self.tmp, "d.diff")
        second = (self.tmp / "_out/typegate.json").read_bytes()
        self.assertEqual(first, second)

    def test_empty_diff_refuses(self):
        _tree(self.tmp, BASE)
        _diff(self.tmp, "e.diff", "")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "e.diff")
        self.assertIn("DIFF_EMPTY", str(ctx.exception))

    def test_path_escape_refuses(self):
        _tree(self.tmp, BASE)
        _diff(self.tmp, "d.diff", GREEN_DIFF)
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "../escape.diff")
        self.assertIn("PATH_ESCAPE", str(ctx.exception))

    def test_touched_file_missing_in_worktree_refuses(self):
        _tree(self.tmp, BASE)
        _diff(self.tmp, "m.diff",
              "--- a/pkg/ghost.py\n+++ b/pkg/ghost.py\n@@ -1,1 +1,1 @@\n-def a():\n+def b():\n     pass\n")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "m.diff")
        self.assertIn("TOUCHED_FILE_MISSING_IN_WORKTREE", str(ctx.exception))

    def test_created_file_devnull_diff(self):
        new_content = "def born() -> int:\n    return 1\n"
        _tree(self.tmp, new_content)
        _diff(self.tmp, "c.diff",
              "--- /dev/null\n+++ b/pkg/calc.py\n@@ -0,0 +1,2 @@\n+def born() -> int:\n+    return 1\n")
        res = _run(self.tmp, "c.diff")
        if not self._have_mypy():
            self.skipTest("mypy not on this interpreter")
        self.assertEqual(res["gate"], "PASS")
        self.assertNotIn("TOUCHED_FILE_MISSING", str(res))

    def test_diff_sha_and_schema_pins(self):
        _tree(self.tmp, BASE)
        _diff(self.tmp, "d.diff", GREEN_DIFF)
        _run(self.tmp, "d.diff")
        art = json.loads((self.tmp / "_out/typegate.json").read_text())
        self.assertEqual(art["diff_sha256"],
                         hashlib.sha256(GREEN_DIFF.encode()).hexdigest())
        for key in ("schema", "gate", "gate_law", "blocking_findings",
                    "advisory_findings", "syntax_errors", "mypy", "complete"):
            self.assertIn(key, art)

    def test_notes_are_advisory_not_blocking(self):
        # untyped def produces a note-class hint at most; must never block
        _tree(self.tmp, TYPE_LIE)
        _diff(self.tmp, "d.diff", RED_DIFF)
        res = _run(self.tmp, "d.diff")
        if not self._have_mypy():
            self.skipTest("mypy not on this interpreter")
        art = json.loads((self.tmp / "_out/typegate.json").read_text())
        self.assertTrue(all(f["severity"] == "error" for f in art["blocking_findings"]))

    def test_gate_is_fail_closed_on_worktree_shape(self):
        _tree(self.tmp, BASE)
        _diff(self.tmp, "d.diff", GREEN_DIFF)
        (self.tmp / "notdir").write_text("x")
        with self.assertRaises(SystemExit):
            gate.run({"diff_path": "d.diff", "worktree_path": "notdir",
                      "output_path": "_out/x.json", "python_executable": PY},
                     self.tmp)


if __name__ == "__main__":
    unittest.main()
