"""The replay-safety gate must be able to see the shipping path's evidence.

WHY THIS EXISTS.

`_effect_may_have_occurred` answers one question: could this run have changed
something on disk? A caller turns the answer directly into a decision --
`autonomous_replay_authorized = not _effect_may_have_occurred(out)` -- and
another uses it to block a reuse fallback. It is a safety gate, so the only
acceptable behaviour under uncertainty is the conservative one.

It failed open on the shipping path. The old body looked for
`effect_outcome_sha256` inside `out["trace"]` and nowhere else. Measured over
all 23 benchmark goals driven through `run_raw_goal`:

  * `out["trace"]` is not a list in a single one -- the front door nests its
    trace under `controller_execution`;
  * `effect_outcome_sha256` never appears at all;
  * so the gate returned False for all 23, including the six that verifiably
    wrote files.

The evidence was present the whole time, under `output_sha256`, and it is
precise: present for the archive, source-audit-JSON, markdown-to-decision,
xlsx-create, ast-audit and decision-verify goals, absent for every read-only
one. After the fix the gate agrees with "did this run write a file" on 23 of 23.

WHAT IS PINNED HERE.

1. A REAL front-door run that wrote a file is caught. A real one that did not is
   not. Both, driven through `run_raw_goal`, not through a hand-built dict.
2. THE DECISION, NOT JUST THE PREDICATE. A failure carrying effect evidence must
   come out of `integrate_solver_output` with `autonomous_replay_authorized`
   NOT True. A failure without evidence must still be authorized -- the gate has
   to discriminate, or it is not a gate, it is a refusal.
3. The original shape still works. This widens what is caught; it must not
   narrow it.
4. No false positives from strings, empties, or absurd nesting.
5. The blind spot itself, restated as data: a result with `output_sha256` and no
   top-level `trace` is exactly what the shipping path produces, and exactly
   what the old body returned False for.

The one composed fixture is marked as such: no benchmark goal both writes a file
and fails, so the "wrote then failed" case takes a real writing result and marks
it failed. Every other fixture here is a real front-door result or a real
`integrate_solver_output` call.
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


class RealFrontDoorResultsTest(unittest.TestCase):
    """Drive the real door; assert the gate against what the run really did."""

    @classmethod
    def setUpClass(cls):
        cls.writing = LIVE.run_raw_goal({
            "task_id": "GATE_WRITE_" + uuid.uuid4().hex[:8],
            "goal": "Create a tar.gz archive from a manifest and verify it."})
        cls.readonly = LIVE.run_raw_goal({
            "task_id": "GATE_READ_" + uuid.uuid4().hex[:8],
            "goal": "Extract the text content from a PDF file."})

    @staticmethod
    def _wrote(result):
        """Ground truth, computed independently of the function under test."""
        def walk(node):
            if isinstance(node, dict):
                if node.get("output_sha256"):
                    return True
                return any(walk(v) for v in node.values())
            if isinstance(node, list):
                return any(walk(v) for v in node)
            return False
        return walk(result)

    def test_the_fixtures_are_what_the_rest_of_the_file_assumes(self):
        self.assertIs(self.writing.get("pass"), True,
                      "fixture: the archive goal must really pass on this box")
        self.assertTrue(self._wrote(self.writing),
                        "fixture: the archive goal must really have produced a file")
        self.assertFalse(self._wrote(self.readonly),
                         "fixture: pdf text extraction must really be read-only")

    def test_a_real_run_that_wrote_a_file_is_caught(self):
        """THE DEFECT. The old body returned False for this exact result."""
        self.assertTrue(
            AVS._effect_may_have_occurred(self.writing),
            "a front-door run that produced an artifact must not be waved through "
            "as safe to replay")

    def test_a_real_read_only_run_is_not_flagged(self):
        """The gate must discriminate, or it is a refusal rather than a gate."""
        self.assertFalse(AVS._effect_may_have_occurred(self.readonly))

    def test_the_shipping_path_produces_no_top_level_trace(self):
        """Restating the blind spot as data, so it cannot silently come back."""
        self.assertNotIsInstance(self.writing.get("trace"), list,
                                 "if the front door ever grows a top-level trace, "
                                 "this test should be revisited, not deleted")
        self.assertNotIn("effect_outcome_sha256", json.dumps(self.writing, default=str),
                         "the key the old gate looked for is not one the front "
                         "door emits; if that changes, revisit rather than delete")
        self.assertIn("output_sha256", json.dumps(self.writing, default=str),
                      "the evidence the front door does emit must still be there")


class ReplayDecisionTest(unittest.TestCase):
    """The decision a caller actually makes, through the real write path.

    Runs its own real goal in setUpClass rather than borrowing another class's
    fixture: unittest orders classes alphabetically, so a borrowed attribute
    would make this file pass or fail depending on a name.
    """

    @classmethod
    def setUpClass(cls):
        cls.real_writing = LIVE.run_raw_goal({
            "task_id": "GATE_DECISION_" + uuid.uuid4().hex[:8],
            "goal": "Create a tar.gz archive from a manifest and verify it."})

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="brain_gate_"))
        self.state = self.tmp / "state.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _authorized(self, failure_out):
        AVS.integrate_solver_output(
            failure_out, state_path=self.state,
            retry_context={"goal": "g", "attempt": 2})
        table = json.loads(self.state.read_text())["failures"]
        capsules = [c for e in table.values()
                    for c in (e.get("retry_capsules") or {}).values()]
        self.assertTrue(capsules, "fixture: a retry capsule must have been stored")
        return capsules[-1].get("autonomous_replay_authorized")

    def test_a_failure_that_wrote_something_is_not_authorized_to_replay(self):
        # Composed, and labelled: no benchmark goal both writes a file and fails,
        # so this takes a real writing result and marks it failed. The shape is
        # the front door's own; only `pass` and `status` are changed.
        self.assertIs(self.real_writing.get("pass"), True,
                      "fixture: the archive goal must really pass")
        wrote_then_failed = dict(self.real_writing)
        wrote_then_failed["pass"] = False
        wrote_then_failed["status"] = "FAIL__LIVE_CONTROLLER_EXECUTION"
        self.assertTrue(AVS._effect_may_have_occurred(wrote_then_failed),
                        "fixture: this failure must still carry effect evidence")
        self.assertIsNot(
            self._authorized(wrote_then_failed), True,
            "a failure whose run already produced an artifact must never be "
            "authorized for autonomous replay")

    def test_a_failure_that_wrote_nothing_is_still_authorized(self):
        """Symmetry: the gate must not become a blanket refusal."""
        clean_failure = {
            "pass": False,
            "status": "FAIL__LIVE_CONTROLLER_EXECUTION",
            "reason": "Blocker:BOUND_SYSTEM_TOOL_MISSING:qrencode",
        }
        self.assertFalse(AVS._effect_may_have_occurred(clean_failure))
        self.assertIs(self._authorized(clean_failure), True,
                      "a failure with no effect evidence is still safe to replay")


class BackwardCompatibilityTest(unittest.TestCase):
    """Widening what is caught must not narrow it."""

    def test_the_original_shape_is_still_caught(self):
        legacy = {"trace": [{"effect_outcome_sha256": "a" * 64}]}
        self.assertTrue(AVS._effect_may_have_occurred(legacy))

    def test_the_original_shape_without_evidence_is_still_clear(self):
        self.assertFalse(AVS._effect_may_have_occurred(
            {"trace": [{"step": 1}, {"step": 2}]}))

    def test_both_evidence_keys_are_honoured(self):
        for key in AVS.EFFECT_EVIDENCE_KEYS:
            self.assertTrue(AVS._effect_may_have_occurred({key: "b" * 64}),
                            "%s must count as evidence" % key)


class NoFalsePositivesTest(unittest.TestCase):
    def test_empty_and_absent_results_are_clear(self):
        for value in ({}, [], None, "", 0, False, "output_sha256"):
            self.assertFalse(AVS._effect_may_have_occurred(value),
                             "%r must not read as evidence" % (value,))

    def test_an_empty_evidence_key_is_not_evidence(self):
        self.assertFalse(AVS._effect_may_have_occurred({"output_sha256": ""}))
        self.assertFalse(AVS._effect_may_have_occurred({"output_sha256": None}))

    def test_a_string_is_not_walked_as_a_sequence(self):
        self.assertFalse(AVS._effect_may_have_occurred({"reason": "output_sha256"}))

    def test_absurd_nesting_does_not_hang_or_raise(self):
        node = {"output_sha256": "c" * 64}
        for _ in range(200):
            node = {"nested": node}
        try:
            result = AVS._effect_may_have_occurred(node)
        except RecursionError as exc:  # pragma: no cover - the bound must prevent it
            self.fail("the depth bound did not hold: %r" % (exc,))
        self.assertIsInstance(result, bool)


if __name__ == "__main__":
    unittest.main()
