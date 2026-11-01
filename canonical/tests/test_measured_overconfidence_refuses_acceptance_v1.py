"""A measured overconfidence must refuse acceptance, and must stop refusing when the evidence changes.

WHY THIS EXISTS
---------------
Yesterday's change made self-prediction *scorable*. A score that is recorded and never obeyed is a
dashboard, not a self-model, so this test binds the score to a consequence:

* an overconfident ledger refuses acceptance with a named status;
* the same ledger, after honest attempts are settled, stops refusing -- so the refusal is a function
  of evidence and not a flag somebody can turn off;
* a thin or unreadable ledger does not refuse, but the gate's state is still reported, because a
  silent pass is indistinguishable from a gate that never ran.

The last property is the one that keeps this from becoming decoration in the other direction: the
gate must be visible whether or not it bites.
"""
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import raw_goal_trace_acceptance_v1 as R  # noqa: E402
from canonical.runtime import self_prediction_calibration_v1 as C  # noqa: E402


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger_path = pathlib.Path(self.tmp.name) / "ledger.jsonl"
        self._old = os.environ.get("BRAIN_SELF_PREDICTION_LEDGER")
        os.environ["BRAIN_SELF_PREDICTION_LEDGER"] = str(self.ledger_path)
        self.ledger = C.Ledger(self.ledger_path)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("BRAIN_SELF_PREDICTION_LEDGER", None)
        else:
            os.environ["BRAIN_SELF_PREDICTION_LEDGER"] = self._old
        self.tmp.cleanup()

    def _settle(self, pairs):
        for p, outcome in pairs:
            row = self.ledger.predict(capability_id="chart.raster.scene_graph.v1",
                                      predicted_pass_probability=p)
            self.ledger.settle(row["record_id"], outcome_pass=outcome, inspector="inspector")

    def test_an_overconfident_ledger_refuses_acceptance(self):
        # It separates outcomes (0.85 on passes, 0.55 on fails) and beats the base rate, so the
        # ONLY clause that can fire is overconfidence: it claims 0.70 while delivering 0.50.
        self._settle([(0.85, True)] * 20 + [(0.55, False)] * 20)
        g = C.gate()
        self.assertEqual(g["state"], "MEASURED_OVERCONFIDENCE", g)
        self.assertTrue(g["refuse"])
        refusal = R.verify(goal="", compiled_plan=None, execution=None,
                           raw_contract={}, root=pathlib.Path(self.tmp.name))
        self.assertEqual(refusal["status"], "RAW_GOAL_ACCEPTANCE_UNRESOLVED")
        self.assertEqual(refusal["reason"], "REFUSED__MEASURED_OVERCONFIDENCE")
        self.assertEqual(refusal["self_prediction_gate"]["state"], "MEASURED_OVERCONFIDENCE")

    def test_the_refusal_lifts_when_the_evidence_changes(self):
        self._settle([(0.85, True)] * 20 + [(0.55, False)] * 20)
        self.assertTrue(C.gate()["refuse"])
        # The same system, now predicting honestly and being right about it.
        self._settle([(0.95, True)] * 40 + [(0.05, False)] * 60)
        g = C.gate()
        self.assertFalse(g["refuse"], g)
        self.assertEqual(g["state"], "NO_MEASURED_OVERCONFIDENCE")

    def test_an_empty_ledger_does_not_refuse_but_reports_itself(self):
        g = C.gate()
        self.assertFalse(g["refuse"])
        self.assertEqual(g["state"], "INSUFFICIENT_EVIDENCE")

    def test_a_thin_ledger_does_not_refuse(self):
        self._settle([(0.99, False)] * 3)
        g = C.gate()
        self.assertFalse(g["refuse"])
        self.assertEqual(g["state"], "INSUFFICIENT_EVIDENCE")

    def test_a_broken_ledger_does_not_brick_acceptance_but_says_so(self):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text("{not json at all\n", encoding="utf-8")
        g = C.gate()
        self.assertFalse(g["refuse"])
        self.assertIn(g["state"], {"INSUFFICIENT_EVIDENCE", "NO_MEASURED_OVERCONFIDENCE"})

    def test_the_acceptance_path_consults_the_same_gate(self):
        self._settle([(0.85, True)] * 20 + [(0.55, False)] * 20)
        self.assertEqual(R._self_prediction_gate()["state"], "MEASURED_OVERCONFIDENCE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
