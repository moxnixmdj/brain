"""A failure record must name the thing that failed, without lying about it.

WHY THIS EXISTS.

The shipping path records its failures (see
`test_raw_goal_failure_diagnosis_v1`), but the record carried a status, a reason
and a fingerprint and no subject. Measured over the failing benchmark goals: the
stored record for EXT_OCR_SCANNED_IMAGE did not contain the string
`image.extract.ocr.tesseract` anywhere. Eight failure classes, none of them
saying which capability broke.

That is not a cosmetic gap. The fingerprint is computed over the record's core,
so two failures with the same status and the same reason share one class no
matter how different their causes are. Measured on the 23-goal benchmark:
`EXT_SQLITE_VERIFY`, which fails inside
`sqlite.table.verify_against_json_records`, and
`BENCH_SQLITE_CREATE_INSERT_QUERY`, which fails before any capability is bound,
both report the bare reason `RuntimeError` and collapsed into a single class --
one recurring failure, counted together, for two different situations. Naming
the capability that IS known separates them, and the class count goes 8 -> 9.

WHAT IS PINNED HERE.

1. A real front-door failure's record names the real capability that failed.
2. THE REFUSAL TO LIE. `falsified_capability_ids` must stay empty. In this
   codebase that field is not "this failed" -- `_complete_route_failure` in the
   solver family returns True only when the proposal search was complete over
   the declared finite domain, and the solver files a capability under
   `falsified` on that proof and under `deferred` otherwise. The front door
   searches nothing, so it cannot claim exhaustion, and a later retry would act
   on the claim. Every counterexample row here therefore asserts
   `route_falsified_for_current_contract: False`.
3. The split is real: two capabilities, same reason, two classes.
4. A failure with no bound capability names none. Two of the eleven fail before
   a capability is bound and inventing one would be worse than silence.
5. The caller's result is returned byte for byte; the counterexample is attached
   only to what the learning layer sees.
6. Repeat counting survives: one recurring failure is still one class counted
   twice, not two classes.

Nothing here mocks the thing under test: the goals go through `run_raw_goal`,
the records are read out of the real `integrate_solver_output` store by their
own fingerprint, and the negative control is removing the wiring.
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


def _record_for(state_path, out):
    """Read the exact row integrate_solver_output writes for this result."""
    enriched = dict(out)
    rows = LIVE._failure_counterexample(out)
    if rows:
        enriched["counterexamples"] = rows
    fid = AVS._diagnose_failure(enriched)["failure_fingerprint"]
    table = json.loads(pathlib.Path(state_path).read_text())["failures"]
    return table[fid]


class NamedCapabilityTest(unittest.TestCase):
    """Run the real door on goals that really fail; read the real records."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_named_"))
        cls.state = cls.tmp / "state.json"
        cls.goals = {
            "ocr": "Extract text from a scanned image with OCR.",
            "sqlite_create": "Create a sqlite table with a schema, then insert "
                             "records, then query the records back.",
            "sqlite_verify": "Verify a sqlite table against JSON records.",
        }
        cls.results = {}
        for key, goal in cls.goals.items():
            out = LIVE.run_raw_goal({
                "task_id": "NAMED_%s_%s" % (key, uuid.uuid4().hex[:8]),
                "goal": goal})
            cls.results[key] = out
            LIVE._record_raw_goal_failure_diagnosis(out, None, state_path=cls.state)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_fixtures_really_failed(self):
        for key, out in self.results.items():
            self.assertIs(out.get("pass"), False, "%s must really fail" % key)

    def test_the_record_names_the_capability_that_failed(self):
        """THE GAP. This record used to have no subject at all."""
        record = _record_for(self.state, self.results["ocr"])
        names = [str(c.get("capability_id") or "")
                 for c in (record.get("counterexamples") or [])]
        self.assertIn("image.extract.ocr.tesseract", names,
                      "a failure record must say which capability broke")

    def test_the_reason_is_the_unwrapped_code_not_the_envelope(self):
        record = _record_for(self.state, self.results["ocr"])
        reason = str((record.get("counterexamples") or [{}])[0].get("reason") or "")
        self.assertEqual(reason, "BOUND_CAPABILITY_SOURCE_UNSUPPORTED")
        self.assertNotIn("Blocker:", reason,
                         "the envelope must not leak into the recorded reason")

    def test_the_record_does_not_claim_the_route_is_dead(self):
        """THE REFUSAL TO LIE. The front door searched nothing, so it proved nothing."""
        for key, out in self.results.items():
            record = _record_for(self.state, out)
            for row in (record.get("counterexamples") or []):
                self.assertIs(
                    row.get("route_falsified_for_current_contract"), False,
                    "%s: only an exhaustive search may falsify a route" % key)
            self.assertEqual(
                list(record.get("falsified_capability_ids") or []), [],
                "%s: falsified_capability_ids means PROOF OF EXHAUSTION and a "
                "single front-door attempt is not one" % key)

    def test_a_named_failure_does_not_share_a_class_with_an_unnamed_one(self):
        """The measured split, stated exactly as it happens.

        Both of these fail with the same status and the same bare `RuntimeError`,
        so before this change they produced ONE fingerprint and were counted as
        a single recurring failure. They are not the same failure: one is
        `sqlite.table.verify_against_json_records` and the other never bound a
        capability at all. Naming the one that is known separates them, which is
        what takes the class count from 8 to 9 on the 23-goal benchmark.

        Note what this does NOT claim. It is not "two named capabilities were
        merged" -- measured, `BENCH_SQLITE_CREATE_INSERT_QUERY` fails with
        `compiled_capability_id` empty, so it correctly names nothing. The split
        comes from distinguishing a failure with a known subject from one
        without.
        """
        create = _record_for(self.state, self.results["sqlite_create"])
        verify = _record_for(self.state, self.results["sqlite_verify"])
        self.assertEqual(list(create.get("counterexamples") or []), [],
                         "this goal binds no capability, so it must name none")
        self.assertEqual(
            [c["capability_id"] for c in verify["counterexamples"]],
            ["sqlite.table.verify_against_json_records"])
        self.assertNotEqual(
            create["failure_fingerprint"], verify["failure_fingerprint"],
            "a failure with a known subject must not share a class with one "
            "that has none, however alike their status and reason look")


class TruthfulAbsenceTest(unittest.TestCase):
    """A failure with no bound capability must not invent one."""

    def test_a_result_with_no_capability_records_no_counterexample(self):
        out = {"pass": False, "status": "FAIL__NO_CAPABILITY",
               "reason": "Blocker:GOAL_COMPILATION_FAILED"}
        self.assertEqual(LIVE._failure_counterexample(out), [])

    def test_a_blank_capability_id_is_treated_as_absent(self):
        for value in ("", "   ", None):
            self.assertEqual(
                LIVE._failure_counterexample(
                    {"pass": False, "compiled_capability_id": value}), [],
                "%r must not become a capability name" % (value,))


class CallerResultUntouchedTest(unittest.TestCase):
    """run_raw_goal promises its result byte for byte."""

    def test_recording_does_not_mutate_the_result(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_nomut_"))
        try:
            out = LIVE.run_raw_goal({
                "task_id": "NOMUT_" + uuid.uuid4().hex[:8],
                "goal": "Extract text from a scanned image with OCR."})
            self.assertIs(out.get("pass"), False)
            before = json.dumps(out, sort_keys=True, default=str)
            LIVE._record_raw_goal_failure_diagnosis(
                out, None, state_path=tmp / "s.json")
            self.assertEqual(json.dumps(out, sort_keys=True, default=str), before,
                             "the counterexample belongs to the learning layer's "
                             "copy, not to the caller's result")
            self.assertNotIn("counterexamples", out)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class RepeatCountingStillWorksTest(unittest.TestCase):
    """Naming the capability must not turn one recurring failure into many."""

    def test_the_same_failure_twice_is_one_class_counted_twice(self):
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_repeat_"))
        try:
            state = tmp / "s.json"
            goal = "Extract text from a scanned image with OCR."
            for i in range(2):
                out = LIVE.run_raw_goal({
                    "task_id": "REPEAT%d_%s" % (i, uuid.uuid4().hex[:8]),
                    "goal": goal})
                self.assertIs(out.get("pass"), False)
                LIVE._record_raw_goal_failure_diagnosis(out, None, state_path=state)
            table = json.loads(state.read_text())["failures"]
            self.assertEqual(len(table), 1,
                             "one recurring failure must stay ONE class")
            self.assertEqual(int(next(iter(table.values()))["count"]), 2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class WiringTest(unittest.TestCase):
    """The counterexample must reach the store through run_raw_goal itself.

    Looked up by fingerprint rather than by "is this key new": the real store
    persists across runs, so a recurring failure updates an existing class and
    a test that only looks for new keys would pass or fail depending on whether
    the machine had seen this goal before.
    """

    def test_a_live_failure_lands_in_the_store_naming_its_capability(self):
        goal = "Extract text from a scanned image with OCR."
        # The store persists across runs, so a leftover record at this
        # fingerprint would let a test that merely checks "does the record name
        # the capability" pass on stale bytes even with the wiring removed --
        # measured, it did exactly that. So the assertion is that THIS run moved
        # the count: only a run that actually wrote this class can do that.
        path = pathlib.Path(AVS.DEFAULT_STATE_PATH)

        def probe_count():
            out = LIVE.run_raw_goal({
                "task_id": "NAMEDPROBE_" + uuid.uuid4().hex[:8], "goal": goal})
            self.assertIs(out.get("pass"), False)
            table = json.loads(path.read_text())["failures"] \
                if path.is_file() else {}
            enriched = dict(out)
            rows = LIVE._failure_counterexample(out)
            if rows:
                enriched["counterexamples"] = rows
            fid = AVS._diagnose_failure(enriched)["failure_fingerprint"]
            return int((table.get(fid) or {}).get("count") or 0), out

        first, _ = probe_count()
        second, out = probe_count()
        self.assertEqual(second, first + 1,
                         "the shipping path did not write the failure class that "
                         "names its capability, so the counterexample is not "
                         "reaching integrate_solver_output")
        record = _record_for(AVS.DEFAULT_STATE_PATH, out)
        names = [str(c.get("capability_id") or "")
                 for c in (record.get("counterexamples") or [])]
        self.assertIn("image.extract.ocr.tesseract", names,
                      "the shipping path must name the capability that failed")


if __name__ == "__main__":
    unittest.main()
