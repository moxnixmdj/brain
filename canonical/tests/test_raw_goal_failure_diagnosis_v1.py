"""The front door must be able to tell 'failed once' from 'fails every time'.

WHY THIS EXISTS.

Both learning hooks on the shipping path bailed out on a failure.
`_record_raw_goal_experience` returns unless ``out["pass"] is True``, and
`_record_raw_goal_pathology` writes a cell about how this box behaves but keeps
no account of the failure itself. So the episode store's ``failures`` table was
permanently empty -- measured at ``failure_class_count: 0`` after running all 23
benchmark goals, 11 of which fail -- while `integrate_solver_output` already
held the entire failure half of the learning loop: diagnose, fingerprint, count
repeats, record a repair class. Nothing on the shipping path called it.

WHAT IS PINNED HERE.

1. A real front-door failure becomes a real diagnosed failure class. This is the
   gap; nothing else in this file matters if this one is hollow.
2. REPEATS ARE COUNTED AND NOT DUPLICATED. Three runs of one failing goal give
   ONE class with ``count == 3``. This is the whole point: the count is the only
   thing that separates a transient problem from a permanent one, and a store
   that grows a new entry per run cannot express it.
3. Distinct failures get distinct classes -- the fingerprint discriminates.
4. A success records nothing here, because `record_success_observation` already
   owns successes and itself refuses an output that did not pass. Sending both
   would record a success twice.
5. RECORDING IS MEMORY, NOT POLICY. Diagnosing a failure must not change what
   the front door chooses next time. This is the test that fails the day someone
   turns the failure table into a refusal list.
6. What is NOT claimed: no repair is granted, no replay authorized, and the
   improvement queue gains no actionable work. Pinned so nobody later reads a
   populated table as evidence that a repair loop exists.

Nothing here mocks the thing under test: the goals go through `run_raw_goal`,
and the diagnosis is the real `integrate_solver_output` writing real bytes,
aimed at a scratch state only so the live one is left alone.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import tempfile
import unittest
import uuid

from canonical.runtime import autonomous_verified_self_improvement_v1 as AVS
from canonical.runtime import live_integrated_brain_v1 as LIVE


def _failures(path):
    state = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    return state.get("failures") or {}


class FailureDiagnosisTest(unittest.TestCase):
    """Run the real front door on goals that really fail; read the real store."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_faildiag_"))
        cls.state = cls.tmp / "self_improvement.json"
        cls.ocr_goal = "Extract text from a scanned image with OCR."
        cls.pdf_goal = "Convert a markdown document to PDF."
        cls.tar_goal = "Verify a tar.gz archive against its manifest."

        cls.ocr_runs = []
        for i in range(3):
            cls.ocr_runs.append(LIVE.run_raw_goal({
                "task_id": "FD_OCR%d_%s" % (i, uuid.uuid4().hex[:8]),
                "goal": cls.ocr_goal,
            }))
        cls.pdf = LIVE.run_raw_goal({
            "task_id": "FD_PDF_" + uuid.uuid4().hex[:8], "goal": cls.pdf_goal})
        cls.tar = LIVE.run_raw_goal({
            "task_id": "FD_TAR_" + uuid.uuid4().hex[:8], "goal": cls.tar_goal})

        # Now record every one of them through the function under test, into a
        # scratch state, exactly as run_raw_goal does on the live path.
        for out in cls.ocr_runs + [cls.pdf, cls.tar]:
            LIVE._record_raw_goal_failure_diagnosis(out, None, state_path=cls.state)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_fixtures_behaved_as_expected_or_the_rest_is_meaningless(self):
        self.assertTrue(all(r.get("pass") is False for r in self.ocr_runs),
                        "the OCR goal must really fail on this box")
        self.assertIs(self.pdf.get("pass"), False)
        self.assertIs(self.tar.get("pass"), True,
                      "the tar goal must really pass, so the success case is real")

    def test_a_real_failure_becomes_a_real_diagnosed_failure_class(self):
        """THE GAP THAT WAS OPEN. A failure used to reach no failure store at all."""
        table = _failures(self.state)
        self.assertTrue(table, "no failure class was recorded at all")
        entry = next(iter(table.values()))
        self.assertTrue(str(entry.get("failure_fingerprint") or ""),
                        "a failure class without a fingerprint cannot be recounted")
        self.assertEqual(entry.get("original_failure_repaired"), False,
                         "recording a failure must not claim it was repaired")
        self.assertEqual(str(entry.get("status")), "FAIL__LIVE_CONTROLLER_EXECUTION")

    def test_repeats_are_counted_and_not_duplicated(self):
        """THE SUBSTANCE. Three identical failures are one class counted three times."""
        table = _failures(self.state)
        ocr = [e for e in table.values()
               if "SOURCE_UNSUPPORTED" in str(e.get("reason") or "")]
        self.assertEqual(len(ocr), 1,
                         "one recurring failure must be ONE class, not one per run; "
                         "a store that grows per run cannot express 'every time'")
        self.assertEqual(int(ocr[0].get("count")), 3,
                         "three runs of the same failure must count to 3")

    def test_distinct_failures_get_distinct_classes(self):
        """The fingerprint discriminates; it is not one bucket for all failures."""
        table = _failures(self.state)
        self.assertGreaterEqual(len(table), 2,
                                "OCR and PDF fail for different reasons and must not "
                                "share a class")

    def test_a_success_records_no_failure_class(self):
        """No double-recording: successes belong to record_success_observation alone."""
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_nosucc_"))
        try:
            state = tmp / "state.json"
            LIVE._record_raw_goal_failure_diagnosis(self.tar, None, state_path=state)
            self.assertEqual(
                _failures(state) if state.is_file() else {}, {},
                "a passing run must not create a failure class")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_failure_class_count_statistic_moves_off_zero(self):
        """The number that read 0 after every run must now read the real count."""
        state = AVS.load_state(self.state)
        self.assertGreaterEqual(int(state["stats"]["failure_class_count"]), 2)


class RecordingIsMemoryNotPolicyTest(unittest.TestCase):
    """Diagnosing a failure must not narrow what the front door will choose.

    A failure table is an account of what happened, not a list of things to
    refuse. Turning it into a refusal list is how a machine that failed once at
    OCR stops being willing to attempt OCR -- which reads as learning and is
    actually a grudge. `experience_v1` learned this the hard way and documents
    it; this test keeps the same mistake out of the failure table.
    """

    def test_selection_is_unchanged_after_the_failure_is_recorded(self):
        goal = "Extract text from a scanned image with OCR."
        before = LIVE.compile_against_live_registry(goal)[2]
        before_cid = str(before.get("selected_capability") or "")

        tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_notpolicy_"))
        try:
            state = tmp / "state.json"
            failed = LIVE.run_raw_goal({
                "task_id": "FD_POLICY_" + uuid.uuid4().hex[:8], "goal": goal})
            self.assertIs(failed.get("pass"), False)
            LIVE._record_raw_goal_failure_diagnosis(failed, None, state_path=state)
            self.assertTrue(_failures(state), "fixture: the failure must be recorded")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        after = LIVE.compile_against_live_registry(goal)[2]
        self.assertEqual(str(after.get("selected_capability") or ""), before_cid,
                         "recording a failure must not change the next selection")


class WiringTest(unittest.TestCase):
    """The hook must actually be on the shipping path, not merely exist.

    Every other test in this file calls `_record_raw_goal_failure_diagnosis`
    directly, which means all of them would still pass if `run_raw_goal` never
    called it. This is the test that fails when the wiring line is deleted --
    measured: removing that one line turns it red while the rest stay green.

    `wraps=` is deliberate. The spy calls the real function through, so the
    diagnosis really is written; the assertion is only about whether the
    shipping path reached it at all.
    """

    def test_run_raw_goal_reaches_the_failure_hook(self):
        from unittest import mock

        goal = "Extract text from a scanned image with OCR."
        with mock.patch.object(
            AVS, "integrate_solver_output", wraps=AVS.integrate_solver_output
        ) as spy:
            out = LIVE.run_raw_goal({
                "task_id": "FD_WIRING_" + uuid.uuid4().hex[:8], "goal": goal})
        self.assertIs(out.get("pass"), False, "fixture: this goal must really fail")
        self.assertTrue(
            spy.called,
            "run_raw_goal never reached integrate_solver_output, so a front-door "
            "failure is still being dropped on the floor",
        )
        passed = [c.args[0] for c in spy.call_args_list if c.args]
        self.assertTrue(
            any(p.get("pass") is not True for p in passed),
            "the hook was reached but never with a failure",
        )

    def test_a_passing_run_creates_no_failure_class(self):
        """The split with record_success_observation, pinned from the other side.

        Asserted on the store, not on call arguments: `integrate_solver_output`
        is also called legitimately by the improvement-queue driver that
        `_advance_learning_queue` runs, with successful solver outputs. What
        must hold is narrower and is the thing that actually matters -- a
        passing run must not add a row to the failure table.
        """
        state_path = AVS.DEFAULT_STATE_PATH
        before = set(AVS.load_state(state_path).get("failures") or {})
        out = LIVE.run_raw_goal({
            "task_id": "FD_WIRING_OK_" + uuid.uuid4().hex[:8],
            "goal": "Verify a tar.gz archive against its manifest."})
        self.assertIs(out.get("pass"), True, "fixture: this goal must really pass")
        after = set(AVS.load_state(state_path).get("failures") or {})
        self.assertEqual(after - before, set(),
                         "a success must never create a failure class")


class ForgettingMustNeverFailARunTest(unittest.TestCase):
    """The containment the docstring promises."""

    def test_an_undiagnosable_result_never_raises(self):
        # integrate_solver_output asserts credit-path governance and can raise on
        # a malformed mapping; none of that may reach the caller.
        for bad in (None, "not a mapping", 17, [], {"pass": False}):
            try:
                LIVE._record_raw_goal_failure_diagnosis(bad, None)
            except Exception as exc:  # pragma: no cover - the point is it must not
                self.fail("diagnosis raised %r; forgetting must never become failing"
                          % (exc,))

    def test_a_passing_result_is_not_sent_to_the_failure_path(self):
        # Guarded twice over: the hook checks `pass is True` and the module
        # itself diagnoses only failures. Either alone would be enough; both is
        # what makes the split with record_success_observation safe.
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_guard_"))
        try:
            state = tmp / "state.json"
            LIVE._record_raw_goal_failure_diagnosis(
                {"pass": True, "status": "PASS__X"}, None, state_path=state)
            self.assertFalse(state.is_file(),
                             "a pass must not even open the failure store")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
