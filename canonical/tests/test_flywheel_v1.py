"""Regression: the flywheel actually turns.

For as long as `from credit_gates_v1 import e_process` was the only import
attempted, the module resolved only when canonical/runtime/ happened to be on
sys.path. Everywhere else it raised ModuleNotFoundError, the except branch fell
through to a `mean` it had never bound, and status() -- and therefore record()
-- died with UnboundLocalError on every single call.

The consequences were silent and total: nothing was ever recorded, so nothing
was ever credited, so primers() was always empty, so no run was ever told
anything before it acted. The flywheel looked installed and was not turning.

experience_v1._e_value already tried both import paths; flywheel_v1 did not.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from canonical.runtime import flywheel_v1 as F


class FlywheelTurns(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self._tmp.name, "flywheel.json")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # ---------------------------------------------------------- the regression
    def test_record_does_not_raise(self):
        """Before the fix this raised UnboundLocalError on every call."""
        out = F.record("reading a file", "ENOENT", True, path=self.path)
        self.assertIsInstance(out, dict)
        self.assertIn("n", out)

    def test_status_does_not_raise_and_reports_observations(self):
        F.record("reading a file", "ENOENT", True, path=self.path)
        F.record("reading a file", "ENOENT", True, path=self.path)
        st = F.status(F.cell_of("reading a file", "ENOENT"), path=self.path)
        self.assertEqual(st["n"], 2)
        self.assertIn("mean", st)
        self.assertIn("e_value", st)

    def test_cells_is_enumerable(self):
        """Before the fix, cells() died with UnboundLocalError too."""
        F.record("reading a file", "ENOENT", True, path=self.path)
        self.assertEqual(len(F.cells(path=self.path)), 1)

    # --------------------------------------------------------------- the gate
    def test_consistent_success_earns_credit(self):
        for _ in range(10):
            F.record("reading a file", "ENOENT", True, path=self.path)
        st = F.status(F.cell_of("reading a file", "ENOENT"), path=self.path)
        self.assertEqual(st["n"], 10)
        self.assertEqual(st["mean"], 1.0)
        self.assertIs(st["credited"], True, st)

    def test_consistent_failure_is_never_credited(self):
        """The sign gate. Strong evidence of HARM is still evidence against the
        null, and is still not grounds for credit."""
        for _ in range(10):
            F.record("x", "y", False, path=self.path)
        st = F.status(F.cell_of("x", "y"), path=self.path)
        self.assertEqual(st["n"], 10)
        self.assertEqual(st["mean"], -1.0)
        self.assertIs(st["credited"], False, st)
        self.assertIn("harmful", st["reason"])

    def test_magnitude_alone_never_credits(self):
        """Both directions accumulate similar e-values; only the sign differs."""
        for _ in range(10):
            F.record("a", "b", True, path=self.path)
        good = F.status(F.cell_of("a", "b"), path=self.path)
        bad_path = os.path.join(self._tmp.name, "bad.json")
        for _ in range(10):
            F.record("a", "b", False, path=bad_path)
        bad = F.status(F.cell_of("a", "b"), path=bad_path)
        self.assertAlmostEqual(good["e_value"], bad["e_value"], places=3)
        self.assertIs(good["credited"], True)
        self.assertIs(bad["credited"], False)

    # ------------------------------------------------------------- keyed right
    def test_memory_is_keyed_on_pathology_not_task(self):
        """(WHERE x WHY) recurs across domains; a task instance does not."""
        self.assertEqual(
            F.cell_of("reading a file", "ENOENT"),
            F.cell_of("reading a file", "ENOENT"),
        )
        self.assertNotEqual(
            F.cell_of("reading a file", "ENOENT"),
            F.cell_of("reading a file", "EACCES"),
        )

    def test_classify_names_a_failure_from_the_error_alone(self):
        where, why = F.classify("FileNotFoundError: [Errno 2] No such file")
        self.assertTrue(where)
        self.assertTrue(why)


if __name__ == "__main__":
    unittest.main()
