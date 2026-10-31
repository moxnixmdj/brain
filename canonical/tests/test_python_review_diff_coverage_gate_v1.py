# PROJECT_BRAIN
"""Pins for python.review.diff_coverage_gate.v1 — the senior "every changed
line must be executed" gate.  Paired worlds: a covered change PASSES, the
same-shaped uncovered change FAILS with the exact missing lines named.

Run: python -m pytest canonical/tests/test_python_review_diff_coverage_gate_v1.py -q
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
    python_review_diff_coverage_gate as gate,
)

PY = sys.executable
PY_ANCHOR = """def add(a: int, b: int) -> int:
    return a + b
"""
PY_TEST = """import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pkg.m import add


def test_add():
    assert add(1, 2) == 3
"""

# adds a covered function (test exists) — def line 5 executes at import,
# body line 6 executed by the test
COVERED_DIFF = """--- a/pkg/m.py
+++ b/pkg/m.py
@@ -1,2 +1,6 @@
 def add(a: int, b: int) -> int:
     return a + b
+
+
+def mul(a: int, b: int) -> int:
+    return a * b
--- a/tests/test_m.py
+++ b/tests/test_m.py
@@ -6,2 +6,7 @@
 def test_add():
     assert add(1, 2) == 3
+
+
+def test_mul():
+    from pkg.m import mul
+    assert mul(2, 3) == 6
"""

# identical shape but NO test for the added function -> body line uncovered
UNCOVERED_DIFF = """--- a/pkg/m.py
+++ b/pkg/m.py
@@ -1,2 +1,6 @@
 def add(a: int, b: int) -> int:
     return a + b
+
+
+def div(a: int, b: int) -> float:
+    return a / b
"""


def _build(root: Path, with_tests: bool = True) -> Path:
    anchor = root / "anchor"
    (anchor / "pkg").mkdir(parents=True)
    (anchor / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (anchor / "pkg" / "m.py").write_text(PY_ANCHOR, encoding="utf-8")
    if with_tests:
        (anchor / "tests").mkdir(parents=True)
        (anchor / "tests" / "test_m.py").write_text(PY_TEST, encoding="utf-8")
    return anchor


def _manifest(path: Path) -> str:
    rows = []
    for f in sorted(path.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts and f.name != ".coverage":
            rows.append(str(f.relative_to(path)) + ":" + hashlib.sha256(f.read_bytes()).hexdigest())
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def _run(root: Path, diff_rel: str, py: str = PY, out_rel: str = "_out/cov.json"):
    return gate.run({
        "anchor_path": "anchor",
        "diff_path": diff_rel,
        "output_path": out_rel,
        "python_executable": py,
        "timeout_s": 180,
    }, root)


class TestDiffCoverageGate(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="covgate_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _have_coverage(self) -> bool:
        p = subprocess.run([PY, "-m", "coverage", "--version"],
                           capture_output=True, text=True)
        return p.returncode == 0

    def test_covered_change_passes(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(COVERED_DIFF, encoding="utf-8")
        res = _run(self.tmp, "d.diff")
        if not self._have_coverage():
            self.skipTest("coverage not on this interpreter")
        self.assertEqual(res["gate"], "UNRESOLVED__UNAUTHENTICATED_EVIDENCE")
        self.assertEqual(res["local_gate"], "PASS")
        self.assertEqual(res["diff_covered_ratio"], 1.0)
        self.assertFalse(res["verified"])

    def test_uncovered_change_fails_with_named_lines(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(UNCOVERED_DIFF, encoding="utf-8")
        res = _run(self.tmp, "d.diff")
        if not self._have_coverage():
            self.skipTest("coverage not on this interpreter")
        self.assertEqual(res["gate"], "FAIL")
        self.assertFalse(res["verified"])
        art = json.loads((self.tmp / "_out/cov.json").read_text())
        self.assertEqual(art["diff_miss_lines"], [{"file": "pkg/m.py", "line": 6}])

    def test_byte_identical_rerun(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(COVERED_DIFF, encoding="utf-8")
        _run(self.tmp, "d.diff")
        first = (self.tmp / "_out/cov.json").read_bytes()
        _run(self.tmp, "d.diff")
        self.assertEqual(first, (self.tmp / "_out/cov.json").read_bytes())

    def test_anchor_never_mutated(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(UNCOVERED_DIFF, encoding="utf-8")
        before = _manifest(self.tmp / "anchor")
        _run(self.tmp, "d.diff")
        self.assertEqual(before, _manifest(self.tmp / "anchor"))

    def test_coverage_absent_degrades_loudly(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(COVERED_DIFF, encoding="utf-8")
        res = _run(self.tmp, "d.diff", py="/usr/bin/false") \
            if False else gate.run({
                "anchor_path": "anchor", "diff_path": "d.diff",
                "output_path": "_out/cov.json",
                "python_executable": "/usr/bin/false", "timeout_s": 60}, self.tmp)
        # /usr/bin/false cannot probe coverage NOR run pytest: pytest call rc!=0
        # -> suite_green False -> FAIL, never a silent pass
        self.assertIn(res["gate"], ("FAIL", "PASS_BLIND"))
        self.assertFalse(res["verified"])
        art = json.loads((self.tmp / "_out/cov.json").read_text())
        self.assertEqual(art["coverage_tool"], "UNAVAILABLE")

    def test_empty_diff_refuses(self):
        _build(self.tmp)
        (self.tmp / "e.diff").write_text("", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "e.diff")
        self.assertIn("DIFF_EMPTY", str(ctx.exception))

    def test_no_tests_refuses(self):
        _build(self.tmp, with_tests=False)
        (self.tmp / "d.diff").write_text(UNCOVERED_DIFF, encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "d.diff")
        self.assertIn("NO_TESTS_DISCOVERED", str(ctx.exception))

    def test_bogus_diff_refuses(self):
        _build(self.tmp)
        (self.tmp / "bad.diff").write_text(
            "--- a/pkg/m.py\n+++ b/pkg/m.py\n@@ -99,1 +99,1 @@\n-def x():\n+def y():\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "bad.diff")
        self.assertIn("DIFF_DOES_NOT_APPLY", str(ctx.exception))

    def test_red_suite_refuses_not_zero_coverage(self):
        _build(self.tmp)
        broken = COVERED_DIFF + """--- a/tests/test_m.py
+++ b/tests/test_m.py
@@ -10,3 +10,5 @@
 def test_mul():
     from pkg.m import mul
     assert mul(2, 3) == 6
+
+    assert False, "detonator"
"""
        (self.tmp / "red.diff").write_text(broken, encoding="utf-8")
        if not self._have_coverage():
            self.skipTest("coverage not present")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "red.diff")
        self.assertIn("SUITE_RED", str(ctx.exception))

    def test_path_escape_refuses(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(COVERED_DIFF, encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "../out.diff")
        self.assertIn("PATH_ESCAPE", str(ctx.exception))

    def test_scratch_removed(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(COVERED_DIFF, encoding="utf-8")
        _run(self.tmp, "d.diff")
        leftovers = [p for p in (self.tmp / "_out").iterdir() if p.name.startswith("_cov_tree_")]
        self.assertEqual(leftovers, [])

    def test_threshold_parameter_respected(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(UNCOVERED_DIFF, encoding="utf-8")
        res = gate.run({
            "anchor_path": "anchor", "diff_path": "d.diff",
            "output_path": "_out/cov2.json", "python_executable": PY,
            "timeout_s": 180, "min_coverage_ratio": 0.5}, self.tmp)
        if not self._have_coverage():
            self.skipTest("coverage not present")
        # changed executable lines {1,2,5,6}; only body line 6 misses -> 3/4
        self.assertEqual(res["gate"], "UNRESOLVED__UNAUTHENTICATED_EVIDENCE")
        self.assertEqual(res["local_gate"], "PASS")
        self.assertEqual(res["diff_covered_ratio"], 0.75)

    def test_schema_and_sha_pins(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(COVERED_DIFF, encoding="utf-8")
        _run(self.tmp, "d.diff")
        art = json.loads((self.tmp / "_out/cov.json").read_text())
        self.assertEqual(art["diff_sha256"],
                         hashlib.sha256(COVERED_DIFF.encode()).hexdigest())
        for key in ("schema", "gate", "gate_law", "diff_miss_lines",
                    "diff_covered_ratio", "diff_executable_lines",
                    "tests_discovered", "coverage_tool", "complete"):
            self.assertIn(key, art)


if __name__ == "__main__":
    unittest.main()
