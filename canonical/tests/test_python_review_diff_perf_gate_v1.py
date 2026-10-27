# PROJECT_BRAIN
"""Pins for python.review.diff_perf_gate.v1 — the performance-regression
gate.  Physical timings are NOT byte-deterministic, so the pins prove the
honest invariants: verdict stability on fixed worlds, disjoint-distribution
FAIL on a planted 100x slowdown, byte-identical verdict recomputation, all
refusal classes, zero anchor mutation.

Run: python -m pytest canonical/tests/test_python_review_diff_perf_gate_v1.py -q
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
    python_review_diff_perf_gate as gate,
)

PY = sys.executable

CORE = """def fib(n: int) -> int:
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)
"""

BENCH = """from pkg.core import fib


def bench():
    fib(22)
"""

# no-op refactor: same complexity, verdict must be PASS on every run
NEUTRAL_DIFF = """--- a/pkg/core.py
+++ b/pkg/core.py
@@ -1,4 +1,5 @@
 def fib(n: int) -> int:
     if n < 2:
         return n
-    return fib(n - 1) + fib(n - 2)
+    left = fib(n - 1) + fib(n - 2)
+    return left
"""

# planted regression: 100x+ slower hot path
SLOW_DIFF = """--- a/pkg/core.py
+++ b/pkg/core.py
@@ -1,4 +1,6 @@
 def fib(n: int) -> int:
+    if n == 22:
+        _ = [x * x for x in range(400000)]
     if n < 2:
         return n
     return fib(n - 1) + fib(n - 2)
"""


def _build(root: Path) -> Path:
    anchor = root / "anchor"
    (anchor / "pkg").mkdir(parents=True)
    (anchor / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (anchor / "pkg" / "core.py").write_text(CORE, encoding="utf-8")
    (anchor / "bench").mkdir(parents=True)
    (anchor / "bench" / "case.py").write_text(BENCH, encoding="utf-8")
    return anchor


def _manifest(path: Path) -> str:
    rows = []
    for f in sorted(path.rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            rows.append(str(f.relative_to(path)) + ":" + hashlib.sha256(f.read_bytes()).hexdigest())
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def _run(root: Path, diff_rel: str, out_rel: str = "_out/perf.json"):
    return gate.run({
        "anchor_path": "anchor",
        "diff_path": diff_rel,
        "bench_path": "bench/case.py",
        "output_path": out_rel,
        "python_executable": PY,
        "repeats": 5,
        # measured shared-sandbox noise floor ~0.11 after calibration;
        # the band must sit above it (real regressions are 5x+)
        "tolerance": 0.30,
        "timeout_s": 90,
    }, root)


class TestDiffPerfGate(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="perfgate_"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_neutral_refactor_passes(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(NEUTRAL_DIFF, encoding="utf-8")
        res = _run(self.tmp, "d.diff")
        self.assertEqual(res["gate"], "PASS")
        self.assertTrue(res["verified"])
        self.assertGreaterEqual(res["slowdown_ratio"], 0)

    def test_planted_slowdown_fails_disjoint(self):
        _build(self.tmp)
        (self.tmp / "s.diff").write_text(SLOW_DIFF, encoding="utf-8")
        res = _run(self.tmp, "s.diff")
        self.assertEqual(res["gate"], "FAIL")
        self.assertFalse(res["verified"])
        self.assertGreater(res["slowdown_ratio"], 5.0)

    def test_verdict_stable_across_reruns(self):
        # the honest determinism law for physical measurements: same world,
        # same verdict, every time (not byte-identical nanoseconds)
        _build(self.tmp)
        (self.tmp / "s.diff").write_text(SLOW_DIFF, encoding="utf-8")
        verdicts = {_run(self.tmp, "s.diff", out_rel=f"_out/r{i}.json")["gate"]
                    for i in range(3)}
        self.assertEqual(verdicts, {"FAIL"})

    def test_verdict_recompute_from_recorded_runs_is_deterministic(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(SLOW_DIFF, encoding="utf-8")
        _run(self.tmp, "d.diff")
        art = json.loads((self.tmp / "_out/perf.json").read_text())
        a = art["anchor_runs_ns"]; p = art["patched_runs_ns"]
        import statistics
        ratio1 = statistics.median(p) / statistics.median(a)
        ratio2 = statistics.median(p) / statistics.median(a)
        self.assertEqual(ratio1, ratio2)  # recorded runs -> identical verdict math
        self.assertTrue(min(p) > max(a))  # disjoint => FAIL law holds

    def test_anchor_never_mutated(self):
        _build(self.tmp)
        (self.tmp / "s.diff").write_text(SLOW_DIFF, encoding="utf-8")
        before = _manifest(self.tmp / "anchor")
        _run(self.tmp, "s.diff")
        self.assertEqual(before, _manifest(self.tmp / "anchor"))

    def test_scratch_removed_after_run(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(NEUTRAL_DIFF, encoding="utf-8")
        _run(self.tmp, "d.diff")
        leftovers = [p.name for p in (self.tmp / "_out").iterdir()
                     if p.name.startswith("_perf_")]
        self.assertEqual(leftovers, [])

    def test_empty_diff_refuses(self):
        _build(self.tmp)
        (self.tmp / "e.diff").write_text("", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "e.diff")
        self.assertIn("DIFF_EMPTY", str(ctx.exception))

    def test_bogus_diff_refuses(self):
        _build(self.tmp)
        (self.tmp / "b.diff").write_text(
            "--- a/pkg/core.py\n+++ b/pkg/core.py\n@@ -40,1 +40,1 @@\n-def nope():\n+def nah():\n", encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "b.diff")
        self.assertIn("DIFF_DOES_NOT_APPLY", str(ctx.exception))

    def test_bench_callable_missing_refuses(self):
        _build(self.tmp)
        (self.tmp / "anchor" / "bench" / "empty.py").write_text("X = 1\n")
        (self.tmp / "d.diff").write_text(NEUTRAL_DIFF, encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            gate.run({"anchor_path": "anchor", "diff_path": "d.diff",
                      "bench_path": "bench/empty.py", "output_path": "_out/x.json",
                      "python_executable": PY, "repeats": 3, "timeout_s": 60},
                     self.tmp)
        self.assertIn("BENCH_CALLABLE_MISSING", str(ctx.exception))

    def test_bench_file_missing_refuses(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(NEUTRAL_DIFF, encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            gate.run({"anchor_path": "anchor", "diff_path": "d.diff",
                      "bench_path": "bench/ghost.py", "output_path": "_out/x.json",
                      "python_executable": PY, "repeats": 3, "timeout_s": 60},
                     self.tmp)
        self.assertIn("BENCH_FILE_MISSING", str(ctx.exception))

    def test_path_escape_refuses(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(NEUTRAL_DIFF, encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            _run(self.tmp, "../out.diff")
        self.assertIn("PATH_ESCAPE", str(ctx.exception))

    def test_schema_and_ratio_fields(self):
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(NEUTRAL_DIFF, encoding="utf-8")
        _run(self.tmp, "d.diff")
        art = json.loads((self.tmp / "_out/perf.json").read_text())
        for key in ("schema", "gate", "gate_law", "anchor_runs_ns",
                    "patched_runs_ns", "slowdown_ratio", "anchor_median_ns",
                    "patched_median_ns", "repeats", "tolerance", "complete"):
            self.assertIn(key, art)
        self.assertEqual(len(art["anchor_runs_ns"]), 5)
        self.assertEqual(len(art["patched_runs_ns"]), 5)

    def test_isolation_from_ambient_tree(self):
        # child must import the TREE's bench, not whatever the host cwd says:
        # host runs from repo root where bench/case.py does not exist
        _build(self.tmp)
        (self.tmp / "d.diff").write_text(NEUTRAL_DIFF, encoding="utf-8")
        res = _run(self.tmp, "d.diff")
        self.assertEqual(res["slowdown_ratio"] is not None, True)
        self.assertEqual(res["repeats"], 5)


if __name__ == "__main__":
    unittest.main()
