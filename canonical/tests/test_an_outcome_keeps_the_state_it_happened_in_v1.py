"""An outcome without its state cannot teach WHERE a plan applies.

THE MEASURED DEFECT
-------------------
`what_a_success_teaches_20261112.py`, run on this tree, reports:

    one success                      -> 0 / 200 hidden requirements identified
    chosen contrasts (with failures) -> 25 / 25, mean 2.76 demonstrations

`macro_v1.record` and `macro_v1.note_failure` both accept the state an outcome
happened in, and `applicability_v1` can identify a requirement from it. But the
live front door and the confined-trajectory controller called them WITHOUT it,
and `record(context=None)` writes no evidence row at all. The live store held
3 successes and 0 failures with no states, so the boundary learner could never
leave `UNDETERMINED`: the machinery for the 25/25 regime was present and the
live loop fed it the 0/200 regime.

These tests pin the repair at the seam that lost the information, not at the
learner that was already correct.

Producer-run regression tests. Authority NONE. No capability credit.
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from canonical.runtime import applicability_v1 as app
from canonical.runtime import macro_v1 as MC
from canonical.runtime.memory_policy_v1 import READ_ONLY, memory_policy_scope
from canonical.swe_kernel.forged_binding_and_macro_spine_v1 import (
    record_verified_chain_macro,
    verified_chain_learning_receipt,
)

ROOT = pathlib.Path(__file__).resolve().parents[2]
CLAUSES = ["audit the python source pkg", "verify the archive out.tar.gz"]
STEPS = [{"capability_id": "a", "verified": True}, {"capability_id": "b", "verified": True}]


class OutcomeStateSeamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="brain-outcome-state-")
        self.state = pathlib.Path(self.tmp.name) / "macros.json"
        self._orig = MC.STATE
        MC.STATE = self.state

    def tearDown(self) -> None:
        MC.STATE = self._orig
        self.tmp.cleanup()

    def _rows(self) -> list:
        if not self.state.exists():
            return []
        doc = json.loads(self.state.read_text(encoding="utf-8"))
        entry = (doc.get("macros") or {}).get(MC.signature(CLAUSES)) or {}
        return entry.get("evidence") or []

    def test_the_wrapper_retains_the_state_it_is_given(self) -> None:
        ok = record_verified_chain_macro(
            CLAUSES, STEPS, state_path=self.state, context={"source.available", "manifest.available"},
        )
        self.assertTrue(ok)
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["ok"])
        self.assertEqual(rows[0]["facts"], ["manifest.available", "source.available"])

    def test_omitting_the_state_keeps_the_previous_behaviour(self) -> None:
        """The change is additive: no caller is forced to supply a context."""
        self.assertTrue(record_verified_chain_macro(CLAUSES, STEPS, state_path=self.state))
        self.assertEqual(self._rows(), [])

    def test_one_success_is_not_reported_as_an_identified_scope(self) -> None:
        """The overclaim this refuses: 'it did it once, so it knows it everywhere'."""
        record_verified_chain_macro(
            CLAUSES, STEPS, state_path=self.state, context={"source.available"},
        )
        receipt = verified_chain_learning_receipt(
            CLAUSES, state_path=self.state, context={"source.available"},
        )
        boundary = receipt["applicability"]
        self.assertNotEqual(boundary["status"], app.IDENTIFIED)
        self.assertIsNone(boundary["required"])
        self.assertEqual(boundary["failures"], 0)
        self.assertEqual(boundary["reason"], "NO_FAILURE__NECESSITY_IS_ONLY_REFUTED_BY_FAILURE")

    def test_repeating_a_success_in_the_same_state_teaches_nothing(self) -> None:
        for _ in range(5):
            record_verified_chain_macro(
                CLAUSES, STEPS, state_path=self.state, context={"source.available"},
            )
        receipt = verified_chain_learning_receipt(
            CLAUSES, state_path=self.state, context={"source.available"},
        )
        self.assertEqual(receipt["next_contrast"]["guaranteed_elimination"], 0)
        self.assertNotEqual(receipt["applicability"]["status"], app.IDENTIFIED)

    def test_chosen_contrasts_identify_what_repetition_cannot(self) -> None:
        """Success, a failure without the fact, then a success with only that fact."""
        record_verified_chain_macro(
            CLAUSES, STEPS, state_path=self.state, context={"keep", "other"},
        )
        MC.note_failure(MC.signature(CLAUSES), context={"other"})
        record_verified_chain_macro(
            CLAUSES, STEPS, state_path=self.state, context={"keep"},
        )
        boundary = MC.applicability(MC.signature(CLAUSES))
        self.assertEqual(boundary.status, app.IDENTIFIED, boundary.as_row())
        self.assertEqual(boundary.required, ("keep",))

    def test_a_failure_without_a_state_cannot_identify_anything(self) -> None:
        """The exact live defect: a bare failure counts, but teaches no scope."""
        record_verified_chain_macro(
            CLAUSES, STEPS, state_path=self.state, context={"keep", "other"},
        )
        MC.note_failure(MC.signature(CLAUSES))
        self.assertNotEqual(MC.applicability(MC.signature(CLAUSES)).status, app.IDENTIFIED)

    def test_read_only_memory_retains_no_evidence(self) -> None:
        with memory_policy_scope(READ_ONLY):
            ok = record_verified_chain_macro(
                CLAUSES, STEPS, state_path=self.state, context={"source.available"},
            )
        self.assertFalse(ok)
        self.assertFalse(self.state.exists())

    def test_the_learning_receipt_never_breaks_a_served_answer(self) -> None:
        receipt = verified_chain_learning_receipt([], state_path=self.state)
        self.assertEqual(receipt["schema"], "PROJECT_BRAIN_CHAIN_LEARNING_RECEIPT_V1")
        self.assertEqual(receipt["authority"], "NONE")


if __name__ == "__main__":
    unittest.main()
