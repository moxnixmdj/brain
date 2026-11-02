"""The self-prediction ledger must be settled by the acceptance path, not by the producer.

WHY THIS EXISTS
---------------
`self_prediction_calibration_v1` is only worth anything if it is fed verdicts that come from
somewhere other than the party being scored. `raw_goal_trace_acceptance_v1` now settles a declared
`prediction_record_id` with the boolean its independent re-inspector returned.

This test checks the wiring end to end, including the case that matters most: a step with NO
registered inspector settles as a failure, so a system cannot keep its calibration clean by only
declaring predictions where it knows it will pass.
"""
import json
import os
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from canonical.runtime import raw_goal_trace_acceptance_v1 as R  # noqa: E402
from canonical.runtime import self_prediction_calibration_v1 as C  # noqa: E402


class SettlementTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger_path = pathlib.Path(self.tmp.name) / "ledger.jsonl"
        self._old = os.environ.get("BRAIN_SELF_PREDICTION_LEDGER")
        os.environ["BRAIN_SELF_PREDICTION_LEDGER"] = str(self.ledger_path)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("BRAIN_SELF_PREDICTION_LEDGER", None)
        else:
            os.environ["BRAIN_SELF_PREDICTION_LEDGER"] = self._old
        self.tmp.cleanup()

    def _predict(self, p):
        return C.Ledger().predict(capability_id="chart.raster.scene_graph.v1",
                                  predicted_pass_probability=p)

    def test_the_inspectors_verdict_settles_the_prediction(self):
        rec = self._predict(0.8)
        row = {"args": {"prediction_record_id": rec["record_id"]}, "result": {}}
        R._settle_declared_prediction(row, ok=True, inspector="_inspect_raster_scene_graph")
        settled = C.Ledger().settled_rows()
        self.assertEqual(len(settled), 1)
        self.assertTrue(settled[0]["outcome_pass"])
        self.assertEqual(settled[0]["inspector"], "_inspect_raster_scene_graph")

    def test_a_failed_reinspection_is_recorded_as_a_failure(self):
        rec = self._predict(0.9)
        row = {"args": {"prediction_record_id": rec["record_id"]}, "result": {}}
        R._settle_declared_prediction(row, ok=False, inspector="_inspect_raster_scene_graph")
        settled = C.Ledger().settled_rows()
        self.assertFalse(settled[0]["outcome_pass"])

    def test_no_registered_inspector_settles_as_a_failure(self):
        rec = self._predict(0.95)
        row = {"args": {"prediction_record_id": rec["record_id"]}, "result": {}}
        R._settle_declared_prediction(row, ok=False, inspector="NO_INDEPENDENT_REINSPECTION")
        self.assertFalse(C.Ledger().settled_rows()[0]["outcome_pass"])

    def test_a_step_without_a_declared_prediction_writes_nothing(self):
        R._settle_declared_prediction({"args": {}, "result": {}}, ok=True, inspector="x")
        self.assertEqual(C.Ledger().settled_rows(), [])

    def test_an_unusable_record_cannot_break_acceptance(self):
        row = {"args": {"prediction_record_id": "no_such_record"}, "result": {}}
        R._settle_declared_prediction(row, ok=True, inspector="x")  # must not raise
        self.assertEqual(C.Ledger().settled_rows(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
