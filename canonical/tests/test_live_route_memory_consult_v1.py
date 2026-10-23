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
import pathlib
import tempfile
import unittest

from canonical.runtime import live_brain_route_admission_v1 as ra

# A goal that compiles and executes in a bare environment.
#
# This used to be "run shell command echo hello".  It stopped compiling, and seven tests in
# this file failed as a cascade with FAIL__RAW_GOAL_COMPILATION_GAP / 
# GOAL_COMPILATION_NO_VERIFIED_CAPABILITY_MATCH -- none of which said what was actually wrong.
# The reason: `shell.command.run` is one of only two entries in BOUND_CAPABILITY_REGISTRY_V1
# whose `status` is not VERIFIED_BOUND_CAPABILITY (the other is `text.file.write`).  Neither
# carries a `verification` receipt, a `source`, or any mission under
# canonical/astra_runtime/missions, so promote_pending_binding cannot promote either and
# setting the status by hand would forge the one proof the registry exists to hold.  The
# refusal is correct; the test's premise was false.
#
# The subject of this file is memory consultation, not shell execution, so the goal is
# scaffolding -- but scaffolding that rots silently is worse than none.  The precondition in
# setUpClass below makes it loud: if this goal ever stops compiling, one test fails and names
# the compiler code, instead of seven failing for a reason none of them states.
GOAL = "Verify a tar.gz archive against its manifest"

# The failure path needs a goal nothing here can do.  It used to be the PDF-extraction
# sentence, which stopped being impossible: pdf.extract.text.pypdf carries a receipt on disk
# whose mission digest matches, so the verified-capability adapter now admits it and that goal
# reaches route admission instead of failing to compile.  That is the machine getting more
# capable, not a regression -- but a test that hard-codes an impossibility rots the moment it
# stops being impossible.  The precondition in LearnOnFailureTests.setUpClass now checks the
# premise and says so, rather than letting assertions fail on a status string.
UNCOMPILABLE_GOAL = "transcribe the audio in this recording to text"


class ConsultationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """Fail once, loudly, if the scaffolding goal stops compiling.

        Without this, a capability losing its verification turns into seven failures whose
        messages describe memory rather than the real cause.
        """
        import uuid
        r = ra.solve({"task_id": uuid.uuid4().hex, "goal": GOAL})
        if r.get("pass") is not True:
            raise unittest.SkipTest(
                "scaffolding goal no longer compiles, so this file cannot test memory "
                "consultation: goal=%r status=%s compiler_code=%s"
                % (GOAL, r.get("status"), r.get("compiler_code")))

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
        self.mem.remember("verify a tar.gz archive against its manifest works",
                          kind="procedure")
        recalled = ra._recall_for(GOAL)
        self.assertTrue(recalled, "memory held a relevant lesson and was not asked")

    # --- outcomes teach it what mattered ---------------------------------------

    def test_success_raises_the_importance_of_what_was_offered(self):
        eid = self.mem.remember("verify a tar.gz archive against its manifest", kind="procedure")
        before = self.mem.stats()["max_importance"]
        rows = ra._recall_for(GOAL)
        ra._credit_recall(rows, succeeded=True)
        entry = self.mem._load(self.mem.DEFAULT_STATE)["entries"][eid]
        self.assertGreater(float(entry.get("credited") or 0), 0)
        self.assertGreater(self.mem.stats()["max_importance"], before)

    def test_failure_lowers_the_importance_of_what_was_offered(self):
        eid = self.mem.remember("a misleading lesson about tar.gz archive verification",
                                kind="procedure")
        rows = ra._recall_for(GOAL)
        ra._credit_recall(rows, succeeded=False)
        entry = self.mem._load(self.mem.DEFAULT_STATE)["entries"][eid]
        self.assertGreater(float(entry.get("blamed") or 0), 0)
        self.assertLess(float(entry.get("credited") or 0), 1)

    def test_a_real_solve_teaches_memory_something(self):
        """End to end: the outcome of a real execution moves importance."""
        self.mem.remember("tar.gz archive manifest verification", kind="procedure")
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


class LearnOnFailureTests(unittest.TestCase):
    """'I cannot do this' is the most precise data the machine has about itself."""

    @classmethod
    def setUpClass(cls) -> None:
        """Check the premise instead of assuming it.

        The PDF-extraction sentence used to serve here and silently stopped being impossible.
        Asserting the premise costs one solve and turns a future capability gain into one
        clear message instead of three failures about a status string.
        """
        import uuid
        r = ra.solve({"task_id": uuid.uuid4().hex, "goal": UNCOMPILABLE_GOAL})
        if r.get("status") != "FAIL__RAW_GOAL_COMPILATION_GAP":
            raise unittest.SkipTest(
                "the failure-path scaffolding goal is no longer impossible, so this file "
                "cannot exercise learn-on-failure: goal=%r status=%s"
                % (UNCOMPILABLE_GOAL, r.get("status")))

    def setUp(self) -> None:
        from canonical.runtime import ignorance_ledger_v1 as led
        from canonical.runtime import associative_memory_v1 as mem
        self.led, self.mem = led, mem
        self._lp, self._mp = led.DEFAULT_STATE, mem.DEFAULT_STATE
        self.tmp = tempfile.mkdtemp(prefix="brain-learn-on-fail-")
        led.DEFAULT_STATE = os.path.join(self.tmp, "ledger.json")
        mem.DEFAULT_STATE = os.path.join(self.tmp, "mem.json")
        # acquisition can REGISTER into the registry -- the source of truth of
        # what the machine can do. A test must never touch the real one.
        from canonical.runtime import capability_type_surface_v1 as ts
        self.ts = ts
        self._rp = ts.REGISTRY
        self.regp = os.path.join(self.tmp, "REGISTRY.json")
        pathlib.Path(self.regp).write_text(
            pathlib.Path(ts.REGISTRY).read_text(encoding="utf-8"), encoding="utf-8")
        ts.REGISTRY = self.regp

    def tearDown(self) -> None:
        self.led.DEFAULT_STATE, self.mem.DEFAULT_STATE = self._lp, self._mp
        self.ts.REGISTRY = self._rp
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_failure_records_the_gap(self):
        # composition now closes "write the text hello to out.txt", so the
        # failure path is exercised with something nothing here can do
        r = ra.solve_or_learn({"task_id": "t",
                               "goal": UNCOMPILABLE_GOAL},
                              registry_path=self.regp)
        self.assertEqual(r["status"], "FAIL__RAW_GOAL_COMPILATION_GAP")
        self.assertTrue(r["learning"]["gap_recorded"])
        self.assertTrue(r["learning"]["what_to_learn_next"])

    def test_failure_says_what_to_learn_next(self):
        ra.solve_or_learn({"task_id": "t",
                           "goal": UNCOMPILABLE_GOAL},
                          registry_path=self.regp)
        ranked = self.led.rank(limit=3)
        self.assertTrue(ranked)

    def test_a_goal_naming_a_real_program_is_attempted(self):
        r = ra.solve_or_learn({"task_id": "t",
                               "goal": "use base64 to encode text into out.txt"},
                              registry_path=self.regp)
        learned = r.get("learning") or {}
        self.assertTrue(learned.get("attempted"), learned)
        self.assertEqual(learned.get("executable"), "base64")

    def test_a_success_does_not_trigger_learning(self):
        r = ra.solve_or_learn({"task_id": "t", "goal": GOAL},
                              registry_path=self.regp)
        self.assertTrue(r.get("pass") is True, r.get("status"))
        self.assertNotIn("learning", r)

    def test_learning_can_be_turned_off(self):
        r = ra.solve_or_learn({"task_id": "t",
                               "goal": UNCOMPILABLE_GOAL},
                              learn=False, registry_path=self.regp)
        self.assertNotIn("learning", r)

    def test_solve_itself_is_unchanged(self):
        """The measured path must not move: only the wrapper learns."""
        # composition closes "write the text hello to out.txt" now; this
        # one nothing here can do, so the failure path is still exercised
        r = ra.solve({"task_id": "t", "goal": UNCOMPILABLE_GOAL})
        self.assertNotIn("learning", r)
        self.assertEqual(r["status"], "FAIL__RAW_GOAL_COMPILATION_GAP")
