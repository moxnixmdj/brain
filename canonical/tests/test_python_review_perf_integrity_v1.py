"""Safety controls for the host-executed review performance gate."""
from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from canonical.runtime.bound_capabilities import python_review_diff_perf_gate as gate

DIFF = """--- a/m.py
+++ b/m.py
@@ -1 +1 @@
-value = 1
+value = 2
"""


class PerfGateIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="brain-perf-integrity-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.anchor = self.root / "anchor"
        self.anchor.mkdir()
        (self.anchor / "m.py").write_text("value = 1\n")
        (self.anchor / "bench.py").write_text("def bench(): return 1\n")
        (self.root / "patch.diff").write_text(DIFF)
        self.args = {"anchor_path": "anchor", "diff_path": "patch.diff",
                     "bench_path": "bench.py", "output_path": "out/report.json"}

    def test_existing_predictable_scratch_is_never_deleted(self):
        old = self.root / "out" / ("_perf_anchor_" + hashlib.sha256(DIFF.encode()).hexdigest()[:12])
        old.mkdir(parents=True)
        (old / "sentinel").write_text("do not delete")
        with mock.patch.object(gate, "_bench", return_value=([10] * 5, [10] * 5)):
            gate.run(self.args, self.root)
        self.assertEqual((old / "sentinel").read_text(), "do not delete")

    def test_output_cannot_replace_diff_or_any_anchor_file(self):
        diff = (self.root / "patch.diff").read_bytes()
        source = (self.anchor / "m.py").read_bytes()
        for target in ("patch.diff", "anchor/m.py", "anchor/result.json"):
            with self.subTest(target=target):
                with self.assertRaises(SystemExit) as exc:
                    gate.run({**self.args, "output_path": target}, self.root)
                self.assertIn("OUTPUT_OVERLAPS_INPUT", str(exc.exception))
                self.assertEqual((self.root / "patch.diff").read_bytes(), diff)
                self.assertEqual((self.anchor / "m.py").read_bytes(), source)

    def test_benchmark_cannot_escape_anchor(self):
        (self.root / "outside.py").write_text("def bench(): return 1\n")
        with self.assertRaises(SystemExit) as exc:
            gate.run({**self.args, "bench_path": "../outside.py"}, self.root)
        self.assertIn("BENCH_PATH_ESCAPE", str(exc.exception))

    def test_child_timings_must_be_positive_integers(self):
        class Proc:
            returncode = 0
            stdout = '{"runs_ns": [-1, -1, -1], "calib_ns": [1, 1, 1]}'
            stderr = ""
        with mock.patch.object(gate.subprocess, "run", return_value=Proc()):
            with self.assertRaises(SystemExit) as exc:
                gate._bench(self.anchor, "bench.py", "python", 3, 1)
        self.assertIn("BENCH_OUTPUT_SHAPE_UNEXPECTED", str(exc.exception))


if __name__ == "__main__":
    unittest.main()
