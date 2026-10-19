#!/usr/bin/env python3
"""The machine must ask itself what it already knows, before it acts.

Memory existed and nothing consulted it. Every solve re-derived everything from
keyword overlap, so a lesson learned once changed nothing the next time -- the
machine had a past it never used.

These tests cover both halves of "memorizes and retrieves what is important":

  retrieving  -- solve() asks memory what bears on the goal before deciding
  important   -- the outcome then tells memory whether what it offered was
                 worth offering, so importance differentiates over time

Without the second half, every memory sits at the 0.5 prior forever and
"important" never means anything.
"""

from __future__ import annotations

import os
import tempfile
import unittest

from canonical.runtime import live_brain_route_admission_v1 as ra

# a goal that compiles and executes in a bare environment
GOAL = "run shell command echo hello"


class ConsultationTests(unittest.TestCase):
    def setUp(self) -> None:
        from canonical.runtime import associative_memory_v1 as mem
        self.mem = mem
        self._real = mem.DEFAULT_STATE
        self.tmp = tempfile.mkdtemp(prefix="brain-route-mem-")
        mem.DEFAULT_STATE = os.path.join(self.tmp, "mem.json")

    def tearDown(self) -> None:
        self.mem.DEFAULT_STATE = self._real
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    # --- it asks ---------------------------------------------------------------

    def test_solve_consults_memory(self):
        r = ra.solve({"task_id": "t1", "goal": GOAL})
        self.assertIn("memory_recalled", r, "solve did not ask memory anything")

    def test_consultation_does_not_change_the_verdict(self):
        """Memory informs; it does not overrule. The measured path must not move."""
        r = ra.solve({"task_id": "t1", "goal": GOAL})
        self.assertTrue(r.get("pass") is True, r.get("status"))
        self.assertIn("PASS__RAW_GOAL_COMPILED", str(r.get("status")))

    def test_a_remembered_lesson_is_surfaced_for_a_related_goal(self):
        self.mem.remember("shell command run echo hello works with argv",
                          kind="procedure")
        recalled = ra._recall_for(GOAL)
        self.assertTrue(recalled, "memory held a relevant lesson and was not asked")

    # --- outcomes teach it what mattered ---------------------------------------

    def test_success_raises_the_importance_of_what_was_offered(self):
        eid = self.mem.remember("shell command run via argv list", kind="procedure")
        before = self.mem.stats()["max_importance"]
        rows = ra._recall_for(GOAL)
        ra._credit_recall(rows, succeeded=True)
        entry = self.mem._load(self.mem.DEFAULT_STATE)["entries"][eid]
        self.assertGreater(float(entry.get("credited") or 0), 0)
        self.assertGreater(self.mem.stats()["max_importance"], before)

    def test_failure_lowers_the_importance_of_what_was_offered(self):
        eid = self.mem.remember("a misleading lesson about shell commands",
                                kind="procedure")
        rows = ra._recall_for(GOAL)
        ra._credit_recall(rows, succeeded=False)
        entry = self.mem._load(self.mem.DEFAULT_STATE)["entries"][eid]
        self.assertGreater(float(entry.get("blamed") or 0), 0)
        self.assertLess(float(entry.get("credited") or 0), 1)

    def test_a_real_solve_teaches_memory_something(self):
        """End to end: the outcome of a real execution moves importance."""
        self.mem.remember("shell command echo hello", kind="procedure")
        before = self.mem.stats()["max_importance"]
        ra.solve({"task_id": "t1", "goal": GOAL})
        self.assertNotEqual(self.mem.stats()["max_importance"], before)

    # --- safety ---------------------------------------------------------------

    def test_broken_memory_never_breaks_the_live_path(self):
        self.mem.DEFAULT_STATE = "/nonexistent/deeply/broken/mem.json"
        try:
            self.assertEqual(ra._recall_for(GOAL), [])
            r = ra.solve({"task_id": "t1", "goal": GOAL})
            self.assertTrue(r.get("pass") is True, r.get("status"))
        finally:
            self.mem.DEFAULT_STATE = os.path.join(self.tmp, "mem.json")

    def test_credit_tolerates_junk_rows(self):
        ra._credit_recall([{"id": "nope"}, {}, None], succeeded=True)

    def test_empty_recall_is_harmless(self):
        ra._credit_recall([], succeeded=True)


if __name__ == "__main__":
    unittest.main()
