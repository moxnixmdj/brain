#!/usr/bin/env python3
"""Honest tests for the code-repair drive (SPECIALIST path, real files)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from canonical.swe_kernel import perfect_algorithm_v1 as pa
from canonical.swe_kernel.code_repair_env_v1 import drive_code_repair
from canonical.swe_kernel.lesson_admission_gate_v1 import Victim


class CodeRepairDriveTests(unittest.TestCase):

    def test_drive_admits_once_and_replays_on_a_fresh_defect(self):
        with tempfile.TemporaryDirectory() as td:
            mem = Path(td) / "memory.json"
            mem_init = pa.load_memory(mem)

            # the one demonstrated repair
            BEFORE = "def check(x):\n    return x <= 100\n"
            AFTER = "def check(x):\n    return x < 100\n"

            def strict(_src, point):
                return point < 100

            victims = [
                Victim("transfer", "def count_ok(z):\n    return z <= 100\n",
                       strict, (0, 99, 100, 101, 1001, 5000)),
                Victim("guarded", "def bounded(n):\n    if n > 1000:\n        return n <= 100\n    return n < 100\n",
                       strict, (0, 99, 100, 101, 1001, 5000)),
            ]

            out = drive_code_repair(
                goal="make the strict boundary condition strict",
                demo_before=BEFORE,
                demo_after=AFTER,
                victims=victims,
                fresh_source="def count_ok(n):\n    return n <= 100\n",
                fresh_oracle=strict,
                fresh_probes=[0, 99, 100, 101, 1001, 5000],
                fresh_test_files=(
                    "count_ok_fresh",
                    "from count_ok_fresh import count_ok\n"
                    "assert count_ok(99) is True\n"
                    "assert count_ok(100) is False\n"
                    "assert count_ok(0) is True\n"
                    "print('PASS')\n",
                ),
                memory_path_=mem,
            )

            self.assertEqual(out["verdict"], "ADMIT", out)
            self.assertTrue(out["persisted"])
            self.assertTrue(out["learn"]["persist"])
            self.assertEqual(out["learn"]["verdict"], "ADMIT")
            self.assertEqual(out["replay"]["verdict"], "PASS__REPLAYED_AND_REPAIRED")
            self.assertTrue(out["replay"]["passed"])
            self.assertTrue(out["fresh_real_test"]["verified"])
            self.assertEqual(
                out["fresh_real_test"]["stdout"].strip(),
                "PASS",
            )
            self.assertTrue(out["learn"]["counts"].get("repaired", 0) >= 1)

    def test_drive_refuses_with_no_victims(self):
        out = drive_code_repair(
            goal="make it strict",
            demo_before="def check(x):\n    return x <= 100\n",
            demo_after="def check(x):\n    return x < 100\n",
            victims=[],
            fresh_source="def count_ok(z):\n    return z <= 100\n",
            fresh_oracle=lambda _s, p: p < 100,
            fresh_probes=[0, 100],
        )
        self.assertEqual(out["verdict"], "REFUSED")
        self.assertFalse(out["persisted"])

    def test_drive_does_not_persist_harmful_lesson(self):
        with tempfile.TemporaryDirectory() as td:
            mem = Path(td) / "memory.json"

            # harmful victim: correct under an inclusive contract, broke by the lesson
            def inclusive_spec(_src, point):
                return point <= 100

            harmful = Victim("inclusive_keep",
                             "def guarded(n):\n    return n <= 100\n",
                             inclusive_spec, (0, 99, 100, 101, 1001, 5000))

            out = drive_code_repair(
                goal="make it strict",
                demo_before="def check(x):\n    return x <= 100\n",
                demo_after="def check(x):\n    return x < 100\n",
                victims=[harmful],
                fresh_source="def count_ok(z):\n    return z <= 100\n",
                fresh_oracle=lambda _s, p: p < 100,
                fresh_probes=[0, 100, 101],
                memory_path_=mem,
            )
            self.assertIn(out["verdict"], ("REJECT", "REFINE", "REFUSED"))
            self.assertFalse(out["persisted"])


if __name__ == "__main__":
    unittest.main()
