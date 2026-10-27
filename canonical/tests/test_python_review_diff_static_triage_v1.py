# PROJECT_BRAIN
"""Pins for python.review.diff_static_triage.v1 — the diff review gate."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from canonical.runtime.bound_capabilities import python_review_diff_static_triage as tr

B_BASE = '''def compute(x: int) -> int:
    return x + 1
'''
B_DIRTY = B_BASE + "    y = undefined_name + 1\n    return y\n"
B_SYNTAX = B_BASE + "    return (x + 1\n"
A_LEGACY = '''def legacy_ok(x):
    return slur_preexisting_bug_outside_any_diff  # untouched everywhere
'''


def _make_repo(tmp: Path) -> Path:
    root = tmp / "fixture_repo"
    (root / "wt").mkdir(parents=True)
    (root / "wt" / "pkg").mkdir()
    (root / "wt" / "pkg" / "b.py").write_text(B_BASE, encoding="utf-8")
    (root / "wt" / "pkg" / "a.py").write_text(A_LEGACY, encoding="utf-8")
    return root


def _write_diff(root: Path, name: str, diff: str) -> Path:
    p = root / name
    p.write_text(diff, encoding="utf-8")
    return p


def _run(root: Path, diff_name: str, extra: dict | None = None) -> dict:
    args = {"diff_path": diff_name, "worktree_path": "wt",
            "output_path": "_out/triage.json",
            "python_executable": sys.executable}
    if extra:
        args.update(extra)
    return tr.run(args, root)


CLEAN_DIFF = "--- a/pkg/b.py\n+++ b/pkg/b.py\n@@ -1,2 +1,2 @@\n def compute(x: int) -> int:\n-    return x + 1\n+    return x + 1  # tuned constant\n"
DIRTY_DIFF = "--- a/pkg/b.py\n+++ b/pkg/b.py\n@@ -1,2 +1,4 @@\n def compute(x: int) -> int:\n     return x + 1\n+    y = undefined_name + 1\n+    return y\n"
SYNTAX_DIFF = "--- a/pkg/b.py\n+++ b/pkg/b.py\n@@ -1,2 +1,3 @@\n def compute(x: int) -> int:\n-    return x + 1\n+    return (x + 1\n"
SYNTAX_WT_DIFF = SYNTAX_DIFF


class TestDiffStaticTriage(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="triage_pins_"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clean_diff_gate_pass(self):
        root = _make_repo(self.tmp)
        _write_diff(root, "c.diff", CLEAN_DIFF)
        res = _run(root, "c.diff")
        if res["ruff"] == "UNAVAILABLE":
            self.skipTest("ruff not on this interpreter — gate basis covered in verify env")
        self.assertEqual(res["gate"], "PASS")
        self.assertTrue(res["verified"])
        self.assertEqual(res["blocking_findings"], 0)

    def test_f821_on_changed_line_is_blocking(self):
        root = _make_repo(self.tmp)
        (root / "wt" / "pkg" / "b.py").write_text(B_DIRTY, encoding="utf-8")
        _write_diff(root, "d.diff", DIRTY_DIFF)
        res = _run(root, "d.diff")
        if res["ruff"] == "UNAVAILABLE":
            self.skipTest("ruff not on this interpreter")
        self.assertEqual(res["gate"], "FAIL")
        self.assertFalse(res["verified"])
        art = json.loads((root / "_out" / "triage.json").read_text())
        self.assertEqual(art["blocking_findings"][0]["code"], "F821")
        self.assertEqual(art["blocking_findings"][0]["line"], 3)

    def test_syntax_error_blocks_even_without_ruff(self):
        root = _make_repo(self.tmp)
        (root / "wt" / "pkg" / "b.py").write_text(B_SYNTAX, encoding="utf-8")
        _write_diff(root, "s.diff", SYNTAX_WT_DIFF)
        res = _run(root, "s.diff", extra={"python_executable": "/usr/bin/false"})
        self.assertEqual(res["gate"], "FAIL")
        art = json.loads((root / "_out" / "triage.json").read_text())
        self.assertTrue(art["syntax_errors"])
        self.assertEqual(art["ruff"], "UNAVAILABLE")

    def test_ruff_absent_clean_records_pass_syntax_only_loudly(self):
        root = _make_repo(self.tmp)
        _write_diff(root, "c.diff", CLEAN_DIFF)
        res = _run(root, "c.diff", extra={"python_executable": "/usr/bin/false"})
        art = json.loads((root / "_out" / "triage.json").read_text())
        self.assertEqual(res["gate"], "PASS_SYNTAX_ONLY")
        self.assertEqual(art["ruff"], "UNAVAILABLE")

    def test_preexisting_finding_outside_diff_never_blocks(self):
        root = _make_repo(self.tmp)
        _write_diff(root, "c.diff", CLEAN_DIFF)
        res = _run(root, "c.diff")
        if res["ruff"] == "UNAVAILABLE":
            self.skipTest("ruff not on this interpreter")
        art = json.loads((root / "_out" / "triage.json").read_text())
        self.assertEqual(art["gate"], "PASS")

    def test_created_file_diff_counts_as_fully_changed(self):
        root = _make_repo(self.tmp)
        (root / "wt" / "pkg" / "new.py").write_text("def n() -> int:\n    return nope\n", encoding="utf-8")
        created_diff = "--- /dev/null\n+++ b/pkg/new.py\n@@ -0,0 +1,2 @@\n+def n() -> int:\n+    return nope\n"
        _write_diff(root, "new.diff", created_diff)
        res = _run(root, "new.diff")
        if res["ruff"] == "UNAVAILABLE":
            self.skipTest("ruff not on this interpreter")
        self.assertEqual(res["gate"], "FAIL")
        art = json.loads((root / "_out" / "triage.json").read_text())
        self.assertIn("pkg/new.py", art["created_files"])

    def test_touched_file_missing_in_worktree_refuses(self):
        root = _make_repo(self.tmp)
        ghost = "--- a/pkg/ghost.py\n+++ b/pkg/ghost.py\n@@ -1,1 +1,1 @@\n-x\n+y\n"
        _write_diff(root, "g.diff", ghost)
        with self.assertRaises(SystemExit) as cm:
            _run(root, "g.diff")
        self.assertIn("TOUCHED_FILE_MISSING_IN_WORKTREE:pkg/ghost.py", str(cm.exception))

    def test_empty_diff_refused(self):
        root = _make_repo(self.tmp)
        _write_diff(root, "e.diff", "")
        with self.assertRaises(SystemExit) as cm:
            _run(root, "e.diff")
        self.assertIn("DIFF_EMPTY", str(cm.exception))

    def test_path_escape_refused(self):
        root = _make_repo(self.tmp)
        _write_diff(root, "c.diff", CLEAN_DIFF)
        with self.assertRaises(SystemExit) as cm:
            _run(root, "c.diff", extra={"output_path": "../escape.json"})
        self.assertIn("PATH_ESCAPE", str(cm.exception))

    def test_deterministic_byte_identical_rerun(self):
        root = _make_repo(self.tmp)
        (root / "wt" / "pkg" / "b.py").write_text(B_DIRTY, encoding="utf-8")
        _write_diff(root, "d.diff", DIRTY_DIFF)
        r1 = _run(root, "d.diff")
        first = (root / "_out" / "triage.json").read_bytes()
        r2 = _run(root, "d.diff")
        second = (root / "_out" / "triage.json").read_bytes()
        self.assertEqual(first, second)
        self.assertEqual(r1["output_sha256"], r2["output_sha256"])

    def test_diff_hash_matches_artifact(self):
        root = _make_repo(self.tmp)
        _write_diff(root, "c.diff", CLEAN_DIFF)
        res = _run(root, "c.diff")
        import hashlib
        self.assertEqual(res["diff_sha256"],
                         hashlib.sha256(CLEAN_DIFF.encode("utf-8")).hexdigest())

    def test_advisory_e501_never_blocks(self):
        root = _make_repo(self.tmp)
        long_line = '    return "' + ("x" * 120) + '"\n'
        new_body = B_BASE.replace("    return x + 1\n", long_line)
        (root / "wt" / "pkg" / "b.py").write_text(new_body, encoding="utf-8")
        diff = "--- a/pkg/b.py\n+++ b/pkg/b.py\n@@ -1,2 +1,2 @@\n def compute(x: int) -> int:\n-    return x + 1\n+" + long_line
        _write_diff(root, "a.diff", diff)
        res = _run(root, "a.diff")
        if res["ruff"] == "UNAVAILABLE":
            self.skipTest("ruff not on this interpreter")
        self.assertEqual(res["gate"], "PASS")
        art = json.loads((root / "_out" / "triage.json").read_text())
        adv = [a for a in art["advisory_findings"] if a["code"].startswith("E501")]
        self.assertTrue(adv)


if __name__ == "__main__":
    unittest.main()
