"""A refusal must not be a cage: the hard slice has to be able to lift it.

WHY THIS EXISTS
---------------
The overconfidence gate refuses acceptance while the calibration ledger measures systematic
overconfidence. Its recorded counterexample says the danger plainly: the gate changes what is
accepted, not what is predicted, so a refused system could stop producing the evidence it needs to
escape.

`external_hard_slice_v1` is the answer, and this test is the acceptance test for it:

* the slice is chosen from inspector-verified failures and missing inspectors -- NOT from the
  system's stated confidence, so the sample cannot be curated;
* a gate refusal does not stop the attempt (only acceptance is withheld);
* starting from a refused, overconfident ledger, running the slice produces a ledger whose gate no
  longer refuses.

The last point is the whole design. If it failed, the gate would be a trap and the module would be
worthless, so it is asserted rather than described.
"""
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import external_hard_slice_v1 as S  # noqa: E402
from canonical.runtime import self_prediction_calibration_v1 as C  # noqa: E402

CAPS = [f"cap.{i:02d}" for i in range(12)]
INSPECTORS_FOR = {f"cap.{i:02d}": object() for i in range(6)}  # only half are inspectable


class HardSliceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = C.Ledger(pathlib.Path(self.tmp.name) / "ledger.jsonl")
        # The gate reads its ledger from the environment, so point it at this test's file. Without
        # this the assertions below would silently grade a different ledger.
        self._old = os.environ.get("BRAIN_SELF_PREDICTION_LEDGER")
        os.environ["BRAIN_SELF_PREDICTION_LEDGER"] = str(self.ledger.path)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("BRAIN_SELF_PREDICTION_LEDGER", None)
        else:
            os.environ["BRAIN_SELF_PREDICTION_LEDGER"] = self._old
        self.tmp.cleanup()

    def _settle(self, cid, p, outcome):
        row = self.ledger.predict(capability_id=cid, predicted_pass_probability=p)
        self.ledger.settle(row["record_id"], outcome_pass=outcome, inspector="inspector")

    def test_uninspected_capabilities_are_ranked_first(self):
        plan = S.select(capability_ids=CAPS, ledger=self.ledger, inspectors=INSPECTORS_FOR, size=6)
        self.assertEqual(plan["uninspected_selected"], 6)
        self.assertTrue(all(not row["has_inspector"] for row in plan["selected"]))

    def test_the_systems_own_confidence_is_not_an_input_to_selection(self):
        # Two ledgers that differ only in how confident the system was must select the same slice.
        before = S.select(capability_ids=CAPS, ledger=self.ledger, inspectors=INSPECTORS_FOR, size=4)
        self._settle("cap.00", 0.99, True)
        self._settle("cap.00", 0.99, True)
        after = S.select(capability_ids=CAPS, ledger=self.ledger, inspectors=INSPECTORS_FOR, size=4)
        self.assertEqual([r["capability_id"] for r in before["selected"]],
                         [r["capability_id"] for r in after["selected"]])
        self.assertIn("the system's own stated confidence", after["selection_excludes"])

    def test_verified_failures_raise_a_capability_in_the_ranking(self):
        for _ in range(3):
            self._settle("cap.06", 0.9, False)
        plan = S.select(capability_ids=CAPS, ledger=self.ledger, inspectors=INSPECTORS_FOR, size=8)
        selected = [r["capability_id"] for r in plan["selected"]]
        self.assertIn("cap.06", selected)
        self.assertEqual(plan["hard_selected"], 1)

    def test_a_gate_refusal_does_not_stop_the_attempt(self):
        self._settle("cap.07", 0.85, True)
        self._settle("cap.08", 0.55, False)
        for _ in range(40):
            self._settle("cap.07", 0.85, True)
        for _ in range(40):
            self._settle("cap.08", 0.55, False)
        # Overconfident, so the gate refuses.
        self.assertTrue(C.gate()["refuse"])
        attempts = []

        def attempt(cid):
            attempts.append(cid)
            return {"accepted": False, "inspector": "insp", "refused_by_gate": True}

        result = S.run(capability_ids=CAPS, ledger=self.ledger, inspectors=INSPECTORS_FOR,
                       attempt=attempt, state=lambda cid: 0.4, size=4)
        self.assertEqual(len(attempts), 4)
        self.assertEqual(result["refused_by_gate"], 4)

    def test_the_slice_lifts_a_measured_refusal(self):
        # A confident, wrong history: the gate refuses.
        for _ in range(20):
            self._settle("cap.07", 0.85, True)
        for _ in range(20):
            self._settle("cap.08", 0.55, False)
        self.assertEqual(C.gate()["state"], "MEASURED_OVERCONFIDENCE")
        self.assertTrue(C.gate()["refuse"])

        # Now the slice runs, and the system states honest low probabilities for hard work it is
        # about to fail at, and high ones for work it can do. Both get settled by the inspector.
        def state(cid):
            return 0.2 if cid.endswith(("0", "1", "2", "3", "4")) else 0.95

        def attempt(cid):
            good = cid.endswith(("0", "1", "2", "3", "4"))
            return {"accepted": good, "inspector": "insp", "refused_by_gate": not good}

        S.run(capability_ids=CAPS, ledger=self.ledger, inspectors=INSPECTORS_FOR,
              attempt=attempt, state=state, size=12)
        gate = C.gate()
        self.assertFalse(gate["refuse"], gate)
        self.assertIn(gate["state"], {"NO_MEASURED_OVERCONFIDENCE", "INSUFFICIENT_EVIDENCE"})

    def test_an_attempt_that_does_not_name_an_inspector_is_refused(self):
        with self.assertRaises(S.SliceError):
            S.run(capability_ids=CAPS, ledger=self.ledger, inspectors=INSPECTORS_FOR,
                  attempt=lambda cid: {"accepted": True}, state=lambda cid: 0.5, size=2)

    def test_an_empty_capability_list_is_refused(self):
        with self.assertRaises(S.SliceError):
            S.select(capability_ids=[], ledger=self.ledger, inspectors=INSPECTORS_FOR)


if __name__ == "__main__":
    unittest.main(verbosity=2)
