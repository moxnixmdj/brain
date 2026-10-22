"""The front door must remember how this machine behaves, not only what it achieved.

WHY THIS EXISTS.

`_record_raw_goal_experience` returns unless ``out["pass"] is True``. That is
correct for the episode store -- an episode is something the machine ACHIEVED,
and a failure is not an achievement. But it meant the shipping path dropped
every failure on the floor, while `experience_v1`, whose entire subject is
failure, was written by `grounded_action_v1` alone.

Measured before the change: the pathology store held 37 cells, not one of them
from a front-door run, and the front door rediscovered the same dead routes
(pandoc absent, tesseract's source unsupported) on every single run. That is
verbatim the failure `experience_v1`'s own docstring says it exists to prevent:
"Ask the same thing twice and the machine started from nothing, reached for the
same tool that cannot work on this box, and failed the same way."

WHAT IS PINNED HERE.

1. A real front-door FAILURE lands in the store as a real pathology. This is the
   gap that was open; nothing else in this file matters if this one is hollow.
2. A real front-door SUCCESS lands too, so a capability that works here is
   credited rather than only ever suspected.
3. The reason code is unwrapped from the blocker envelope. Without that, every
   failure on this path files under one useless cell, ``<capability>|blocker``,
   and the machine cannot tell an absent binary from an unsupported source.
4. Structural evidence suppresses and statistical evidence does not -- the
   direction rule that keeps a run of bad luck from banning a capability.
5. THE DECISION NOT TO CONSULT. Selection must keep offering a capability this
   box cannot run, because refusing it faster is not doing it. This is the test
   that fails the day someone wires `is_suppressed` into the shipping path.

Nothing here is a mock of the thing under test: the goals go through
`run_raw_goal`, and the memory is the real `experience_v1` writing real bytes,
aimed at a scratch file only so the tracked store is left alone.
"""
from __future__ import annotations

import pathlib
import shutil
import tempfile
import unittest
import uuid

from canonical.runtime import experience_v1 as EXP
from canonical.runtime import live_integrated_brain_v1 as LIVE


def _store(path):
    return EXP.summary(path=path)["cells"]


class PathologyReasonCodeTest(unittest.TestCase):
    """The envelope is unwrapped, and the code is copied, never guessed."""

    def test_nested_action_expectation_envelope_yields_the_innermost_code(self):
        # Byte-for-byte the `reason` the front door produced for
        # EXT_OCR_SCANNED_IMAGE and EXT_MD_TO_PDF on a real run.
        ocr = (
            "Blocker:ACTION_EXPECTATION_FAILED:pass:OBSERVED=False:REASON="
            "Blocker:BOUND_CAPABILITY_SOURCE_UNSUPPORTED:brain_bound_system_tool:"
            'RESULT={"reason":"Blocker:BOUND_CAPABILITY_SOURCE_UNSUPPORTED"}'
        )
        self.assertEqual(
            LIVE._pathology_reason_code(ocr),
            "BOUND_CAPABILITY_SOURCE_UNSUPPORTED",
        )
        pdf = (
            "Blocker:ACTION_EXPECTATION_FAILED:pass:OBSERVED=False:REASON="
            "Blocker:BOUND_APT_METADATA_NOT_FOUND:pandoc:RESULT={"
            '"reason":"Blocker:BOUND_APT_METADATA_NOT_FOUND:pandoc"}'
        )
        self.assertEqual(
            LIVE._pathology_reason_code(pdf), "BOUND_APT_METADATA_NOT_FOUND"
        )

    def test_the_two_dead_routes_do_not_share_one_cell(self):
        """Absent binary and unsupported source are different machine facts."""
        self.assertNotEqual(
            LIVE._pathology_reason_code("Blocker:X:REASON=Blocker:A:1"),
            LIVE._pathology_reason_code("Blocker:X:REASON=Blocker:B:1"),
        )

    def test_a_bare_reason_is_used_as_it_is(self):
        self.assertEqual(LIVE._pathology_reason_code("SQLITE_STATUS_VALUE_UNRESOLVED"),
                         "SQLITE_STATUS_VALUE_UNRESOLVED")

    def test_an_absent_reason_still_names_a_cell(self):
        # A success carries no reason. observe() then keys on VERIFIED, so this
        # must never raise or return the empty string that would corrupt a key.
        self.assertEqual(LIVE._pathology_reason_code(None), "FAILED")
        self.assertEqual(LIVE._pathology_reason_code(""), "FAILED")


class FrontDoorPathologyTest(unittest.TestCase):
    """Run the real front door; assert the memory it leaves behind."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_pathology_"))
        cls.store = cls.tmp / "experience.json"
        cls.original_default = EXP.DEFAULT_STATE
        # ROOT / <absolute path> is that absolute path, so pointing the module's
        # own default at a scratch file is enough to redirect every write.
        EXP.DEFAULT_STATE = str(cls.store)
        EXP._STATE_CACHE.clear()

        cls.ocr_goal = "Extract text from a scanned image with OCR."
        cls.tar_goal = "Verify a tar.gz archive against its manifest."

        cls.ocr = LIVE.run_raw_goal(
            {"task_id": "PATH_OCR_" + uuid.uuid4().hex[:8], "goal": cls.ocr_goal}
        )
        cls.tar = LIVE.run_raw_goal(
            {"task_id": "PATH_TAR_" + uuid.uuid4().hex[:8], "goal": cls.tar_goal}
        )

    @classmethod
    def tearDownClass(cls):
        EXP.DEFAULT_STATE = cls.original_default
        EXP._STATE_CACHE.clear()
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_runs_behaved_as_expected_or_the_rest_is_meaningless(self):
        """Guard the fixture: one must fail and one must pass."""
        self.assertIs(self.ocr.get("pass"), False)
        self.assertIs(self.tar.get("pass"), True)

    def test_a_front_door_failure_is_recorded_as_a_pathology(self):
        """THE GAP THAT WAS OPEN. A failure used to vanish entirely."""
        cid = str(self.ocr.get("compiled_capability_id") or "")
        self.assertTrue(cid, "the fixture run must name a compiled capability")
        cell = EXP.cell_of(cid, "BOUND_CAPABILITY_SOURCE_UNSUPPORTED")
        entry = _store(self.store).get(cell)
        self.assertIsNotNone(
            entry,
            "the shipping path must remember how this box failed, not only that "
            "it failed: no cell %r" % cell,
        )
        self.assertLess(entry["mean"], 0.0, "a failure must record as a failure")

    def test_the_recorded_pathology_is_the_unwrapped_code_not_the_envelope(self):
        cid = str(self.ocr.get("compiled_capability_id") or "")
        keys = [k for k in _store(self.store) if k.startswith(cid.lower() + "|")]
        self.assertTrue(keys, "expected at least one cell for %s" % cid)
        for key in keys:
            self.assertNotIn("blocker", key,
                             "the envelope leaked into the cell address: %s" % key)

    def test_a_front_door_success_is_recorded_too(self):
        """Symmetry: a capability that works here must be credited, not just suspected."""
        cid = str(self.tar.get("compiled_capability_id") or "")
        self.assertTrue(cid)
        cell = EXP.cell_of(cid, "VERIFIED")
        entry = _store(self.store).get(cell)
        self.assertIsNotNone(entry, "a success must be remembered as well")
        self.assertGreater(entry["mean"], 0.0)

    def test_only_a_machine_fact_suppresses_a_capability(self):
        """Direction, not magnitude: bad luck must never ban a capability."""
        cid = str(self.ocr.get("compiled_capability_id") or "")
        self.assertTrue(
            EXP.is_suppressed(cid, "BOUND_CAPABILITY_SOURCE_UNSUPPORTED",
                              path=self.store),
            "an unsupported source is true of this box forever and may suppress",
        )
        # The same shape of evidence, non-structural: never suppresses, however
        # consistent. This is the rule the module's docstring calls the trap.
        EXP.record("probe.nonstructural.capability", "SOME_TRANSIENT_ERROR",
                   False, structural=False, path=self.store)
        for _ in range(12):
            EXP.record("probe.nonstructural.capability", "SOME_TRANSIENT_ERROR",
                       False, structural=False, path=self.store)
        self.assertFalse(
            EXP.is_suppressed("probe.nonstructural.capability", path=self.store),
            "a statistical run of failures is a fact about what was asked",
        )


class SelectionMustNotConsultMemoryTest(unittest.TestCase):
    """THE DELIBERATE NON-CONSULT. Measured, not assumed.

    `image.extract.ocr.tesseract` is the benchmark's own expected selection for
    EXT_OCR_SCANNED_IMAGE, and this box cannot run it. Consulting
    `is_suppressed` on the shipping path would therefore trade a CORRECT
    selection for a faster refusal: selection 22/23 becomes 21/23 and the
    machine gets worse at choosing while getting better at giving up.

    The memory is still worth writing -- `grounded_action_v1` reads the same
    file -- but the front door's job is to pick the right capability, and "I
    have failed at this before" is not evidence that it is the wrong one.
    """

    def test_a_suppressed_capability_is_still_selected_when_it_is_the_right_one(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_noconsult_"))
        try:
            store = tmp / "experience.json"
            EXP.record("image.extract.ocr.tesseract",
                       "BOUND_CAPABILITY_SOURCE_UNSUPPORTED", False,
                       structural=True, path=store)
            self.assertTrue(
                EXP.is_suppressed("image.extract.ocr.tesseract", path=store),
                "fixture: the capability must actually be suppressed for this "
                "test to mean anything",
            )
            # compile_against_live_registry returns (registry, admissible, compiled);
            # only the third element is the compilation.
            _registry, _admissible, compiled = LIVE.compile_against_live_registry(
                "Extract text from a scanned image with OCR."
            )
            cid = str(compiled.get("selected_capability") or "")
            if not cid:
                parts = compiled.get("compiled_parts") or []
                cid = str((parts[0] or {}).get("selected_capability") or "") if parts else ""
            self.assertEqual(
                cid, "image.extract.ocr.tesseract",
                "memory must not narrow what the front door is willing to choose",
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class ForgettingMustNeverFailARunTest(unittest.TestCase):
    """The containment the docstring promises: memory cannot break execution."""

    def test_an_unrecordable_result_is_returned_unchanged(self):
        for bad in (None, "not a mapping", 17, {"pass": True}):
            try:
                LIVE._record_raw_goal_pathology(bad, {"goal": "x"})
            except Exception as exc:  # pragma: no cover - the point is it must not
                self.fail("memory raised %r; forgetting must never become failing"
                          % (exc,))


if __name__ == "__main__":
    unittest.main()
